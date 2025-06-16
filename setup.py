import os
from glob import glob
from setuptools import setup, find_packages
package_name = 'gps_denied_navigation_sim'

def recursive_data_files(directory):
    return [
        (os.path.join('share', package_name, root), [os.path.join(root, file) for file in files])
        for root, _, files in os.walk(directory) if files
    ]

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        *recursive_data_files('config'),
        *recursive_data_files('models'),
        *recursive_data_files('launch'),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        *([(os.path.join('share', package_name, 'worlds'), glob('worlds/*'))] if os.path.exists('worlds') and glob('worlds/*') else []),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Khaled Gabr',
    maintainer_email='khaledgabr77@gmail.com',
    description='Simulation environment that can be used for GPS-denied navigation frameworks.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gimbal_stabilizer = gps_denied_navigation_sim.gimbal_stabilizer:main',
            'execute_random_trajectories = gps_denied_navigation_sim.execute_random_trajectories_node:main',
            'data_sync_recorder = gps_denied_navigation_sim.data_sync_recorder:main',
            'camera_info_publisher = gps_denied_navigation_sim.camera_info_publisher:main',
            'test_stereo = gps_denied_navigation_sim.test_stereo:main',
            'tf_relay = gps_denied_navigation_sim.tf_relay:main',
            'image_stitcher = gps_denied_navigation_sim.image_stitcher:main',
            'adaptive_image_stitcher = gps_denied_navigation_sim.adaptive_image_stitcher:main',
            'trajectory_publisher = gps_denied_navigation_sim.gt_trajectory_publisher:main',
            'path_error_calculator = gps_denied_navigation_sim.path_error_calculator:main',
        ],
    },
)
