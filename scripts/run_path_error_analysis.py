#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from scipy.spatial.transform import Rotation
import time
import argparse
import csv
import os
from datetime import datetime
import math

class PathErrorController(Node):
    def __init__(self, output_file=None):
        super().__init__('path_error_controller')
        
        # Service clients
        self.start_client = self.create_client(SetBool, 'start_error_recording')
        self.stop_client = self.create_client(SetBool, 'stop_error_recording')
        self.reset_client = self.create_client(SetBool, 'reset_error_data')
        
        # Data recording
        self.recording = False
        self.data_rows = []
        self.latest_estimated = None
        self.latest_gt = None
        self.output_file = output_file or f"pose_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Subscribers for pose data
        self.estimated_sub = self.create_subscription(
            Path, '/path', self.estimated_callback, 10)
        self.gt_sub = self.create_subscription(
            Path, '/target/gt_path', self.gt_callback, 10)
        
        # Timer for data collection
        self.timer = self.create_timer(0.1, self.collect_data)  # 10Hz data collection
        
        # Wait for services
        self.get_logger().info("Waiting for path error calculator services...")
        self.start_client.wait_for_service(timeout_sec=10.0)
        self.stop_client.wait_for_service(timeout_sec=10.0)
        self.reset_client.wait_for_service(timeout_sec=10.0)
        self.get_logger().info("Services found!")
        
        # Initialize CSV file
        self.init_csv_file()

    def init_csv_file(self):
        """Initialize CSV file with headers"""
        with open(self.output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'timestamp',
                'est_frame_id', 'est_x', 'est_y', 'est_z', 
                'est_qx', 'est_qy', 'est_qz', 'est_qw',
                'est_roll_deg', 'est_pitch_deg', 'est_yaw_deg',
                'gt_frame_id', 'gt_x', 'gt_y', 'gt_z',
                'gt_qx', 'gt_qy', 'gt_qz', 'gt_qw', 
                'gt_roll_deg', 'gt_pitch_deg', 'gt_yaw_deg',
                'pos_error_x', 'pos_error_y', 'pos_error_z',
                'pos_error_magnitude', 'rot_error_deg',
                'yaw_diff_deg', 'aligned_est_x', 'aligned_est_y', 'aligned_est_z'
            ])
        self.get_logger().info(f"Initialized CSV file: {self.output_file}")

    def estimated_callback(self, msg):
        """Store latest estimated pose"""
        if msg.poses:
            self.latest_estimated = msg.poses[-1]

    def gt_callback(self, msg):
        """Store latest ground truth pose"""
        if msg.poses:
            self.latest_gt = msg.poses[-1]

    def quaternion_to_euler(self, x, y, z, w):
        """Convert quaternion to euler angles in degrees"""
        r = Rotation.from_quat([x, y, z, w])
        euler = r.as_euler('xyz', degrees=True)
        return euler[0], euler[1], euler[2]  # roll, pitch, yaw

    def apply_coordinate_transform(self, est_x, est_y, est_z):
        """Apply coordinate transformation: GT(+X) = EST(-Y), GT(+Z) = EST(-X), GT(+Y) = EST(+Z)"""
        aligned_x = -est_y  # GT X = -EST Y
        aligned_y = est_z   # GT Y = EST Z  
        aligned_z = -est_x  # GT Z = -EST X
        return aligned_x, aligned_y, aligned_z

    def calculate_errors(self, est_pose, gt_pose):
        """Calculate position and rotation errors"""
        # Position errors (direct comparison)
        pos_error_x = gt_pose.position.x - est_pose.position.x
        pos_error_y = gt_pose.position.y - est_pose.position.y
        pos_error_z = gt_pose.position.z - est_pose.position.z
        pos_error_mag = math.sqrt(pos_error_x**2 + pos_error_y**2 + pos_error_z**2)
        
        # Rotation error
        gt_quat = [gt_pose.orientation.x, gt_pose.orientation.y, 
                   gt_pose.orientation.z, gt_pose.orientation.w]
        est_quat = [est_pose.orientation.x, est_pose.orientation.y, 
                    est_pose.orientation.z, est_pose.orientation.w]
        
        gt_rot = Rotation.from_quat(gt_quat)
        est_rot = Rotation.from_quat(est_quat)
        
        # Calculate angular difference
        relative_rot = gt_rot.inv() * est_rot
        rot_error_deg = math.degrees(relative_rot.magnitude())
        
        # Yaw difference
        _, _, gt_yaw = self.quaternion_to_euler(gt_pose.orientation.x, gt_pose.orientation.y,
                                               gt_pose.orientation.z, gt_pose.orientation.w)
        _, _, est_yaw = self.quaternion_to_euler(est_pose.orientation.x, est_pose.orientation.y,
                                                est_pose.orientation.z, est_pose.orientation.w)
        yaw_diff = abs(gt_yaw - est_yaw)
        if yaw_diff > 180:
            yaw_diff = 360 - yaw_diff
        
        return pos_error_x, pos_error_y, pos_error_z, pos_error_mag, rot_error_deg, yaw_diff

    def collect_data(self):
        """Collect and record pose data if recording is active"""
        if not self.recording or self.latest_estimated is None or self.latest_gt is None:
            return
            
        current_time = self.get_clock().now().nanoseconds / 1e9
        
        # Extract poses
        est_pose = self.latest_estimated.pose
        gt_pose = self.latest_gt.pose
        
        # Convert quaternions to euler angles
        est_roll, est_pitch, est_yaw = self.quaternion_to_euler(
            est_pose.orientation.x, est_pose.orientation.y,
            est_pose.orientation.z, est_pose.orientation.w)
        
        gt_roll, gt_pitch, gt_yaw = self.quaternion_to_euler(
            gt_pose.orientation.x, gt_pose.orientation.y,
            gt_pose.orientation.z, gt_pose.orientation.w)
        
        # Calculate errors
        pos_err_x, pos_err_y, pos_err_z, pos_err_mag, rot_err_deg, yaw_diff = self.calculate_errors(est_pose, gt_pose)
        
        # Apply coordinate transformation to estimated pose
        aligned_x, aligned_y, aligned_z = self.apply_coordinate_transform(
            est_pose.position.x, est_pose.position.y, est_pose.position.z)
        
        # Create data row
        row = [
            f"{current_time:.6f}",
            self.latest_estimated.header.frame_id,
            f"{est_pose.position.x:.6f}", f"{est_pose.position.y:.6f}", f"{est_pose.position.z:.6f}",
            f"{est_pose.orientation.x:.6f}", f"{est_pose.orientation.y:.6f}", 
            f"{est_pose.orientation.z:.6f}", f"{est_pose.orientation.w:.6f}",
            f"{est_roll:.3f}", f"{est_pitch:.3f}", f"{est_yaw:.3f}",
            self.latest_gt.header.frame_id,
            f"{gt_pose.position.x:.6f}", f"{gt_pose.position.y:.6f}", f"{gt_pose.position.z:.6f}",
            f"{gt_pose.orientation.x:.6f}", f"{gt_pose.orientation.y:.6f}",
            f"{gt_pose.orientation.z:.6f}", f"{gt_pose.orientation.w:.6f}",
            f"{gt_roll:.3f}", f"{gt_pitch:.3f}", f"{gt_yaw:.3f}",
            f"{pos_err_x:.6f}", f"{pos_err_y:.6f}", f"{pos_err_z:.6f}",
            f"{pos_err_mag:.6f}", f"{rot_err_deg:.3f}", f"{yaw_diff:.3f}",
            f"{aligned_x:.6f}", f"{aligned_y:.6f}", f"{aligned_z:.6f}"
        ]
        
        # Write to CSV
        with open(self.output_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(row)

    def start_recording(self):
        """Start error recording"""
        request = SetBool.Request()
        request.data = True
        
        future = self.start_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            response = future.result()
            if response.success:
                self.get_logger().info(f"✓ Started recording: {response.message}")
                self.recording = True
                return True
            else:
                self.get_logger().error(f"✗ Failed to start recording: {response.message}")
                return False
        else:
            self.get_logger().error("✗ Service call failed")
            return False

    def stop_recording(self):
        """Stop error recording and generate summary"""
        self.recording = False
        
        request = SetBool.Request()
        request.data = True
        
        future = self.stop_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            response = future.result()
            if response.success:
                self.get_logger().info(f"✓ Stopped recording: {response.message}")
                self.get_logger().info(f"📊 Data saved to: {self.output_file}")
                return True
            else:
                self.get_logger().error(f"✗ Failed to stop recording: {response.message}")
                return False
        else:
            self.get_logger().error("✗ Service call failed")
            return False

    def reset_data(self):
        """Reset accumulated error data"""
        request = SetBool.Request()
        request.data = True
        
        future = self.reset_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            response = future.result()
            if response.success:
                self.get_logger().info(f"✓ Reset data: {response.message}")
                return True
            else:
                self.get_logger().error(f"✗ Failed to reset data: {response.message}")
                return False
        else:
            self.get_logger().error("✗ Service call failed")
            return False

def print_usage():
    print("\n" + "="*60)
    print("Enhanced Path Error Analysis Controller")
    print("="*60)
    print("\nThis script records detailed pose data and errors to CSV for analysis.")
    print("\nCSV Output includes:")
    print("  - Timestamp and frame IDs")
    print("  - Estimated pose (position, quaternion, euler angles)")
    print("  - Ground truth pose (position, quaternion, euler angles)")
    print("  - Position errors (x, y, z, magnitude)")
    print("  - Rotation errors (angular difference, yaw difference)")
    print("  - Coordinate-aligned estimated position")
    print("\nInput topics:")
    print("  /path                  - Estimated path (body frame)")
    print("  /target/gt_path        - Ground truth path")
    print("\nCoordinate transformation applied:")
    print("  GT(+X) = EST(-Y), GT(+Z) = EST(-X), GT(+Y) = EST(+Z)")
    print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description='Control path error analysis recording with CSV output')
    parser.add_argument('command', choices=['start', 'stop', 'reset', 'auto'], 
                       help='Command to execute')
    parser.add_argument('--duration', type=float, default=60.0,
                       help='Duration for auto recording (seconds)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output CSV file name (default: auto-generated)')
    
    args = parser.parse_args()
    
    rclpy.init()
    controller = PathErrorController(output_file=args.output)
    
    try:
        if args.command == 'start':
            print_usage()
            print(f"\n🚀 Starting error recording to: {controller.output_file}")
            if controller.start_recording():
                print("📊 Recording started! Press Ctrl+C or use 'stop' command to finish.")
                try:
                    rclpy.spin(controller)
                except KeyboardInterrupt:
                    print("\n⏹️  Stopping recording...")
                    controller.stop_recording()
        
        elif args.command == 'stop':
            print("⏹️  Stopping error recording and generating summary...")
            controller.stop_recording()
            print("✅ Analysis complete! Check the CSV file for detailed data.")
        
        elif args.command == 'reset':
            print("🔄 Resetting accumulated error data...")
            controller.reset_data()
            print("✅ Data reset complete.")
        
        elif args.command == 'auto':
            print_usage()
            print(f"\n🤖 Starting automatic {args.duration}s recording to: {controller.output_file}")
            
            if controller.start_recording():
                print(f"📊 Recording for {args.duration} seconds...")
                time.sleep(args.duration)
                print("⏹️  Stopping recording...")
                controller.stop_recording()
                print(f"✅ Automatic analysis complete! Data saved to: {controller.output_file}")
            else:
                print("❌ Failed to start recording.")
        
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 