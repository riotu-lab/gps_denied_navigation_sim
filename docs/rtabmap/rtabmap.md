# rtabmap Setup
https://github.com/introlab/rtabmap_ros/tree/ros2
* Make rtabmap worksapace 
```bash
cd ~/shared_volume && mkdir rtabmap_ws
```
* Clone rtabmap repo inside the `~/shared_volume/rtabmap_ws/src` **inside the contianer**

```bash
cd ~/shared_volume/ros2_ws
git clone https://github.com/introlab/rtabmap.git src/rtabmap
git clone --branch ros2 https://github.com/introlab/rtabmap_ros.git src/rtabmap_ros
rosdep update && rosdep install --from-paths src --ignore-src -r -y
export MAKEFLAGS="-j6" # Can be ignored if you have a lot of RAM (>16GB)
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
git clone -b ros2 https://github.com/mzahana/rtabmap.git
```