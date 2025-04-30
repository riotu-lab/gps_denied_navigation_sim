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
                   
                   '-r', '/camera:='+ns+'/camera',
                   '-r', '/camera_info:='+ns+'/camera_info',
                   '-r', '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu:='+ns+'/imu',

                   ],
        parameters=[
            {'verbose': True}
        ],
    )
   
    # Add stereo_image_proc node for stereo processing
    stereo_image_proc_node = Node(
        package='stereo_image_proc',
        executable='disparity_node',
        name='stereo_image_proc',
        namespace=f'{ns}/stereo',
        remappings=[
            ('left/image_rect', 'left/image_raw'),
            ('left/camera_info', 'left/camera_info'),
            ('right/image_rect', 'right/image_raw'),
            ('right/camera_info', 'right/camera_info'),
            ('disparity', 'disparity')
        ],
        parameters=[
            {'approximate_sync': True}
        ]
    )
    
    # Add camera info publishers for stereo cameras
    camera_info_publisher = Node(
        package='gps_denied_navigation_sim',
        executable='camera_info_publisher',
        name='camera_info_publisher',
        namespace=f'{ns}',
        parameters=[
            {'left_camera_topic': f'stereo/left/camera_info'},
            {'right_camera_topic': f'stereo/right/camera_info'},
            {'frame_rate': 30.0}
        ]
    )
    
    random_trajectories_node = Node(
        package='gps_denied_navigation_sim',
        executable='execute_random_trajectories',
        output='screen',
        name='execute_random_trajectories',
        namespace=ns,
        parameters=[{'system_id': 1},
                    {'radius_bounds': [100.0, 2500.0]},
                    {'omega_bounds': [1.0,2.0]},
                    {'xyz_bound_min': [-100.0, -100.0, 1000.0]},
                    {'xyz_bound_max': [100.0, 100.0, 1500.0]},
                    {'num_traj': 5},
                    {'traj_2D': False},
                    {'traj_directory': '/home/user/shared_volume/gazebo_trajectories/'},
                    {'file_name': 'gazebo_trajectory2D'},
                    {'rgb_image_directory': '/home/user/shared_volume/gazebo_trajectories/rbg_images'}

        ],
        remappings=[
            ('mavros/state', 'mavros/state'),
            ('mavros/local_position/odom', 'mavros/local_position/odom'),
            ('mavros/setpoint_raw/local', 'mavros/setpoint_raw/local')
        ]
    )
    
    gimbal_node = Node(
        package='gps_denied_navigation_sim',
        executable='gimbal_stabilizer',
        name='gimbal_stabilizer',
        output='screen',
         )

    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_file_path],
        )

    # Define nodes that should be included based on localization_model
    if localization_model == 'mins':
        return [
            gz_launch,
            map2pose_tf_node,
            base2lidar_tf_node,
            mavros_launch,
            # random_trajectories_node,  # Uncomment if you want this node
            gimbal_node,
            ros_gz_bridge,
            stereo_image_proc_node,
            camera_info_publisher,
            rviz_node,
        ]
    elif localization_model == 'ov':
        return [
            gz_launch,
            map2pose_tf_node,
            base2lidar_tf_node,
            mavros_launch,
            # random_trajectories_node,  # Uncomment if you want this node
            gimbal_node,
            ros_gz_bridge,
            stereo_image_proc_node,
            camera_info_publisher,
            rviz_node
        ]
    else:
        return [
            gz_launch,
            map2pose_tf_node,
            base2lidar_tf_node,
            mavros_launch,
            # random_trajectories_node,  # Uncomment if you want this node
            gimbal_node,
            ros_gz_bridge,
            stereo_image_proc_node,
            camera_info_publisher,
            rviz_node
        ]

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'world_type',
            default_value='default',
            description='Gazebo world to use'),
        DeclareLaunchArgument(
            'localization_model',
            default_value='none',
            description='Localization model to use (mins, ov, or none)'),
        OpaqueFunction(function=launch_setup)
    ]) 