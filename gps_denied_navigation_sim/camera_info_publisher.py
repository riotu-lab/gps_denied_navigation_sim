#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo
from builtin_interfaces.msg import Time
from std_msgs.msg import Header

class CameraInfoPublisher(Node):
    def __init__(self):
        super().__init__('camera_info_publisher')
        
        self.declare_parameter('left_camera_topic', 'stereo/left/camera_info')
        self.declare_parameter('right_camera_topic', 'stereo/right/camera_info')
        self.declare_parameter('frame_rate', 30.0)
        
        left_topic = self.get_parameter('left_camera_topic').value
        right_topic = self.get_parameter('right_camera_topic').value
        frame_rate = self.get_parameter('frame_rate').value
        
        # Create publishers
        self.left_pub = self.create_publisher(CameraInfo, left_topic, 10)
        self.right_pub = self.create_publisher(CameraInfo, right_topic, 10)
        
        # Create camera info messages
        self.left_info_msg = self.create_camera_info("stereo_left")
        self.right_info_msg = self.create_camera_info("stereo_right", is_right=True)
        
        # Create timer for publishing at the specified rate
        self.timer = self.create_timer(1.0/frame_rate, self.timer_callback)
        
        self.get_logger().info(f"Publishing camera info to {left_topic} and {right_topic} at {frame_rate} Hz")
    
    def create_camera_info(self, frame_id, is_right=False):
        info = CameraInfo()
        info.header = Header()
        info.header.frame_id = frame_id
        info.height = 480
        info.width = 752
        info.distortion_model = "plumb_bob"
        info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        info.k = [450.0, 0.0, 376.0, 0.0, 450.0, 240.0, 0.0, 0.0, 1.0]
        info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        
        # For right camera, add baseline in the P matrix
        if is_right:
            # Assuming 6cm baseline
            baseline = -0.06 * 450.0  # -baseline * focal_length
            info.p = [450.0, 0.0, 376.0, baseline, 0.0, 450.0, 240.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        else:
            info.p = [450.0, 0.0, 376.0, 0.0, 0.0, 450.0, 240.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        
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