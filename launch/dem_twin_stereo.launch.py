#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction, SetEnvironmentVariable
from launch_ros.actions import Node
from ament_index_python import get_package_share_directory
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration
import math

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
        rviz_file_name = 'dem.rviz'
    else:
        rviz_file_name = 'dem.rviz'
    rviz_file_path = os.path.join(package_share_directory, 'rviz', rviz_file_name)

    # gz node
    m_name = 'x500_twin_stereo_twin_velodyne'
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
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_ns': ns,
            'headless': headless['headless'],
            'gz_model_name': model_name['gz_model_name'],
            'gz_world': w_name,
            'px4_autostart_id': '4024',
            'instance_id': f'{m_id}',
            'xpos': xpos,
            'ypos': ypos,
            'zpos': zpos,
            'verbose': 'true',
            'use_sim_time': 'true'
        }.items()
    )

    # # Environment variable for ROS domain ID to ensure all nodes are on the same domain
    # ros_domain_id = SetEnvironmentVariable(
    #     name='ROS_DOMAIN_ID',
    #     value='71'
    # )

    # Set use_sim_time for all ROS nodes
    use_sim_time_env = SetEnvironmentVariable(
        name='ROS_PARAM_use_sim_time',
        value='true'
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
            'map_frame': 'map',
            'use_sim_time': 'true'
        }.items()
    )    

    # Add static identity transform between map and global
    map2global_tf_node = Node(
        package='tf2_ros',
        name='map2global_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'global', 'map'],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # Add static identity transform between map and global
    camerainit2map_tf_node = Node(
        package='tf2_ros',
        name='camerainit2map_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'camera_init'],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # Add map to map_frd transform (FRD = Forward-Right-Down)
    # This is a 90-degree rotation around X to convert from ENU to FRD
    map2map_frd_tf_node = Node(
        package='tf2_ros',
        name='map2map_frd_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '1.5708', '0', '1.5708', 'map', 'map_frd'],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # Static TF map(or world) -> local_pose_ENU
    map_frame = 'map'
    odom_frame= 'odom'
    map2pose_tf_node = Node(
        package='tf2_ros',
        name='map2px4_'+ns+'_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', map_frame, ns+'/'+odom_frame],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # Dynamic transform from target/odom to target/base_link using our custom tf_relay node
    odom2base_tf_node = Node(
        package='gps_denied_navigation_sim',
        executable='tf_relay',
        name='odom2base_tf_relay',
        parameters=[
            {'use_sim_time': True},
            {'source_topic': f'/{ns}/mavros/local_position/pose'},
            {'target_frame_id': f'{ns}/odom'},
            {'child_frame_id': f'{ns}/base_link'},
            {'queue_size': 50},  # Larger queue size for more reliable transformation
            {'publish_rate': 50.0}  # Higher publish rate (Hz) for smoother motion
        ],
        output='log',  # Redirect output to log file
    )

    # From SDF - Front lidar transform from base_link
    # <pose relative_to="base_link" degrees="true">0.05 0.0 -0.17 0 45 0</pose>
    base_frame = 'target/base_link'
    front_lidar_tf_node = Node(
        package='tf2_ros',
        name='front_lidar_tf_node',
        executable='static_transform_publisher',
        arguments=[
            '0.05', '0.0', '-0.17',                      # x y z (translation)
            str(math.radians(0)),                      # yaw
            str(math.radians(45)),                       # pitch
            str(math.radians(0)),                        # roll
            base_frame, 'front_lidar_link'               # parent, child
        ],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # Connect the Gazebo lidar frame to our TF tree for front lidar
    front_lidar2gazebo_tf_node = Node(
        package='tf2_ros',
        name='front_lidar2gazebo_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'front_lidar_link', 'x500_twin_stereo_twin_velodyne_0/front_lidar/lidar3d_link/velodyne_16'],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # From SDF - Rear lidar transform from base_link
    # <pose relative_to="base_link" degrees="true">-0.05 0.0 -0.17 0 45 180</pose>
    rear_lidar_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='rear_lidar_tf_node',
        arguments=[
            '-0.05', '0.0', '-0.17',                      # x y z (translation)
            str(math.radians(180)),                      # yaw
            str(math.radians(45)),                       # pitch
            str(math.radians(0)),                        # roll
            base_frame, 'rear_lidar_link'               # parent, child
        ],
        parameters=[{"use_sim_time": True}],
        output='log',  # Redirect output to log file
    )

    # Connect the Gazebo lidar frame to our TF tree for rear lidar
    rear_lidar2gazebo_tf_node = Node(
        package='tf2_ros',
        name='rear_lidar2gazebo_tf_node',
        executable='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'rear_lidar_link', 'x500_twin_stereo_twin_velodyne_0/rear_lidar/lidar3d_link/velodyne_16'],
        parameters=[
                {"use_sim_time": True},
        ],
        output='log',  # Redirect output to log file
    )

    # Static TF base_link -> left_camera_link
    left_camera_tf_node = Node(
        package='tf2_ros',
        name='base_to_left_camera_tf',
        executable='static_transform_publisher',
        arguments=['0.20', '0.15', '-0.10', '0', '0.0872', '0', '0.9962', base_frame, 'left_camera_link'],
        parameters=[
                {"use_sim_time": True},
        ],
    )

    # Static TF base_link -> right_camera_link
    right_camera_tf_node = Node(
        package='tf2_ros',
        name='base_to_right_camera_tf',
        executable='static_transform_publisher',
        arguments=['0.20', '-0.15', '-0.10', '0', '0.0872', '0', '0.9962', base_frame, 'right_camera_link'],
        parameters=[
                {"use_sim_time": True},
        ],
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
                  
                  # Bridge for front and rear lidar topics
                  f'/world/{w_name}/model/{m_name}_0/model/front_lidar/link/lidar3d_link/sensor/velodyne_16/scan/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
                  f'/world/{w_name}/model/{m_name}_0/model/rear_lidar/link/lidar3d_link/sensor/velodyne_16/scan/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
                  
                  # Bridge for front stereo camera topics
                  f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/left_camera_link/sensor/left_camera_sensor/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                  f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/right_camera_link/sensor/right_camera_sensor/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                  f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/left_camera_link/sensor/left_camera_sensor/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/right_camera_link/sensor/right_camera_sensor/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  
                  # Bridge for rear stereo camera topics
                  f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/left_camera_link/sensor/left_camera_sensor/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                  f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/right_camera_link/sensor/right_camera_sensor/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                  f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/left_camera_link/sensor/left_camera_sensor/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/right_camera_link/sensor/right_camera_sensor/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                  
                  # Bridge for IMU and other sensors
                  f'/world/{w_name}/model/{m_name}_0/model/x500/link/base_link/sensor/imu_sensor/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                  f'/world/{w_name}/model/{m_name}_0/model/x500/link/base_link/sensor/air_pressure_sensor/air_pressure@sensor_msgs/msg/FluidPressure[ignition.msgs.FluidPressure',
                  f'/world/{w_name}/model/{m_name}_0/model/x500/link/base_link/sensor/navsat_sensor/navsat@sensor_msgs/msg/NavSatFix[ignition.msgs.NavSat',
                  
                  '--ros-args',
                  # Remappings for front lidar
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/front_lidar/link/lidar3d_link/sensor/velodyne_16/scan/points:='+ns+'/front_lidar/points',
                  # Remappings for rear lidar
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/rear_lidar/link/lidar3d_link/sensor/velodyne_16/scan/points:='+ns+'/rear_lidar/points',
                  
                  # Remappings for front stereo camera
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/left_camera_link/sensor/left_camera_sensor/image:='+ns+'/front_stereo/left_cam/image_raw',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/right_camera_link/sensor/right_camera_sensor/image:='+ns+'/front_stereo/right_cam/image_raw',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/left_camera_link/sensor/left_camera_sensor/camera_info:='+ns+'/front_stereo/left_cam/camera_info',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/front_stereo/link/right_camera_link/sensor/right_camera_sensor/camera_info:='+ns+'/front_stereo/right_cam/camera_info',
                  
                  # Remappings for rear stereo camera
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/left_camera_link/sensor/left_camera_sensor/image:='+ns+'/rear_stereo/left_cam/image_raw',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/right_camera_link/sensor/right_camera_sensor/image:='+ns+'/rear_stereo/right_cam/image_raw',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/left_camera_link/sensor/left_camera_sensor/camera_info:='+ns+'/rear_stereo/left_cam/camera_info',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/rear_stereo/link/right_camera_link/sensor/right_camera_sensor/camera_info:='+ns+'/rear_stereo/right_cam/camera_info',
                  
                  # Remappings for IMU and other sensors
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/x500/link/base_link/sensor/imu_sensor/imu:='+ns+'/imu',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/x500/link/base_link/sensor/air_pressure_sensor/air_pressure:='+ns+'/air_pressure',
                  '-r', f'/world/{w_name}/model/{m_name}_0/model/x500/link/base_link/sensor/navsat_sensor/navsat:='+ns+'/gps',
                  ],
        parameters=[
            {'use_sim_time': True},
            {'verbose': False}  # Disable verbose output
        ],
        output='log',  # Redirect output to log file
    )
    
    gimbal_node = Node(
        package='gps_denied_navigation_sim',
        executable='gimbal_stabilizer',
        name='gimbal_stabilizer',
        output='log',
        parameters=[
            {'use_sim_time': True}
        ],
    )

    # Image monitor node for camera feeds
    image_stitcher_node = Node(
        package='gps_denied_navigation_sim',
        executable='image_stitcher',
        name='image_stitcher',
        parameters=[
            {'use_sim_time': True},
            {'front_left_topic': f'/{ns}/front_stereo/left_cam/image_raw'},
            {'front_right_topic': f'/{ns}/front_stereo/right_cam/image_raw'},
            {'rear_left_topic': f'/{ns}/rear_stereo/left_cam/image_raw'},
            {'rear_right_topic': f'/{ns}/rear_stereo/right_cam/image_raw'},
            {'verbose': False}  # Disable debug messages
        ],
        output='log',  # Redirect output to log file instead of terminal
    )

    trajectory_publisher_node = Node(
        package='gps_denied_navigation_sim',
        executable='trajectory_publisher',
        name='trajectory_publisher',
        parameters=[
            {'use_sim_time': True},
            {'pose_topic': f'/{ns}/mavros/local_position/pose'},
            {'path_topic': f'/{ns}/gt_path'},
            {'max_path_length': 5000},
            {'verbose': False}  # Disable debug messages
        ],
        output='log',  # Redirect output to log file instead of terminal
    )
    
    # Buffer size configuration for RViz2 to handle transforms better
    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='log',  # Change from 'screen' to 'log' to reduce terminal spam
            arguments=['-d', rviz_file_path],
            parameters=[
                {'use_sim_time': True},
                {'tf_buffer_cache_time_ms': 60000},  # Increased to 60 seconds
                {'default_display_update_rate': 10.0},  # Lower update rate to reduce CPU load
                {'transform_tolerance': 5.0},  # Increased tolerance to 5 seconds
                {'message_filter_queue_size': 200},  # Larger message queue for TF lookups
                {'synchronize_time': True}  # Try to synchronize time between nodes
            ],
    )

    return [
        # Environment variables
        # ros_domain_id,
        use_sim_time_env,
        
        # Gazebo and PX4
        gz_launch,
        
        # MAVROS node should be launched early to establish connection
        mavros_launch,
        
        # TF tree setup - static transforms
        map2global_tf_node,
        camerainit2map_tf_node,
        map2map_frd_tf_node,
        map2pose_tf_node,
        
        # Dynamic transform for the drone position
        odom2base_tf_node, 
        
        # Lidar transforms
        front_lidar_tf_node,
        front_lidar2gazebo_tf_node,
        rear_lidar_tf_node,
        rear_lidar2gazebo_tf_node,
        
        # Bridge for sensor data from Gazebo
        ros_gz_bridge,

        # Other nodes
        # gimbal_node,
        
        # Camera and trajectory visualization
        image_stitcher_node,
        trajectory_publisher_node,
        
        # RViz should be started last, after all transforms are established
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
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
        OpaqueFunction(function=launch_setup)
    ]) 