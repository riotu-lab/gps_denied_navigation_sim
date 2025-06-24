# FAST_LIO Parameter Documentation

This document provides a comprehensive explanation of all parameters used in FAST_LIO configuration files, along with code snippets from the implementation showing how each parameter is used.

## Table of Contents
1. [Feature Extraction Parameters](#feature-extraction-parameters)
2. [General Processing Parameters](#general-processing-parameters)
3. [Common Parameters](#common-parameters)
4. [Preprocessing Parameters](#preprocessing-parameters)
5. [Mapping Parameters](#mapping-parameters)
6. [Publishing Parameters](#publishing-parameters)
7. [PCD Save Parameters](#pcd-save-parameters)
8. [Taif World Specific Configuration](#taif-world-specific-configuration)

---

## Feature Extraction Parameters

### `feature_extract_enable`
**Type:** `bool`  
**Default:** `false`  
**Description:** Enables or disables feature extraction from point clouds.

**Implementation:**
```cpp
// From laserMapping.cpp:829
this->declare_parameter<bool>("feature_extract_enable", false);
this->get_parameter_or<bool>("feature_extract_enable", p_pre->feature_enabled, false);
```

**Usage in preprocessing:**
```cpp
// From preprocess.cpp:98-185
if (feature_enabled)
{
    for (uint i = 1; i < plsize; i++)
    {
        // Feature extraction logic for Livox points
        // Processes points line by line and extracts geometric features
    }
    // Extract features using give_feature() function
}
else
{
    // Simple point filtering without feature extraction
    if (valid_num % point_filter_num == 0)
    {
        // Add points to output cloud
    }
}
```

---

## General Processing Parameters

### `point_filter_num`
**Type:** `int`  
**Default:** `4`  
**Description:** Point filtering number - keeps every Nth point to reduce computational load.

**Implementation:**
```cpp
// From laserMapping.cpp:857
this->get_parameter_or<int>("point_filter_num", p_pre->point_filter_num, 2);
```

**Usage:**
```cpp
// From preprocess.cpp:184 (Livox handler)
if (valid_num % point_filter_num == 0)
{
    // Process this point
}

// From preprocess.cpp:270 (Velodyne handler)
if (i % point_filter_num != 0) continue;
```

### `max_iteration`
**Type:** `int`  
**Default:** `3`  
**Description:** Maximum iterations for the iterative closest point (ICP) algorithm in mapping.

**Implementation:**
```cpp
// From laserMapping.cpp:843
this->get_parameter_or<int>("max_iteration", NUM_MAX_ITERATIONS, 4);

// Usage in EKF initialization
kf.init_dyn_share(get_f, df_dx, df_dw, h_share_model, NUM_MAX_ITERATIONS, epsi);
```

### `filter_size_surf` & `filter_size_map`
**Type:** `double`  
**Default:** `0.5`  
**Description:** Voxel filter leaf size for surface features and map downsampling.

**Implementation:**
```cpp
// From laserMapping.cpp:847-849
this->get_parameter_or<double>("filter_size_surf",filter_size_surf_min,0.5);
this->get_parameter_or<double>("filter_size_map",filter_size_map_min,0.5);

// Usage for point cloud filtering
downSizeFilterSurf.setLeafSize(filter_size_surf_min, filter_size_surf_min, filter_size_surf_min);
downSizeFilterMap.setLeafSize(filter_size_map_min, filter_size_map_min, filter_size_map_min);
```

### `cube_side_length`
**Type:** `double`  
**Default:** `1000.0`  
**Description:** Side length of the cube used for local map management.

**Implementation:**
```cpp
// From laserMapping.cpp:851
this->get_parameter_or<double>("cube_side_length",cube_len,200.f);

// Usage in map management
float mov_dist = max((cube_len - 2.0 * MOV_THRESHOLD * DET_RANGE) * 0.5 * 0.9, 
                     double(DET_RANGE * (MOV_THRESHOLD -1)));
```

### `runtime_pos_log_enable`
**Type:** `bool`  
**Default:** `false`  
**Description:** Enables logging of position data during runtime.

**Implementation:**
```cpp
// From laserMapping.cpp:865
this->get_parameter_or<bool>("runtime_pos_log_enable", runtime_pos_log, 0);

// Usage in position logging
if(runtime_pos_log)
{
    dump_lio_state_to_log(fp);
}
```

### `map_file_path`
**Type:** `string`  
**Default:** `"./test.pcd"`  
**Description:** File path where the final map will be saved as a PCD file.

**Implementation:**
```cpp
// From laserMapping.cpp:843
this->get_parameter_or<string>("map_file_path", map_file_path, "");

// Usage in map saving
if (!map_file_path.empty())
{
    pcd_writer.writeBinary(map_file_path, *pcl_wait_pub);
    RCLCPP_INFO(this->get_logger(), "Saving map to %s...", map_file_path.c_str());
}
```

---

## Common Parameters

### `lid_topic`
**Type:** `string`  
**Default:** `"/target/front_lidar/points"`  
**Description:** ROS topic name for LiDAR point cloud messages.

**Implementation:**
```cpp
// From laserMapping.cpp:844
this->get_parameter_or<string>("common.lid_topic", lid_topic, "/livox/lidar");

// Usage in subscription setup
if (p_pre->lidar_type == AVIA)
{
    sub_pcl_livox_ = this->create_subscription<livox_ros_driver2::msg::CustomMsg>(
        lid_topic, 20, livox_pcl_cbk);
}
else
{
    sub_pcl_pc_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
        lid_topic, rclcpp::SensorDataQoS(), standard_pcl_cbk);
}
```

### `imu_topic`
**Type:** `string`  
**Default:** `"/target/mavros/imu/data_raw"`  
**Description:** ROS topic name for IMU data messages.

**Implementation:**
```cpp
// From laserMapping.cpp:845
this->get_parameter_or<string>("common.imu_topic", imu_topic,"/livox/imu");

// Usage in IMU subscription
sub_imu_ = this->create_subscription<sensor_msgs::msg::Imu>(imu_topic, 10, imu_cbk);
```

### `time_sync_en`
**Type:** `bool`  
**Default:** `false`  
**Description:** Enables external time synchronization. Should only be enabled when external sync is not possible.

**Implementation:**
```cpp
// From laserMapping.cpp:846
this->get_parameter_or<bool>("common.time_sync_en", time_sync_en, false);
```

### `time_offset_lidar_to_imu`
**Type:** `double`  
**Default:** `0.0`  
**Description:** Time offset between LiDAR and IMU in seconds. Calibrated by external algorithms like LI-Init.

**Implementation:**
```cpp
// From laserMapping.cpp:847
this->get_parameter_or<double>("common.time_offset_lidar_to_imu", time_diff_lidar_to_imu, 0.0);
```

---

## Preprocessing Parameters

### `lidar_type`
**Type:** `int`  
**Default:** `2`  
**Description:** Type of LiDAR sensor: 1=Livox, 2=Velodyne, 3=Ouster, 4=MID360.

**Implementation:**
```cpp
// From preprocess.h:14-18
enum LID_TYPE
{
  AVIA = 1,     // Livox AVIA
  VELO16,       // Velodyne VLP-16
  OUST64,       // Ouster OS1-64
  MID360        // Livox MID-360
};

// From laserMapping.cpp:855
this->get_parameter_or<int>("preprocess.lidar_type", p_pre->lidar_type, AVIA);

// Usage in point cloud processing
switch (lidar_type)
{
    case OUST64:
        oust64_handler(msg);
        break;
    case VELO16:
        velodyne_handler(msg);
        break;
    case MID360:
        mid360_handler(msg);
        break;
    default:
        default_handler(msg);
        break;
}
```

### `scan_line`
**Type:** `int`  
**Default:** `32`  
**Description:** Number of scan lines in the LiDAR.

**Implementation:**
```cpp
// From laserMapping.cpp:856
this->get_parameter_or<int>("preprocess.scan_line", p_pre->N_SCANS, 16);

// Usage in preprocessing
for (int i = 0; i < N_SCANS; i++)
{
    pl_buff[i].clear();
    pl_buff[i].reserve(plsize);
}
```

### `scan_rate`
**Type:** `int`  
**Default:** `10`  
**Description:** Scan rate of the LiDAR in Hz (only needed for Velodyne).

**Implementation:**
```cpp
// From laserMapping.cpp:857
this->get_parameter_or<int>("preprocess.scan_rate", p_pre->SCAN_RATE, 10);

// Usage in Velodyne processing
double omega_l = 0.361 * SCAN_RATE;  // scan angular velocity
```

### `timestamp_unit`
**Type:** `int`  
**Default:** `2`  
**Description:** Unit of time/t field in PointCloud2: 0=second, 1=millisecond, 2=microsecond, 3=nanosecond.

**Implementation:**
```cpp
// From preprocess.h:19-24
enum TIME_UNIT
{
  SEC = 0,
  MS = 1,
  US = 2,
  NS = 3
};

// From preprocess.cpp:52-68
switch (time_unit)
{
    case SEC:
        time_unit_scale = 1.e3f;
        break;
    case MS:
        time_unit_scale = 1.f;
        break;
    case US:
        time_unit_scale = 1.e-3f;
        break;
    case NS:
        time_unit_scale = 1.e-6f;
        break;
}
```

### `blind`
**Type:** `double`  
**Default:** `2.0`  
**Description:** Minimum distance threshold - points closer than this distance are ignored.

**Implementation:**
```cpp
// From laserMapping.cpp:855
this->get_parameter_or<double>("preprocess.blind", p_pre->blind, 0.01);

// Usage in distance filtering
if (range < (blind * blind))
    continue;  // Skip points too close

// From preprocess.cpp:180-186
if (pl_full[i].x * pl_full[i].x + pl_full[i].y * pl_full[i].y + pl_full[i].z * pl_full[i].z > (blind * blind))
{
    pl_surf.push_back(pl_full[i]);
}
```

---

## Mapping Parameters

### `acc_cov` & `gyr_cov`
**Type:** `double`  
**Default:** `0.1`  
**Description:** Accelerometer and gyroscope noise covariance for the IMU.

**Implementation:**
```cpp
// From laserMapping.cpp:854-855
this->get_parameter_or<double>("mapping.acc_cov",acc_cov,0.1);
this->get_parameter_or<double>("mapping.gyr_cov",gyr_cov,0.1);

// Usage in IMU processor setup
p_imu->set_gyr_cov(V3D(gyr_cov, gyr_cov, gyr_cov));
p_imu->set_acc_cov(V3D(acc_cov, acc_cov, acc_cov));
```

### `b_acc_cov` & `b_gyr_cov`
**Type:** `double`  
**Default:** `0.0001`  
**Description:** Accelerometer and gyroscope bias noise covariance.

**Implementation:**
```cpp
// From laserMapping.cpp:856-857
this->get_parameter_or<double>("mapping.b_gyr_cov",b_gyr_cov,0.0001);
this->get_parameter_or<double>("mapping.b_acc_cov",b_acc_cov,0.0001);

// Usage in IMU processor setup
p_imu->set_gyr_bias_cov(V3D(b_gyr_cov, b_gyr_cov, b_gyr_cov));
p_imu->set_acc_bias_cov(V3D(b_acc_cov, b_acc_cov, b_acc_cov));
```

### `fov_degree`
**Type:** `double`  
**Default:** `360.0`  
**Description:** Field of view of the LiDAR in degrees.

**Implementation:**
```cpp
// From laserMapping.cpp:853
this->get_parameter_or<double>("mapping.fov_degree",fov_deg,180.f);

// Usage in FOV calculations
FOV_DEG = (fov_deg + 10.0) > 179.9 ? 179.9 : (fov_deg + 10.0);
HALF_FOV_COS = cos((FOV_DEG) * 0.5 * PI_M / 180.0);
```

### `det_range`
**Type:** `double`  
**Default:** `100.0`  
**Description:** Maximum detection range for LiDAR points in meters.

**Implementation:**
```cpp
// From laserMapping.cpp:852
this->get_parameter_or<float>("mapping.det_range",DET_RANGE,300.f);

// Usage in map boundary detection
if (dist_to_map_edge[i][0] <= MOV_THRESHOLD * DET_RANGE || 
    dist_to_map_edge[i][1] <= MOV_THRESHOLD * DET_RANGE) 
{
    need_move = true;
}
```

### `extrinsic_est_en`
**Type:** `bool`  
**Default:** `false`  
**Description:** Enables online estimation of IMU-LiDAR extrinsic parameters.

**Implementation:**
```cpp
// From laserMapping.cpp:866
this->get_parameter_or<bool>("mapping.extrinsic_est_en", extrinsic_est_en, true);
```

### `extrinsic_T` & `extrinsic_R`
**Type:** `vector<double>`  
**Default:** See config file  
**Description:** Translation and rotation matrices for IMU-LiDAR extrinsic calibration.

**Implementation:**
```cpp
// From laserMapping.cpp:869-870
this->get_parameter_or<vector<double>>("mapping.extrinsic_T", extrinT, vector<double>());
this->get_parameter_or<vector<double>>("mapping.extrinsic_R", extrinR, vector<double>());

// Usage in transformation setup
Lidar_T_wrt_IMU<<VEC_FROM_ARRAY(extrinT);
Lidar_R_wrt_IMU<<MAT_FROM_ARRAY(extrinR);
p_imu->set_extrinsic(Lidar_T_wrt_IMU, Lidar_R_wrt_IMU);
```

---

## Publishing Parameters

### `path_en`
**Type:** `bool`  
**Default:** `true`  
**Description:** Enables publishing of the trajectory path.

### `scan_publish_en`
**Type:** `bool`  
**Default:** `false`  
**Description:** Enables publishing of point cloud scans. Set to false to reduce output.

### `dense_publish_en`
**Type:** `bool`  
**Default:** `false`  
**Description:** Controls point density in published global frame point clouds.

### `scan_bodyframe_pub_en`
**Type:** `bool`  
**Default:** `false`  
**Description:** Enables publishing of point cloud scans in IMU body frame.

**Implementation:**
```cpp
// From laserMapping.cpp:836-840
this->get_parameter_or<bool>("publish.path_en", path_en, true);
this->get_parameter_or<bool>("publish.scan_publish_en", scan_pub_en, true);
this->get_parameter_or<bool>("publish.dense_publish_en", dense_pub_en, true);
this->get_parameter_or<bool>("publish.scan_bodyframe_pub_en", scan_body_pub_en, true);

// Usage in publishing logic
if(scan_pub_en) publish_frame_world(pubLaserCloudFull_);
if(dense_pub_en) publish_frame_world(pubLaserCloudFull_);
if(scan_body_pub_en) publish_frame_body(pubLaserCloudFull_body_);
if(path_en) publish_path(pubPath_);
```

---

## PCD Save Parameters

### `pcd_save_en`
**Type:** `bool`  
**Default:** `true`  
**Description:** Enables saving of point cloud data to PCD files.

### `interval`
**Type:** `int`  
**Default:** `-1`  
**Description:** Number of LiDAR frames to save in each PCD file. -1 saves all frames in one file.

**Implementation:**
```cpp
// From laserMapping.cpp:867-868
this->get_parameter_or<bool>("pcd_save.pcd_save_en", pcd_save_en, false);
this->get_parameter_or<int>("pcd_save.interval", pcd_save_interval, -1);

// Usage in PCD saving logic
if(pcd_save_en)
{
    if(pcd_save_interval == -1)
    {
        // Save all points in one file
        *pcl_wait_save += *feats_down_body;
    }
    else
    {
        // Save periodically based on interval
        if(frame_num % pcd_save_interval == 0)
        {
            save_to_pcd();
        }
    }
}
```

---

## Taif World Specific Configuration

### Environment Overview
The Taif world represents a challenging GPS-denied navigation scenario in mountainous terrain:

- **Location**: Taif, Saudi Arabia (21.27081°N, 40.34730°E)
- **Altitude**: 1,874.6 meters
- **Terrain Type**: Mountainous/Highland DEM-based terrain
- **Coverage Area**: ~12.8 km × 4.8 km (~61.4 km²)
- **Environment**: Outdoor, natural terrain with significant elevation changes

### Optimized Parameter Configuration

#### Key Adjustments for Mountainous Terrain

```yaml
# Taif-specific optimized configuration
point_filter_num: 2              # Reduced for better point density in sparse outdoor environment
max_iteration: 5                 # Increased for robust convergence in complex terrain
filter_size_surf: 0.25           # Fine resolution for detailed terrain mapping
filter_size_map: 0.35            # Balanced for outdoor environment
cube_side_length: 3000.0         # Large 3km cube for extensive terrain coverage
det_range: 500.0                 # Extended range for large-scale terrain mapping
blind: 1.0                       # Reduced for mountainous obstacle detection

# IMU parameters optimized for outdoor aerial navigation
acc_cov: 0.03                    # Low noise for stable outdoor flight
gyr_cov: 0.03                    # Low gyro noise for smooth maneuvers
b_acc_cov: 0.00003               # Very low bias for stability
b_gyr_cov: 0.00003               # Very low gyro bias for long missions

# Publishing enabled for terrain visualization
scan_publish_en: true            # Enable terrain visualization
dense_publish_en: true           # Enable detailed terrain mapping
interval: 300                    # Manageable PCD file sizes for large environments
```

### Parameter Rationale for Taif World

#### 1. **Point Density Optimization**
- **`point_filter_num: 2`**: Outdoor environments typically have sparser features than indoor environments. Reducing filtering preserves more points for better terrain detail.

#### 2. **Convergence Robustness**
- **`max_iteration: 5`**: Mountainous terrain with varying slopes and features requires more iterations for robust convergence.

#### 3. **Scale Adaptations**
- **`cube_side_length: 3000.0`**: Large 3km cube accommodates the extensive 12.8×4.8km terrain area.
- **`det_range: 500.0`**: Extended detection range suitable for open mountainous environment.

#### 4. **Resolution Balance**
- **`filter_size_surf: 0.25`**: Finer surface resolution captures terrain detail without excessive computational load.
- **`filter_size_map: 0.35`**: Balanced map resolution for outdoor navigation.

#### 5. **IMU Noise Optimization**
- **Lower covariance values**: Outdoor flight typically has less vibration and disturbance than indoor navigation.
- **Reduced bias parameters**: Stable outdoor conditions allow for lower noise assumptions.

#### 6. **Memory Management**
- **`interval: 300`**: Prevents memory overflow while maintaining comprehensive terrain coverage in large environments.

### Usage Instructions

#### For Taif World Simulation:
```bash
# Use the optimized Taif configuration
ros2 launch fast_lio fast_lio.launch.py config:=taif_outdoor.yaml
```

#### Alternative Configurations:
```yaml
# Conservative settings for initial testing
point_filter_num: 3
max_iteration: 4
det_range: 300.0

# High-detail settings for detailed mapping
filter_size_surf: 0.2
filter_size_map: 0.3
interval: 200
```

### Performance Considerations

#### Computational Load
- **Higher point density** (lower `point_filter_num`) increases processing time
- **More iterations** improve accuracy but reduce real-time performance
- **Finer filters** provide better detail but require more memory

#### Memory Usage
- Large `cube_side_length` and `det_range` increase memory requirements
- Frequent PCD saving (lower `interval`) can fill disk space quickly
- Dense point clouds require substantial RAM for processing

### Expected Results
With these optimized parameters for Taif world, you should observe:

1. **Improved terrain following** due to finer surface resolution
2. **Better long-range mapping** with extended detection range
3. **Stable navigation** in mountainous terrain with optimized IMU parameters
4. **Comprehensive coverage** of the large outdoor environment
5. **Manageable computational load** balanced for real-time performance

This documentation provides comprehensive understanding of each parameter's purpose and implementation within the FAST_LIO system. 