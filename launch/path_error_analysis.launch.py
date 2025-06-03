#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import os

def generate_launch_description():
    # Declare launch arguments
    output_directory_arg = DeclareLaunchArgument(
        'output_directory',
        default_value='/home/user/shared_volume/error_analysis/',
        description='Directory to save error analysis files'
    )
    
    file_name_arg = DeclareLaunchArgument(
        'file_name',
        default_value='path_error_analysis',
        description='Base filename for error analysis outputs'
    )
    
    max_time_diff_arg = DeclareLaunchArgument(
        'max_time_diff',
        default_value='0.1',
        description='Maximum time difference for pose association (seconds)'
    )
    
    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='10.0',
        description='Rate for publishing error metrics (Hz)'
    )

    # Path Error Calculator Node
    path_error_calculator_node = Node(
        package='gps_denied_navigation_sim',
        executable='path_error_calculator',
        name='path_error_calculator',
        output='screen',
        parameters=[{
            'output_directory': LaunchConfiguration('output_directory'),
            'file_name': LaunchConfiguration('file_name'),
            'max_time_diff': LaunchConfiguration('max_time_diff'),
            'publish_rate': LaunchConfiguration('publish_rate'),
        }],
        remappings=[
            # Add any topic remappings if needed
            # ('/target/gt_path', '/your/gt/path/topic'),
            # ('/mins/imu/path', '/your/estimated/path/topic'),
        ]
    )

    return LaunchDescription([
        output_directory_arg,
        file_name_arg,
        max_time_diff_arg,
        publish_rate_arg,
        path_error_calculator_node,
    ]) 