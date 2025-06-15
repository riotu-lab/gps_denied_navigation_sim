# MINS Marker and Location Visualization Reference

## Overview

This document provides a comprehensive reference for marker and location visualization functionality in the MINS (Multisensor-aided Inertial Navigation System) workspace. The system supports multiple types of markers and visualization components for simulation, debugging, and real-time monitoring.

## Core Components

### 1. Visualization Classes

#### SimVisualizer (ROS1)
- **Location**: `mins_ws/src/mins/mins/src/sim/SimVisualizer.cpp` and `SimVisualizer.h`
- **Purpose**: Handles visualization for ROS1 environments
- **Key Features**:
  - LiDAR plane structure visualization
  - Camera feature point publishing
  - Ground truth trajectory display
  - RMSE/NEES statistics computation

#### Sim2Visualizer (ROS2)
- **Location**: `mins_ws/src/mins/mins/src/sim/Sim2Visualizer.cpp` and `Sim2Visualizer.h`
- **Purpose**: Handles visualization for ROS2 environments
- **Key Features**: Identical to ROS1 version with ROS2 API adaptations

### 2. ArUco Tag Support (OpenVINS Integration)

#### TrackAruco Class
- **Location**: `mins_ws/src/mins/thirdparty/open_vins/ov_core/src/track/TrackAruco.cpp` and `TrackAruco.h`
- **Dictionary**: `cv::aruco::DICT_6X6_1000`
- **Tag Generation**: Use online utility: https://chev.me/arucogen/
- **Features**:
  - Corner-based tracking (4 corners per tag)
  - Multi-camera support
  - Automatic undistortion
  - Mask-based filtering

## Published Topics

### Core Visualization Topics

| Topic | Message Type | Description |
|-------|-------------|-------------|
| `/mins/sim_lidar_map` | `visualization_msgs::MarkerArray` | LiDAR plane structure visualization |
| `/mins/cam/points_sim` | `sensor_msgs::PointCloud2` | Simulated camera feature points |
| `/mins/imu/pose_gt` | `geometry_msgs::PoseStamped` | Ground truth IMU pose |
| `/mins/imu/path_gt` | `nav_msgs::Path` | Ground truth trajectory path |

### Transform Frames

| Frame ID | Description |
|----------|-------------|
| `global` | Global reference frame |
| `truth` | Ground truth frame |

## Marker Types and Implementation

### 1. LiDAR Plane Markers

**Type**: `visualization_msgs::Marker::LINE_LIST`

```cpp
// Create plane marker
Marker marker_plane;
marker_plane.header.frame_id = "global";
marker_plane.header.stamp = ros::Time::now();
marker_plane.ns = "sim_lidar_map";
marker_plane.id = ct;
marker_plane.type = Marker::LINE_LIST;
marker_plane.action = Marker::MODIFY;
marker_plane.scale.x = 0.03;
marker_plane.color.b = 1.0;  // Blue color
marker_plane.color.a = 1.0;  // Full opacity
```

**Visualization Pattern**:
- Rectangle outline (4 edges)
- Cross pattern through center
- 12 total line segments per plane

### 2. ArUco Tag Markers

**Detection Process**:
1. Image preprocessing and downsampling
2. ArUco detection using OpenCV
3. Corner extraction and undistortion
4. Feature database update
5. Visualization overlay

**ID Encoding**:
```cpp
size_t tmp_id = (size_t)ids_aruco[cam_id].at(i) + n * max_tag_id;
```
- Base ID: ArUco tag ID
- Corner offset: `n * max_tag_id` (where n = 0,1,2,3)

## Key Methods and Functions

### SimVisualizer Methods

#### `publish_lidar_structure()`
- **Purpose**: Publishes LiDAR plane markers for simulation visualization
- **Input**: Simulated plane data from `Simulator::get_lidar_planes()`
- **Output**: MarkerArray with LINE_LIST markers
- **Coordinate Transform**: Applies ENU transformation if GPS enabled

#### `publish_sim_cam_features()`
- **Purpose**: Publishes camera feature points as point cloud
- **Input**: Feature map from `Simulator::get_cam_map_vec()`
- **Output**: PointCloud2 message
- **Frame**: Global coordinate system

#### `publish_groundtruth()`
- **Purpose**: Publishes ground truth pose and trajectory
- **Features**:
  - IMU pose publishing
  - Path trajectory with downsampling (max 16384 poses)
  - TF transform broadcasting
  - RMSE/NEES statistics computation

### TrackAruco Methods

#### `feed_new_camera()`
- **Purpose**: Process new camera frame for ArUco detection
- **Parameters**:
  - `timestamp`: Image timestamp
  - `img`: Input image
  - `cam_id`: Camera identifier
  - `maskin`: Detection mask
- **Process**:
  1. Image downsampling (optional)
  2. ArUco detection
  3. Corner refinement
  4. Feature database update

#### `display_active()`
- **Purpose**: Create visualization overlay with detected markers
- **Output**: Multi-camera image with marker overlays
- **Features**:
  - Detected markers (green)
  - Rejected candidates (red)
  - Camera ID labels
  - Mask overlay

## Configuration and Parameters

### RViz Configuration

**File**: `mins_ws/src/mins/mins/launch/display.rviz`

```yaml
- Class: rviz/MarkerArray
  Enabled: true
  Marker Topic: /mins/sim_lidar_map
  Name: LiDAR sim map
  Namespaces: {}
  Queue Size: 100
  Value: true
```

### ArUco Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_tag_id` | 1000 | Maximum ArUco tag ID |
| Dictionary | `DICT_6X6_1000` | ArUco dictionary type |
| Corner refinement | Enabled | Sub-pixel corner accuracy |

### Visualization Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Line width | 0.03 | Marker line thickness |
| Color | Blue (0,0,1) | Default marker color |
| Transparency | 1.0 | Full opacity |

## Usage Examples

### 1. Enable LiDAR Visualization

```cpp
// In simulation setup
if (sim != nullptr && sys->state->op->lidar->enabled) {
    pub_sim_lidar_map = make_shared<ros::Publisher>(
        nh->advertise<MarkerArray>("/mins/sim_lidar_map", 2)
    );
}
```

### 2. ArUco Tag Detection Setup

```cpp
// Enable ArUco tracking
#if ENABLE_ARUCO_TAGS
    tracker = std::make_shared<TrackAruco>(camera_calib, max_tag_id);
#endif
```

### 3. Custom Marker Creation

```cpp
// Create custom marker
visualization_msgs::Marker custom_marker;
custom_marker.header.frame_id = "global";
custom_marker.header.stamp = ros::Time::now();
custom_marker.ns = "custom_namespace";
custom_marker.id = unique_id;
custom_marker.type = visualization_msgs::Marker::SPHERE;
custom_marker.action = visualization_msgs::Marker::ADD;
custom_marker.scale.x = custom_marker.scale.y = custom_marker.scale.z = 0.1;
custom_marker.color.r = 1.0;
custom_marker.color.a = 1.0;
```

## Coordinate Systems and Transformations

### Frame Relationships

```
global (ENU) ← WtoE_trans ← world (simulation)
   ↓
truth (ground truth)
   ↓
imu (estimated pose)
```

### ENU Transformation

When GPS is enabled and initialized:
```cpp
// Transform from world to ENU coordinates
Matrix3d RWtoE = quat_2_Rot(sim->op->sim->WtoE_trans.block(0, 0, 4, 1));
Vector3d pWinE = sim->op->sim->WtoE_trans.block(4, 0, 3, 1);
point_enu = pWinE + RWtoE * point_world;
```

## Performance Considerations

### Optimization Strategies

1. **Subscriber Checking**: Only publish when subscribers are present
```cpp
if (pub_sim_cam_points->getNumSubscribers() == 0) return;
```

2. **Path Downsampling**: Limit trajectory points to prevent RViz crashes
```cpp
for (size_t i = 0; i < poses_gt.size(); i += floor((double)poses_gt.size() / 16384.0) + 1)
```

3. **Conditional Publishing**: Enable visualization only when needed
```cpp
if (sim == nullptr || sim->get_lidar_planes().empty()) return;
```

## Debugging and Troubleshooting

### Common Issues

1. **No Markers Visible**:
   - Check topic subscription: `rostopic echo /mins/sim_lidar_map`
   - Verify frame_id matches RViz fixed frame
   - Ensure simulation is running

2. **ArUco Detection Failures**:
   - Verify OpenCV ArUco module compilation
   - Check lighting conditions
   - Validate camera calibration
   - Ensure tag dictionary matches

3. **Coordinate System Issues**:
   - Verify ENU transformation parameters
   - Check GPS initialization status
   - Validate frame relationships in TF tree

### Debug Commands

```bash
# Check marker topics
rostopic list | grep marker

# Monitor marker messages
rostopic echo /mins/sim_lidar_map

# Verify TF transforms
rosrun tf tf_echo global truth

# Check ArUco compilation
rospack find cv_bridge
```

## Integration with Other Systems

### RTAB-Map Integration
- Marker detection parameters shared
- Common coordinate frame usage
- Synchronized timestamp handling

### OpenVINS Integration
- ArUco tracking pipeline
- Feature database management
- Multi-camera synchronization

### ROS/ROS2 Compatibility
- Dual implementation support
- Message type adaptations
- API compatibility layer

## Future Enhancements

### Planned Features
1. Dynamic marker color coding
2. Interactive marker support
3. Real-time parameter tuning
4. Enhanced ArUco pose estimation
5. Multi-dictionary support

### Extension Points
- Custom marker types
- Additional coordinate systems
- Performance profiling tools
- Automated calibration workflows

## References

- [OpenCV ArUco Documentation](https://docs.opencv.org/master/d5/dae/tutorial_aruco_detection.html)
- [RViz Marker Documentation](http://wiki.ros.org/rviz/DisplayTypes/Marker)
- [MINS Paper and Documentation](https://github.com/rpng/MINS)
- [ArUco Tag Generator](https://chev.me/arucogen/) 