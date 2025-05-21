#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import tf2_ros
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
import math
from tf_transformations import quaternion_from_euler

class TFRelay(Node):
    def __init__(self):
        super().__init__('tf_relay')
        
        # Declare parameters
        self.declare_parameter('source_topic', '/target/mavros/local_position/pose')
        self.declare_parameter('target_frame_id', 'target/odom')
        self.declare_parameter('child_frame_id', 'target/base_link')
        
        # Get parameters
        self.source_topic = self.get_parameter('source_topic').value
        self.target_frame_id = self.get_parameter('target_frame_id').value
        self.child_frame_id = self.get_parameter('child_frame_id').value
        
        # Create subscriber to pose topic
        self.pose_sub = self.create_subscription(
            PoseStamped,
            self.source_topic,
            self.pose_callback,
            10)
        
        # Create transform broadcaster
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        
        self.get_logger().info(f'TF relay initialized from {self.source_topic} to transform {self.target_frame_id} -> {self.child_frame_id}')
    
    def pose_callback(self, msg):
        # Create transform message
        transform = TransformStamped()
        transform.header.stamp = msg.header.stamp
        transform.header.frame_id = self.target_frame_id
        transform.child_frame_id = self.child_frame_id
        
        # Set translation from pose message
        transform.transform.translation.x = msg.pose.position.x
        transform.transform.translation.y = msg.pose.position.y
        transform.transform.translation.z = msg.pose.position.z
        
        # Set rotation from pose message
        transform.transform.rotation = msg.pose.orientation
        
        # Broadcast transform
        self.tf_broadcaster.sendTransform(transform)

def main(args=None):
    rclpy.init(args=args)
    tf_relay = TFRelay()
    rclpy.spin(tf_relay)
    tf_relay.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main() 