# MINS LiDAR Parameters Documentation

This document provides a detailed explanation of all parameters in the MINS LiDAR configuration file, with code snippets showing their implementation in the codebase.

## Basic Configuration Parameters

### `enabled`
Enables or disables the LiDAR sensor in the system.

```cpp
// from OptionsLidar.h
bool enabled = true;

// from OptionsLidar.cpp
parser->parse_external(f, "lidar", "enabled", enabled);
```

### `max_n`
Maximum number of LiDAR sensors that can be used.

```cpp
// from OptionsLidar.h
int max_n = 2;

// from OptionsLidar.cpp
parser->parse_external(f, "lidar", "max_n", max_n);

// from UpdaterLidar.cpp
UpdaterLidar::UpdaterLidar(shared_ptr<State> state) : state(state) {
  for (int i = 0; i < state->op->lidar->max_n; i++) {
    Chi.emplace_back(make_shared<UpdaterStatistics>(state->op->lidar->chi2_mult, "LIDAR", i));
    t_hist.insert({i, deque<double>()});
    ikd_data.push_back(make_shared<iKDDATA>(i));
  }
}
```

## Calibration Parameters

### `do_calib_dt` and `do_calib_ext`
Enable/disable calibration of timeoffset and extrinsic parameters.

```cpp
// from OptionsLidar.h
bool do_calib_dt = false;
bool do_calib_ext = false;

// from UpdaterLidar.cpp - Used for state estimation
state->op->lidar->do_calib_ext ? StateHelper::insert_map({calibration}, map_hx, H_order, total_hx) : void();
state->op->lidar->do_calib_dt ? StateHelper::insert_map({timeoffset}, map_hx, H_order, total_hx) : void();
```

### `init_cov_dt`, `init_cov_ex_o`, and `init_cov_ex_p`
Initial covariance values for calibration parameters.

```cpp
// from OptionsLidar.h
double init_cov_dt = 1e-3;
double init_cov_ex_o = 1e-3;
double init_cov_ex_p = 1e-3;
```

## Range Parameters

### `max_range` and `min_range`
Maximum and minimum allowable range for LiDAR measurements. Points outside this range are discarded.

```cpp
// from OptionsLidar.h
double max_range = 100.0;
double min_range = 0.05;

// from LidarTypes.cpp - Used when filtering raw measurements
LiDARData::LiDARData(double time, double ref_time, int id, std::shared_ptr<pcl::PointCloud<pcl::PointXYZ>> pointcloud, double max_range, double min_range) : time(time), id(id) {
  // [...]
  for (int i = 0; i < (int)pointcloud->size(); i++) {
    // filter out-of-range measurements
    float n = pointcloud->points[i].getVector3fMap().norm();
    if (n > max_range || n < min_range)
      continue;
    
    // Copy point to pointcloud
    // [...]
  }
}
```

## Chi-Square Test Parameter

### `chi2_mult`
Multiplier for chi-square test threshold. Higher values are more permissive with outliers.

```cpp
// from OptionsLidar.h
double chi2_mult = 1;

// from UpdaterLidar.cpp
UpdaterLidar::UpdaterLidar(shared_ptr<State> state) : state(state) {
  for (int i = 0; i < state->op->lidar->max_n; i++) {
    Chi.emplace_back(make_shared<UpdaterStatistics>(state->op->lidar->chi2_mult, "LIDAR", i));
    // [...]
  }
}

// from UpdaterStatistics.cpp
bool UpdaterStatistics::Chi2Check(const MatrixXd &P, const MatrixXd &H, const VectorXd &res, const MatrixXd &R, bool print) {
  // [...]
  if (res.rows() < max_chi_size) {
    thr = chi2_mult * chi_squared_table[res.rows()];
  } else {
    chi_squared chi_squared_dist(res.rows());
    thr = chi2_mult * quantile(chi_squared_dist, 0.95);
  }
  // [...]
  // return Chi square test results
  if (chi < thr) {
    n_acp++;
    // Accept measurement
    // [...]
    return true;
  } else {
    n_rej++;
    // Reject measurement
    // [...]
    return false;
  }
}
```

## Raw Point Cloud Processing Parameters

### `raw_do_downsample`
Boolean to enable downsampling of raw point clouds.

```cpp
// from OptionsLidar.h
bool raw_do_downsample = false;

// from UpdaterLidar.cpp
// Do down sample the pointcloud if enabled
state->op->lidar->raw_do_downsample ? LidarHelper::downsample((*it), state->op->lidar->raw_downsample_size) : void();
```

### `raw_downsample_size`
Voxel grid size for downsampling raw point clouds. Larger values mean more aggressive downsampling.

```cpp
// from OptionsLidar.h
double raw_downsample_size = 0.5;

// from LidarHelper.cpp
void LidarHelper::downsample(shared_ptr<LiDARData> lidar, double downsample_size) {
  pcl::VoxelGrid<pcl::PointXYZI> downSizeFilter;
  downSizeFilter.setLeafSize((float)downsample_size, (float)downsample_size, (float)downsample_size);
  downSizeFilter.setInputCloud((*lidar->pointcloud).makeShared());
  downSizeFilter.filter(*lidar->pointcloud);
}
```

### `raw_noise`
Expected noise level in raw measurements. Used in the EKF update step.

```cpp
// from OptionsLidar.h
double raw_noise = 0.01;

// from UpdaterLidar.cpp - Used in state estimation
// Whiten the noise
double raw_noise = plane_abcd.head(3).norm() * state->op->lidar->raw_noise + intr_std;
double map_noise = plane_abcd.head(3).norm() * state->op->lidar->map_noise + intr_std;
H.block(row_size - 1, 0, 1, total_hx) /= raw_noise;
dz_dplane_abc.block(row_size - 1, 0, 1, 3) /= raw_noise;
dz_dplane_abc.block(0, 0, state->op->lidar->map_ngbr_num, 3) /= map_noise;
res(row_size - 1) /= raw_noise;
res.head(state->op->lidar->map_ngbr_num) /= map_noise;
```

### `raw_remove_motion_blur`
Enable/disable motion blur correction for raw point clouds.

```cpp
// from OptionsLidar.h
bool raw_remove_motion_blur = true;

// from LidarHelper.cpp
bool LidarHelper::remove_motion_blur(shared_ptr<State> state, shared_ptr<LiDARData> lidar_inL, shared_ptr<OptionsLidar> op) {
  // if this option is not enabled, return true
  if (!op->raw_remove_motion_blur)
    return true;

  // Here we undistort the lidar pointcloud using state
  // [motion correction implementation]
  // [...]
}
```

### `raw_point_dt`
Timestamp difference between consecutive points in a scan. Used for motion blur correction.

```cpp
// from OptionsLidar.h
double raw_point_dt = 1e-6;

// from LidarHelper.cpp - Used in motion blur correction
int total = op->v_angles.at(lidar_inL->id).size() * op->h_angles.at(lidar_inL->id).size();
if (state->get_interpolated_pose(lidar_inL->time + dt - total * op->raw_point_dt, D.R, D.p))
  return false;

// [...]

// Get IMU pose at time i
Matrix3d RGtoIi;
Vector3d pIiinG;
success = state->get_interpolated_pose(lidar_inL->time + dt - (total - i) * op->raw_point_dt, RGtoIi, pIiinG);
```

## Map Processing Parameters

### `map_do_downsample`
Boolean to enable downsampling when adding points to the map.

```cpp
// from OptionsLidar.h
bool map_do_downsample = true;

// from LidarHelper.cpp
if (lidar->icp_success) {
  pcl::PointCloud<pcl::PointXYZI> tr_points;
  pcl::transformPointCloud(*(lidar->pointcloud_original), tr_points, lidar->T_LtoM);
  ikd->tree->Add_Points(tr_points.points, state->op->lidar->map_do_downsample);
  ikd->last_up_time = lidar->time;
}
```

### `map_downsample_size`
Voxel grid size for downsampling the map point cloud.

```cpp
// from OptionsLidar.h
double map_downsample_size = 0.1;

// from LidarHelper.cpp
void LidarHelper::init_map_local(const shared_ptr<LiDARData> &lidar_inL, shared_ptr<iKDDATA> ikd, shared_ptr<OptionsLidar> op, bool prop) {
  // [...]
  ikd->tree->set_downsample_param(op->map_downsample_size);
  ikd->tree->Build(lidar_inL->pointcloud->points);
}

// from LidarHelper.cpp
void LidarHelper::propagate_map_to_newest_clone(shared_ptr<State> state, shared_ptr<iKDDATA> ikd, shared_ptr<OptionsLidar> op, double FT) {
  // [...]
  op->map_do_downsample ? downsample(map_points, state->op->lidar->map_downsample_size) : void();
  // [...]
}
```

### `map_noise`
Expected noise level in map points. Used in the EKF update step.

```cpp
// from OptionsLidar.h
double map_noise = 0.01;

// from UpdaterLidar.cpp - Used in state estimation
double map_noise = plane_abcd.head(3).norm() * state->op->lidar->map_noise + intr_std;
dz_dplane_abc.block(0, 0, state->op->lidar->map_ngbr_num, 3) /= map_noise;
res.head(state->op->lidar->map_ngbr_num) /= map_noise;
```

### `map_ngbr_num`
Minimum number of neighbors required for plane extraction.

```cpp
// from OptionsLidar.h
int map_ngbr_num = 5;

// from LidarHelper.cpp
bool LidarHelper::get_neighbors(Vector3d pfinM, POINTCLOUD_XYZI_PTR neighbors, shared_ptr<KD_TREE<pcl::PointXYZI>> tree, shared_ptr<OptionsLidar> op) {
  // [...]
  // Now find neighbors from the map
  vector<float> neighbors_d;
  tree->Nearest_Search(pfinM_, op->map_ngbr_num, neighbors->points, neighbors_d);

  // continue if we didn't find enough points
  if ((int)neighbors->size() < op->map_ngbr_num || (int)neighbors_d.size() < op->map_ngbr_num)
    return false;
  // [...]
}
```

### `map_ngbr_max_d`
Maximum distance to consider for neighbor points during feature extraction.

```cpp
// from OptionsLidar.h
double map_ngbr_max_d = 1;

// from LidarHelper.cpp
bool LidarHelper::get_neighbors(Vector3d pfinM, POINTCLOUD_XYZI_PTR neighbors, shared_ptr<KD_TREE<pcl::PointXYZI>> tree, shared_ptr<OptionsLidar> op) {
  // [...]
  // continue if near point distance is too far
  if (neighbors_d.back() > op->map_ngbr_max_d)
    return false;
  // [...]
}
```

### `map_decay_time` and `map_decay_dist`
Time (in seconds) and distance (in meters) thresholds for removing old map points.

```cpp
// from OptionsLidar.h
double map_decay_time = 120;
double map_decay_dist = 200;

// from LidarHelper.cpp
void LidarHelper::propagate_map_to_newest_clone(shared_ptr<State> state, shared_ptr<iKDDATA> ikd, shared_ptr<OptionsLidar> op, double FT) {
  // [...]
  // Delete old points
  shared_ptr<LiDARData> lidar_inM = shared_ptr<LiDARData>(new LiDARData);
  lidar_inM->pointcloud->points.reserve(map_points->size());
  for (auto &pt : map_points->points) {
    if (pt.intensity + FT + op->map_decay_time < state->time)
      continue;
    if (Vector3f(pt.x, pt.y, pt.z).norm() > state->op->lidar->map_decay_dist)
      continue;
    // Keep this feature
    lidar_inM->pointcloud->push_back(pt);
  }
  // [...]
}
```

## ICP Parameters

### `map_use_icp`
Boolean to enable ICP for aligning new scans to the map.

```cpp
// from OptionsLidar.h
bool map_use_icp = true;

// from LidarHelper.cpp
bool LidarHelper::transform_to_map(shared_ptr<State> state, shared_ptr<LiDARData> lidar, shared_ptr<iKDDATA> ikd) {
  // [...]
  if (state->op->lidar->map_use_icp) {
    POINTCLOUD_XYZI_PTR map_pointcloud = std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();
    ikd->tree->flatten(ikd->tree->Root_Node, map_pointcloud->points, NOT_RECORD);
    POINTCLOUD_XYZI_PTR new_pointcloud = lidar->pointcloud;

    typedef PointMatcher<float> PM;
    PM::ICP icp;
    icp.setDefault();
    // [ICP implementation]
    // [...]
  } else {
    lidar->T_LtoM = T_LtoM;
    lidar->icp_success = true;
  }
  // [...]
}
```

### `map_icp_dist`
Maximum distance to consider between corresponding points in ICP.

```cpp
// from OptionsLidar.h
double map_icp_dist = 50;

// from LidarHelper.cpp
if (state->op->lidar->map_use_icp) {
  // [...]
  // Adjust referenceDataPointsFilters
  auto params = PM::Parameters();
  params["maxDist"] = to_string(state->op->lidar->map_icp_dist);
  icp.referenceDataPointsFilters.clear();
  icp.referenceDataPointsFilters.push_back(PM::get().DataPointsFilterRegistrar.create("MaxDistDataPointsFilter", params));
  // [...]
}
```

## Plane Extraction Parameters

### `plane_max_p2pd`
Maximum point-to-plane distance allowed for plane fitting.

```cpp
// from OptionsLidar.h
double plane_max_p2pd = 0.5;

// from LidarHelper.cpp
bool LidarHelper::compute_plane(Vector4d &plane_abcd, POINTCLOUD_XYZI_PTR pointcloud, shared_ptr<OptionsLidar> op) {
  // [...]
  // sanity check
  Vector4d pl = plane_abcd / plane_abcd.head(3).norm();
  for (int j = 0; j < (int)pointcloud->size(); j++) {
    pcl::PointXYZI pt = pointcloud->points[j];
    if (fabs(pl(0) * pt.x + pl(1) * pt.y + pl(2) * pt.z + pl(3)) > op->plane_max_p2pd) {
      return false;
    }
  }
  // All good :)
  return true;
}

// Also used in UpdaterLidar.cpp to discard bad matches
if (-plane_abcd.head(3).transpose() * pfinM_est - plane_abcd(3) > state->op->lidar->plane_max_p2pd * 3)
  continue;
```

### `plane_max_condi`
Maximum condition number allowed for plane fitting.

```cpp
// from OptionsLidar.h
double plane_max_condi = 200.0;

// from LidarHelper.cpp
bool LidarHelper::compute_plane(Vector4d &plane_abcd, POINTCLOUD_XYZI_PTR pointcloud, shared_ptr<OptionsLidar> op) {
  // [...]
  // Check the condition number of A.
  JacobiSVD<MatrixXd> svd(A, ComputeThinU | ComputeThinV);
  MatrixXd singularValues;
  singularValues.resize(svd.singularValues().rows(), 1);
  singularValues = svd.singularValues();
  double condA = singularValues(0, 0) / singularValues(singularValues.rows() - 1, 0);
  if (condA > op->plane_max_condi) {
    return false;
  }
  // [...]
}
```

## LiDAR Sensor Configuration Parameters

### Sensor-Specific Parameters
Each LiDAR sensor is configured with the following parameters:

```yaml
lidar0:
  timeoffset: 0.0
  topic: "/lidar/points"
  T_imu_lidar: [transformation matrix]
  v_angles: [vertical angles array]
  h_resolution: 2.0
  h_start: -180
  h_end: 180
```

These parameters define:
- `timeoffset`: Temporal offset between LiDAR and IMU
- `topic`: ROS topic for LiDAR data
- `T_imu_lidar`: Transformation matrix from IMU to LiDAR
- `v_angles`: Array of vertical angles (degrees) for the scan pattern
- `h_resolution`: Horizontal angle resolution (degrees)
- `h_start` and `h_end`: Start and end horizontal angles (degrees)

## Parameter Optimization for UAV Above 50m

For a UAV flying above 50m with sparse terrain features, consider these optimizations:

1. **Range parameters**:
   - `min_range`: Set to just under the flying altitude (e.g., 45m)
   - `max_range`: Increase to 300m to capture distant terrain features

2. **Downsampling parameters**:
   - Increase `raw_downsample_size` and `map_downsample_size` (e.g., 5.0m)
   - Increase `h_resolution` (e.g., 2.0°) to reduce point density

3. **Feature extraction parameters**:
   - Reduce `map_ngbr_num` (e.g., 6) to work with fewer points
   - Increase `plane_max_p2pd` and `plane_max_condi` to be more permissive

4. **Noise handling**:
   - Increase `raw_noise` and `map_noise` to account for uncertainty
   - Increase `chi2_mult` to be more permissive with outliers

5. **Map management**:
   - Increase `map_decay_time` and `map_decay_dist` to maintain features longer 