#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from stereo_msgs.msg import DisparityImage
import time
from threading import Lock
import subprocess
import re
import os

# Try to import OpenCV-related libraries, but don't fail if not available
try:
    from cv_bridge import CvBridge
    import cv2
    import numpy as np
    CV_BRIDGE_AVAILABLE = True
except ImportError:
    CV_BRIDGE_AVAILABLE = False

class StereoMonitor(Node):
    def __init__(self):
        super().__init__('stereo_monitor')
        
        # Topic list update timer (every 10 seconds)
        self.create_timer(10.0, self.update_topic_list)
        self.stereo_topics = []
        
        # Flag to enable basic disparity calculation if stereo_image_proc fails
        self.declare_parameter('do_stereo_processing', False)
        self.do_stereo_processing = self.get_parameter('do_stereo_processing').value
        
        self.get_logger().info(f"OpenCV/cv_bridge available: {CV_BRIDGE_AVAILABLE}")
        
        # Create CV bridge only if available and needed
        if CV_BRIDGE_AVAILABLE and self.do_stereo_processing:
            self.cv_bridge = CvBridge()
            # Create a basic StereoBM matcher for fallback processing
            self.stereo_matcher = cv2.StereoBM.create()
            self.stereo_matcher.setMinDisparity(0)
            self.stereo_matcher.setNumDisparities(64)
            self.stereo_matcher.setBlockSize(15)
            self.stereo_matcher.setPreFilterSize(9)
            self.stereo_matcher.setPreFilterCap(31)
            self.stereo_matcher.setTextureThreshold(10)
            self.stereo_matcher.setUniquenessRatio(15)
            self.stereo_matcher.setSpeckleWindowSize(100)
            self.stereo_matcher.setSpeckleRange(4)
            
            # Create publisher for disparity
            self.disparity_pub = self.create_publisher(
                DisparityImage,
                '/target/stereo/disparity',
                10
            )
            
            self.get_logger().info("Basic stereo processing enabled as fallback")
        else:
            if self.do_stereo_processing:
                self.get_logger().warn("Stereo processing requested but OpenCV/cv_bridge not available")
            self.do_stereo_processing = False
        
        # Create locks for thread safety
        self.left_lock = Lock()
        self.right_lock = Lock()
        self.disparity_lock = Lock()
        
        # Store latest messages
        self.left_img = None
        self.right_img = None
        self.left_info = None
        self.right_info = None
        self.left_info_gz = None
        self.right_info_gz = None
        self.disparity_img = None
        
        # Store timestamps and counters
        self.left_count = 0
        self.right_count = 0
        self.left_info_count = 0
        self.right_info_count = 0
        self.left_info_gz_count = 0
        self.right_info_gz_count = 0
        self.disparity_count = 0
        self.last_report_time = time.time()
        
        # Create subscribers for stereo pipeline
        self.create_subscription(
            Image, 
            '/target/stereo/left/image_raw', 
            self.left_callback, 
            10)
        
        self.create_subscription(
            Image, 
            '/target/stereo/right/image_raw', 
            self.right_callback, 
            10)
            
        self.create_subscription(
            CameraInfo, 
            '/target/stereo/left/camera_info', 
            self.left_info_callback, 
            10)
            
        self.create_subscription(
            CameraInfo, 
            '/target/stereo/right/camera_info', 
            self.right_info_callback, 
            10)
            
        # Add subscribers for Gazebo camera info topics
        # self.create_subscription(
        #     CameraInfo, 
        #     '/target/stereo/left/camera_info_gz', 
        #     self.left_info_gz_callback, 
        #     10)
            
        # self.create_subscription(
        #     CameraInfo, 
        #     '/target/stereo/right/camera_info_gz', 
        #     self.right_info_gz_callback, 
        #     10)
            
        self.create_subscription(
            DisparityImage, 
            '/target/stereo/disparity', 
            self.disparity_callback, 
            10)
            
        # Create timer for periodic status reports
        self.create_timer(1.0, self.report_status)
        
        self.get_logger().info('Stereo Monitor initialized')
        
    def left_callback(self, msg):
        with self.left_lock:
            self.left_img = msg
            self.left_count += 1
            
    def right_callback(self, msg):
        with self.right_lock:
            self.right_img = msg
            self.right_count += 1
            
            # If we're doing stereo processing and we have both images, compute disparity
            if self.do_stereo_processing and self.left_img is not None and CV_BRIDGE_AVAILABLE:
                try:
                    self.compute_disparity()
                except Exception as e:
                    self.get_logger().error(f"Error computing disparity: {e}")
                    
    def left_info_callback(self, msg):
        with self.left_lock:
            self.left_info = msg
            self.left_info_count += 1
            
    def right_info_callback(self, msg):
        with self.right_lock:
            self.right_info = msg
            self.right_info_count += 1
            
    # def left_info_gz_callback(self, msg):
    #     with self.left_lock:
    #         self.left_info_gz = msg
    #         self.left_info_gz_count += 1
            
    # def right_info_gz_callback(self, msg):
    #     with self.right_lock:
    #         self.right_info_gz = msg
    #         self.right_info_gz_count += 1
            
    def disparity_callback(self, msg):
        with self.disparity_lock:
            self.disparity_img = msg
            self.disparity_count += 1
    
    def compute_disparity(self):
        if not CV_BRIDGE_AVAILABLE:
            return
            
        # Convert ROS Image messages to OpenCV images
        left_img = self.cv_bridge.imgmsg_to_cv2(self.left_img, "mono8")
        right_img = self.cv_bridge.imgmsg_to_cv2(self.right_img, "mono8")
        
        # Compute disparity map
        disparity = self.stereo_matcher.compute(left_img, right_img)
        
        # Normalize for visualization
        disparity_normalized = cv2.normalize(disparity, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Create DisparityImage message
        disp_msg = DisparityImage()
        disp_msg.header = self.left_img.header
        disp_msg.image = self.cv_bridge.cv2_to_imgmsg(disparity.astype(np.float32) / 16.0, "32FC1")
        disp_msg.f = 450.0  # focal length
        disp_msg.t = 0.1    # baseline
        disp_msg.min_disparity = float(self.stereo_matcher.getMinDisparity())
        disp_msg.max_disparity = float(self.stereo_matcher.getMinDisparity() + self.stereo_matcher.getNumDisparities())
        
        # Publish disparity message
        self.disparity_pub.publish(disp_msg)
        self.get_logger().debug("Published disparity from fallback processor")
     
    def report_status(self):
        current_time = time.time()
        duration = current_time - self.last_report_time
        
        # Calculate rates
        left_rate = self.left_count / duration if duration > 0 else 0
        right_rate = self.right_count / duration if duration > 0 else 0
        left_info_rate = self.left_info_count / duration if duration > 0 else 0
        right_info_rate = self.right_info_count / duration if duration > 0 else 0
        left_info_gz_rate = self.left_info_gz_count / duration if duration > 0 else 0
        right_info_gz_rate = self.right_info_gz_count / duration if duration > 0 else 0
        disparity_rate = self.disparity_count / duration if duration > 0 else 0
        
        # Print status with dividers for better visibility
        self.get_logger().info("="*80)
        self.get_logger().info(f"STEREO MONITOR STATUS - {current_time:.0f} - Duration: {duration:.2f}s")
        self.get_logger().info("-"*80)
        
        # Group and format topic data for better readability
        self.get_logger().info("TOPIC RATES:")
        self.get_logger().info(f"  Images:       Left: {self.left_count:3d} msgs ({left_rate:6.2f} Hz)    Right: {self.right_count:3d} msgs ({right_rate:6.2f} Hz)")
        self.get_logger().info(f"  Camera Info:  Left: {self.left_info_count:3d} msgs ({left_info_rate:6.2f} Hz)    Right: {self.right_info_count:3d} msgs ({right_info_rate:6.2f} Hz)")
        self.get_logger().info(f"  Gazebo Info:  Left: {self.left_info_gz_count:3d} msgs ({left_info_gz_rate:6.2f} Hz)    Right: {self.right_info_gz_count:3d} msgs ({right_info_gz_rate:6.2f} Hz)")
        self.get_logger().info(f"  Disparity:    {self.disparity_count:3d} msgs ({disparity_rate:6.2f} Hz)")
        
        # Check if disparity is being produced in relation to images
        disparity_ratio = (disparity_rate / max(left_rate, 0.1)) * 100 if left_rate > 0 else 0
        self.get_logger().info(f"  Disparity ratio: {disparity_ratio:.1f}% of image rate")
        
        # Look for Gazebo topics with ros2 command
        self.update_topic_list()
        
        # Reset counters and timestamp
        self.left_count = 0
        self.right_count = 0
        self.left_info_count = 0
        self.right_info_count = 0
        self.left_info_gz_count = 0
        self.right_info_gz_count = 0
        self.disparity_count = 0
        self.last_report_time = current_time
        
        # Check if we have received camera info messages and display their properties
        if self.left_info or self.right_info:
            self.get_logger().info("-"*80)
            self.get_logger().info("CAMERA INFO:")
            
        if self.left_info:
            self.get_logger().info(f"  Left camera: frame_id={self.left_info.header.frame_id}, size={self.left_info.width}x{self.left_info.height}")
            
        if self.right_info:
            self.get_logger().info(f"  Right camera: frame_id={self.right_info.header.frame_id}, size={self.right_info.width}x{self.right_info.height}")
        
        # Check on the disparity image
        if self.disparity_img:
            self.get_logger().info("-"*80)
            self.get_logger().info("DISPARITY INFO:")
            self.get_logger().info(f"  Frame ID: {self.disparity_img.header.frame_id}")
            self.get_logger().info(f"  Focal Length: {self.disparity_img.f}")
            self.get_logger().info(f"  Baseline: {self.disparity_img.t}")
            self.get_logger().info(f"  Min/Max Disparity: {self.disparity_img.min_disparity}/{self.disparity_img.max_disparity}")
            
            if not CV_BRIDGE_AVAILABLE:
                self.get_logger().info(f"  (Detailed stats unavailable without OpenCV)")
            else:
                try:
                    with self.disparity_lock:
                        disp_img = self.cv_bridge.imgmsg_to_cv2(self.disparity_img.image)
                        valid_pixels = np.count_nonzero(~np.isnan(disp_img))
                        total_pixels = disp_img.size
                        min_disp = np.nanmin(disp_img) if valid_pixels > 0 else 0
                        max_disp = np.nanmax(disp_img) if valid_pixels > 0 else 0
                        
                        self.get_logger().info(f"  Value Range: min={min_disp:.2f}, max={max_disp:.2f}")
                        self.get_logger().info(f"  Valid Pixels: {valid_pixels}/{total_pixels} ({valid_pixels/total_pixels*100:.2f}%)")
                except Exception as e:
                    self.get_logger().error(f"  Error processing disparity image: {e}")
        
        # Check if specific nodes are running by looking for their expected topics
        self.get_logger().info("-"*80)
        self.get_logger().info("STEREO NODE STATUS CHECK:")
        
        # Check for stereo_image_proc's expected output topics
        is_left_image_active = bool(left_rate > 0.5)  # More than 0.5 Hz means active
        is_right_image_active = bool(right_rate > 0.5)  # More than 0.5 Hz means active
        is_disparity_active = bool(disparity_rate > 0.5)  # More than 0.5 Hz means active
        
        self.get_logger().info(f"  Left Image:       {'✓' if is_left_image_active else '✗'} (/target/stereo/left/image_raw) - {left_rate:.1f} Hz")
        self.get_logger().info(f"  Right Image:      {'✓' if is_right_image_active else '✗'} (/target/stereo/right/image_raw) - {right_rate:.1f} Hz")
        self.get_logger().info(f"  Disparity Image:  {'✓' if is_disparity_active else '✗'} (/target/stereo/disparity) - {disparity_rate:.1f} Hz")
        self.get_logger().info(f"  Stereo Pipeline:  {'✓' if (is_left_image_active and is_right_image_active and is_disparity_active) else '✗'} (all required topics active)")
        
        self.get_logger().info("="*80)

    def update_topic_list(self):
        """Query available ROS topics and filter for stereo-related ones"""
        try:
            # This is a bit hacky but works within the container
            cmd = "ros2 topic list"
            result = os.popen(cmd).read()
            
            # Extract topic names and filter for stereo-related ones
            all_topics = result.strip().split('\n')
            self.stereo_topics = [t for t in all_topics if 'stereo' in t or 'disparity' in t]
            
            # Print filtered topics
            if self.stereo_topics:
                self.get_logger().info("-"*80)
                self.get_logger().info("AVAILABLE STEREO TOPICS:")
                for topic in sorted(self.stereo_topics):
                    self.get_logger().info(f"  {topic}")
        except Exception as e:
            self.get_logger().error(f"Failed to list topics: {e}")

def main(args=None):
    rclpy.init(args=args)
    
    # Create our node
    try:
        node = StereoMonitor()
        rclpy.spin(node)
    except Exception as e:
        print(f"Error in StereoMonitor: {e}")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main() 