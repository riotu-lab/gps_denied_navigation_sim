#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from ament_index_python import get_package_share_directory
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution

def generate_launch_description():
    ld = LaunchDescription()

    # gz node
    m_name = 'x500_mono_cam_3d_lidar'
    model_name = {'gz_model_name': m_name}
    m_id=0
    # for original dem use dem_world
    # for Taif DEM use taif_world
    # For empty world use default
    w_name='taif_world'
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
    
    xpos = {'xpos': '135.0'}
    ypos = {'ypos': '100.0'}
    zpos = {'zpos': '2000.0'}
    # xpos = {'xpos': '0.0'}
    # ypos = {'ypos': '0.0'}
    # zpos = {'zpos': '0.1'}
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
            'gz_world': world_name['gz_world'],
            'px4_autostart_id': autostart_id['px4_autostart_id'],
            'instance_id': instance_id['instance_id'],
            'xpos': xpos['xpos'],
            'ypos': ypos['ypos'],
            'zpos': zpos['zpos']
        }.items()
    )

    # MAVROS
    file_name = 'target_px4_pluginlists.yaml'
    package_share_directory = get_package_share_directory('gps_denied_navigation_sim')
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
        arguments=[str(xpos['xpos']), str(ypos['ypos']), '0', '0', '0', '0', map_frame, ns+'/'+odom_frame],
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

                   '/gimbal/cmd_yaw@std_msgs/msg/Float64]ignition.msgs.Double',
                   '/gimbal/cmd_roll@std_msgs/msg/Float64]ignition.msgs.Double',
                   '/gimbal/cmd_pitch@std_msgs/msg/Float64]ignition.msgs.Double',
                   '/imu_gimbal@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                   '--ros-args', '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/image:='+ns+'/gimbal/camera',
                   '-r', '/world/'+w_name+'/model/'+ m_name +f'_{m_id}' +'/link/pitch_link/sensor/camera/camera_info:='+ns+'/gimbal/camera_info',
                   '-r', '/camera:='+ns+'/camera',
                   '-r', '/camera_info:='+ns+'/camera_info',

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

    rviz_file_name = 'dem.rviz'
    package_share_directory = get_package_share_directory('gps_denied_navigation_sim')
    rviz_file_path = os.path.join(package_share_directory, rviz_file_name)
    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_file_path],
        )


    ld.add_action(gz_launch)
    ld.add_action(map2pose_tf_node)
    ld.add_action(base2lidar_tf_node)
    ld.add_action(mavros_launch)
    # ld.add_action(random_trajectories_node)
    ld.add_action(gimbal_node)
    ld.add_action(ros_gz_bridge)
    ld.add_action(rviz_node)
    return ld
