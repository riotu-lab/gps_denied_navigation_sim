import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float64
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from transformations import euler_from_quaternion
import tf2_ros
import math

class GimbalStabilizer(Node):
    def __init__(self):
        super().__init__('gimbal_stabilizer')
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.imu_sub = self.create_subscription(
            Imu,
            '/imu_gimbal',
            self.imu_callback,
            qos_profile=qos_profile_sensor_data
        )

        self.pitch_pub = self.create_publisher(Float64, '/gimbal/cmd_pitch', 10)
        self.roll_pub = self.create_publisher(Float64, '/gimbal/cmd_roll', 10)
        self.yaw_pub = self.create_publisher(Float64, '/gimbal/cmd_yaw', 10)

        self.pitch_cmd = 0.0
        self.roll_cmd = 0.0
        self.yaw_cmd = 0.0
        self.get_logger().info('Gimbal Stabilizer.')

    def imu_callback(self, imu_msg: Imu):
        quaternion = (
            imu_msg.orientation.w,
            imu_msg.orientation.x,
            imu_msg.orientation.y,
            imu_msg.orientation.z)
        
        # self.get_logger().info('orientation_x: {:.2f}, orientation_y: {:.2f}, orientation_z: {:.2f}'.format(imu_msg.orientation.x, imu_msg.orientation.y, imu_msg.orientation.z))

        euler = euler_from_quaternion(quaternion)
        self.roll_cmd  = -euler[0]
        self.pitch_cmd = -euler[1]
        # self.get_logger().info('Roll: {:.2f}, Pitch: {:.2f}, Yaw: {:.2f}'.format(self.roll_cmd, self.pitch_cmd, self.yaw_cmd))

        self.pitch_pub.publish(Float64(data=self.pitch_cmd))
        self.roll_pub.publish(Float64(data=self.roll_cmd))
        # self.yaw_pub.publish(Float64(data=self.yaw_cmd))

def main(args=None):
    rclpy.init(args=args)

    gimbal_stabilizer = GimbalStabilizer()

    rclpy.spin(gimbal_stabilizer)

    gimbal_stabilizer.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
