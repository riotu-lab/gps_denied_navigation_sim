#!/bin/bash -e

# This script sets up the D2DTracker simulation environment

if [ -z "${DEV_DIR}" ]; then
  echo "Error: DEV_DIR environment variable is not set. Set it using export DEV_DIR=<DEV_DIR_deirectory_that_should_contain_PX4-Autopilot_and_ros2_ws>"
  exit 1
fi
echo "DEV_DIR=$DEV_DIR"
sleep 1
echo "GIT_USER=$GIT_USER"
echo "GIT_TOKEN=$GIT_TOKEN"
sleep 1

ROS2_WS=$DEV_DIR/ros2_ws
ROS2_SRC=$DEV_DIR/ros2_ws/src
PX4_DIR=$DEV_DIR/PX4-Autopilot
OSQP_SRC=$DEV_DIR

# # Make sure that PX4 root directory is set
# if [ -z "${PX4_ROOT}" ]; then
#   echo "Error: PX4_ROOT environment variable is not set. Set it using export PX4_ROOT=<PX4-ROOT_deirectory_that_contains_PX4-Autopilot>"
#   exit 1
# fi

# # Make sure that ROS2_WS directory is set
# if [ -z "${ROS2_WS}" ]; then
#   echo "Error: ROS2_WS environment variable is not set. Set it using export ROS2_WS=<ROS2_WS_deirectory_that_contains_ros2_ws>"
#   exit 1
# fi

if [ ! -d "$ROS2_WS" ]; then
  echo "Creating $ROS2_SRC"
  mkdir -p $ROS2_SRC
fi

SIM_PKG_URL=''
if [[ -n "$GIT_USER" ]] && [[ -n "$GIT_TOKEN" ]]; then
    SIM_PKG_URL=https://$GIT_USER:$GIT_TOKEN@riotu-lab/gps_denied_navigation_sim.git
else
    SIM_PKG_URL=https://github.com/riotu-lab/gps_denied_navigation_sim.git
fi

# Clone the d2dtracker_sim if it doesn't exist
if [ ! -d "$ROS2_SRC/gps_denied_navigation_sim" ]; then
    cd $ROS2_SRC
    git clone $SIM_PKG_URL
else
    cd $ROS2_SRC/gps_denied_navigation_sim && git pull origin main
fi

# Clone and build PX4-Autopilot if it doesn't exist
if [ ! -d "$PX4_DIR" ]; then
    echo "Cloning $PX4_DIR..."
    cd $DEV_DIR
    git clone https://github.com/riotu-lab/PX4-Autopilot.git --recursive
    make submodulesclean
    make clean
    make distclean
    cd $PX4_DIR
    # git checkout v1.14.0
    git checkout navsat_callback
    make submodulesclean
    make clean
    make distclean
else
    echo "PX4_DIR=$PX4_DIR already exists"
    cd $PX4_DIR
    make submodulesclean
    make clean
    make distclean
    # git checkout v1.14.0
    git checkout navsat_callback
    make submodulesclean
    make clean
    make distclean
fi

# Copy files to $PX4_DIR
echo && echo  "Copying files to ${PX4_DIR}" && echo
sleep 1
cp -r ${ROS2_SRC}/gps_denied_navigation_sim/models/* ${PX4_DIR}/Tools/simulation/gz/models/
cp -r ${ROS2_SRC}/gps_denied_navigation_sim/worlds/* ${PX4_DIR}/Tools/simulation/gz/worlds/
cp -r ${ROS2_SRC}/gps_denied_navigation_sim//config/px4/* ${PX4_DIR}/ROMFS/px4fmu_common/init.d-posix/airframes/

# Build px4_sitl
cd $PX4_DIR && make px4_sitl
# Checkout commit f1c461f in https://github.com/PX4/PX4-gazebo-models.git
cd $PX4_DIR/Tools/simulation/gz && git checkout f1c461f
cd $DEV_DIR


#
# yolov8
#
if [ ! -d "$ROS2_SRC/yolov8_ros" ]; then
    cd $ROS2_SRC
    git clone https://github.com/mgonzs13/yolov8_ros.git
    cd $ROS2_SRC/yolov8_ros && git checkout 2.0.1
else
    cd $ROS2_SRC/yolov8_ros && git pull origin && git checkout 2.0.1
fi

#
# MAVROS
#
# these mavlink and mavros versions are working for ros2 humble
# Sept 17, 2023
echo "Cloning mavlink package ... " && sleep 1
if [ ! -d "$ROS2_SRC/mavlink" ]; then
    cd $ROS2_SRC
    git clone  https://github.com/ros2-gbp/mavlink-gbp-release.git mavlink
    cd $ROS2_SRC/mavlink && git checkout release/humble/mavlink/2023.9.9-1
fi
# Custom mavros pkg is required to handle TF issues in multi-vehicle simulation
echo "Cloning custom mavros package ... " && sleep 1
if [ ! -d "$ROS2_SRC/mavros" ]; then
    cd $ROS2_SRC
    git clone  https://github.com/mzahana/mavros.git
    cd $ROS2_SRC/mavros && git checkout ros2_humble
fi

cd $ROS2_WS && rosdep init && rosdep update && rosdep install --from-paths src --ignore-src -r -y

cd $ROS2_WS && MAKEFLAGS='j1 -l1' colcon  build --packages-up-to mavros --executor sequential

cd $ROS2_WS && MAKEFLAGS='j1 -l1' colcon build --packages-up-to mavros_extras --executor sequential

cd $ROS2_WS && colcon build

echo "DONE. Pkgs are built. Models and airframe config files are copied to the respective folder in the ${PX4_DIR} directory"
# echo "Source the ros2_ws and use <ros2 launch d2dtracker_sim interceptor.launch.py> to run the simulation"
cd $HOME
