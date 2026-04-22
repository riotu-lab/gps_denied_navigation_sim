#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import time
import numpy as np
from cv_bridge import CvBridge
import cv2
import re
from typing import Dict, List, Optional, Tuple

class AdaptiveImageStitcher(Node):
    """
    Adaptive node that can stitch images from various camera configurations:
    - Single camera
    - Stereo camera (left/right)
    - Dual stereo cameras (front stereo + rear stereo)
    - Any number of detected cameras
    
    Always publishes to the same output topic regardless of input configuration.
    """

    def __init__(self):
        super().__init__('adaptive_image_stitcher')
        
        # Wait for ROS to initialize
        time.sleep(2.0)
        
        # Declare parameters
        self.declare_parameter('output_topic', '/camera/stitched_image')
        self.declare_parameter('output_width', 800)
        self.declare_parameter('output_height', 600)
        self.declare_parameter('discovery_timeout', 5.0)  # seconds to wait for camera discovery
        self.declare_parameter('verbose', True)
        self.declare_parameter('stitch_rate', 10.0)  # Hz
        self.declare_parameter('namespace_filter', '')  # Filter cameras by namespace (e.g., '/target/')
        
        # Get parameters
        self.output_topic = self.get_parameter('output_topic').value
        self.output_width = self.get_parameter('output_width').value
        self.output_height = self.get_parameter('output_height').value
        self.discovery_timeout = self.get_parameter('discovery_timeout').value
        self.verbose = self.get_parameter('verbose').value
        self.stitch_rate = self.get_parameter('stitch_rate').value
        self.namespace_filter = self.get_parameter('namespace_filter').value
        
        # Initialize OpenCV bridge
        self.bridge = CvBridge()
        
        # Camera storage and metadata
        self.cameras: Dict[str, Dict] = {}  # camera_name -> {subscriber, image, count, position}
        self.camera_layout = None  # Will be determined after discovery
        self.stitched_count = 0
        
        # Create QoS profile
        self.qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create publisher for stitched image
        self.stitched_pub = self.create_publisher(Image, self.output_topic, 10)
        
        # Start camera discovery
        self.get_logger().info('Starting adaptive camera discovery...')
        self.discover_cameras()
        
        # Create timers
        self.stitch_timer = self.create_timer(1.0/self.stitch_rate, self.stitch_timer_callback)
        if self.verbose:
            self.status_timer = self.create_timer(5.0, self.status_timer_callback)
        
        self.get_logger().info(f'Adaptive Image Stitcher initialized with {len(self.cameras)} cameras')
    
    def discover_cameras(self):
        """
        Automatically discover available camera topics and create appropriate layout
        """
        # Wait for topic discovery
        start_time = time.time()
        while (time.time() - start_time) < self.discovery_timeout:
            topic_names_and_types = self.get_topic_names_and_types()
            
            # Find image topics
            image_topics = []
            for topic_name, topic_types in topic_names_and_types:
                for topic_type in topic_types:
                    if 'sensor_msgs/msg/Image' in topic_type and 'image_raw' in topic_name:
                        # Apply namespace filter if specified
                        if not self.namespace_filter or self.namespace_filter in topic_name:
                            image_topics.append(topic_name)
            
            if image_topics:
                break
            time.sleep(0.5)
        
        if not image_topics:
            self.get_logger().warn('No camera topics found! Will publish placeholder images.')
            self.setup_placeholder_mode()
            return
        
        self.get_logger().info(f'Discovered {len(image_topics)} camera topics:')
        for topic in sorted(image_topics):
            self.get_logger().info(f'  - {topic}')
        
        # Analyze camera configuration
        self.analyze_camera_configuration(image_topics)
        
        # Create subscribers
        self.create_camera_subscribers()
    
    def analyze_camera_configuration(self, topics: List[str]):
        """
        Analyze discovered topics to determine camera configuration and layout
        """
        # Sort topics for consistent ordering
        topics = sorted(topics)
        
        # Enhanced camera categorization patterns - order matters! More specific first
        patterns = {
            # Most specific patterns first (front/rear stereo)
            'front_left': [r'front_stereo.*left', r'front.*stereo.*left', r'stereo.*front.*left', r'front.*left'],
            'front_right': [r'front_stereo.*right', r'front.*stereo.*right', r'stereo.*front.*right', r'front.*right'],
            'rear_left': [r'rear_stereo.*left', r'rear.*stereo.*left', r'back_stereo.*left', r'rear.*left', r'back.*left'],
            'rear_right': [r'rear_stereo.*right', r'rear.*stereo.*right', r'back_stereo.*right', r'rear.*right', r'back.*right'],
            
            # Single camera directions
            'front': [r'front_cam', r'forward', r'front[^_](?!.*stereo)', r'mono.*front'],
            'rear': [r'rear_cam', r'back_cam', r'backward', r'rear[^_](?!.*stereo)', r'mono.*rear'],
            
            # Generic left/right (only if no front/rear context)
            'left': [r'(?<!front_)(?<!rear_)left_cam$', r'(?<!front)(?<!rear)left[^_]', r'left_camera'],
            'right': [r'(?<!front_)(?<!rear_)right_cam$', r'(?<!front)(?<!rear)right[^_]', r'right_camera'],
            
            # Other cameras
            'center': [r'center', r'main', r'primary'],
            'mono': [r'mono', r'single', r'main_cam']
        }
        
        # Categorize cameras
        categorized = {}
        uncategorized = []
        
        for topic in topics:
            topic_lower = topic.lower()
            matched = False
            
            # Try patterns in order (most specific first)
            for category, category_patterns in patterns.items():
                for pattern in category_patterns:
                    if re.search(pattern, topic_lower):
                        # Only assign if not already taken (first match wins)
                        if category not in categorized:
                            categorized[category] = topic
                            matched = True
                            break
                if matched:
                    break
            
            if not matched:
                uncategorized.append(topic)
        
        # Debug logging
        if self.verbose:
            self.get_logger().info(f'Camera categorization results:')
            for category, topic in categorized.items():
                self.get_logger().info(f'  {category}: {topic}')
            if uncategorized:
                self.get_logger().info(f'  Uncategorized: {uncategorized}')
        
        # Determine layout based on detected cameras
        self.determine_layout(categorized, uncategorized, topics)
    
    def determine_layout(self, categorized: Dict[str, str], uncategorized: List[str], all_topics: List[str]):
        """
        Determine the optimal layout based on detected camera configuration
        """
        num_cameras = len(all_topics)
        
        if num_cameras == 0:
            self.camera_layout = 'placeholder'
            return
        
        # Check for specific configurations
        if num_cameras == 1:
            # Single camera
            topic = all_topics[0]
            self.cameras['single'] = {'topic': topic, 'position': (0, 0), 'span': (1, 1)}
            self.camera_layout = 'single'
            
        elif num_cameras == 2:
            # Check if it's a stereo pair
            if 'front_left' in categorized and 'front_right' in categorized:
                self.cameras['front_left'] = {'topic': categorized['front_left'], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['front_right'] = {'topic': categorized['front_right'], 'position': (0, 1), 'span': (1, 1)}
                self.camera_layout = 'stereo_horizontal'
            elif 'left' in categorized and 'right' in categorized:
                # Check if these are actually front stereo cameras misclassified
                left_topic = categorized['left'].lower()
                right_topic = categorized['right'].lower()
                if 'front' in left_topic or 'front' in right_topic or 'stereo' in left_topic or 'stereo' in right_topic:
                    # These are likely front stereo cameras
                    self.cameras['front_left'] = {'topic': categorized['left'], 'position': (0, 0), 'span': (1, 1)}
                    self.cameras['front_right'] = {'topic': categorized['right'], 'position': (0, 1), 'span': (1, 1)}
                    self.camera_layout = 'stereo_horizontal'
                else:
                    self.cameras['left'] = {'topic': categorized['left'], 'position': (0, 0), 'span': (1, 1)}
                    self.cameras['right'] = {'topic': categorized['right'], 'position': (0, 1), 'span': (1, 1)}
                    self.camera_layout = 'stereo_horizontal'
            elif 'front' in categorized and 'rear' in categorized:
                self.cameras['front'] = {'topic': categorized['front'], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['rear'] = {'topic': categorized['rear'], 'position': (1, 0), 'span': (1, 1)}
                self.camera_layout = 'stereo_vertical'
            else:
                # Two unmatched cameras - try to infer from topic names
                self.infer_camera_names_and_layout(all_topics, 2)
                
        elif num_cameras == 4:
            # Check for dual stereo configuration
            if all(cam in categorized for cam in ['front_left', 'front_right', 'rear_left', 'rear_right']):
                self.cameras['front_left'] = {'topic': categorized['front_left'], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['front_right'] = {'topic': categorized['front_right'], 'position': (0, 1), 'span': (1, 1)}
                self.cameras['rear_left'] = {'topic': categorized['rear_left'], 'position': (1, 0), 'span': (1, 1)}
                self.cameras['rear_right'] = {'topic': categorized['rear_right'], 'position': (1, 1), 'span': (1, 1)}
                self.camera_layout = 'quad_stereo'
            else:
                # Try to handle partial matches or infer camera positions
                self.smart_camera_assignment(categorized, all_topics)
        
        else:
            # Multiple cameras - arrange in grid
            self.arrange_grid_layout(all_topics)
            self.camera_layout = 'multi_grid'
        
        self.get_logger().info(f'Detected camera layout: {self.camera_layout}')
        for name, info in self.cameras.items():
            self.get_logger().info(f'  {name}: {info["topic"]} at position {info["position"]}')
    
    def smart_camera_assignment(self, categorized: Dict[str, str], all_topics: List[str]):
        """
        Smart assignment for 4 cameras when not all match expected patterns
        """
        expected_cameras = ['front_left', 'front_right', 'rear_left', 'rear_right']
        
        # Start with what we have categorized
        assigned = {}
        remaining_topics = all_topics.copy()
        
        # Special handling for left/right cameras that might be front stereo
        if 'left' in categorized and 'right' in categorized and len(all_topics) == 2:
            # This is a 2-camera stereo setup misclassified - treat as front stereo
            assigned['front_left'] = categorized['left']
            assigned['front_right'] = categorized['right']
            remaining_topics.remove(categorized['left'])
            remaining_topics.remove(categorized['right'])
        else:
            # Assign categorized cameras first
            for cam_type in expected_cameras:
                if cam_type in categorized:
                    assigned[cam_type] = categorized[cam_type]
                    remaining_topics.remove(categorized[cam_type])
            
            # Handle special case: we have left/right but no front/rear
            # In a 4-camera setup, left/right likely means front_left/front_right
            if 'left' in categorized and 'right' in categorized and 'front_left' not in assigned and 'front_right' not in assigned:
                left_topic = categorized['left'].lower()
                right_topic = categorized['right'].lower()
                # If topics contain "front" or "stereo", assign as front cameras
                if ('front' in left_topic or 'stereo' in left_topic) and ('front' in right_topic or 'stereo' in right_topic):
                    assigned['front_left'] = categorized['left']
                    assigned['front_right'] = categorized['right']
                    remaining_topics.remove(categorized['left'])
                    remaining_topics.remove(categorized['right'])
        
        # Try to infer missing cameras from remaining topics
        for topic in remaining_topics:
            topic_lower = topic.lower()
            
            # Try to infer camera position from topic structure
            if 'front' in topic_lower and 'left' in topic_lower and 'front_left' not in assigned:
                assigned['front_left'] = topic
            elif 'front' in topic_lower and 'right' in topic_lower and 'front_right' not in assigned:
                assigned['front_right'] = topic
            elif 'rear' in topic_lower and 'left' in topic_lower and 'rear_left' not in assigned:
                assigned['rear_left'] = topic
            elif 'rear' in topic_lower and 'right' in topic_lower and 'rear_right' not in assigned:
                assigned['rear_right'] = topic
            # If still unclear, try simpler patterns
            elif 'left' in topic_lower and 'front_left' not in assigned and 'rear_left' not in assigned:
                # Prefer front assignment for unspecified left cameras
                if 'front_left' not in assigned:
                    assigned['front_left'] = topic
                elif 'rear_left' not in assigned:
                    assigned['rear_left'] = topic
            elif 'right' in topic_lower and 'front_right' not in assigned and 'rear_right' not in assigned:
                # Prefer front assignment for unspecified right cameras
                if 'front_right' not in assigned:
                    assigned['front_right'] = topic
                elif 'rear_right' not in assigned:
                    assigned['rear_right'] = topic
        
        # Fill in any remaining cameras with fallback names in logical order
        unassigned_topics = [t for t in all_topics if t not in assigned.values()]
        unassigned_positions = [cam for cam in expected_cameras if cam not in assigned]
        
        for i, topic in enumerate(unassigned_topics):
            if i < len(unassigned_positions):
                assigned[unassigned_positions[i]] = topic
        
        # Debug logging for assignment
        if self.verbose:
            self.get_logger().info(f'Smart camera assignment results:')
            for cam_type, topic in assigned.items():
                self.get_logger().info(f'  {cam_type}: {topic}')
        
        # Set up camera layout
        if len(assigned) >= 4:
            self.cameras['front_left'] = {'topic': assigned.get('front_left', all_topics[0]), 'position': (0, 0), 'span': (1, 1)}
            self.cameras['front_right'] = {'topic': assigned.get('front_right', all_topics[1]), 'position': (0, 1), 'span': (1, 1)}
            self.cameras['rear_left'] = {'topic': assigned.get('rear_left', all_topics[2]), 'position': (1, 0), 'span': (1, 1)}
            self.cameras['rear_right'] = {'topic': assigned.get('rear_right', all_topics[3]), 'position': (1, 1), 'span': (1, 1)}
            self.camera_layout = 'quad_stereo'
        elif len(assigned) == 2 and 'front_left' in assigned and 'front_right' in assigned:
            # Handle 2-camera front stereo case
            self.cameras['front_left'] = {'topic': assigned['front_left'], 'position': (0, 0), 'span': (1, 1)}
            self.cameras['front_right'] = {'topic': assigned['front_right'], 'position': (0, 1), 'span': (1, 1)}
            self.camera_layout = 'stereo_horizontal'
        else:
            # Fallback to grid layout with generic names
            for i, topic in enumerate(all_topics):
                row, col = divmod(i, 2)
                self.cameras[f'cam{i+1}'] = {'topic': topic, 'position': (row, col), 'span': (1, 1)}
            self.camera_layout = 'quad_grid'
    
    def infer_camera_names_and_layout(self, topics: List[str], num_cameras: int):
        """
        Try to infer meaningful camera names when categorization fails
        """
        if num_cameras == 2:
            # Try to determine if it's left/right or front/rear
            topic1, topic2 = topics[0].lower(), topics[1].lower()
            
            if 'left' in topic1 and 'right' in topic2:
                self.cameras['left'] = {'topic': topics[0], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['right'] = {'topic': topics[1], 'position': (0, 1), 'span': (1, 1)}
                self.camera_layout = 'stereo_horizontal'
            elif 'right' in topic1 and 'left' in topic2:
                self.cameras['left'] = {'topic': topics[1], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['right'] = {'topic': topics[0], 'position': (0, 1), 'span': (1, 1)}
                self.camera_layout = 'stereo_horizontal'
            elif 'front' in topic1 and 'rear' in topic2:
                self.cameras['front'] = {'topic': topics[0], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['rear'] = {'topic': topics[1], 'position': (1, 0), 'span': (1, 1)}
                self.camera_layout = 'stereo_vertical'
            elif 'rear' in topic1 and 'front' in topic2:
                self.cameras['front'] = {'topic': topics[1], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['rear'] = {'topic': topics[0], 'position': (1, 0), 'span': (1, 1)}
                self.camera_layout = 'stereo_vertical'
            else:
                # Fallback to generic names
                self.cameras['cam1'] = {'topic': topics[0], 'position': (0, 0), 'span': (1, 1)}
                self.cameras['cam2'] = {'topic': topics[1], 'position': (0, 1), 'span': (1, 1)}
                self.camera_layout = 'dual_horizontal'
    
    def arrange_grid_layout(self, topics: List[str]):
        """
        Arrange multiple cameras in an optimal grid layout
        """
        num_cameras = len(topics)
        
        # Calculate optimal grid dimensions
        if num_cameras <= 4:
            rows, cols = 2, 2
        elif num_cameras <= 6:
            rows, cols = 2, 3
        elif num_cameras <= 9:
            rows, cols = 3, 3
        else:
            # For more cameras, create a square-ish grid
            cols = int(np.ceil(np.sqrt(num_cameras)))
            rows = int(np.ceil(num_cameras / cols))
        
        # Assign positions
        for i, topic in enumerate(topics):
            row = i // cols
            col = i % cols
            self.cameras[f'cam{i+1}'] = {'topic': topic, 'position': (row, col), 'span': (1, 1)}
        
        # Store grid dimensions for later use
        self.grid_rows = rows
        self.grid_cols = cols
    
    def setup_placeholder_mode(self):
        """
        Setup placeholder mode when no cameras are detected
        """
        self.cameras['placeholder'] = {
            'topic': None, 
            'position': (0, 0), 
            'span': (1, 1),
            'image': self.create_placeholder_image("No Cameras Detected")
        }
        self.camera_layout = 'placeholder'
    
    def create_camera_subscribers(self):
        """
        Create subscribers for all detected cameras
        """
        for name, info in self.cameras.items():
            if info['topic'] is None:  # Skip placeholder cameras
                continue
                
            # Initialize camera data
            info['subscriber'] = None
            info['image'] = None
            info['count'] = 0
            
            # Create callback function
            def make_callback(camera_name):
                def callback(msg):
                    self.camera_callback(camera_name, msg)
                return callback
            
            # Create subscriber
            info['subscriber'] = self.create_subscription(
                Image, 
                info['topic'], 
                make_callback(name), 
                self.qos
            )
            
            self.get_logger().info(f'Subscribed to {name}: {info["topic"]}')
    
    def camera_callback(self, camera_name: str, msg: Image):
        """
        Generic callback for camera images
        """
        if camera_name not in self.cameras:
            return
            
        camera_info = self.cameras[camera_name]
        
        # Log first image received
        if camera_info['count'] == 0:
            self.get_logger().info(f'Received first image from {camera_name} ({camera_info["topic"]})')
        
        camera_info['count'] += 1
        
        try:
            camera_info['image'] = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Error converting image from {camera_name}: {str(e)}')
    
    def stitch_timer_callback(self):
        """
        Create and publish stitched image based on current layout
        """
        try:
            if self.camera_layout == 'placeholder':
                stitched = self.create_placeholder_image("No Camera Data Available")
            else:
                stitched = self.create_stitched_image()
            
            if stitched is not None:
                # Publish stitched image
                msg = self.bridge.cv2_to_imgmsg(stitched, "bgr8")
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = "stitched_camera"
                self.stitched_pub.publish(msg)
                self.stitched_count += 1
                
        except Exception as e:
            self.get_logger().error(f'Error in stitching: {str(e)}')
    
    def create_stitched_image(self) -> Optional[np.ndarray]:
        """
        Create stitched image based on current camera layout
        """
        if self.camera_layout == 'single':
            return self.create_single_layout()
        elif self.camera_layout in ['stereo_horizontal', 'dual_horizontal']:
            return self.create_horizontal_layout()
        elif self.camera_layout == 'stereo_vertical':
            return self.create_vertical_layout()
        elif self.camera_layout in ['quad_stereo', 'quad_grid']:
            return self.create_quad_layout()
        elif self.camera_layout == 'multi_grid':
            return self.create_grid_layout()
        else:
            return self.create_placeholder_image(f"Unknown layout: {self.camera_layout}")
    
    def create_single_layout(self) -> np.ndarray:
        """Create layout for single camera"""
        camera = list(self.cameras.values())[0]
        if camera['image'] is not None:
            return cv2.resize(camera['image'], (self.output_width, self.output_height))
        else:
            return self.create_placeholder_image("Single Camera", "Waiting for image...")
    
    def create_horizontal_layout(self) -> np.ndarray:
        """Create horizontal layout for 2 cameras with correct positioning"""
        half_width = self.output_width // 2
        
        # Define better display labels
        camera_labels = {
            'front_left': 'Front Left',
            'front_right': 'Front Right', 
            'rear_left': 'Rear Left',
            'rear_right': 'Rear Right',
            'left': 'Left',
            'right': 'Right',
            'front': 'Front',
            'rear': 'Rear'
        }
        
        # Define logical positions for horizontal layout (left/right)
        horizontal_positions = {
            'front_left': 0,          # Left side
            'front_right': half_width, # Right side
            'left': 0,                # Left side
            'right': half_width,      # Right side
        }
        
        stitched = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        
        # Place cameras in their correct horizontal positions
        for camera_name, camera in self.cameras.items():
            # Get horizontal position for this camera type
            if camera_name in horizontal_positions:
                x_offset = horizontal_positions[camera_name]
            else:
                # Fallback for unexpected camera names - use index-based positions
                cam_index = list(self.cameras.keys()).index(camera_name)
                x_offset = cam_index * half_width
            
            # Get display label
            display_label = camera_labels.get(camera_name, camera_name.replace('_', ' ').title())
            
            if camera['image'] is not None:
                resized = cv2.resize(camera['image'], (half_width, self.output_height))
                stitched[:, x_offset:x_offset + half_width] = resized
                # Add clear label
                self.add_text_label(stitched, display_label, (x_offset + 10, 30))
            else:
                placeholder = self.create_placeholder_image(display_label, size=(half_width, self.output_height))
                stitched[:, x_offset:x_offset + half_width] = placeholder
        
        return stitched
    
    def create_vertical_layout(self) -> np.ndarray:
        """Create vertical layout for 2 cameras with correct positioning"""
        half_height = self.output_height // 2
        
        # Define better display labels
        camera_labels = {
            'front_left': 'Front Left',
            'front_right': 'Front Right', 
            'rear_left': 'Rear Left',
            'rear_right': 'Rear Right',
            'left': 'Left',
            'right': 'Right',
            'front': 'Front',
            'rear': 'Rear'
        }
        
        # Define logical positions for vertical layout (front/rear)
        vertical_positions = {
            'front': 0,           # Top
            'rear': half_height,  # Bottom
        }
        
        stitched = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        
        # Place cameras in their correct vertical positions
        for camera_name, camera in self.cameras.items():
            # Get vertical position for this camera type
            if camera_name in vertical_positions:
                y_offset = vertical_positions[camera_name]
            else:
                # Fallback for unexpected camera names - use index-based positions
                cam_index = list(self.cameras.keys()).index(camera_name)
                y_offset = cam_index * half_height
            
            # Get display label
            display_label = camera_labels.get(camera_name, camera_name.replace('_', ' ').title())
            
            if camera['image'] is not None:
                resized = cv2.resize(camera['image'], (self.output_width, half_height))
                stitched[y_offset:y_offset + half_height, :] = resized
                # Add clear label
                self.add_text_label(stitched, display_label, (10, y_offset + 30))
            else:
                placeholder = self.create_placeholder_image(display_label, size=(self.output_width, half_height))
                stitched[y_offset:y_offset + half_height, :] = placeholder
        
        return stitched
    
    def create_quad_layout(self) -> np.ndarray:
        """Create 2x2 quad layout for 4 cameras with correct positioning"""
        half_width = self.output_width // 2
        half_height = self.output_height // 2
        
        stitched = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        
        # Define logical positions for camera types
        camera_positions = {
            'front_left': (0, 0),              # Top-left
            'front_right': (0, half_width),    # Top-right
            'rear_left': (half_height, 0),     # Bottom-left
            'rear_right': (half_height, half_width)  # Bottom-right
        }
        
        # Define better display labels
        camera_labels = {
            'front_left': 'Front Left',
            'front_right': 'Front Right', 
            'rear_left': 'Rear Left',
            'rear_right': 'Rear Right',
            'left': 'Left',
            'right': 'Right',
            'front': 'Front',
            'rear': 'Rear'
        }
        
        # Place cameras in their correct positions
        for camera_name, camera in self.cameras.items():
            # Get position for this camera type
            if camera_name in camera_positions:
                y_offset, x_offset = camera_positions[camera_name]
            else:
                # Fallback for unexpected camera names - use grid positions
                cam_index = list(self.cameras.keys()).index(camera_name)
                y_offset = (cam_index // 2) * half_height
                x_offset = (cam_index % 2) * half_width
            
            # Get display label
            display_label = camera_labels.get(camera_name, camera_name.replace('_', ' ').title())
            
            if camera['image'] is not None:
                resized = cv2.resize(camera['image'], (half_width, half_height))
                stitched[y_offset:y_offset + half_height, x_offset:x_offset + half_width] = resized
                
                # Add clear label
                self.add_text_label(stitched, display_label, (x_offset + 10, y_offset + 30))
            else:
                placeholder = self.create_placeholder_image(display_label, size=(half_width, half_height))
                stitched[y_offset:y_offset + half_height, x_offset:x_offset + half_width] = placeholder
        
        return stitched
    
    def create_grid_layout(self) -> np.ndarray:
        """Create grid layout for multiple cameras"""
        if not hasattr(self, 'grid_rows') or not hasattr(self, 'grid_cols'):
            return self.create_placeholder_image("Grid Layout Error")
        
        cell_width = self.output_width // self.grid_cols
        cell_height = self.output_height // self.grid_rows
        
        # Define better display labels
        camera_labels = {
            'front_left': 'Front Left',
            'front_right': 'Front Right', 
            'rear_left': 'Rear Left',
            'rear_right': 'Rear Right',
            'left': 'Left',
            'right': 'Right',
            'front': 'Front',
            'rear': 'Rear'
        }
        
        stitched = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        
        for i, (camera_name, camera) in enumerate(self.cameras.items()):
            row = i // self.grid_cols
            col = i % self.grid_cols
            
            if row >= self.grid_rows:  # Skip excess cameras
                break
            
            x_offset = col * cell_width
            y_offset = row * cell_height
            
            # Get display label
            display_label = camera_labels.get(camera_name, camera_name.replace('_', ' ').title())
            
            if camera['image'] is not None:
                resized = cv2.resize(camera['image'], (cell_width, cell_height))
                stitched[y_offset:y_offset + cell_height, x_offset:x_offset + cell_width] = resized
                
                # Add clear label
                self.add_text_label(stitched, display_label, (x_offset + 5, y_offset + 25))
            else:
                placeholder = self.create_placeholder_image(display_label, size=(cell_width, cell_height))
                stitched[y_offset:y_offset + cell_height, x_offset:x_offset + cell_width] = placeholder
        
        return stitched
    
    def create_placeholder_image(self, title: str, subtitle: str = "", size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """Create a placeholder image with text"""
        if size is None:
            size = (self.output_width, self.output_height)
        
        width, height = size
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (64, 64, 64)  # Dark gray background
        
        # Add title text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = min(width, height) / 500.0  # Scale font based on image size
        font_thickness = max(1, int(font_scale * 2))
        
        # Calculate text position for centering
        title_size = cv2.getTextSize(title, font, font_scale, font_thickness)[0]
        title_x = (width - title_size[0]) // 2
        title_y = height // 2
        
        cv2.putText(img, title, (title_x, title_y), font, font_scale, (255, 255, 255), font_thickness)
        
        if subtitle:
            subtitle_size = cv2.getTextSize(subtitle, font, font_scale * 0.7, font_thickness)[0]
            subtitle_x = (width - subtitle_size[0]) // 2
            subtitle_y = title_y + 40
            cv2.putText(img, subtitle, (subtitle_x, subtitle_y), font, font_scale * 0.7, (200, 200, 200), font_thickness)
        
        return img
    
    def add_text_label(self, img: np.ndarray, text: str, position: Tuple[int, int]):
        """Add text label with background to image"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6  # Slightly larger for better readability
        font_thickness = 2
        font_color = (255, 255, 255)  # White text
        bg_color = (0, 0, 0)          # Black background
        border_color = (0, 255, 0)    # Green border
        
        # Get text size
        text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
        x, y = position
        
        # Add some padding
        padding = 4
        
        # Draw background rectangle with border
        cv2.rectangle(img, 
                     (x - padding, y - text_size[1] - padding), 
                     (x + text_size[0] + padding, y + padding), 
                     bg_color, -1)
        
        # Draw border
        cv2.rectangle(img, 
                     (x - padding, y - text_size[1] - padding), 
                     (x + text_size[0] + padding, y + padding), 
                     border_color, 1)
        
        # Draw text
        cv2.putText(img, text, (x, y), font, font_scale, font_color, font_thickness)
    
    def status_timer_callback(self):
        """Report status periodically"""
        if not self.verbose:
            return
        
        self.get_logger().info(f'Adaptive Camera Stitcher Status (Layout: {self.camera_layout}):')
        for name, camera in self.cameras.items():
            if 'count' in camera:
                self.get_logger().info(f'  - {name}: {camera["count"]} images received')
        self.get_logger().info(f'  - Stitched: {self.stitched_count} images published')

def main(args=None):
    rclpy.init(args=args)
    node = AdaptiveImageStitcher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 