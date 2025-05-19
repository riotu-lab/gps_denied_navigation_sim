# MINS Camera Parameters Documentation

This document provides a detailed explanation of all parameters in the MINS Camera configuration file, with code snippets showing their implementation in the codebase.

## Basic Configuration Parameters

### `enabled`
Enables or disables the camera sensor in the system.

```cpp
// from OptionsCamera.h
bool enabled = true;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "enabled", enabled);
```

### `max_n`
Maximum number of camera sensors that can be used.

```cpp
// from OptionsCamera.h
int max_n = 2;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "max_n", max_n);

// from UpdaterCamera.cpp
UpdaterCamera::UpdaterCamera(shared_ptr<State> state) : state(state) {
  shared_ptr<OptionsCamera> op = state->op->cam;
  // Let's make a feature extractor and other setups
  for (int i = 0; i < op->max_n; i++) {
    // check if we have the trackDATABASE for this camera
    if (trackDATABASE.find(i) == trackDATABASE.end()) {
      // ...setup for this camera...
    }
  }
}
```

### `use_stereo`
Boolean to determine if the system should use stereo constraints for feature tracking and triangulation.

```cpp
// from OptionsCamera.h
bool use_stereo = true;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "use_stereo", use_stereo);

// from UpdaterCamera.cpp
if (!op->use_stereo || op->stereo_pairs.find(i) == op->stereo_pairs.end()) {
  // this is mono camera setup
} else {
  // this is stereo camera setup
}
```

### `stereo_pair`
Array that specifies which cameras form stereo pairs.

```cpp
// from OptionsCamera.cpp
if (use_stereo) {
  std::vector<int> vec_stereo_pair;
  parser->parse_external(f, "cam", "stereo_pair", vec_stereo_pair);
  if ((int)vec_stereo_pair.size() % 2 != 0) {
    PRINT4(RED "Stero pair should be provided even number.\n" RESET);
    exit(EXIT_FAILURE);
  }
  for (int i = 0; i < (int)vec_stereo_pair.size() / 2; i++) {
    if (vec_stereo_pair.at(2 * i) < max_n && vec_stereo_pair.at(2 * i + 1) < max_n) {
      if (stereo_pairs.find(vec_stereo_pair.at(2 * i)) != stereo_pairs.end() || 
          stereo_pairs.find(vec_stereo_pair.at(2 * i + 1)) != stereo_pairs.end()) {
        PRINT4(RED "A camera is paired with more than one camera.\n" RESET);
        exit(EXIT_FAILURE);
      }
      stereo_pairs.insert({vec_stereo_pair.at(2 * i), vec_stereo_pair.at(2 * i + 1)});
      stereo_pairs.insert({vec_stereo_pair.at(2 * i + 1), vec_stereo_pair.at(2 * i)});
    }
  }
}
```

## Calibration Parameters

### `do_calib_ext`, `do_calib_int`, and `do_calib_dt`
Enable/disable calibration of extrinsic parameters, intrinsic parameters, and timeoffset.

```cpp
// from OptionsCamera.h
bool do_calib_ext = false;
bool do_calib_int = false;
bool do_calib_dt = false;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "do_calib_ext", do_calib_ext);
parser->parse_external(f, "cam", "do_calib_int", do_calib_int);
parser->parse_external(f, "cam", "do_calib_dt", do_calib_dt);

// from CamHelper.cpp - Used in state estimation
// If doing calibration extrinsics
if (state->op->cam->do_calib_ext && map_hx.find(calibration) == map_hx.end()) {
  map_hx.insert({calibration, total_hx});
  linsys.Hx_order.push_back(calibration);
  total_hx += calibration->size();
}

// If doing calibration intrinsics
if (state->op->cam->do_calib_int && map_hx.find(distortion) == map_hx.end()) {
  map_hx.insert({distortion, total_hx});
  linsys.Hx_order.push_back(distortion);
  total_hx += distortion->size();
}

// If doing calibration timeoffset
if (state->op->cam->do_calib_dt && map_hx.find(timeoffset) == map_hx.end()) {
  map_hx.insert({timeoffset, total_hx});
  linsys.Hx_order.push_back(timeoffset);
  total_hx += timeoffset->size();
}
```

### `init_cov_dt`, `init_cov_ex_o`, `init_cov_ex_p`, `init_cov_in_k`, `init_cov_in_c`, and `init_cov_in_r`
Initial covariance values for calibration parameters.

```cpp
// from OptionsCamera.h
double init_cov_dt = 1e-4;  // time offset
double init_cov_ex_o = 1e-4; // extrinsic orientation
double init_cov_ex_p = 1e-3; // extrinsic position
double init_cov_in_k = 1e-0; // intrinsic focal length
double init_cov_in_c = 1e-0; // intrinsic principal point
double init_cov_in_r = 1e-5; // intrinsic distortion

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "init_cov_dt", init_cov_dt);
parser->parse_external(f, "cam", "init_cov_ex_o", init_cov_ex_o);
parser->parse_external(f, "cam", "init_cov_ex_p", init_cov_ex_p);
parser->parse_external(f, "cam", "init_cov_in_k", init_cov_in_k);
parser->parse_external(f, "cam", "init_cov_in_c", init_cov_in_c);
parser->parse_external(f, "cam", "init_cov_in_r", init_cov_in_r);
```

## Feature Extraction Parameters

### `n_pts`
The number of points to extract and track in each image frame.

```cpp
// from OptionsCamera.h
int n_pts = 150;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "n_pts", n_pts);

// from UpdaterCamera.cpp
trackFEATS.insert({i, shared_ptr<TrackBase>(new TrackKLT(state->cam_intrinsic_model, 
                  op->n_pts, 0, op->use_stereo, op->histogram, op->fast, 
                  op->grid_x, op->grid_y, op->min_px_dist))});
```

### `fast`
Fast extraction threshold. Lower values detect more features but may include weaker corners.

```cpp
// from OptionsCamera.h
int fast = 20;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "fast", fast);

// from TrackKLT.cpp
Grider_FAST::perform_griding(img0pyr.at(0), mask0_updated, valid_locs, pts0_ext, num_features, grid_x, grid_y, threshold, true);
// Where threshold is set to fast in the constructor
```

### `grid_x` and `grid_y` 
Number of grid cells to split the image column-wise and row-wise for feature extraction.

```cpp
// from OptionsCamera.h
int grid_x = 5;
int grid_y = 5;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "grid_x", grid_x);
parser->parse_external(f, "cam", "grid_y", grid_y);

// from Grider_FAST.h
static void perform_griding(const cv::Mat &img, const cv::Mat &mask, std::vector<cv::KeyPoint> &pts, 
                            int num_features, int grid_x, int grid_y, int threshold, bool nonmaxSuppression) {
  // Calculate the size our extraction boxes should be
  int size_x = img.cols / grid_x;
  int size_y = img.rows / grid_y;
  
  // Calculate features per grid
  int num_features_grid = (int)((double)num_features / (double)(grid_x * grid_y)) + 1;
  
  // Extract features from each grid cell
  // ...
}
```

### `min_px_dist`
Minimum pixel distance between features. Used to prevent clustering of features.

```cpp
// from OptionsCamera.h
int min_px_dist = 10;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "min_px_dist", min_px_dist);

// from TrackKLT.cpp
// Used to create grid for feature distribution
cv::Size size_close0((int)((float)img0pyr.at(0).cols / (float)min_px_dist), 
                     (int)((float)img0pyr.at(0).rows / (float)min_px_dist));
cv::Mat grid_2d_close0 = cv::Mat::zeros(size_close0, CV_8UC1);

// Used to reject features too close to existing ones
if (x - min_px_dist >= 0 && x + min_px_dist < img0pyr.at(0).cols && 
    y - min_px_dist >= 0 && y + min_px_dist < img0pyr.at(0).rows) {
  cv::Point pt1(x - min_px_dist, y - min_px_dist);
  cv::Point pt2(x + min_px_dist, y + min_px_dist);
  cv::rectangle(mask0_updated, pt1, pt2, cv::Scalar(255), -1);
}
```

### `knn`
KNN ratio between top two descriptor matches required to be a good match.

```cpp
// from OptionsCamera.h
double knn = 0.85;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "knn", knn);

// Used in descriptor matching (when using descriptor-based tracking)
```

### `downsample`
Will half the resolution of all tracking images if set to true.

```cpp
// from OptionsCamera.h
bool downsample = false;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "downsample", downsample);

// from OptionsCamera.cpp - Downsampling intrinsics if enabled
intrinsic(0) /= (downsample) ? 2.0 : 1.0;
intrinsic(1) /= (downsample) ? 2.0 : 1.0;
intrinsic(2) /= (downsample) ? 2.0 : 1.0;
intrinsic(3) /= (downsample) ? 2.0 : 1.0;

// from OptionsCamera.cpp - Downsampling resolution if enabled
wh_i[0] /= (downsample) ? 2.0 : 1.0;
wh_i[1] /= (downsample) ? 2.0 : 1.0;
```

### `histogram_method`
Type of histogram equalization to apply to images before processing.

```cpp
// from OptionsCamera.h
ov_core::TrackBase::HistogramMethod histogram = ov_core::TrackBase::HistogramMethod::HISTOGRAM;

// from OptionsCamera.cpp
std::string histogram_method_str = "HISTOGRAM";
parser->parse_external(f, "cam", "histogram_method", histogram_method_str);
if (histogram_method_str == "NONE") {
  histogram = ov_core::TrackBase::NONE;
} else if (histogram_method_str == "HISTOGRAM") {
  histogram = ov_core::TrackBase::HISTOGRAM;
} else if (histogram_method_str == "CLAHE") {
  histogram = ov_core::TrackBase::CLAHE;
} else {
  PRINT4(RED "OptionsCamera: invalid feature histogram specified: %s. Available: NONE, HISTOGRAM, CLAHE\n" RESET, 
         histogram_method_str.c_str());
  std::exit(EXIT_FAILURE);
}
```

## Feature Management Parameters

### `max_slam`
Maximum number of SLAM features to maintain in the state vector.

```cpp
// from OptionsCamera.h
int max_slam = 25;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "max_slam", max_slam);

// from CamHelper.cpp - Used in feature selection
for (auto feat = feats_pool.begin(); 
     feat != feats_pool.end() && (int)init.size() < state->op->cam->max_slam - (int)state->cam_SLAM_features.size(); 
     feat++) {
  // Add feature to initialize list
}
```

### `max_msckf`
Maximum number of MSCKF features to use for filter updates.

```cpp
// from OptionsCamera.h
int max_msckf = 1000;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "max_msckf", max_msckf);

// from CamHelper.cpp - Used in feature selection
for (auto feat = feats_pool.begin(); 
     feat != feats_pool.end() && (int)msckf.size() < state->op->cam->max_msckf; 
     feat++) {
  // Add feature to MSCKF list
}
```

### `feat_rep`
What representation features should use (GLOBAL_3D or GLOBAL_FULL_INVERSE_DEPTH).

```cpp
// from OptionsCamera.h
ov_type::LandmarkRepresentation::Representation feat_rep;

// from OptionsCamera.cpp
std::string feat_rep_ = "GLOBAL_3D";
parser->parse_external(f, "cam", "feat_rep", feat_rep_);
feat_rep = ov_type::LandmarkRepresentation::from_string(feat_rep_);
if (feat_rep != ov_type::LandmarkRepresentation::GLOBAL_3D && 
    feat_rep != ov_type::LandmarkRepresentation::GLOBAL_FULL_INVERSE_DEPTH) {
  PRINT4(RED "unsupported feature representation: %s\n" RESET, 
         ov_type::LandmarkRepresentation::as_string(feat_rep).c_str());
  std::exit(EXIT_FAILURE);
}
```

## Error Parameters

### `sigma_px`
Standard deviation of pixel noise in measurements. Used to weight observations.

```cpp
// from OptionsCamera.h
double sigma_pix = 1;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "sigma_px", sigma_pix);

// Used in measurement noise covariance matrices during EKF updates
```

### `chi2_mult`
Chi-squared test multiplier for outlier rejection. Higher values are more permissive.

```cpp
// from OptionsCamera.h
double chi2_mult = 1;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "chi2_mult", chi2_mult);

// from UpdaterCamera.cpp - Initializing Chi objects for outlier rejection
Chi.insert({i, make_shared<UpdaterStatistics>(op->chi2_mult, "CAM", i)});

// from UpdaterStatistics.cpp - Used in chi-squared test
if (res.rows() < max_chi_size) {
  thr = chi2_mult * chi_squared_table[res.rows()];
} else {
  chi_squared chi_squared_dist(res.rows());
  thr = chi2_mult * quantile(chi_squared_dist, 0.95);
}

// Accepting or rejecting based on chi-squared test
if (chi < thr) {
  // Accept measurement
  return true;
} else {
  // Reject measurement
  return false;
}
```

## Feature Initialization Parameters

### `fi_min_dist` and `fi_max_dist`
Minimum and maximum distance allowed for triangulated features.

```cpp
// from FeatureInitializerOptions.h
double min_dist = 0.10;
double max_dist = 60;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "fi_min_dist", featinit_options->min_dist, false);
parser->parse_external(f, "cam", "fi_max_dist", featinit_options->max_dist, false);

// from FeatureInitializer.cpp - Used to reject bad triangulations
if (std::abs(condA) > _options.max_cond_number || 
    p_f(2, 0) < _options.min_dist || 
    p_f(2, 0) > _options.max_dist ||
    std::isnan(p_f.norm())) {
  return false;
}
```

### `fi_max_baseline`
Maximum baseline ratio allowed for triangulation.

```cpp
// from FeatureInitializerOptions.h
double max_baseline = 40;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "fi_max_baseline", featinit_options->max_baseline, false);

// Used to limit triangulation of features with excessive baseline
```

### `fi_max_cond_number`
Maximum condition number allowed for triangulation matrix.

```cpp
// from FeatureInitializerOptions.h
double max_cond_number = 10000;

// from OptionsCamera.cpp
parser->parse_external(f, "cam", "fi_max_cond_number", featinit_options->max_cond_number, false);

// from FeatureInitializer.cpp - Used to check quality of triangulation
Eigen::JacobiSVD<Eigen::Matrix3d> svd(A);
Eigen::MatrixXd singularValues;
singularValues.resize(svd.singularValues().rows(), 1);
singularValues = svd.singularValues();
double condA = singularValues(0, 0) / singularValues(singularValues.rows() - 1, 0);

// Reject if condition number is too high
if (std::abs(condA) > _options.max_cond_number || ...) {
  return false;
}
```

## Camera-Specific Parameters

### Sensor Configuration Parameters
Each camera sensor is configured with the following parameters:

```yaml
cam0:
  timeoffset: 0.0
  topic: "/cam0/image_raw"
  T_imu_cam: [transformation matrix]
  distortion_coeffs: [k1, k2, p1, p2]
  distortion_model: "radtan"
  intrinsics: [fx, fy, cx, cy]
  resolution: [width, height]
```

These parameters define:
- `timeoffset`: Temporal offset between camera and IMU
- `topic`: ROS topic for camera data
- `T_imu_cam`: Transformation matrix from IMU to camera
- `distortion_coeffs`: Lens distortion parameters
- `distortion_model`: Type of distortion model (radtan or equidistant)
- `intrinsics`: Camera intrinsic parameters (focal lengths and principal point)
- `resolution`: Image resolution in pixels

## Parameter Optimization for UAV Above 50m

For a UAV flying above 50m with sparse terrain features, consider these optimizations:

1. **Feature extraction parameters**:
   - Increase `n_pts` (e.g., 800) to extract more features in sparse environments
   - Decrease `fast` threshold (e.g., 20) to be more sensitive to weaker features
   - Increase `grid_x` and `grid_y` (e.g., 30x30) for better feature distribution
   - Increase `min_px_dist` (e.g., 20) to avoid clustering features

2. **Feature triangulation parameters**:
   - Increase `fi_min_dist` (e.g., 30m) to avoid triangulating close features below the UAV
   - Increase `fi_max_dist` (e.g., 300m) to allow distant terrain features
   - Increase `fi_max_baseline` and `fi_max_cond_number` to be more permissive with triangulation

3. **Noise handling**:
   - Increase `sigma_px` (e.g., 3.0) to account for increased pixel uncertainty at distance
   - Increase `chi2_mult` (e.g., 3.0) to be more permissive with outliers

4. **Feature management parameters**:
   - Increase `max_slam` and `max_msckf` to track more features through the environment
   - Use `GLOBAL_FULL_INVERSE_DEPTH` representation for better handling of distant points 