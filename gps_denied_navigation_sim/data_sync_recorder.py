import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu, NavSatFix, LaserScan
from mavros_msgs.msg import Altitude

import os
import csv
from cv_bridge import CvBridge
import message_filters
from message_filters import ApproximateTimeSynchronizer

from std_srvs.srv import SetBool

import cv2

class DataSyncRecorder(Node):
    QUEUE_SIZE = 10

    def __init__(self):
        super().__init__('data_sync_recorder')

        self.data_saving_enabled = False

        self.declare_parameter("record_directory", "/home/user/shared_volume/data_recordings/")
        self.record_directory_ = self.get_parameter('record_directory').get_parameter_value().string_value

        self.declare_parameter("file_name", "recorded_data")
        self.file_name_ = self.get_parameter('file_name').get_parameter_value().string_value

        self.create_folder(self.record_directory_)

        self.csv_file_ = None
        self.csv_writer_ = None

        self.bridge = CvBridge()

        self.create_services()
        self.setup_subscribers()

    def create_services(self):
        self.start_service = self.create_service(SetBool, 'start_recording', self.start_recording_callback)
        self.stop_service = self.create_service(SetBool, 'stop_recording', self.stop_recording_callback)

    def start_recording_callback(self, request, response):
        self.data_saving_enabled = request.data
        if self.data_saving_enabled:
            self.start_new_csv_file()
            response.success = True
            response.message = "Data recording started."
        else:
            response.success = False
            response.message = "Data recording not started."
        return response

    def stop_recording_callback(self, request, response):
        if request.data and self.data_saving_enabled:
            self.data_saving_enabled = False
            if self.csv_file_:
                self.csv_file_.close()
            response.success = True
            response.message = "Data recording stopped."
        else:
            response.success = False
            response.message = "Data recording not stopped."
        return response

    def start_new_csv_file(self):
        self.csv_file_ = open(os.path.join(self.record_directory_, f"{self.file_name_}.csv"), 'w', newline='')
        self.csv_writer_ = csv.writer(self.csv_file_)
        self.csv_writer_.writerow(["timestamp", "image_name",
                                   "tx", "ty", "tz", "vel_x", "vel_y", "vel_z",
                                   "orientation_x", "orientation_y", "orientation_z", "orientation_w",
                                   "angular_vel_x", "angular_vel_y", "angular_vel_z",
                                   "linear_acc_x", "linear_acc_y", "linear_acc_z",
                                   "latitude", "longitude", "altitude",
                                   "lidar_range", "AMSL"])

    def create_folder(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

    def setup_subscribers(self):
        sensor_qos_profile = QoSProfile(
            depth=10,  # A larger queue size to handle high-frequency sensor data
            reliability=ReliabilityPolicy.BEST_EFFORT,  # Suitable for high-throughput data
            durability=DurabilityPolicy.VOLATILE,  # Only interested in the most recent values
            history=HistoryPolicy.KEEP_LAST  # Keep only a number of latest samples defined by the depth
        )

        self.odom_sub = message_filters.Subscriber(self, Odometry, 'mavros/local_position/odom', qos_profile=sensor_qos_profile)
        self.img_sub = message_filters.Subscriber(self, Image, '/target/rgb_image', qos_profile=sensor_qos_profile)
        self.imu_sub = message_filters.Subscriber(self, Imu, '/target/mavros/imu/data', qos_profile=sensor_qos_profile)
        self.gps_sub = message_filters.Subscriber(self, NavSatFix, '/target/mavros/global_position/raw/fix', qos_profile=sensor_qos_profile)
        self.lidar_sub = message_filters.Subscriber(self, LaserScan, '/scan', qos_profile=sensor_qos_profile)
        self.amsl_sub = message_filters.Subscriber(self, Altitude, '/target/mavros/altitude', qos_profile=sensor_qos_profile)

        self.time_synchronizer = ApproximateTimeSynchronizer(
            [self.odom_sub, self.img_sub, self.imu_sub, self.gps_sub, self.lidar_sub, self.amsl_sub],
            self.QUEUE_SIZE,
            slop=0.15
        )
        self.time_synchronizer.registerCallback(self.data_callback)

    def data_callback(self, odom_msg, img_msg, imu_msg, gps_msg, lidar_msg, amsl_msg):
        if not self.data_saving_enabled:
            return

        t = odom_msg.header.stamp.sec + odom_msg.header.stamp.nanosec * 1e-9
        tx, ty, tz = odom_msg.pose.pose.position.x, odom_msg.pose.pose.position.y, odom_msg.pose.pose.position.z
        vel_x, vel_y, vel_z = odom_msg.twist.twist.linear.x, odom_msg.twist.twist.linear.y, odom_msg.twist.twist.linear.z
        orientation_x, orientation_y, orientation_z, orientation_w = imu_msg.orientation.x, imu_msg.orientation.y, imu_msg.orientation.z, imu_msg.orientation.w
        angular_velocity_x, angular_velocity_y, angular_velocity_z = imu_msg.angular_velocity.x, imu_msg.angular_velocity.y, imu_msg.angular_velocity.z
        linear_acceleration_x, linear_acceleration_y, linear_acceleration_z = imu_msg.linear_acceleration.x, imu_msg.linear_acceleration.y, imu_msg.linear_acceleration.z
        latitude, longitude, altitude = gps_msg.latitude, gps_msg.longitude, gps_msg.altitude
        lidar_range = lidar_msg.ranges[0] if lidar_msg.ranges else None
        amsl_val = amsl_msg.amsl

        image_name = f"{self.file_name_}_{odom_msg.header.stamp.sec}_{odom_msg.header.stamp.nanosec}.png"
        cv_image_rgb = self.bridge.imgmsg_to_cv2(img_msg, "bgr8")
        cv2.imwrite(os.path.join(self.record_directory_, image_name), cv_image_rgb)

        data_to_write = [
            t, image_name,
            tx, ty, tz, vel_x, vel_y, vel_z,
            orientation_x, orientation_y, orientation_z, orientation_w,
            angular_velocity_x, angular_velocity_y, angular_velocity_z,
            linear_acceleration_x, linear_acceleration_y, linear_acceleration_z,
            latitude, longitude, altitude,
            lidar_range, amsl_val
        ]
        data_to_write = [str(value) if value is not None else 'None' for value in data_to_write]
        self.csv_writer_.writerow(data_to_write)

def main(args=None):
    rclpy.init(args=args)

    data_sync_recorder = DataSyncRecorder()

    rclpy.spin(data_sync_recorder)

    data_sync_recorder.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
