import os
from glob import glob
from setuptools import setup, find_packages
package_name = 'gps_denied_navigation_sim'

# setup(
#     name=package_name,
#     version='0.0.0',
#     packages=[package_name],
#     data_files=[
#         ('share/ament_index/resource_index/packages',
#             ['resource/' + package_name]),
#         ('share/' + package_name, ['package.xml']),
#         (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*')),
#         (os.path.join('share', package_name), glob('config/mavros/*.yaml')),
#         (os.path.join('share', package_name), glob('rviz/*.rviz')),
#         (os.path.join('share', package_name), glob('models/x500_stereo_cam_3d_lidar/*')),
#     ],
setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Include launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        # Include configuration files recursively
        *[
            (os.path.join('share', package_name, root), [os.path.join(root, file) for file in files])
            for root, dirs, files in os.walk('config')
            if files  # Only include directories that contain files
        ],
        # Include RViz configuration files
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        # Include model files recursively
        *[
            (os.path.join('share', package_name, root), [os.path.join(root, file) for file in files])
            for root, dirs, files in os.walk('models')
            if files  # Only include directories that contain files
        ],
        # Include worlds directory if it exists
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
        ],
    },
)
