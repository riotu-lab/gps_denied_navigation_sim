# FAST_LIO Setup
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
* Make FAST_LIO worksapace 
```bash
cd ~/shared_volume && mkdir lio_ws
```
* Clone FAST_LIO repo inside the `~/shared_volume/lio_ws/src` **inside the contianer**

```bash
cd ~/shared_volume && mkdir -p lio_ws/src
cd ~/shared_volume/lio_ws/src
git clone https://github.com/Ericsii/FAST_LIO.git --recursive -b ros2
cd ~/shared_volume/lio_ws && source ~/shared_volume/ws_livox/install/setup.bash && rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
```

# How to run?
* To run the FAST_LIO filter you can use some of the aliases defined in the `scripts/bash.sh` script.

    For example,
    ```bash
    fast_lio
    ```


## Configurations
You can find the `FAST_LIO` configurations in the `config/fast_lio` sub-dirictory.