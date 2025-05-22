#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

class TrajectoryPublisher(Node):
    """
    Node to publish drone trajectory as a Path message for visualization
    """

    def __init__(self):
        super().__init__('trajectory_publisher')
        
        # Declare parameters
        self.declare_parameter('pose_topic', '/target/mavros/local_position/pose')
        self.declare_parameter('path_topic', '/target/gt_path')
        self.declare_parameter('max_path_length', 1000)  # Maximum number of poses to keep in the path
        self.declare_parameter('verbose', False)  # Parameter to control logging verbosity
        
        # Get parameters
        self.pose_topic = self.get_parameter('pose_topic').value
        self.path_topic = self.get_parameter('path_topic').value
        self.max_path_length = self.get_parameter('max_path_length').value
        self.verbose = self.get_parameter('verbose').value
        
        # Create a QoS profile with reliability and history settings
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create publisher for the path
        self.path_pub = self.create_publisher(Path, self.path_topic, 10)
        
        # Create subscriber to the pose topic
        self.get_logger().info(f'Subscribing to pose topic: {self.pose_topic}')
        self.pose_sub = self.create_subscription(
            PoseStamped, 
            self.pose_topic, 
            self.pose_callback, 
            qos
        )
        
        # Initialize path message
        self.path = Path()
        self.path.header.frame_id = 'map'  # Set the frame ID to match your global frame
        
        # Initialize pose counter
        self.pose_count = 0
        
        # Create a timer to periodically publish the path
        self.timer = self.create_timer(0.5, self.timer_callback)  # 2Hz
        
        self.get_logger().info('Trajectory publisher initialized')
    
    def pose_callback(self, msg):
        """
        Callback for pose messages - add the pose to the path
        """
        if self.pose_count == 0 and self.verbose:
            self.get_logger().info(f'Received first pose from {self.pose_topic}')
        
        # Add the pose to the path
        self.path.poses.append(msg)
        self.pose_count += 1
        
        # Keep the path length within limits
        if len(self.path.poses) > self.max_path_length:
            # Remove oldest poses to maintain max length
            self.path.poses = self.path.poses[-self.max_path_length:]
    
    def timer_callback(self):
        """
        Timer callback to publish the path
        """
        if len(self.path.poses) > 0:
            # Update the header timestamp
            self.path.header.stamp = self.get_clock().now().to_msg()
            
            # Publish the path
            self.path_pub.publish(self.path)
            
            # Log status periodically if verbose is enabled
            if self.verbose and self.pose_count % 100 == 0:
                self.get_logger().info(f'Path contains {len(self.path.poses)} poses')

def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 