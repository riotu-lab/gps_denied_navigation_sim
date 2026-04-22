# spark Setup
https://github.com/MIT-SPARK/spark-fast-lio/tree/main?tab=readme-ov-file
* Make spark worksapace 
```bash
cd ~/shared_volume && mkdir spark_ws
```
## Install KISS-Matcher
* CMake Version
```bash
cd ~/shared_volume/thirdparty
wget https://github.com/Kitware/CMake/releases/download/v3.27.9/cmake-3.27.9-linux-x86_64.tar.gz
tar -xf cmake-3.27.9-linux-x86_64.tar.gz
sudo mv cmake-3.27.9-linux-x86_64 /opt/cmake-3.27
export PATH=/opt/cmake-3.27/bin:$PATH
hash -r
echo 'export PATH=/opt/cmake-3.27/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```
* GSTAM
```bash
cd ~/shared_volume/thirdparty
git clone https://github.com/borglab/gtsam.git
cd gtsam
git checkout 4.2.0  # Or latest stable version
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local -DGTSAM_USE_SYSTEM_EIGEN=ON
make -j$(nproc)
sudo make install
```
* Build KISS-Matcher-SAM for the first time:
```bash
cd ~/shared_volume/spark_ws/src
git clone https://github.com/MIT-SPARK/KISS-Matcher.git
cd ..
colcon build --packages-select kiss_matcher_ros
```
* Modify src code at: 
`~/shared_volume/spark_ws/build/kiss_matcher_ros/_deps/robin-src/src/graph_solvers.cpp`

`lines 64-65:`

```bash
    std::vector<int> edges;
    std::vector<long long> vertices;
```
* Build KISS-Matcher-SAM:
```bash
cd ~/shared_volume/spark_ws
colcon build --packages-select kiss_matcher_ros
```
## SPARK
* Clone spark repo inside the `~/shared_volume/spark_ws/src` 

```bash
cd ~/shared_volume/spark_ws/src
git clone https://github.com/MIT-SPARK/spark-fast-lio.git
cd ..
colcon build --packages-up-to spark_fast_lio
```