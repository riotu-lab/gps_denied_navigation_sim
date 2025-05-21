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
    world_type = LaunchConfiguration('world_type').perform(context)
    localization_model = LaunchConfiguration('localization_model').perform(context)

    # Set world and position based on world_type
    if world_type == 'taif_world':
        xpos, ypos, zpos = '-50.0', '100.0', '2000.0'
    elif world_type == 'dem_world':
        xpos, ypos, zpos = '0.0', '200.0', '900.0'
    elif world_type == 'tugbot_depot':
        xpos, ypos, zpos = '0.0', '0.0', '0.1'
    else:
        xpos, ypos, zpos = '0.0', '0.0', '1.0'
    w_name = world_type

    # RViz config selection
    package_share_directory = get_package_share_directory('gps_denied_navigation_sim')
    if localization_model == 'ov':
        rviz_file_name = 'rviz/dem_stereo_ov.rviz'
    else:
        rviz_file_name = 'rviz/dem_stereo_mins.rviz'
    rviz_file_path = os.path.join(package_share_directory, rviz_file_name)

    # gz node
    m_name = 'x500_stereo_cam_3d_lidar'
    model_name = {'gz_model_name': m_name}
    m_id=0
    # for original dem use dem_world
    # for Taif DEM use taif_world
    # For empty world use default
    # w_name='tugbot_depot'
    headless= {'headless' : '0'}

    # Namespace
    ns='target'

    # PX4 SITL + Spawn x3
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gps_denied_navigation_sim'),
                'launch/gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_ns': ns,
            'headless': headless['headless'],
            'gz_model_name': model_name['gz_model_name'],
            'gz_world': w_name,
            'px4_autostart_id': '4023',
            'instance_id': f'{m_id}',
            'xpos': xpos,
            'ypos': ypos,
            'zpos': zpos,
            'verbose': 'true'
        }.items()
    )

    # MAVROS
    file_name = 'target_px4_pluginlists.yaml'
    plugins_file_path = os.path.join(package_share_directory, file_name)
    file_name = 'target_px4_config.yaml'
    config_file_path = os.path.join(package_share_directory, file_name)
    mavros_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gps_denied_navigation_sim'),
                'launch/mavros.launch.py'
            ])
        ]),
        launch_arguments={
            'mavros_namespace' :ns+'/mavros',
            'tgt_system': '1',
            'fcu_url': 'udp://:14540@127.0.0.1:14557',
            'pluginlists_yaml': plugins_file_path,
            'config_yaml': config_file_path,
            'base_link_frame': 'target/base_link',
            'odom_frame': 'target/odom',
            'map_frame': 'map'
        }.items()
    )    

    # Add static identity transform between map and global
    map2global_tf_node = Node(
        package='tf2_ros',
        name='map2global_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'global', 'map'],
    )

    # Static TF map(or world) -> local_pose_ENU
    map_frame = 'map'
    odom_frame= 'odom'
    map2pose_tf_node = Node(
        package='tf2_ros',
        name='map2px4_'+ns+'_tf_node',
        executable='static_transform_publisher',
        arguments=[xpos, ypos, '0', '0', '0', '0', map_frame, ns+'/'+odom_frame],
    )

    base_frame = 'target/base_link'
    odom2base_tf_node = Node(
        package='tf2_ros',
        name='px42base_'+ns+'_tf_node',
        executable='static_transform_publisher',
        arguments=[xpos, ypos, '0', '0', '0', '0', ns+'/'+odom_frame, base_frame],
    )

    # Static TF target/base_link to lidar link
    # The valuse are taken from the model.sdf of x500_d435_3d_lidar
    lidar_frame= 'lidar3d_link'
    base2lidar_tf_node = Node(
        package='tf2_ros',
        name='base2lidar_'+ns+'_tf_node',
        executable='static_transform_publisher',
        arguments=[str(0), str(0), '0.12', '0', '1.5707963267948966', '0', base_frame, lidar_frame],
    )

    # Static TF base_link -> left_camera_link
    left_camera_tf_node = Node(
        package='tf2_ros',
        name='base_to_left_camera_tf',
        executable='static_transform_publisher',
        arguments=['0.20', '0.15', '0.10', '0', '0.0872', '0', '0.9962', base_frame, 'left_camera_link'],
    )

    # Static TF base_link -> right_camera_link
    right_camera_tf_node = Node(
        package='tf2_ros',
        name='base_to_right_camera_tf',
        executable='static_transform_publisher',
        arguments=['0.20', '-0.15', '0.10', '0', '0.0872', '0', '0.9962', base_frame, 'right_camera_link'],
    )

    # Load the robot model (URDF or SDF)
    model_path = os.path.join(package_share_directory, 'models/x500_stereo_cam_3d_lidar/model.sdf')
    with open(model_path, 'r') as file:
        robot_description_content = file.read()

    # Robot State Publisher to publish the URDF model
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}],
        remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')]
    )
    
    # Transport rgb and depth images from GZ topics to ROS topics    
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        name='ros_bridge_node_depthcam',
        executable='parameter_bridge',
        arguments=[
                  '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
                  '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
                  '/scan/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
                  '/lidar/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
                  '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                  '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' + '/link/pitch_link/sensor/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  
                  # Bridge for left and right stereo camera topics
                  '/left/camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                  '/right/camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                  '/left/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  '/right/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  
                  '/camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                  '/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',

                  '/gimbal/cmd_yaw@std_msgs/msg/Float64]ignition.msgs.Double',
                  '/gimbal/cmd_roll@std_msgs/msg/Float64]ignition.msgs.Double',
                  '/gimbal/cmd_pitch@std_msgs/msg/Float64]ignition.msgs.Double',
                  '/imu_gimbal@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                  '--ros-args', '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/image:='+ns+'/gimbal/camera',
                  '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/camera_info:='+ns+'/gimbal/camera_info',
                  
                  # Remappings for left and right stereo camera topics
                  '-r', '/left/camera:='+ns+'/stereo/left/image_raw',
                  '-r', '/right/camera:='+ns+'/stereo/right/image_raw',
                  '-r', '/left/camera_info:='+ns+'/stereo/left/camera_info',
                  '-r', '/right/camera_info:='+ns+'/stereo/right/camera_info',
                  
                  '-r', '/camera:='+ns+'/camera',
                  '-r', '/camera_info:='+ns+'/camera_info',
                  '-r', '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu:='+ns+'/imu',

                  ],
        parameters=[
            {'verbose': True}
        ],
    )
    
    gimbal_node = Node(
        package='gps_denied_navigation_sim',
        executable='gimbal_stabilizer',
        name='gimbal_stabilizer',
        output='log',
    )

    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',  # Change from 'log' to 'screen' to see any errors
            arguments=['-d', rviz_file_path],
            parameters=[],  # Empty parameters list
            # ros_arguments=['--log-level', 'error']  # Set ROS log level properly
        )

    return [
        gz_launch,
        map2pose_tf_node,
        odom2base_tf_node,
        base2lidar_tf_node,
        left_camera_tf_node,
        right_camera_tf_node,
        map2global_tf_node,
        robot_state_publisher,
        mavros_launch,
        gimbal_node,
        ros_gz_bridge,
        rviz_node,
    ]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'world_type',
            default_value='taif_world',
            description='Type of world to launch (taif_world, dem_world, tugbot_depot)'
        ),
        DeclareLaunchArgument(
            'localization_model',
            default_value='mins',
            description='Localization model to use (mins, ov)'
        ),
        OpaqueFunction(function=launch_setup)
    ]) 