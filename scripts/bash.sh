
################# Aliases #################

alias gd='gedit ~/.bashrc'
alias gs='gedit ~/shared_volume/bash.sh'
alias src='source ~/.bashrc'
alias zenoh='ros2 run rmw_zenoh_cpp rmw_zenohd'
alias sss='source install/setup.bash'
alias qgc='cd ~/shared_volume && ./QGroundControl.AppImage'
alias px4='cd ~/shared_volume/PX4-Autopilot && make px4_sitl gz_x500_twin_stereo_twin_velodyne'
alias sensors_visualization='ros2 launch gps_denied_navigation_sim sensors_visualization.launch.py'
alias orb_slam='. ~/shared_volume/orb_slam3_ws/src/ORB-SLAM3-ROS2-Docker/run_orb_slam.sh'

#Launch
## Stereo sim
alias stereo_tug_dem_mins_tug='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=tugbot_depot localization_model:=mins'
alias stereo_tug_dem_ov='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=tugbot_depot localization_model:=ov'
alias stereo_taif_dem_mins='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=taif_world localization_model:=mins'
alias stereo_taif_dem_ov='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=taif_world localization_model:=ov'

## Mono sim
alias mono_tug_dem_mins='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=tugbot_depot localization_model:=mins'
alias mono_tug_dem_ov='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=tugbot_depot localization_model:=ov'
alias mono_taif_dem_mins='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=taif_world localization_model:=mins'
alias mono_taif_dem_ov='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=taif_world localization_model:=ov'

## Localization models
alias mono_ov='ros2 launch ov_msckf subscribe.launch.py config:=openvins_gpsd_sim_mono use_stereo:=false max_cameras:=1'
alias stereo_ov='source ~/shared_volume/openvins_ws/install/setup.bash && ros2 launch ov_msckf subscribe.launch.py config:=openvins_gpsd_sim_stereo use_stereo:=true max_cameras:=2 verbosity:=DEBUG'

alias mins_mono='cd ~/shared_volume && ros2 run mins subscribe ros2_ws/src/gps_denied_navigation_sim/config/mins_mono/config.yaml'
alias mins_stereo='source ~/shared_volume/mins_ws/install/setup.bash && cd ~/shared_volume && ros2 run mins subscribe ros2_ws/src/gps_denied_navigation_sim/config/mins_twin_stereo_cam/config.yaml'

alias fast_lio='source ~/shared_volume/lio_ws/install/setup.bash && ros2 launch fast_lio mapping.launch.py config_file:=velodyne.yaml'
alias spark='source ~/shared_volume/spark_ws/install/setup.bash && ros2 launch spark_fast_lio mapping_dem_sim.launch.py'
alias livo='source ~/shared_volume/livo2_ws/install/setup.bash && ros2 launch spark_fast_lio mapping_dem_sim.launch.py'

alias rtmap='source ~/shared_volume/rtabmap_ws/install/setup.bash && ros2 launch spark_fast_lio mapping_dem_sim.launch.py'

#Build
alias cbov='cd ~/shared_volume/ros2_ws && colcon build --packages-select ov_msckf'
alias cbgps='cd ~/shared_volume/ros2_ws && colcon build --packages-select gps_denied_navigation_sim'
alias cbov='cd ~/shared_volume/ros2_ws && colcon build --packages-select ov_msckf'
alias cbspark='cd ~/shared_volume/ros2_ws && colcon build --packages-select spark_fast_lio'
alias cb_livox='source ~/shared_volume/ws_livox/install/setup.bash && cd ~/shared_volume/lio_ws && colcon build --symlink-install'
alias cb_rtmap='source ~/shared_volume/rtabmap_ws/install/setup.bash && cd ~/shared_volume/rtabmap_ws && colcon build --symlink-install'

################# ROS #################

export RMW_IMPLEMENTATION=rmw_zenoh_cpp
# export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
# export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=

################# Github Repos #################

export GIT_USER=
export GIT_TOKEN=
