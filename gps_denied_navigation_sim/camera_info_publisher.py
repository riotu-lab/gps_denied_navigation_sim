#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo
from builtin_interfaces.msg import Time
from std_msgs.msg import Header
import time

class CameraInfoPublisher(Node):
    def __init__(self):
        super().__init__('camera_info_publisher')
        
        # Declare all parameters with defaults
        self.declare_parameter('left_camera_topic', 'stereo/left/camera_info')
        self.declare_parameter('right_camera_topic', 'stereo/right/camera_info')
        self.declare_parameter('frame_rate', 30.0)
        self.declare_parameter('baseline', 0.1)  # 10cm baseline by default
        self.declare_parameter('image_width', 640)
        self.declare_parameter('image_height', 480)
        self.declare_parameter('focal_length', 500.0)
        self.declare_parameter('left_frame_id', 'stereo/left_camera_optical_frame')
        self.declare_parameter('right_frame_id', 'stereo/right_camera_optical_frame')
        
        # Get parameter values
        left_topic = self.get_parameter('left_camera_topic').value
        right_topic = self.get_parameter('right_camera_topic').value
        frame_rate = self.get_parameter('frame_rate').value
        self.baseline = self.get_parameter('baseline').value
        self.width = self.get_parameter('image_width').value
        self.height = self.get_parameter('image_height').value
        self.focal_length = self.get_parameter('focal_length').value
        self.left_frame_id = self.get_parameter('left_frame_id').value
        self.right_frame_id = self.get_parameter('right_frame_id').value
        
        # Log the parameters
        self.get_logger().info(f"Stereo camera parameters:")
        self.get_logger().info(f"  Baseline: {self.baseline} m")
        self.get_logger().info(f"  Image size: {self.width}x{self.height}")
        self.get_logger().info(f"  Focal length: {self.focal_length} px")
        self.get_logger().info(f"  Left frame: {self.left_frame_id}")
        self.get_logger().info(f"  Right frame: {self.right_frame_id}")
        
        # Create publishers
        self.left_pub = self.create_publisher(CameraInfo, left_topic, 10)
        self.right_pub = self.create_publisher(CameraInfo, right_topic, 10)
        
        # Create camera info messages
        self.left_info_msg = self.create_camera_info(self.left_frame_id)
        self.right_info_msg = self.create_camera_info(self.right_frame_id, is_right=True)
        
        # Publish a few messages immediately to make sure they're available
        # before other nodes start subscribing
        now = self.get_clock().now().to_msg()
        self.left_info_msg.header.stamp = now
        self.right_info_msg.header.stamp = now
        
        self.get_logger().info("Publishing initial camera_info messages...")
        for _ in range(5):  # Publish a few times to ensure availability
            self.left_pub.publish(self.left_info_msg)
            self.right_pub.publish(self.right_info_msg)
            # Sleep a tiny bit between publishes
            time.sleep(0.1)
        
        # Create timer for continuous publishing at the specified rate
        self.timer = self.create_timer(1.0/frame_rate, self.timer_callback)
        
        self.get_logger().info(f"Now publishing camera info continuously to {left_topic} and {right_topic} at {frame_rate} Hz")
    
    def create_camera_info(self, frame_id, is_right=False):
        info = CameraInfo()
        info.header = Header()
        info.header.frame_id = frame_id
        info.height = self.height
        info.width = self.width
        info.distortion_model = "plumb_bob"
        
        # Camera parameters from ROS parameters
        focal_length = self.focal_length
        cx = self.width / 2.0    # principal point at image center
        cy = self.height / 2.0   # principal point at image center
        baseline = self.baseline
        
        # Zero distortion for simplicity
        info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        
        # Camera matrix (same for both cameras)
        info.k = [focal_length, 0.0, cx, 
                  0.0, focal_length, cy, 
                  0.0, 0.0, 1.0]
        
        # Rectification matrix (identity for rectified images)
        info.r = [1.0, 0.0, 0.0, 
                  0.0, 1.0, 0.0, 
                  0.0, 0.0, 1.0]
        
        # Projection matrix
        if is_right:
            # Right camera has -fx*baseline as the 4th parameter (x-axis shift)
            info.p = [focal_length, 0.0, cx, -focal_length * baseline,
                      0.0, focal_length, cy, 0.0,
                      0.0, 0.0, 1.0, 0.0]
        else:
            # Left camera has standard projection matrix
            info.p = [focal_length, 0.0, cx, 0.0,
                      0.0, focal_length, cy, 0.0,
                      0.0, 0.0, 1.0, 0.0]
        
        return info
    
    def timer_callback(self):
        now = self.get_clock().now().to_msg()
        self.left_info_msg.header.stamp = now
        self.right_info_msg.header.stamp = now
        
        self.left_pub.publish(self.left_info_msg)
        self.right_pub.publish(self.right_info_msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraInfoPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 