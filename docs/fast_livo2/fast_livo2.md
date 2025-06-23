# FAST_LIVO2 Setup
https://github.com/integralrobotics/FAST-LIVO2
* Make FAST_LIVO2 worksapace 
```bash
cd ~/shared_volume && mkdir -p livo2_ws/src
```
* Install PCL && Eigen && OpenCV
* Install Sophus
```bash
git clone https://github.com/strasdat/Sophus.git
cd Sophus
git checkout a621ff
mkdir build && cd build && cmake ..
make
sudo make install
```
## Install Vikit
https://github.com/uavfly/vikit.git
* remove line 3 in ~/shared_volume/livo2_ws/src/vikit/vikit_ros/package.xml
* change c++ 14 to 17 in ~/shared_volume/livo2_ws/src/vikit/vikit_ros/CMakeLists.txt
* Build
```bash
cd ~/shared_volume/livo2_ws/src
git clone https://github.com/uavfly/vikit.git
cd ..
colcon build --packages-select vikit_common vikit_ros
```
## Build & install the Livox-SDK2
```bash
cd ~/shared_volume && mkdir thirdparty && cd thirdparty
git clone https://github.com/Livox-SDK/Livox-SDK2.git
cd ./Livox-SDK2/
mkdir build
cd build
cmake .. && make -j
sudo make install
```
* Build & install the Livox-SDK2
```bash
cd ~/shared_volume && git clone https://github.com/Livox-SDK/livox_ros_driver2.git ws_livox/src/livox_ros_driver2
cd ws_livox/src/livox_ros_driver2 && ./build.sh humble
```

## Clone FAST_LIVO2 repo inside the `~/shared_volume/livo2_ws/src` **inside the contianer**

```bash
cd ~/shared_volume/livo2_ws/src
git clone https://github.com/Robotic-Developer-Road/FAST-LIVO2.git
```

## Required Modifications to Fix Build Issues

### 1. Fix Multiple Definition Linker Errors

#### Modify `livo2_ws/src/vikit/vikit_ros/include/vikit/camera_loader.h`:
Add `inline` keyword to function definitions:
- **Line 25**: Change `bool loadFromRosNs(...)` to `inline bool loadFromRosNs(...)`
- **Line 100**: Change `bool loadFromRosNs(...)` to `inline bool loadFromRosNs(...)`

#### Modify `livo2_ws/src/vikit/vikit_ros/include/vikit/params_helper.h`:
Add `inline` keyword to template function definitions:
- **Line 42**: Change `T getParam(...)` to `inline T getParam(...)`
- **Line 60**: Change `std::string getParam<std::string>(...)` to `inline std::string getParam<std::string>(...)`
- **Line 87**: Change `typename std::enable_if<!std::is_same<T, std::string>::value, T>::type getParam(...)` to `inline typename std::enable_if<!std::is_same<T, std::string>::value, T>::type getParam(...)`
- **Line 103**: Change `typename std::enable_if<std::is_same<T, std::string>::value, T>::type getParam(...)` to `inline typename std::enable_if<std::is_same<T, std::string>::value, T>::type getParam(...)`

### 2. CMakeLists.txt Modifications

#### In `livo2_ws/src/FAST-LIVO2/CMakeLists.txt`:
- **Line 99**: Add `find_package(fmt REQUIRED)`
- **Line 177**: Add `fmt::fmt` to target_link_libraries

```cmake
# Line 99
find_package(fmt REQUIRED)

# Lines 166-178
target_link_libraries(fastlivo_mapping
  laser_mapping
  vio
  lio
  pre
  imu_proc
  ${PCL_LIBRARIES}
  ${OpenCV_LIBRARIES}
  ${Sophus_LIBRARIES}
  ${Boost_LIBRARIES}
  fmt::fmt
)
```

* Build
```bash
cd ~/shared_volume/livo2_ws
colcon build --symlink-install --continue-on-error
```

# How to run?
* To run the FAST_LIVO2 filter you can use some of the aliases defined in the `scripts/bash.sh` script.

    For example,
    ```bash
    fast_liVo2
    ```


## Configurations
You can find the `FAST_LIVO2` configurations in the `config/fast_liVo2` sub-dirictory.