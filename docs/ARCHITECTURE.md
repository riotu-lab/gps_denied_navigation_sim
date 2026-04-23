# System Architecture

Mermaid diagrams of the full `gps_denied_navigation_sim` stack — from Gazebo down through PX4 SITL, MAVROS and the `ros_gz_bridge` into user-space ROS 2 algorithms.

---

## 1. High-level stack

```mermaid
graph TB
    subgraph HW [Simulation]
        GZ[Gazebo Garden<br/>world SDF + heightmap]
        PX4[PX4 SITL<br/>EKF2 + mavlink]
        GZ -- joint-state / IMU / cam / LiDAR / GPS --> PX4
        PX4 -- actuator commands --> GZ
    end

    subgraph BRIDGE [Transport]
        MAV[MAVROS<br/>namespace target/]
        GZR[ros_gz_bridge]
        PX4 -- UDP 14540/14557 --> MAV
        GZ -- ign.msgs --> GZR
    end

    subgraph ROS [ROS 2 graph]
        TF[TF tree<br/>map → target/odom → target/base_link → lidar_link]
        MAV --> TF
        GZR --> TF
        ALG[Localisation algorithm<br/>TERCOM / MINS / OpenVINS / FAST-LIO …]
        MAV --> ALG
        GZR --> ALG
    end

    subgraph VIZ [Visualisation & analysis]
        RV[RViz2 + tercom_rviz_plugins]
        REC[Bag / CSV recorder]
        ANA[path_error_calculator<br/>+ analyze_tercom_log.py]
        ALG --> RV
        MAV --> RV
        ALG --> REC
        MAV --> REC
        REC --> ANA
    end
```

---

## 2. Default `dem.launch.py` launch graph (mono + TERCOM)

```mermaid
graph LR
    L[dem.launch.py<br/>world_type:=taif_test4] --> L1[gz_sim.launch.py]
    L --> L2[mavros.launch.py]
    L --> L3[Static TF<br/>map → target/odom]
    L --> L4[Static TF<br/>target/base_link → lidar_link]
    L --> L5[ros_gz_bridge]
    L --> L6[execute_random_trajectories]
    L --> L7[RViz2 rviz_tercom.rviz]

    L1 --> GZ[Gazebo + PX4 SITL]
    L2 --> MAV[MAVROS target/]
    L5 --> TOPICS[/scan/points, /camera, /imu_gimbal ... /]
    L7 --> PANELS[tercom_rviz_plugins<br/>Filter Status · Quality · Error · Profiling]

    L_TERCOM[ros2 launch tercom_nav tercom_nav.launch.py] -.separate terminal.-> N1[dem_server_node]
    L_TERCOM -.-> N2[tercom_node]
    L_TERCOM -.-> N3[eskf_node]
    L_TERCOM -.-> N4[diagnostics_node]
    MAV --> N2
    MAV --> N3
    N3 --> PANELS
    N4 --> PANELS
```

---

## 3. ROS topics published by the simulator

Per UAV (namespace `target`):

| Topic | Type | Source |
|-------|------|--------|
| `/target/mavros/imu/data` | `sensor_msgs/Imu` | MAVROS |
| `/target/mavros/altitude` | `mavros_msgs/Altitude` | MAVROS |
| `/target/mavros/distance_sensor/rangefinder_pub` | `sensor_msgs/Range` | MAVROS |
| `/target/mavros/global_position/global` | `sensor_msgs/NavSatFix` | MAVROS |
| `/target/mavros/local_position/odom` | `nav_msgs/Odometry` | MAVROS |
| `/target/mavros/local_position/velocity_local` | `geometry_msgs/TwistStamped` | MAVROS |
| `/target/mavros/local_position/pose` | `geometry_msgs/PoseStamped` | MAVROS |
| `/target/gt_path` | `nav_msgs/Path` | `gt_trajectory_publisher` |
| `/target/camera` + `/target/camera_info` | `sensor_msgs/Image / CameraInfo` | `ros_gz_bridge` |
| `/target/gimbal/camera` + `/target/gimbal/camera_info` | same | `ros_gz_bridge` |
| `/scan/points` | `sensor_msgs/PointCloud2` | `ros_gz_bridge` |
| `/target/stereo/{left,right}_cam/image_raw` | `sensor_msgs/Image` | `ros_gz_bridge` (stereo UAV) |
| `/target/velodyne_{front,rear}/points` | `sensor_msgs/PointCloud2` | `ros_gz_bridge` (twin UAV) |
| `/imu_gimbal` | `sensor_msgs/Imu` | `ros_gz_bridge` |
| `/clock` | `rosgraph_msgs/Clock` | `ros_gz_bridge` |

TF tree published:

```
map
 └── target/odom          (static, from dem.launch.py)
      └── target/base_link          (dynamic, from MAVROS local_position)
           ├── target/base_link_frd (NED flavour, MAVROS)
           └── lidar_link           (static, from dem.launch.py)
```

---

## 4. Per-UAV ROS graph

```mermaid
graph LR
    subgraph Sensors [Gazebo sensors]
        IM[IMU]
        GPS[GPS]
        BP[Baro]
        RF[Rangefinder]
        CAM[Camera / Stereo]
        LID[LiDAR]
    end
    subgraph Gazebo [ros_gz_bridge]
        CAM --> R1[/target/camera/]
        LID --> R2[/scan/points/]
    end
    subgraph PX4 [PX4 SITL + EKF2]
        IM --> P1
        GPS --> P1
        BP --> P1
        RF --> P1
        P1[EKF2] --> P2[mavlink]
    end
    subgraph MAVROS [MAVROS target/]
        P2 --> M1[/target/mavros/imu/data/]
        P2 --> M2[/target/mavros/local_position/odom/]
        P2 --> M3[/target/mavros/altitude/]
        P2 --> M4[/target/mavros/global_position/global/]
        P2 --> M5[/target/mavros/distance_sensor/rangefinder_pub/]
    end
```

---

## 5. State of an algorithm-under-test

```mermaid
stateDiagram-v2
    [*] --> LOADING
    LOADING --> WAITING : workspace sourced, launch file active
    WAITING --> INIT : all subscribed topics receiving
    INIT --> RUNNING : estimator initialised
    RUNNING --> FAILED : divergence / NIS blow-up / NaN
    RUNNING --> COMPLETED : flight ended, bag/CSV closed
    FAILED --> [*]
    COMPLETED --> [*]
```

---

## 6. Module classes (Python nodes inside `gps_denied_navigation_sim/`)

```mermaid
classDiagram
    class AdaptiveImageStitcher {
        +discover_cameras()
        +stitch_layout()
    }
    class DataSyncRecorder {
        +start_recording(SetBool)
        +stop_recording(SetBool)
        -csv_writer_
    }
    class ExecuteRandomTrajectories {
        +generate_random_trajectory()
        +publish_setpoints()
    }
    class PathErrorCalculator {
        +on_gt_path()
        +on_est_path()
        +compute_metrics()
    }
    class GimbalStabilizer
    class TfMonitor
    class TfRelay
    class GtTrajectoryPublisher

    PathErrorCalculator --> GtTrajectoryPublisher : consumes /target/gt_path
    DataSyncRecorder --> AdaptiveImageStitcher : optional
```

---

## See also

- [`TERCOM.md`](TERCOM.md) for the TERCOM-specific mermaid diagrams
- [`ALGORITHM_ANALYSIS.md`](ALGORITHM_ANALYSIS.md) for the comparison pipeline
- [`tercom_nav/docs/TERCOM_MERMAID_DIAGRAMS.md`](../../tercom_nav/docs/TERCOM_MERMAID_DIAGRAMS.md) for the algorithm-internal view
