#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Declare launch arguments
    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Namespace for the drone (e.g., /target/)'
    )
    
    output_topic_arg = DeclareLaunchArgument(
        'output_topic',
        default_value='/camera/stitched_image',
        description='Output topic for stitched image'
    )
    
    output_width_arg = DeclareLaunchArgument(
        'output_width',
        default_value='800',
        description='Output image width'
    )
    
    output_height_arg = DeclareLaunchArgument(
        'output_height',
        default_value='600',
        description='Output image height'
    )
    
    discovery_timeout_arg = DeclareLaunchArgument(
        'discovery_timeout',
        default_value='5.0',
        description='Time to wait for camera discovery (seconds)'
    )
    
    verbose_arg = DeclareLaunchArgument(
        'verbose',
        default_value='true',
        description='Enable verbose logging'
    )
    
    stitch_rate_arg = DeclareLaunchArgument(
        'stitch_rate',
        default_value='10.0',
        description='Stitching rate in Hz'
    )
    
    namespace_filter_arg = DeclareLaunchArgument(
        'namespace_filter',
        default_value='',
        description='Filter cameras by namespace (e.g., /target/)'
    )
    
    # Create the adaptive image stitcher node
    adaptive_stitcher_node = Node(
        package='gps_denied_navigation_sim',
        executable='adaptive_image_stitcher.py',
        name='adaptive_image_stitcher',
        namespace=LaunchConfiguration('namespace'),
        parameters=[{
            'output_topic': LaunchConfiguration('output_topic'),
            'output_width': LaunchConfiguration('output_width'),
            'output_height': LaunchConfiguration('output_height'),
            'discovery_timeout': LaunchConfiguration('discovery_timeout'),
            'verbose': LaunchConfiguration('verbose'),
            'stitch_rate': LaunchConfiguration('stitch_rate'),
            'namespace_filter': LaunchConfiguration('namespace_filter'),
        }],
        output='screen'
    )
    
    return LaunchDescription([
        namespace_arg,
        output_topic_arg,
        output_width_arg,
        output_height_arg,
        discovery_timeout_arg,
        verbose_arg,
        stitch_rate_arg,
        namespace_filter_arg,
        adaptive_stitcher_node
    ]) 