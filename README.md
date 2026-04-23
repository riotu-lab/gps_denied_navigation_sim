# gps_denied_navigation_sim

A **PX4 SITL + Gazebo** simulation package for developing, benchmarking, and comparing **GPS-denied navigation** frameworks on multirotor UAVs. It ships with:

- Multi-UAV Gazebo models (mono / stereo / twin-stereo + 3D LiDAR variants)
- DEM-based outdoor worlds (`taif_world`, `taif1_world`, `taif_test4`, `dem_world`) and an indoor warehouse (`tugbot_depot`)
- PX4 airframes, MAVROS configuration, and pre-baked RViz layouts
- Integration targets for **TERCOM**, **MINS**, **OpenVINS**, **FAST-LIO**, **FAST-LIVO2**, **RTAB-Map**, **ORB-SLAM3**, **KISS-Matcher**, **SPARK** and others
- Ground-truth path logging and a CSV-based error analyser for head-to-head algorithm comparison

> **DEM generation:** to build your own elevation model for Gazebo, see [`generate_dem.md`](generate_dem.md).

---

## Table of Contents

1. [Dependencies](#dependencies)
2. [Installation](#installation)
3. [Quick Run](#quick-run)
4. [Documentation Map](#documentation-map)
5. [TERCOM — GPS-denied localisation used by default](#tercom--gps-denied-localisation-used-by-default)
6. [Analysing and Comparing Algorithms](#analysing-and-comparing-algorithms)
7. [Repository Layout](#repository-layout)

---

## Dependencies

| Component | Version |
|-----------|---------|
| Ubuntu | 22.04 |
| ROS 2 | Humble |
| Gazebo | Garden |
| PX4-Autopilot | `navsat_callback` branch (installed by `install.sh`) |
| Python | ≥ 3.10 |

A ready-to-use Docker image with every dependency pre-installed is available at [`gps_denied_navigation_docker`](https://github.com/riotu-lab/gps_denied_navigation_docker).

---

## Installation

Inside the container:

```bash
cd ~/shared_volume/ros2_ws/src
ls      # you should see gps_denied_navigation_sim
```

If the package is missing, clone it:

```bash
cd ~/shared_volume/ros2_ws/src
git clone https://github.com/riotu-lab/gps_denied_navigation_sim.git
```

Then run the installer, which builds PX4 SITL, clones `mavros`, `mavlink`, `yolov8_ros`, `tercom_nav`, `tercom_rviz_plugins`, resolves `rosdep`, builds the workspace, and sources the aliases:

```bash
cd ~/shared_volume/ros2_ws/src/gps_denied_navigation_sim
export DEV_DIR=~/shared_volume
./install.sh
```

All convenience aliases land in [`scripts/bash.sh`](scripts/bash.sh) — the installer sources it from `~/.bashrc` automatically.

---

## Quick Run

Minimum three terminals for the default **TERCOM** pipeline on the **`taif_test4`** world:

| Terminal | Command | Purpose |
|---|---|---|
| 1 | `zenoh` | Start the Zenoh RMW daemon (set by `RMW_IMPLEMENTATION=rmw_zenoh_cpp`) |
| 2 | `mono_taif4` | PX4 SITL + Gazebo + MAVROS + RViz (mono cam + 3D LiDAR on `taif_test4`) |
| 3 | `tercom` | Launch `tercom_nav` (TERCOM + ESKF + DEM server + diagnostics) |

All aliases available for other UAV / world combinations:

```bash
# Mono camera + 3D LiDAR
mono_tug   mono_taif   mono_taif1   mono_taif4

# Stereo camera + 3D LiDAR
stereo_tug   stereo_taif   stereo_taif1   stereo_taif4

# Twin stereo + twin Velodyne
twin_tug   twin_taif   twin_taif1   twin_taif4
```

---

## Documentation Map

| Topic | Document |
|---|---|
| Supported localisation algorithms and how to run each | [`docs/ALGORITHMS.md`](docs/ALGORITHMS.md) |
| Available UAV models and how to switch between them | [`docs/UAV_MODEL.md`](docs/UAV_MODEL.md) |
| Available simulation worlds and how to add a new one | [`docs/SIMULATION_ENVIRONMENT.md`](docs/SIMULATION_ENVIRONMENT.md) |
| TERCOM (Terrain Contour Matching) localisation | [`docs/TERCOM.md`](docs/TERCOM.md) |
| System architecture — ROS graph, data flow, launch graph | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Recording bag/CSV data and comparing algorithm accuracy | [`docs/ALGORITHM_ANALYSIS.md`](docs/ALGORITHM_ANALYSIS.md) |
| Build a Gazebo heightmap from real terrain (SRTM/Mapbox) | [`docs/generate_dem.md`](docs/generate_dem.md) |
| Per-world parameters (size, origin, physics) | [`worlds/WORLD_PARAMETERS.md`](worlds/WORLD_PARAMETERS.md) |
| Per-algorithm setup guides | [`docs/fast_lio/`](docs/fast_lio), [`docs/fast_livo2/`](docs/fast_livo2), [`docs/mins/`](docs/mins), [`docs/openvins/`](docs/openvins), [`docs/orb_slam/`](docs/orb_slam), [`docs/rtabmap/`](docs/rtabmap), [`docs/spark/`](docs/spark), [`docs/kiss_matcher/`](docs/kiss_matcher), [`docs/resple/`](docs/resple), [`docs/super/`](docs/super) |
| Utilities (`gps_to_enu`, `pose2openvins_matrix`, IMU noise conversion) | [`docs/utilities.md`](docs/utilities.md), [`docs/SIMULATION_ENVIRONMENT.md#gps-to-enu-coordinate-conversion`](docs/SIMULATION_ENVIRONMENT.md#gps-to-enu-coordinate-conversion) |
| Adaptive image stitcher for multi-camera UAVs | [`docs/adaptive_image_stitcher.md`](docs/adaptive_image_stitcher.md) |

---

## TERCOM — GPS-denied localisation used by default

The default navigation stack fused with this simulator is **TERCOM (Terrain Contour Matching)** combined with an **Error-State Kalman Filter (ESKF)**. It is delivered as two sibling ROS 2 packages that `install.sh` clones into your workspace:

| Package | Purpose |
|---|---|
| [`tercom_nav`](https://github.com/mzahana/tercom_nav) | Core algorithm: `dem_server_node`, `tercom_node`, `eskf_node`, `diagnostics_node` |
| [`tercom_rviz_plugins`](https://github.com/mzahana/tercom_rviz_plugins) | Dockable RViz2 panels: Filter Status, TERCOM Quality, Error History, Profiling |

See the dedicated write-up in [`docs/TERCOM.md`](docs/TERCOM.md) — it covers the ROS graph, topics, parameters, DEM alignment (`MAP_OFFSET.md`), and the live diagnostic dashboard.

---

## Analysing and Comparing Algorithms

Every launch file publishes a **ground-truth path** on `/target/gt_path` from MAVROS. Each algorithm publishes its estimated path on a well-known topic (e.g. `/mins/imu/path`, `/tercom/eskf_node/odom`, `/Odometry` for FAST-LIO, ...).

The package provides three orthogonal tools for performance analysis:

1. **`path_error_calculator` / `run_path_error_analysis.py`** — online Euclidean / angular / velocity error between any two `nav_msgs/Path` topics with CSV export. See [`docs/path_error_analysis.md`](docs/path_error_analysis.md).
2. **`data_sync_recorder`** — records synchronised images + IMU + GPS + LiDAR + baro into a CSV/image dataset, triggered by a `SetBool` service. See [`gps_denied_navigation_sim/data_sync_recorder.py`](gps_denied_navigation_sim/data_sync_recorder.py).
3. **`analyze_tercom_log.py`** (from `tercom_nav`) — regenerates 15 publication-quality figures (trajectory, RMSE, covariance consistency, NIS, filter health, …) from a single CSV dumped by `diagnostics_node`.

A full walk-through of the offline comparison workflow, including example commands, is documented in [`docs/ALGORITHM_ANALYSIS.md`](docs/ALGORITHM_ANALYSIS.md).

---

## Repository Layout

```
gps_denied_navigation_sim/
├── config/                       PX4 airframes, MAVROS YAML, MINS & OpenVINS configs
├── docs/                         Documentation hub (see table above)
├── gps_denied_navigation_sim/    Python nodes (stitcher, recorder, path-error, ...)
├── install.sh                    Full workspace bootstrap
├── launch/                       dem{,_stereo,_twin_stereo}.launch.py, data_saver, mavros
├── media/                        Screenshots used by the docs and the project page
│   ├── uav_models/               Renders of the shipped X500 variants
│   └── world_models/             Renders of every simulation world
├── models/                       PX4 Gazebo models copied to PX4-Autopilot by install.sh
├── rviz/                         Pre-configured RViz layouts (TERCOM, localisation)
├── scripts/                      bash.sh aliases, path-error analyser, GPS→ENU, ...
├── website/                      Static GitHub Pages site (deployable as-is)
└── worlds/                       Gazebo world SDFs + WORLD_PARAMETERS.md
```

---

## License

MIT — see `package.xml`. Maintained by the RIOTU Lab, Prince Sultan University.
