#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import yaml

def launch_setup(context, *args, **kwargs):
    # Get launch arguments
    use_stereo = LaunchConfiguration('use_stereo').perform(context) == 'true'
    use_rviz = LaunchConfiguration('use_rviz').perform(context) == 'true'
    
    # Set up paths
    openvins_config_path = LaunchConfiguration('config_path').perform(context)
    if not openvins_config_path:
        openvins_config_path = os.path.join(
            get_package_share_directory('gps_denied_navigation_sim'), 
            'config', 'openvins_gpsd_sim'
        )
    
    # Determine which config files to use based on stereo mode
    if use_stereo:
        config_file = os.path.join(openvins_config_path, "estimator_config.yaml")
    else:
        config_file = os.path.join(openvins_config_path, "estimator_config_mono.yaml")
    
    # Verify the config file exists
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    # Read config file to determine verbosity level
    try:
        with open(config_file, 'r') as f:
            # Skip first line which contains %YAML:1.0
            f.readline()
            config = yaml.safe_load(f)
            verbosity = config.get('verbosity', 'DEBUG')
    except Exception as e:
        print(f"Error reading config file: {e}")
        verbosity = 'DEBUG'
    
    # OpenVINS node
    openvins_node = Node(
        package='ov_msckf',
        executable='run_subscribe_msckf',
        name='ov_msckf',
        output='screen',
        parameters=[
            {'verbosity': verbosity},
            {'use_stereo': use_stereo},
            {'max_cameras': 2 if use_stereo else 1},
            {'config_path': config_file},
        ],
        arguments=[
            '--ros-args',
            '--log-level', 'debug'
        ]
    )
    
    # RViz node with appropriate config
    rviz_config_path = os.path.join(
        get_package_share_directory('gps_denied_navigation_sim'), 
        'dem_stereo_ov.rviz' if use_stereo else 'dem_ov.rviz'
    )
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        condition=IfCondition(LaunchConfiguration('use_rviz')),
        output='log',
        arguments=['-d', rviz_config_path, '--ros-args', '--log-level', 'error']
    )
    
    # Debug message for stereo mode
    print(f"\n{'='*80}")
    print(f"  OpenVINS Test Launch")
    print(f"  - Mode: {'Stereo' if use_stereo else 'Mono'}")
    print(f"  - Config: {config_file}")
    print(f"  - Verbosity: {verbosity}")
    print(f"{'='*80}\n")
    
    # Topic echo nodes for debugging
    left_echo_node = Node(
        package='topic_tools',
        executable='relay',
        name='left_cam_relay',
        parameters=[
            {'input_topic': '/target/stereo/left/image_raw'},
            {'output_topic': '/left_image_echo'}
        ],
        arguments=['--ros-args', '--log-level', 'error']
    )
    
    right_echo_node = Node(
        package='topic_tools',
        executable='relay',
        name='right_cam_relay',
        condition=IfCondition(LaunchConfiguration('use_stereo')),
        parameters=[
            {'input_topic': '/target/stereo/right/image_raw'},
            {'output_topic': '/right_image_echo'}
        ],
        arguments=['--ros-args', '--log-level', 'error']
    )
    
    imu_echo_node = Node(
        package='topic_tools',
        executable='relay',
        name='imu_relay',
        parameters=[
            {'input_topic': '/target/imu'},
            {'output_topic': '/imu_echo'}
        ],
        arguments=['--ros-args', '--log-level', 'error']
    )
    
    return [
        openvins_node,
        rviz_node,
        left_echo_node,
        right_echo_node,
        imu_echo_node
    ]

def generate_launch_description():
    return LaunchDescription([
        # Launch Arguments
        DeclareLaunchArgument(
            'use_stereo',
            default_value='true',
            description='Use stereo camera configuration if true, mono if false'
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz for visualization'
        ),
        DeclareLaunchArgument(
            'config_path',
            default_value='',
            description='Path to OpenVINS config directory. If empty, use default in gps_denied_navigation_sim package'
        ),
        
        # Launch setup via OpaqueFunction to access arg values
        OpaqueFunction(function=launch_setup)
    ]) 