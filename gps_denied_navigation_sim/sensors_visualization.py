#!/usr/bin/env python3

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import tf2_ros
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped, PoseStamped
from nav_msgs.msg import Path, Odometry
from sensor_msgs.msg import Image
import yaml
import os
from tf2_msgs.msg import TFMessage
from ament_index_python.packages import get_package_share_directory

# Try to import OpenCV, but continue if it fails
CV_AVAILABLE = False
try:
    import cv2
    from cv_bridge import CvBridge
    CV_AVAILABLE = True
except ImportError:
    print("WARNING: OpenCV (cv2) or cv_bridge not available. Image combining will be disabled.")
except Exception as e:
    print(f"WARNING: Error importing OpenCV: {e}. Image combining will be disabled.")


class SensorsVisualizationNode(Node):
    def __init__(self):
        super().__init__('sensors_visualization_node')

        # Parameters
        self.declare_parameter('config_file', 'config/mins_twin_stereo_cam/config_camera.yaml')
        self.declare_parameter('lidar_config_file', 'config/mins_twin_stereo_cam/config_lidar.yaml')
        self.declare_parameter('publish_rate', 10.0)  # Hz
        
        # Get configuration paths
        cam_config = self.get_parameter('config_file').get_parameter_value().string_value
        lidar_config = self.get_parameter('lidar_config_file').get_parameter_value().string_value
        
        # Check if paths are absolute, if not, prepend package share directory
        pkg_share = get_package_share_directory('gps_denied_navigation_sim')
        if not os.path.isabs(cam_config):
            cam_config = os.path.join(pkg_share, cam_config)
        if not os.path.isabs(lidar_config):
            lidar_config = os.path.join(pkg_share, lidar_config)
        
        # Load configurations
        self.get_logger().info(f"Loading camera config from: {cam_config}")
        self.get_logger().info(f"Loading lidar config from: {lidar_config}")
        self.cam_config = self.load_yaml(cam_config)
        self.lidar_config = self.load_yaml(lidar_config)
        
        # Set up QoS
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Subscribe to odometry for ground truth path
        self.odom_sub = self.create_subscription(
            Odometry, '/target/mavros/odometry/out', self.odom_callback, qos)
        
        # Set up image processing only if OpenCV is available
        if CV_AVAILABLE:
            self.get_logger().info("OpenCV is available. Image combining enabled.")
            # Subscribe to camera images
            self.front_left_sub = self.create_subscription(
                Image, '/target/front_stereo/left_cam/image_raw', self.front_left_callback, qos)
            self.front_right_sub = self.create_subscription(
                Image, '/target/front_stereo/right_cam/image_raw', self.front_right_callback, qos)
            self.rear_left_sub = self.create_subscription(
                Image, '/target/rear_stereo/left_cam/image_raw', self.rear_left_callback, qos)
            self.rear_right_sub = self.create_subscription(
                Image, '/target/rear_stereo/right_cam/image_raw', self.rear_right_callback, qos)
            
            # Publishers for images
            self.combined_image_pub = self.create_publisher(Image, '/target/combined_stereo/image', qos)
            
            # Store the images
            self.front_left_img = None
            self.front_right_img = None
            self.rear_left_img = None
            self.rear_right_img = None
            self.bridge = CvBridge()
        else:
            self.get_logger().warn("OpenCV not available. Image combining disabled.")
        
        # Publishers
        self.path_pub = self.create_publisher(Path, '/target/gt_path', qos)
        
        # TF Broadcaster for sensor transforms visualization
        self.tf_broadcaster = StaticTransformBroadcaster(self)
        
        # Ground truth path
        self.path = Path()
        self.path.header.frame_id = "map"
        
        # Create timer for visualization
        self.timer = self.create_timer(
            1.0/self.get_parameter('publish_rate').get_parameter_value().double_value, 
            self.timer_callback)
        
        # Publish transforms once at startup
        self.publish_sensor_transforms()
        
        self.get_logger().info('Sensors Visualization Node started')
    
    def load_yaml(self, file_path):
        with open(file_path, 'r') as file:
            # Skip the first line which typically contains %YAML:1.0
            first_line = file.readline()
            if not first_line.strip().startswith('%YAML'):
                file.seek(0)  # If it doesn't start with %YAML, go back to beginning
            return yaml.safe_load(file)
    
    # Only define these methods if OpenCV is available
    if CV_AVAILABLE:
        def front_left_callback(self, msg):
            self.front_left_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        def front_right_callback(self, msg):
            self.front_right_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        def rear_left_callback(self, msg):
            self.rear_left_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        def rear_right_callback(self, msg):
            self.rear_right_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        def combine_images(self):
            # Check if we have all images
            if None in [self.front_left_img, self.front_right_img, self.rear_left_img, self.rear_right_img]:
                self.get_logger().warn('Not all camera images received yet')
                return None
            
            # Resize images to ensure they're all the same size
            height, width = self.front_left_img.shape[:2]
            front_left = cv2.resize(self.front_left_img, (width, height))
            front_right = cv2.resize(self.front_right_img, (width, height))
            rear_left = cv2.resize(self.rear_left_img, (width, height))
            rear_right = cv2.resize(self.rear_right_img, (width, height))
            
            # Add text labels to each image
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(front_left, 'Front Left', (10, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(front_right, 'Front Right', (10, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(rear_left, 'Rear Left', (10, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(rear_right, 'Rear Right', (10, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
            
            # Combine images in a 2x2 grid
            top_row = np.hstack((front_left, front_right))
            bottom_row = np.hstack((rear_left, rear_right))
            combined = np.vstack((top_row, bottom_row))
            
            return combined
    
    def odom_callback(self, msg):
        # Add to path
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose = msg.pose.pose
        self.path.header = msg.header
        self.path.poses.append(pose)
        
        # Trim to prevent excessive memory usage
        if len(self.path.poses) > 1000:
            self.path.poses = self.path.poses[-1000:]
        
        # Publish path
        self.path_pub.publish(self.path)
    
    def create_transform_from_matrix(self, matrix, parent_frame, child_frame):
        # Create transform from 4x4 transformation matrix
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = parent_frame
        t.child_frame_id = child_frame
        
        # Get translation
        t.transform.translation.x = matrix[0][3]
        t.transform.translation.y = matrix[1][3]
        t.transform.translation.z = matrix[2][3]
        
        # Convert rotation matrix to quaternion
        # This is a simplified conversion from rotation matrix to quaternion
        # Assumes the matrix is a valid rotation matrix
        rot = np.array([
            [matrix[0][0], matrix[0][1], matrix[0][2]],
            [matrix[1][0], matrix[1][1], matrix[1][2]],
            [matrix[2][0], matrix[2][1], matrix[2][2]]
        ])
        
        trace = rot[0][0] + rot[1][1] + rot[2][2]
        
        if trace > 0:
            S = np.sqrt(trace + 1.0) * 2
            t.transform.rotation.w = 0.25 * S
            t.transform.rotation.x = (rot[2][1] - rot[1][2]) / S
            t.transform.rotation.y = (rot[0][2] - rot[2][0]) / S
            t.transform.rotation.z = (rot[1][0] - rot[0][1]) / S
        elif rot[0][0] > rot[1][1] and rot[0][0] > rot[2][2]:
            S = np.sqrt(1.0 + rot[0][0] - rot[1][1] - rot[2][2]) * 2
            t.transform.rotation.w = (rot[2][1] - rot[1][2]) / S
            t.transform.rotation.x = 0.25 * S
            t.transform.rotation.y = (rot[0][1] + rot[1][0]) / S
            t.transform.rotation.z = (rot[0][2] + rot[2][0]) / S
        elif rot[1][1] > rot[2][2]:
            S = np.sqrt(1.0 + rot[1][1] - rot[0][0] - rot[2][2]) * 2
            t.transform.rotation.w = (rot[0][2] - rot[2][0]) / S
            t.transform.rotation.x = (rot[0][1] + rot[1][0]) / S
            t.transform.rotation.y = 0.25 * S
            t.transform.rotation.z = (rot[1][2] + rot[2][1]) / S
        else:
            S = np.sqrt(1.0 + rot[2][2] - rot[0][0] - rot[1][1]) * 2
            t.transform.rotation.w = (rot[1][0] - rot[0][1]) / S
            t.transform.rotation.x = (rot[0][2] + rot[2][0]) / S
            t.transform.rotation.y = (rot[1][2] + rot[2][1]) / S
            t.transform.rotation.z = 0.25 * S
            
        return t
    
    def publish_sensor_transforms(self):
        transforms = []
        
        # Process camera transforms
        for i in range(4):  # For 4 cameras
            cam_key = f'cam{i}'
            if cam_key in self.cam_config:
                T_matrix = self.cam_config[cam_key]['T_imu_cam']
                # Convert to a numpy array if it's not already
                if not isinstance(T_matrix, np.ndarray):
                    T_matrix = np.array(T_matrix)
                
                # Create transform
                transform = self.create_transform_from_matrix(
                    T_matrix, 
                    "target/base_link", 
                    f"target/{cam_key}_optical_frame"
                )
                transforms.append(transform)
        
        # Process lidar transforms
        for i in range(2):  # For 2 lidars
            lidar_key = f'lidar{i}'
            if lidar_key in self.lidar_config:
                T_matrix = self.lidar_config[lidar_key]['T_imu_lidar']
                # Convert to a numpy array if it's not already
                if not isinstance(T_matrix, np.ndarray):
                    T_matrix = np.array(T_matrix)
                
                # Create transform
                transform = self.create_transform_from_matrix(
                    T_matrix, 
                    "target/base_link", 
                    f"target/{lidar_key}_frame"
                )
                transforms.append(transform)
        
        # Send all transforms
        if transforms:
            self.tf_broadcaster.sendTransform(transforms)
            self.get_logger().info(f'Published {len(transforms)} sensor transforms')
    
    def timer_callback(self):
        # Publish combined camera image only if OpenCV is available
        if CV_AVAILABLE:
            try:
                combined_img = self.combine_images()
                if combined_img is not None:
                    msg = self.bridge.cv2_to_imgmsg(combined_img, encoding='bgr8')
                    msg.header.stamp = self.get_clock().now().to_msg()
                    msg.header.frame_id = "target/base_link"
                    self.combined_image_pub.publish(msg)
            except Exception as e:
                self.get_logger().error(f"Error in image combining: {e}")
            
        # Re-publish sensor transforms periodically
        if hasattr(self, 'sensor_transform_counter'):
            self.sensor_transform_counter += 1
            if self.sensor_transform_counter >= 50:  # Republish every 50 timer callbacks
                self.sensor_transform_counter = 0
                self.publish_sensor_transforms()
        else:
            self.sensor_transform_counter = 0


def main(args=None):
    rclpy.init(args=args)
    try:
        node = SensorsVisualizationNode()
        rclpy.spin(node)
    except Exception as e:
        print(f"Error in sensors_visualization node: {e}")
        import traceback
        traceback.print_exc()
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main() 