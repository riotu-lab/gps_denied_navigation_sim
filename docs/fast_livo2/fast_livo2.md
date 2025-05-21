# FAST_LIVO2 Setup
https://github.com/integralrobotics/FAST-LIVO2
* Build & install the Livox-SDK2
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
* Make FAST_LIVO2 worksapace 
```bash
cd ~/shared_volume && mkdir livo2_ws
```
/media/asmbatati/UbuntuBackup/Docker/docker_shared_volumes/gpsdnav_shared_volume/livo2_ws/src/vikit_ros/package.xml
rmove line 3


* Clone FAST_LIVO2 repo inside the `~/shared_volume/livo2_ws/src` **inside the contianer**

```bash
cd ~/shared_volume && mkdir -p livo2_ws/src
cd ~/shared_volume/livo2_ws/src
git clone https://github.com/integralrobotics/FAST-LIVO2.git
cd ../
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