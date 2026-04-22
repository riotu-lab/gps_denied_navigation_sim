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
        self.declare_parameter('queue_size', 10)
        self.declare_parameter('publish_rate', 30.0)
        
        # Get parameters
        self.source_topic = self.get_parameter('source_topic').value
        self.target_frame_id = self.get_parameter('target_frame_id').value
        self.child_frame_id = self.get_parameter('child_frame_id').value
        queue_size = self.get_parameter('queue_size').value
        self.publish_rate = self.get_parameter('publish_rate').value
        
        # Create subscriber to pose topic with configured queue size
        self.pose_sub = self.create_subscription(
            PoseStamped,
            self.source_topic,
            self.pose_callback,
            queue_size)
        
        # Create transform broadcaster
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        
        # Store the latest pose for republishing at a higher rate if needed
        self.latest_pose = None
        
        # Create a timer to publish transforms at a specified rate
        if self.publish_rate > 0:
            period = 1.0 / self.publish_rate
            self.timer = self.create_timer(period, self.timer_callback)
        
        self.get_logger().info(f'TF relay initialized from {self.source_topic} to transform {self.target_frame_id} -> {self.child_frame_id}')
        self.get_logger().info(f'Queue size: {queue_size}, Publish rate: {self.publish_rate} Hz')
    
    def pose_callback(self, msg):
        # Store the latest pose
        self.latest_pose = msg
        
        # If not using timer, broadcast transform immediately
        if self.publish_rate <= 0:
            self.broadcast_transform(msg)
    
    def timer_callback(self):
        # Republish the latest transform at the timer rate
        if self.latest_pose is not None:
            self.broadcast_transform(self.latest_pose)
    
    def broadcast_transform(self, msg):
        # Create transform message
        transform = TransformStamped()
        
        # Use current time if using sim_time, otherwise use message time
        if self.get_parameter('use_sim_time').value:
            transform.header.stamp = self.get_clock().now().to_msg()
        else:
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