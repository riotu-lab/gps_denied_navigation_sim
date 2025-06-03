#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64, Header
from std_srvs.srv import SetBool

import numpy as np
import math
import csv
import os
from scipy.spatial.transform import Rotation
from threading import Lock

class PathErrorCalculator(Node):
    def __init__(self):
        super().__init__('path_error_calculator')
        
        # Parameters
        self.declare_parameter("output_directory", "/home/user/shared_volume/error_analysis/")
        self.declare_parameter("file_name", "path_error_analysis")
        self.declare_parameter("max_time_diff", 0.1)  # Max time difference for pose association (seconds)
        self.declare_parameter("publish_rate", 10.0)  # Hz for error publishing
        
        self.output_dir = self.get_parameter('output_directory').get_parameter_value().string_value
        self.file_name = self.get_parameter('file_name').get_parameter_value().string_value
        self.max_time_diff = self.get_parameter('max_time_diff').get_parameter_value().double_value
        self.publish_rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        
        # Create output directory
        self.create_folder(self.output_dir)
        
        # Data storage
        self.gt_poses = []  # List of (timestamp, pose) tuples
        self.est_poses = []  # List of (timestamp, pose) tuples
        self.error_data = []  # List of error calculations
        self.data_lock = Lock()
        
        # Recording state
        self.recording_enabled = False
        self.csv_file = None
        self.csv_writer = None
        
        # Setup QoS for path topics
        path_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST
        )
        
        # Subscribers
        self.gt_path_sub = self.create_subscription(
            Path, '/target/gt_path', self.gt_path_callback, path_qos)
        self.est_path_sub = self.create_subscription(
            Path, '/mins/imu/path', self.est_path_callback, path_qos)
        
        # Publishers for real-time error metrics
        self.position_error_pub = self.create_publisher(Float64, '/path_error/position_error', 10)
        self.orientation_error_pub = self.create_publisher(Float64, '/path_error/orientation_error', 10)
        self.velocity_error_pub = self.create_publisher(Float64, '/path_error/velocity_error', 10)
        self.cumulative_error_pub = self.create_publisher(Float64, '/path_error/cumulative_error', 10)
        
        # Services
        self.start_service = self.create_service(SetBool, 'start_error_recording', self.start_recording_callback)
        self.stop_service = self.create_service(SetBool, 'stop_error_recording', self.stop_recording_callback)
        self.reset_service = self.create_service(SetBool, 'reset_error_data', self.reset_data_callback)
        
        # Timer for periodic error calculation and publishing
        self.timer = self.create_timer(1.0/self.publish_rate, self.calculate_and_publish_errors)
        
        self.get_logger().info(f"Path Error Calculator initialized")
        self.get_logger().info(f"Output directory: {self.output_dir}")
        self.get_logger().info(f"Max time difference for association: {self.max_time_diff}s")

    def create_folder(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

    def gt_path_callback(self, msg):
        """Callback for ground truth path messages"""
        with self.data_lock:
            # Extract the latest pose from the path
            if msg.poses:
                latest_pose = msg.poses[-1]
                timestamp = self.msg_to_timestamp(latest_pose.header)
                self.gt_poses.append((timestamp, latest_pose.pose))
                
                # Keep only recent poses (last 60 seconds for memory management)
                current_time = timestamp
                self.gt_poses = [(t, p) for t, p in self.gt_poses if current_time - t < 60.0]

    def est_path_callback(self, msg):
        """Callback for estimated path messages"""
        with self.data_lock:
            # Extract the latest pose from the path
            if msg.poses:
                latest_pose = msg.poses[-1]
                timestamp = self.msg_to_timestamp(latest_pose.header)
                self.est_poses.append((timestamp, latest_pose.pose))
                
                # Keep only recent poses (last 60 seconds for memory management)
                current_time = timestamp
                self.est_poses = [(t, p) for t, p in self.est_poses if current_time - t < 60.0]

    def msg_to_timestamp(self, header):
        """Convert ROS2 header to timestamp in seconds"""
        return header.stamp.sec + header.stamp.nanosec * 1e-9

    def find_closest_pose(self, target_time, pose_list):
        """Find the pose in pose_list closest in time to target_time"""
        if not pose_list:
            return None, float('inf')
        
        closest_pose = None
        min_time_diff = float('inf')
        
        for timestamp, pose in pose_list:
            time_diff = abs(timestamp - target_time)
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_pose = pose
        
        return closest_pose, min_time_diff

    def calculate_position_error(self, gt_pose, est_pose):
        """Calculate Euclidean distance between two poses"""
        gt_pos = gt_pose.position
        est_pos = est_pose.position
        
        dx = gt_pos.x - est_pos.x
        dy = gt_pos.y - est_pos.y
        dz = gt_pos.z - est_pos.z
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def calculate_orientation_error(self, gt_pose, est_pose):
        """Calculate angular difference between two orientations (in radians)"""
        # Convert quaternions to rotation matrices
        gt_quat = [gt_pose.orientation.x, gt_pose.orientation.y, 
                   gt_pose.orientation.z, gt_pose.orientation.w]
        est_quat = [est_pose.orientation.x, est_pose.orientation.y, 
                    est_pose.orientation.z, est_pose.orientation.w]
        
        # Calculate relative rotation
        gt_rot = Rotation.from_quat(gt_quat)
        est_rot = Rotation.from_quat(est_quat)
        
        # Calculate angular difference
        relative_rot = gt_rot.inv() * est_rot
        angle = relative_rot.magnitude()
        
        return angle

    def calculate_velocity_error(self, gt_poses, est_poses, current_time):
        """Estimate velocity error based on recent pose changes"""
        # Need at least 2 poses to calculate velocity
        gt_recent = [(t, p) for t, p in gt_poses if current_time - t < 0.5]
        est_recent = [(t, p) for t, p in est_poses if current_time - t < 0.5]
        
        if len(gt_recent) < 2 or len(est_recent) < 2:
            return 0.0
        
        # Calculate GT velocity
        gt_recent.sort()
        gt_dt = gt_recent[-1][0] - gt_recent[-2][0]
        if gt_dt < 1e-6:
            return 0.0
        
        gt_dx = gt_recent[-1][1].position.x - gt_recent[-2][1].position.x
        gt_dy = gt_recent[-1][1].position.y - gt_recent[-2][1].position.y
        gt_dz = gt_recent[-1][1].position.z - gt_recent[-2][1].position.z
        gt_vel = math.sqrt(gt_dx*gt_dx + gt_dy*gt_dy + gt_dz*gt_dz) / gt_dt
        
        # Calculate estimated velocity
        est_recent.sort()
        est_dt = est_recent[-1][0] - est_recent[-2][0]
        if est_dt < 1e-6:
            return 0.0
        
        est_dx = est_recent[-1][1].position.x - est_recent[-2][1].position.x
        est_dy = est_recent[-1][1].position.y - est_recent[-2][1].position.y
        est_dz = est_recent[-1][1].position.z - est_recent[-2][1].position.z
        est_vel = math.sqrt(est_dx*est_dx + est_dy*est_dy + est_dz*est_dz) / est_dt
        
        return abs(gt_vel - est_vel)

    def calculate_and_publish_errors(self):
        """Calculate current errors and publish them"""
        with self.data_lock:
            if not self.gt_poses or not self.est_poses:
                return
            
            # Get the most recent estimated pose
            current_time, current_est_pose = self.est_poses[-1]
            
            # Find closest ground truth pose
            closest_gt_pose, time_diff = self.find_closest_pose(current_time, self.gt_poses)
            
            if closest_gt_pose is None or time_diff > self.max_time_diff:
                return
            
            # Calculate errors
            pos_error = self.calculate_position_error(closest_gt_pose, current_est_pose)
            ori_error = self.calculate_orientation_error(closest_gt_pose, current_est_pose)
            vel_error = self.calculate_velocity_error(self.gt_poses, self.est_poses, current_time)
            
            # Calculate cumulative error (if we have previous data)
            cumulative_error = 0.0
            if self.error_data:
                cumulative_error = sum([e['position_error'] for e in self.error_data[-100:]]) / min(len(self.error_data), 100)
            
            # Store error data
            error_entry = {
                'timestamp': current_time,
                'time_diff': time_diff,
                'position_error': pos_error,
                'orientation_error': ori_error,
                'velocity_error': vel_error,
                'cumulative_error': cumulative_error,
                'gt_position': [closest_gt_pose.position.x, closest_gt_pose.position.y, closest_gt_pose.position.z],
                'est_position': [current_est_pose.position.x, current_est_pose.position.y, current_est_pose.position.z]
            }
            self.error_data.append(error_entry)
            
            # Limit stored error data to prevent memory issues
            if len(self.error_data) > 10000:
                self.error_data = self.error_data[-5000:]
            
            # Write to CSV if recording
            if self.recording_enabled and self.csv_writer:
                self.csv_writer.writerow([
                    current_time, time_diff, pos_error, ori_error, vel_error, cumulative_error,
                    closest_gt_pose.position.x, closest_gt_pose.position.y, closest_gt_pose.position.z,
                    current_est_pose.position.x, current_est_pose.position.y, current_est_pose.position.z
                ])
                self.csv_file.flush()
            
            # Publish current errors
            self.position_error_pub.publish(Float64(data=pos_error))
            self.orientation_error_pub.publish(Float64(data=ori_error))
            self.velocity_error_pub.publish(Float64(data=vel_error))
            self.cumulative_error_pub.publish(Float64(data=cumulative_error))

    def start_recording_callback(self, request, response):
        """Service callback to start recording error data"""
        if request.data:
            self.recording_enabled = True
            filename = os.path.join(self.output_dir, f"{self.file_name}.csv")
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([
                'timestamp', 'time_diff', 'position_error', 'orientation_error', 
                'velocity_error', 'cumulative_error',
                'gt_x', 'gt_y', 'gt_z', 'est_x', 'est_y', 'est_z'
            ])
            response.success = True
            response.message = f"Error recording started. Output: {filename}"
            self.get_logger().info(f"Started recording errors to {filename}")
        else:
            response.success = False
            response.message = "Recording not started (request.data was False)"
        return response

    def stop_recording_callback(self, request, response):
        """Service callback to stop recording error data"""
        if request.data and self.recording_enabled:
            self.recording_enabled = False
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            
            # Generate summary statistics
            summary_file = os.path.join(self.output_dir, f"{self.file_name}_summary.txt")
            self.generate_error_summary(summary_file)
            
            response.success = True
            response.message = "Error recording stopped and summary generated."
            self.get_logger().info("Stopped recording errors and generated summary")
        else:
            response.success = False
            response.message = "Recording not stopped (not currently recording or request.data was False)"
        return response

    def reset_data_callback(self, request, response):
        """Service callback to reset accumulated error data"""
        if request.data:
            with self.data_lock:
                self.gt_poses.clear()
                self.est_poses.clear()
                self.error_data.clear()
            response.success = True
            response.message = "Error data reset successfully"
            self.get_logger().info("Reset all error data")
        else:
            response.success = False
            response.message = "Data not reset (request.data was False)"
        return response

    def generate_error_summary(self, filename):
        """Generate a summary of error statistics"""
        if not self.error_data:
            return
        
        pos_errors = [e['position_error'] for e in self.error_data]
        ori_errors = [e['orientation_error'] for e in self.error_data]
        vel_errors = [e['velocity_error'] for e in self.error_data]
        
        with open(filename, 'w') as f:
            f.write("Path Error Analysis Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total number of error calculations: {len(self.error_data)}\n")
            f.write(f"Time span: {self.error_data[-1]['timestamp'] - self.error_data[0]['timestamp']:.2f} seconds\n\n")
            
            f.write("Position Error Statistics (meters):\n")
            f.write(f"  Mean: {np.mean(pos_errors):.6f}\n")
            f.write(f"  Median: {np.median(pos_errors):.6f}\n")
            f.write(f"  Standard Deviation: {np.std(pos_errors):.6f}\n")
            f.write(f"  Min: {np.min(pos_errors):.6f}\n")
            f.write(f"  Max: {np.max(pos_errors):.6f}\n")
            f.write(f"  95th Percentile: {np.percentile(pos_errors, 95):.6f}\n\n")
            
            f.write("Orientation Error Statistics (radians):\n")
            f.write(f"  Mean: {np.mean(ori_errors):.6f}\n")
            f.write(f"  Median: {np.median(ori_errors):.6f}\n")
            f.write(f"  Standard Deviation: {np.std(ori_errors):.6f}\n")
            f.write(f"  Min: {np.min(ori_errors):.6f}\n")
            f.write(f"  Max: {np.max(ori_errors):.6f}\n")
            f.write(f"  95th Percentile: {np.percentile(ori_errors, 95):.6f}\n\n")
            
            f.write("Velocity Error Statistics (m/s):\n")
            f.write(f"  Mean: {np.mean(vel_errors):.6f}\n")
            f.write(f"  Median: {np.median(vel_errors):.6f}\n")
            f.write(f"  Standard Deviation: {np.std(vel_errors):.6f}\n")
            f.write(f"  Min: {np.min(vel_errors):.6f}\n")
            f.write(f"  Max: {np.max(vel_errors):.6f}\n")
            f.write(f"  95th Percentile: {np.percentile(vel_errors, 95):.6f}\n\n")

def main(args=None):
    rclpy.init(args=args)
    
    path_error_calculator = PathErrorCalculator()
    
    try:
        rclpy.spin(path_error_calculator)
    except KeyboardInterrupt:
        pass
    finally:
        path_error_calculator.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 