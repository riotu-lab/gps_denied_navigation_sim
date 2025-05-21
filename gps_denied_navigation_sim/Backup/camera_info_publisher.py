#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from builtin_interfaces.msg import Time
from std_msgs.msg import Header
import time

class CameraInfoPublisher(Node):
    def __init__(self):
        super().__init__('camera_info_publisher')
        
        # Declare all parameters with defaults
        self.declare_parameter('robot_name', 'target')
        self.declare_parameter('camera_frame_id', 'stereo/left_camera_optical_frame')
        self.declare_parameter('camera_frame_id_right', 'stereo/right_camera_optical_frame')
        self.declare_parameter('camera_topic_left', '/target/stereo/left/image_raw')
        self.declare_parameter('camera_topic_right', '/target/stereo/right/image_raw')
        self.declare_parameter('camera_info_topic_left', '/target/stereo/left/camera_info')
        self.declare_parameter('camera_info_topic_right', '/target/stereo/right/camera_info')
        self.declare_parameter('publish_image_as_both', False)
        self.declare_parameter('stereo_camera', True)
        self.declare_parameter('frame_rate', 30.0)
        self.declare_parameter('baseline', 0.1)  # 10cm baseline by default
        self.declare_parameter('image_width', 752)
        self.declare_parameter('image_height', 480)
        self.declare_parameter('focal_length', 450.0)
        
        # Get parameter values
        self.robot_name = self.get_parameter('robot_name').value
        self.left_frame_id = self.get_parameter('camera_frame_id').value
        self.right_frame_id = self.get_parameter('camera_frame_id_right').value
        self.left_image_topic = self.get_parameter('camera_topic_left').value
        self.right_image_topic = self.get_parameter('camera_topic_right').value
        self.left_info_topic = self.get_parameter('camera_info_topic_left').value
        self.right_info_topic = self.get_parameter('camera_info_topic_right').value
        self.publish_image_as_both = self.get_parameter('publish_image_as_both').value
        self.stereo_camera = self.get_parameter('stereo_camera').value
        frame_rate = self.get_parameter('frame_rate').value
        self.baseline = self.get_parameter('baseline').value
        self.width = self.get_parameter('image_width').value
        self.height = self.get_parameter('image_height').value
        self.focal_length = self.get_parameter('focal_length').value
        
        # Log the parameters
        self.get_logger().info(f"Stereo camera parameters:")
        self.get_logger().info(f"  Robot name: {self.robot_name}")
        self.get_logger().info(f"  Stereo camera: {self.stereo_camera}")
        self.get_logger().info(f"  Baseline: {self.baseline} m")
        self.get_logger().info(f"  Image size: {self.width}x{self.height}")
        self.get_logger().info(f"  Focal length: {self.focal_length} px")
        self.get_logger().info(f"  Left frame: {self.left_frame_id}")
        self.get_logger().info(f"  Right frame: {self.right_frame_id}")
        self.get_logger().info(f"  Left image topic: {self.left_image_topic}")
        self.get_logger().info(f"  Right image topic: {self.right_image_topic}")
        self.get_logger().info(f"  Left info topic: {self.left_info_topic}")
        self.get_logger().info(f"  Right info topic: {self.right_info_topic}")
        self.get_logger().info(f"  Republish images: {self.publish_image_as_both}")
        
        # Create camera info publishers
        self.left_info_pub = self.create_publisher(CameraInfo, self.left_info_topic, 10)
        
        # Create subscription to image topics if republishing is enabled
        if self.publish_image_as_both:
            # Extract the base topic name without /image_raw suffix
            if self.left_image_topic.endswith('/image_raw'):
                left_base = self.left_image_topic[:-10]  # Remove '/image_raw'
                self.left_image_pub = self.create_publisher(Image, f"{left_base}/image", 10)
                
                # Subscribe to raw images to republish
                self.left_image_sub = self.create_subscription(
                    Image,
                    self.left_image_topic,
                    self.left_image_callback,
                    10
                )
                self.get_logger().info(f"Republishing {self.left_image_topic} -> {left_base}/image")
                
            if self.stereo_camera and self.right_image_topic.endswith('/image_raw'):
                right_base = self.right_image_topic[:-10]  # Remove '/image_raw'
                self.right_image_pub = self.create_publisher(Image, f"{right_base}/image", 10)
                
                # Subscribe to raw images to republish
                self.right_image_sub = self.create_subscription(
                    Image,
                    self.right_image_topic,
                    self.right_image_callback,
                    10
                )
                self.get_logger().info(f"Republishing {self.right_image_topic} -> {right_base}/image")

        # Create right camera info publisher if using stereo
        if self.stereo_camera:
            self.right_info_pub = self.create_publisher(CameraInfo, self.right_info_topic, 10)
            
        # Create camera info messages
        self.left_info_msg = self.create_camera_info(self.left_frame_id)
        
        if self.stereo_camera:
            self.right_info_msg = self.create_camera_info(self.right_frame_id, is_right=True)
        
        # Publish a few messages immediately to make sure they're available
        # before other nodes start subscribing
        now = self.get_clock().now().to_msg()
        self.left_info_msg.header.stamp = now
        
        self.get_logger().info("Publishing initial camera_info messages...")
        for _ in range(5):  # Publish a few times to ensure availability
            self.left_info_pub.publish(self.left_info_msg)
            if self.stereo_camera:
                self.right_info_msg.header.stamp = now
                self.right_info_pub.publish(self.right_info_msg)
            # Sleep a tiny bit between publishes
            time.sleep(0.1)
        
        # Create timer for continuous publishing at the specified rate
        self.timer = self.create_timer(1.0/frame_rate, self.timer_callback)
        
        self.get_logger().info(f"Now publishing camera info continuously at {frame_rate} Hz")
    
    def left_image_callback(self, msg):
        """Republish left camera image from image_raw to image topic"""
        self.left_image_pub.publish(msg)
    
    def right_image_callback(self, msg):
        """Republish right camera image from image_raw to image topic"""
        self.right_image_pub.publish(msg)
    
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
            # The projection matrix P = K * [R|t] where t = -R * baseline
            # For perfect stereo rig, R = Identity, and t = [-baseline, 0, 0]
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
        self.left_info_pub.publish(self.left_info_msg)
        
        if self.stereo_camera:
            self.right_info_msg.header.stamp = now
            self.right_info_pub.publish(self.right_info_msg)

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