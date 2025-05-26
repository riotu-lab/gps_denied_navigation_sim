# ORB-SLAM3 Setup
https://github.com/asmbatati/ORB-SLAM3-ROS2-Docker
* Make ORB-SLAM3 worksapace 
```bash
cd ~/shared_volume && mkdir -p orb_slam3_ws/src
```
* Clone ORB-SLAM3 repo inside the `~/shared_volume/orb_slam3_ws/src` **inside the container**

```bash
cd ~/shared_volume/orb_slam3_ws/src
git clone https://github.com/asmbatati/ORB-SLAM3-ROS2-Docker.git
cd ORB-SLAM3-ROS2-Docker
git submodule update --init --recursive --remote
```
## Build dep
```bash
cd ~/shared_volume/orb_slam3_ws/src/ORB-SLAM3-ROS2-Docker
./fix_paths.sh
./install_deps.sh
./install_libraries.sh
```
## Build
```bash
cd ~/shared_volume/orb_slam3_ws
colcon build --symlink-install && source install/setup.bash
```