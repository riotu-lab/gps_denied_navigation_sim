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
        rviz_file_name = 'gps_denied_localization.rviz'
    else:
        rviz_file_name = 'gps_denied_localization.rviz'
    rviz_file_path = os.path.join(package_share_directory, 'rviz', rviz_file_name)

    # gz node
    m_name = 'x500_mono_cam_3d_lidar'
    model_name = {'gz_model_name': m_name}
    m_id=0
    # for original dem use dem_world
    # for Taif DEM use taif_world
    # For empty world use default
    w_name='taif_test'
    # w_name='taif_world2'
    # w_name='tugbot_depot'
    world_name = {'gz_world': w_name}
    autostart_id = {'px4_autostart_id': '4022'}
    instance_id = {'instance_id': f'{m_id}'}
    # for taif DEM use
    # xpos = {'xpos': '135.0'}
    # ypos = {'ypos': '100.0'}
    # zpos = {'zpos': '2000.0'}

    # For original DEM use
    # xpos = {'xpos': '0.0'}
    # ypos = {'ypos': '200.0'}
    # zpos = {'zpos': '900.0'}
    
    # xpos = {'xpos': '-50.0'}
    # ypos = {'ypos': '100.0'}
    # zpos = {'zpos': '2000.0'}
    xpos = {'xpos': '-97.800292'}
    ypos = {'ypos': '-293.259292'}
    zpos = {'zpos': '58.0'}
    headless= {'headless' : '0'}

    # Namespace
    ns='target'

    # PX4 SITL + Spawn x3
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gps_denied_navigation_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_ns': ns,
            'headless': headless['headless'],
            'gz_model_name': model_name['gz_model_name'],
            'gz_world': w_name,
            'px4_autostart_id': '4022',
            'instance_id': f'{m_id}',
            'xpos': xpos,
            'ypos': ypos,
            'zpos': zpos
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
                'launch',
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
                   '/camera@sensor_msgs/msg/Image[ignition.msgs.Image',
                   '/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                   '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',

                   '/gimbal/cmd_yaw@std_msgs/msg/Float64]ignition.msgs.Double',
                   '/gimbal/cmd_roll@std_msgs/msg/Float64]ignition.msgs.Double',
                   '/gimbal/cmd_pitch@std_msgs/msg/Float64]ignition.msgs.Double',
                   '/imu_gimbal@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                   '--ros-args', '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/image:='+ns+'/gimbal/camera',
                   '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/camera_info:='+ns+'/gimbal/camera_info',
                   '-r', '/camera:='+ns+'/camera',
                   '-r', '/camera_info:='+ns+'/camera_info',
                   '-r', '/world/'+w_name+'/model/'+m_name+f'_{m_id}' +'/link/base_link/sensor/imu_sensor/imu:='+ns+'/imu',

                   ],
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
    # random_trajectories_node = Node(
    #     package='gps_denied_navigation_sim',
    #     executable='execute_random_trajectories',
    #     output='screen',
    #     name='execute_random_trajectories',
    #     namespace=ns,
    #     parameters=[{'system_id': 1},
    #                 {'radius_bounds': [1.0, 2.0]},
    #                 {'omega_bounds': [1.0,2.0]},
    #                 {'xyz_bound_min': [-10.0, -10.0, 100.0]},
    #                 {'xyz_bound_max': [10.0, 10.0, 150.0]},
    #                 {'num_traj': 5},
    #                 {'traj_2D': False},
    #                 {'traj_directory': '/home/user/shared_volume/gazebo_trajectories/'},
    #                 {'file_name': 'gazebo_trajectory2D'},
    #                 {'rgb_image_directory': '/home/user/shared_volume/gazebo_trajectories/rbg_images'}

    #     ],
    #     remappings=[
    #         ('mavros/state', 'mavros/state'),
    #         ('mavros/local_position/odom', 'mavros/local_position/odom'),
    #         ('mavros/setpoint_raw/local', 'mavros/setpoint_raw/local')
    #     ]
    # )
    gimbal_node = Node(
        package='gps_denied_navigation_sim',
        executable='gimbal_stabilizer',
        name='gimbal_stabilizer',
        output='screen',
         )

    # Adaptive image stitcher for camera feeds (handles single camera automatically)
    adaptive_image_stitcher_node = Node(
        package='gps_denied_navigation_sim',
        executable='adaptive_image_stitcher',
        name='adaptive_image_stitcher',
        parameters=[
            {'use_sim_time': True},
            {'namespace_filter': f'/{ns}/'},  # Auto-detect cameras in the target namespace
            {'output_topic': f'/{ns}/camera/stitched_image'},
            {'verbose': False},  # Disable debug messages
            {'discovery_timeout': 10.0},  # Give more time for camera discovery
            {'stitch_rate': 10.0}
        ],
        output='log',  # Redirect output to log file instead of terminal
    )

    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_file_path],
        )
    
    # Add MINS node
    mins_node = Node(
        package='mins',
        executable='mins',
        name='mins_node',
        output='screen',
        # Add any parameters if needed
        parameters=[
            {'config_path': 'ros2_ws/src/gps_denied_navigation_sim/config/mins/config.yaml'}
        ]
    )

    # Add static identity transform between map and global
    map2global_tf_node = Node(
        package='tf2_ros',
        name='map2global_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'global', 'map'],
    )

    # Add static identity transform between map and global
    camerainit2map_tf_node = Node(
        package='tf2_ros',
        name='camerainit2map_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '1.5708', '1.5708', '0', ns+'/'+odom_frame, 'camera_init'],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
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
        gz_launch,
        map2pose_tf_node,
        base2lidar_tf_node,
        mavros_launch,
        # random_trajectories_node,  # Uncomment if you want this node
        gimbal_node,
        adaptive_image_stitcher_node,
        ros_gz_bridge,
        rviz_node,
        # mins_node,
        map2global_tf_node,
        camerainit2map_tf_node,
        # lidar_link2lidar0_tf_node,
        # imu2base_link_tf_node,
    ]

def generate_launch_description():
    ld = LaunchDescription()
    world_type_arg = DeclareLaunchArgument(
        'world_type', default_value='taif_world', description='World type: taif_world, dem_world, tugbot_depot')
    localization_model_arg = DeclareLaunchArgument(
        'localization_model', default_value='mins', description='Localization model: mins or ov')

    ld.add_action(world_type_arg)
    ld.add_action(localization_model_arg)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
