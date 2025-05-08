# MINS Setup
* Clone MINS repo inside the `~/shared_volume/ros2_ws/src` **inside the contianer**

```bash

git clone -b ros2 https://github.com/mzahana/mins.git
```

* Navigate to the `~/shared_volume/ros2_ws`, then execute the following commands in order to build the `mins` package.
```bash
source /opt/ros/humble/setup.bash
colcon build --paths src/mins/thirdparty/*
source install/setup.bash
colcon build --paths src/mins/thirdparty/open_vins/*
source install/setup.bash
colcon build --paths src/mins/mins src/mins/mins_data
source install/setup.bash
colcon build --paths src/mins/mins_eval
```

# How to run?
* To run the mins filter you can use some of the aliases defined in the `scripts/bash.sh` script.

    For example,
    ```bash
    cd ~/shared_volume

    ros2 run mins subscribe ros2_ws/src/gps_denied_navigation_sim/config/mins_stereo/config.yaml
    ```


## Configurations
You can find the `mins` configurations in the `config/mins_mono` and `config/mins_stereo` sub-drictories.