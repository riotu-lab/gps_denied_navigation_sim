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
        rviz_file_name = 'dem_stereo_ov.rviz'
    else:
        rviz_file_name = 'dem_stereo_mins.rviz'
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
                'gz_sim.launch.py'
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
                'mavros.launch.py'
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

    # Static TF map(or world) -> local_pose_ENU
    map_frame = 'map'
    odom_frame= 'odom'
    map2pose_tf_node = Node(
        package='tf2_ros',
        name='map2px4_'+ns+'_tf_node',
        executable='static_transform_publisher',
        arguments=[xpos, ypos, '0', '0', '0', '0', map_frame, ns+'/'+odom_frame],
    )

    # Static TF target/base_link to lidar link
    # The valuse are taken from the model.sdf of x500_d435_3d_lidar
    base_frame = 'target/base_link'
    lidar_frame= 'lidar_link'
    base2lidar_tf_node = Node(
        package='tf2_ros',
        name='base2lidar_'+ns+'_tf_node',
        executable='static_transform_publisher',
        arguments=[str(0), str(0), '0.12', '0', '1.5707963267948966', '0', base_frame, lidar_frame],
    )
    
    # Static TF for stereo cameras - Make sure the transformations match those in kalibr_imucam_chain.yaml
    base2left_cam_tf_node = Node(
        package='tf2_ros',
        name='base2left_stereo_tf_node',
        executable='static_transform_publisher',
        # Position: 0.10 in x, -0.05 in y, 0.0 in z
        # Orientation: Camera optical frame has x forward, y to left, z up while base link has x forward, y right, z up
        # So we need a rotation that maps:
        # x_base -> z_cam, y_base -> -x_cam, z_base -> -y_cam
        # This is a 90 degree rotation around x followed by 90 degrees around the resulting z
        arguments=['0.10', '-0.05', '0.0', '1.57079632679', '0', '1.57079632679', base_frame, f'{ns}/stereo/left_camera_optical_frame'],
    )
    
    base2right_cam_tf_node = Node(
        package='tf2_ros',
        name='base2right_stereo_tf_node',
        executable='static_transform_publisher',
        # Position: 0.10 in x, 0.05 in y, 0.0 in z (just position change compared to left camera)
        arguments=['0.10', '0.05', '0.0', '1.57079632679', '0', '1.57079632679', base_frame, f'{ns}/stereo/right_camera_optical_frame'],
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
                  
                  # Bridge for left and right stereo camera topics - updated with actual topic names
                  '/left_camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                  '/right_camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                  # Add camera info bridges even though we're generating our own
                  '/left_camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  '/right_camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  
                  '/camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                  '/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',

                  '/gimbal/cmd_yaw@std_msgs/msg/Float64]ignition.msgs.Double',
                  '/gimbal/cmd_roll@std_msgs/msg/Float64]ignition.msgs.Double',
                  '/gimbal/cmd_pitch@std_msgs/msg/Float64]ignition.msgs.Double',
                  '/imu_gimbal@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                  '--ros-args', '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/image:='+ns+'/gimbal/camera',
                  '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/camera_info:='+ns+'/gimbal/camera_info',
                  
                  # Remappings for left and right stereo camera topics - updated with actual topic names
                  '-r', '/left_camera:='+ns+'/stereo/left/image_raw',
                  '-r', '/right_camera:='+ns+'/stereo/right/image_raw',
                  '-r', '/left_camera_info:='+ns+'/stereo/left/camera_info',
                  '-r', '/right_camera_info:='+ns+'/stereo/right/camera_info',
                  
                  '-r', '/camera:='+ns+'/camera',
                  '-r', '/camera_info:='+ns+'/camera_info',
                  '-r', '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu:='+ns+'/imu',

                  ],
        parameters=[
            {'verbose': False}
        ],
    )
   
    # Add stereo_image_proc disparity node for synchronized stereo processing
    stereo_image_proc_node = Node(
        package='stereo_image_proc',
        executable='disparity_node',
        name='stereo_image_proc',
        namespace=f'{ns}/stereo',
        parameters=[
            {'approximate_sync': True},
            {'queue_size': 10},
            {'use_color': False}
        ],
        remappings=[
            ('left/image_raw', f'/{ns}/stereo/left/image_raw'),
            ('left/camera_info', f'/{ns}/stereo/left/camera_info'),
            ('right/image_raw', f'/{ns}/stereo/right/image_raw'),
            ('right/camera_info', f'/{ns}/stereo/right/camera_info'),
        ],
        output='screen',
    )
    
    # Add stereo_image_proc point cloud node for 3D reconstruction
    stereo_point_cloud_node = Node(
        package='stereo_image_proc',
        executable='point_cloud_node',
        name='stereo_point_cloud',
        namespace=f'{ns}/stereo',
        parameters=[
            {'approximate_sync': True},
            {'queue_size': 10}
        ],
        remappings=[
            ('left/image_rect', f'/{ns}/stereo/left/image_raw'),
            ('left/camera_info', f'/{ns}/stereo/left/camera_info'),
            ('right/image_rect', f'/{ns}/stereo/right/image_raw'),
            ('right/camera_info', f'/{ns}/stereo/right/camera_info'),
            ('disparity', f'/{ns}/stereo/disparity'),
            ('points2', f'/{ns}/stereo/points2')
        ],
        output='screen',
    )
    
    # Add a debug node to print ROS topics for monitoring
    debug_node = Node(
        package='gps_denied_navigation_sim',
        executable='test_stereo',
        name='stereo_monitor',
        output='screen',
        parameters=[
            {'do_stereo_processing': False}  # Disable OpenCV processing to avoid NumPy errors
        ]
    )
    
    # Enhanced camera_info_publisher with improved parameters to match kalibr calibration
    camera_info_publisher = Node(
        package='gps_denied_navigation_sim',
        executable='camera_info_publisher',
        name='camera_info_publisher',
        parameters=[
            {'robot_name': ns},
            {'camera_frame_id': f'{ns}/stereo/left_camera_optical_frame'},
            {'camera_frame_id_right': f'{ns}/stereo/right_camera_optical_frame'},
            {'camera_topic_left': f'/{ns}/stereo/left/image_raw'},
            {'camera_topic_right': f'/{ns}/stereo/right/image_raw'},
            {'camera_info_topic_left': f'/{ns}/stereo/left/camera_info'},
            {'camera_info_topic_right': f'/{ns}/stereo/right/camera_info'},
            {'publish_image_as_both': True},  # This will republish raw images to both topics
            {'stereo_camera': True},
            {'baseline': 0.1},  # 10cm baseline matches calibration
            {'image_width': 752},  # Matches calibration
            {'image_height': 480},  # Matches calibration
            {'focal_length': 450.0},  # Matches calibration
            {'left_frame_id': f'{ns}/stereo/left_camera_optical_frame'},
            {'right_frame_id': f'{ns}/stereo/right_camera_optical_frame'}
        ],
        output='screen',
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
            ros_arguments=['--log-level', 'error']  # Set ROS log level properly
        )
    
    # Add static identity transform between map and global
    map2global_tf_node = Node(
        package='tf2_ros',
        name='map2global_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'global', 'map'],
    )

    # Define nodes that should be included based on localization_model
    if localization_model == 'mins':
        return [
            gz_launch,
            map2pose_tf_node,
            base2lidar_tf_node,
            base2left_cam_tf_node,
            base2right_cam_tf_node,
            mavros_launch,
            gimbal_node,
            ros_gz_bridge,
            stereo_image_proc_node,
            stereo_point_cloud_node,
            camera_info_publisher,
            debug_node,
            rviz_node,
            map2global_tf_node,
        ]
    elif localization_model == 'ov':
        return [
            gz_launch,
            map2pose_tf_node,
            base2lidar_tf_node,
            base2left_cam_tf_node,
            base2right_cam_tf_node,
            mavros_launch,
            gimbal_node,
            ros_gz_bridge,
            stereo_image_proc_node,
            stereo_point_cloud_node,
            camera_info_publisher,
            debug_node,
            rviz_node,
            map2global_tf_node,
        ]
    else:
        return [
            gz_launch,
            map2pose_tf_node,
            base2lidar_tf_node,
            base2left_cam_tf_node,
            base2right_cam_tf_node,
            mavros_launch,
            gimbal_node,
            ros_gz_bridge,
            stereo_image_proc_node,
            stereo_point_cloud_node,
            camera_info_publisher,
            debug_node,
            rviz_node,
            map2global_tf_node,
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