#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import tf2_ros
from tf2_ros import TransformException
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Path
from scipy.spatial.transform import Rotation
import numpy as np

# ANSI color codes for terminal output
class Colors:
    BLUE = '\033[94m'      # Blue for estimated
    GREEN = '\033[92m'     # Green for ground truth
    YELLOW = '\033[93m'    # Yellow for headers
    RED = '\033[91m'       # Red for errors
    ENDC = '\033[0m'       # End color
    BOLD = '\033[1m'       # Bold

class TFMonitor(Node):
    def __init__(self):
        super().__init__('tf_monitor')
        
        # Declare parameters
        self.declare_parameter('monitor_rate', 2.0)  # Hz
        self.declare_parameter('estimated_path_topic', '/path')  # Estimated path topic
        self.declare_parameter('gt_path_topic', '/target/gt_path')  # Ground truth path topic
        
        # Get parameters
        self.monitor_rate = self.get_parameter('monitor_rate').value
        self.estimated_path_topic = self.get_parameter('estimated_path_topic').value
        self.gt_path_topic = self.get_parameter('gt_path_topic').value
        
        # Store latest poses
        self.latest_estimated_pose = None
        self.latest_gt_pose = None
        self.estimated_frame_id = None
        self.gt_frame_id = None
        
        # Create subscribers
        self.estimated_path_sub = self.create_subscription(
            Path, 
            self.estimated_path_topic, 
            self.estimated_path_callback, 
            10
        )
        
        self.gt_path_sub = self.create_subscription(
            Path, 
            self.gt_path_topic, 
            self.gt_path_callback, 
            10
        )
        
        # Create timer for periodic monitoring
        self.timer = self.create_timer(1.0/self.monitor_rate, self.monitor_poses)
        
        self.get_logger().info(f'{Colors.YELLOW}{Colors.BOLD}TF Monitor initialized{Colors.ENDC}')
        self.get_logger().info(f'{Colors.YELLOW}Subscribed topics:{Colors.ENDC}')
        self.get_logger().info(f'  {Colors.BLUE}Estimated path: {self.estimated_path_topic}{Colors.ENDC}')
        self.get_logger().info(f'  {Colors.GREEN}Ground truth path: {self.gt_path_topic}{Colors.ENDC}')
        self.get_logger().info(f'{Colors.YELLOW}Monitor rate: {self.monitor_rate} Hz{Colors.ENDC}')
        
    def estimated_path_callback(self, msg):
        """Callback for estimated path messages"""
        if msg.poses:
            self.latest_estimated_pose = msg.poses[-1]  # Get latest pose
            self.estimated_frame_id = msg.header.frame_id
            
    def gt_path_callback(self, msg):
        """Callback for ground truth path messages"""
        if msg.poses:
            self.latest_gt_pose = msg.poses[-1]  # Get latest pose
            self.gt_frame_id = msg.header.frame_id
        
    def monitor_poses(self):
        """Monitor and print pose information from subscribed topics"""
        current_time = self.get_clock().now()
        
        self.get_logger().info(f'{Colors.YELLOW}{"="*80}{Colors.ENDC}')
        self.get_logger().info(f'{Colors.YELLOW}{Colors.BOLD}Pose Monitor - Time: {current_time.nanoseconds / 1e9:.3f}{Colors.ENDC}')
        self.get_logger().info(f'{Colors.YELLOW}{"="*80}{Colors.ENDC}')
        
        # Print estimated pose (body frame)
        if self.latest_estimated_pose is not None:
            self.print_pose_info(
                self.latest_estimated_pose.pose, 
                f"ESTIMATED (/body frame from {self.estimated_path_topic})",
                Colors.BLUE,
                self.estimated_frame_id
            )
        else:
            self.get_logger().warn(f'{Colors.RED}No estimated pose data received from {self.estimated_path_topic}{Colors.ENDC}')
            
        # Print ground truth pose (target/base_link frame)
        if self.latest_gt_pose is not None:
            self.print_pose_info(
                self.latest_gt_pose.pose, 
                f"GROUND TRUTH (/target/base_link frame from {self.gt_path_topic})",
                Colors.GREEN,
                self.gt_frame_id
            )
        else:
            self.get_logger().warn(f'{Colors.RED}No ground truth pose data received from {self.gt_path_topic}{Colors.ENDC}')
            
        self.get_logger().info('')  # Empty line for spacing

    def print_pose_info(self, pose, label, color, frame_id):
        """Print formatted pose information with color"""
        # Extract position (x, y, z)
        pos = pose.position
        x, y, z = pos.x, pos.y, pos.z
        
        # Extract rotation (quaternion and convert to euler)
        rot = pose.orientation
        quat = [rot.x, rot.y, rot.z, rot.w]
        
        # Convert quaternion to euler angles (roll, pitch, yaw)
        r = Rotation.from_quat(quat)
        euler = r.as_euler('xyz', degrees=True)  # Roll, Pitch, Yaw in degrees
        roll, pitch, yaw = euler[0], euler[1], euler[2]
        
        # Print frame information with color
        self.get_logger().info(f'{color}{Colors.BOLD}{label}{Colors.ENDC}')
        if frame_id:
            self.get_logger().info(f'{color}  Frame ID: {frame_id}{Colors.ENDC}')
        self.get_logger().info(f'{color}  Position (x, y, z): ({x:.6f}, {y:.6f}, {z:.6f}){Colors.ENDC}')
        self.get_logger().info(f'{color}  Rotation (roll, pitch, yaw): ({roll:.3f}°, {pitch:.3f}°, {yaw:.3f}°){Colors.ENDC}')
        self.get_logger().info(f'{color}  Quaternion (x, y, z, w): ({rot.x:.6f}, {rot.y:.6f}, {rot.z:.6f}, {rot.w:.6f}){Colors.ENDC}')
        self.get_logger().info(f'{color}{"-"*60}{Colors.ENDC}')

def main(args=None):
    rclpy.init(args=args)
    
    tf_monitor = TFMonitor()
    
    try:
        rclpy.spin(tf_monitor)
    except KeyboardInterrupt:
        pass
    finally:
        tf_monitor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 