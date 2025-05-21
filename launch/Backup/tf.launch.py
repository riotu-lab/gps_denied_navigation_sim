#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction
from launch_ros.actions import Node
from ament_index_python import get_package_share_directory
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration

def launch_setup(context, *args, **kwargs):

    # Add static identity transform between map and global
    map2global_tf_node = Node(
        package='tf2_ros',
        name='map2global_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'global', 'map'],
    )

    # Add static transform between lidar_link and lidar0
    lidar_link2lidar0_tf_node = Node(
        package='tf2_ros',
        name='lidar_link2lidar0_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'lidar_link', 'lidar0'],
    )

    # Add static transform between imu and target/base_link
    imu2base_link_tf_node = Node(
        package='tf2_ros',
        name='imu2base_link_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'imu', 'target/base_link'],
    )

    # Add all your actions to a list and return
    return [
        map2global_tf_node,
        lidar_link2lidar0_tf_node,
        imu2base_link_tf_node,
    ]
