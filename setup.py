import os
from glob import glob
from setuptools import setup
package_name = 'gps_denied_navigation_sim'

def recursive_data_files(directory):
    return [
        (os.path.join('share', package_name, root), [os.path.join(root, file) for file in files])
        for root, _, files in os.walk(directory) if files
    ]

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
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
            'sensors_visualization = gps_denied_navigation_sim.publish_sensors_readings:main',
            'tf_relay = gps_denied_navigation_sim.tf_relay:main',
        ],
    },
)
