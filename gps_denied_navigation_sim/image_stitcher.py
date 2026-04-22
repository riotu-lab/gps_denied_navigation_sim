#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import time
import numpy as np
from cv_bridge import CvBridge
import cv2  # Add OpenCV import

class ImageStitcher(Node):
    """
    Node to stitch together four camera feeds and publish the combined view.
    """

    def __init__(self):
        super().__init__('image_stitcher')
        
        # Wait a bit to allow ROS to initialize fully
        time.sleep(2.0)
        
        # Get a list of all available topics
        self.get_logger().info('Discovering available topics...')
        topic_names_and_types = self.get_topic_names_and_types()
        
        # Filter for image topics
        image_topics = []
        for topic_name, topic_types in topic_names_and_types:
            for topic_type in topic_types:
                if 'sensor_msgs/msg/Image' in topic_type and 'image_raw' in topic_name:
                    image_topics.append(topic_name)
        
        self.get_logger().info(f'Found {len(image_topics)} image topics:')
        for topic in image_topics:
            self.get_logger().info(f'  - {topic}')
        
        # Declare parameters with defaults that try different namespaces
        self.declare_parameter('front_left_topic', '/target/front_stereo/left_cam/image_raw')
        self.declare_parameter('front_right_topic', '/target/front_stereo/right_cam/image_raw')
        self.declare_parameter('rear_left_topic', '/target/rear_stereo/left_cam/image_raw')
        self.declare_parameter('rear_right_topic', '/target/rear_stereo/right_cam/image_raw')
        self.declare_parameter('output_width', 800)
        self.declare_parameter('output_height', 600)
        self.declare_parameter('verbose', False)  # Parameter to control logging verbosity
        
        # Get parameters
        self.front_left_topic = self.get_parameter('front_left_topic').value
        self.front_right_topic = self.get_parameter('front_right_topic').value
        self.rear_left_topic = self.get_parameter('rear_left_topic').value
        self.rear_right_topic = self.get_parameter('rear_right_topic').value
        self.output_width = self.get_parameter('output_width').value
        self.output_height = self.get_parameter('output_height').value
        self.verbose = self.get_parameter('verbose').value
        
        # If we found image topics but our configured ones aren't available, try to use the discovered ones
        if image_topics and self.front_left_topic not in image_topics:
            # Try to match topics based on name patterns
            for topic in image_topics:
                if 'front' in topic.lower() and 'left' in topic.lower():
                    self.front_left_topic = topic
                    self.get_logger().info(f'Using discovered front left topic: {topic}')
                elif 'front' in topic.lower() and 'right' in topic.lower():
                    self.front_right_topic = topic
                    self.get_logger().info(f'Using discovered front right topic: {topic}')
                elif 'rear' in topic.lower() and 'left' in topic.lower():
                    self.rear_left_topic = topic
                    self.get_logger().info(f'Using discovered rear left topic: {topic}')
                elif 'rear' in topic.lower() and 'right' in topic.lower():
                    self.rear_right_topic = topic
                    self.get_logger().info(f'Using discovered rear right topic: {topic}')
        
        # Create a QoS profile with reliability and history settings
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Initialize OpenCV bridge
        self.bridge = CvBridge()
        
        # Initialize image storage
        self.front_left_img = None
        self.front_right_img = None
        self.rear_left_img = None
        self.rear_right_img = None
        
        # Create a publisher for the stitched image
        self.stitched_pub = self.create_publisher(
            Image, 
            '/target/camera/stitched_image', 
            10
        )
        
        # Create subscribers to each camera topic
        self.get_logger().info(f'Subscribing to topics:')
        self.get_logger().info(f'  - {self.front_left_topic}')
        self.front_left_sub = self.create_subscription(
            Image, self.front_left_topic, self.front_left_callback, qos)
            
        self.get_logger().info(f'  - {self.front_right_topic}')
        self.front_right_sub = self.create_subscription(
            Image, self.front_right_topic, self.front_right_callback, qos)
            
        self.get_logger().info(f'  - {self.rear_left_topic}')
        self.rear_left_sub = self.create_subscription(
            Image, self.rear_left_topic, self.rear_left_callback, qos)
            
        self.get_logger().info(f'  - {self.rear_right_topic}')
        self.rear_right_sub = self.create_subscription(
            Image, self.rear_right_topic, self.rear_right_callback, qos)
        
        # Initialize counters for received images
        self.front_left_count = 0
        self.front_right_count = 0
        self.rear_left_count = 0
        self.rear_right_count = 0
        self.stitched_count = 0
        
        # Create a timer to periodically report the status
        self.status_timer = self.create_timer(5.0, self.status_timer_callback)
        
        # Create a timer to periodically publish stitched image
        self.stitch_timer = self.create_timer(0.1, self.stitch_timer_callback)  # 10Hz
        
        self.get_logger().info('Camera monitor initialized')
    
    def front_left_callback(self, msg):
        if self.front_left_count == 0:
            self.get_logger().info(f'Received first image from {self.front_left_topic}')
        self.front_left_count += 1
        try:
            self.front_left_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Error converting front left image: {str(e)}')
        
    def front_right_callback(self, msg):
        if self.front_right_count == 0:
            self.get_logger().info(f'Received first image from {self.front_right_topic}')
        self.front_right_count += 1
        try:
            self.front_right_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Error converting front right image: {str(e)}')
        
    def rear_left_callback(self, msg):
        if self.rear_left_count == 0:
            self.get_logger().info(f'Received first image from {self.rear_left_topic}')
        self.rear_left_count += 1
        try:
            self.rear_left_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Error converting rear left image: {str(e)}')
        
    def rear_right_callback(self, msg):
        if self.rear_right_count == 0:
            self.get_logger().info(f'Received first image from {self.rear_right_topic}')
        self.rear_right_count += 1
        try:
            self.rear_right_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Error converting rear right image: {str(e)}')
    
    def stitch_timer_callback(self):
        """
        Timer callback to stitch images and publish the result
        """
        # Check if we have all images
        if (self.front_left_img is not None and self.front_right_img is not None and 
            self.rear_left_img is not None and self.rear_right_img is not None):
            
            try:
                # Create a stitched image
                # Each quadrant will be half the output size
                quad_height = self.output_height // 2
                quad_width = self.output_width // 2
                
                # Resize each image to fit in a quadrant
                try:
                    # Simple resize using NumPy to avoid OpenCV dependency issues
                    fl_resized = self.resize_image(self.front_left_img, quad_width, quad_height)
                    fr_resized = self.resize_image(self.front_right_img, quad_width, quad_height)
                    rl_resized = self.resize_image(self.rear_left_img, quad_width, quad_height)
                    rr_resized = self.resize_image(self.rear_right_img, quad_width, quad_height)
                
                    # Create the combined image
                    # [Front Left | Front Right]
                    # [Rear Left  | Rear Right ]
                    stitched = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
                    
                    # Copy the resized images into the appropriate quadrants
                    stitched[0:quad_height, 0:quad_width] = fl_resized
                    stitched[0:quad_height, quad_width:self.output_width] = fr_resized
                    stitched[quad_height:self.output_height, 0:quad_width] = rl_resized
                    stitched[quad_height:self.output_height, quad_width:self.output_width] = rr_resized
                    
                    # Add labels to each quadrant
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.7
                    font_thickness = 2
                    font_color = (0, 255, 0)  # Green color
                    bg_color = (0, 0, 0)      # Black background
                    
                    # Function to add text with background
                    def add_text_with_bg(img, text, position):
                        # Get text size
                        text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                        # Position text
                        x, y = position
                        # Draw background rectangle
                        cv2.rectangle(img, 
                                    (x, y - text_size[1] - 5), 
                                    (x + text_size[0] + 5, y + 5), 
                                    bg_color, 
                                    -1)  # Filled rectangle
                        # Draw text
                        cv2.putText(img, text, (x, y), font, font_scale, font_color, font_thickness)
                    
                    # Add labels to each quadrant
                    add_text_with_bg(stitched, "Front Left", (10, 30))
                    add_text_with_bg(stitched, "Front Right", (quad_width + 10, 30))
                    add_text_with_bg(stitched, "Rear Left", (10, quad_height + 30))
                    add_text_with_bg(stitched, "Rear Right", (quad_width + 10, quad_height + 30))
                    
                    # Convert back to ROS message and publish
                    msg = self.bridge.cv2_to_imgmsg(stitched, "bgr8")
                    msg.header.stamp = self.get_clock().now().to_msg()
                    self.stitched_pub.publish(msg)
                    self.stitched_count += 1
                    
                except Exception as e:
                    self.get_logger().error(f'Error resizing or combining images: {str(e)}')
            
            except Exception as e:
                self.get_logger().error(f'Error stitching images: {str(e)}')
    
    def resize_image(self, img, target_width, target_height):
        """
        Simple image resize using NumPy for compatibility
        """
        if img is None:
            return np.zeros((target_height, target_width, 3), dtype=np.uint8)
            
        # Get original dimensions
        h, w = img.shape[:2]
        
        # Create target array
        resized = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        
        # Simple scaling factors
        x_ratio = w / target_width
        y_ratio = h / target_height
        
        # Simple nearest-neighbor sampling
        for y in range(target_height):
            for x in range(target_width):
                src_x = min(w - 1, int(x * x_ratio))
                src_y = min(h - 1, int(y * y_ratio))
                resized[y, x] = img[src_y, src_x]
        
        return resized
    
    def status_timer_callback(self):
        """
        Timer callback to report image reception status.
        """
        # Only print status messages if verbose is enabled
        if not self.verbose:
            return
            
        self.get_logger().info('Camera status:')
        self.get_logger().info(f'  - Front Left: {self.front_left_count} images received')
        self.get_logger().info(f'  - Front Right: {self.front_right_count} images received')
        self.get_logger().info(f'  - Rear Left: {self.rear_left_count} images received')
        self.get_logger().info(f'  - Rear Right: {self.rear_right_count} images received')
        self.get_logger().info(f'  - Stitched: {self.stitched_count} images published')

def main(args=None):
    rclpy.init(args=args)
    node = ImageStitcher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 