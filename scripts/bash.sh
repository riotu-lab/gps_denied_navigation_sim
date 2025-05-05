
################# Aliases #################

alias gd='gedit ~/.bashrc'
alias gs='gedit ~/shared_volume/bash.sh'
alias src='source ~/.bashrc'
alias zenoh='ros2 run rmw_zenoh_cpp rmw_zenohd'
alias sss='source install/setup.bash'
alias qgc='cd ~/shared_volume && ./QGroundControl.AppImage'

#Launch
alias mono_tug_dem_mins='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=tugbot_depot localization_model:=mins'
alias stereo_tug_dem_mins_tug='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=tugbot_depot localization_model:=mins'
alias mono_tug_dem_ov='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=tugbot_depot localization_model:=ov'
alias stereo_tug_dem_ov='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=tugbot_depot localization_model:=ov'
alias mono_taif_dem_mins='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=taif_world localization_model:=mins'
alias stereo_taif_dem_mins='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=taif_world localization_model:=mins'
alias mono_taif_dem_ov='ros2 launch gps_denied_navigation_sim dem.launch.py world_type:=taif_world localization_model:=ov'
alias stereo_taif_dem_ov='ros2 launch gps_denied_navigation_sim dem_stereo.launch.py world_type:=taif_world localization_model:=ov'
alias mono_ov='ros2 launch ov_msckf subscribe.launch.py config:=openvins_gpsd_sim_mono use_stereo:=false max_cameras:=1'
alias stereo_ov='ros2 launch ov_msckf subscribe.launch.py config:=openvins_gpsd_sim_stereo use_stereo:=true max_cameras:=2 verbosity:=DEBUG'
alias mins_mono='cd ~/shared_volume && ros2 run mins subscribe ros2_ws/src/gps_denied_navigation_sim/config/mins_mono/config.yaml'
alias mins_stereo='cd ~/shared_volume && ros2 run mins subscribe ros2_ws/src/gps_denied_navigation_sim/config/mins_stereo/config.yaml'
alias spark='ros2 launch spark_fast_lio mapping_dem_sim.launch.py'

#Build
alias cbov='cd ~/shared_volume/ros2_ws && colcon build --packages-select ov_msckf'
alias cbgps='cd ~/shared_volume/ros2_ws && colcon build --packages-select gps_denied_navigation_sim'
alias cbov='cd ~/shared_volume/ros2_ws && colcon build --packages-select ov_msckf'
alias cbspark='cd ~/shared_volume/ros2_ws && colcon build --packages-select spark_fast_lio'

################# ROS #################

# export RMW_IMPLEMENTATION=rmw_zenoh_cpp
# export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=71

################# Github Repos #################

export GIT_USER=
export GIT_TOKEN=

echo 'source ~/shared_volume/ros2_ws/src/gps_denied_navigation_sim/scripts/bash.sh' >> ~/.bashrc