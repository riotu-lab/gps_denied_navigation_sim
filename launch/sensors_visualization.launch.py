#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('gps_denied_navigation_sim')
    
    # Configuration files
    cam_config = os.path.join(pkg_share, 'config', 'mins_twin_stereo_cam', 'config_camera.yaml')
    lidar_config = os.path.join(pkg_share, 'config', 'mins_twin_stereo_cam', 'config_lidar.yaml')
    
    # RViz config file
    rviz_config = os.path.join(pkg_share, 'rviz', 'sensors_visualization.rviz')
    
    # Nodes
    sensors_viz_node = Node(
        package='gps_denied_navigation_sim',
        executable='sensors_visualization',
        name='sensors_visualization_node',
        parameters=[
            {'config_file': cam_config},
            {'lidar_config_file': lidar_config},
            {'publish_rate': 15.0}
        ],
        output='screen'
    )
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen'
    )
    
    return LaunchDescription([
        sensors_viz_node,
        rviz_node
    ]) 