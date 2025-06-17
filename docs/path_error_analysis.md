# Path Error Analysis Tool

A ROS2 utility for real-time analysis and comparison of estimated trajectories against ground truth paths. This tool calculates various error metrics between SLAM/VIO estimated paths and ground truth trajectories, providing both real-time monitoring and comprehensive statistical analysis.

## Overview

The path error analysis tool subscribes to:
- **Ground truth path**: `/target/gt_path` (reference trajectory)
- **Estimated path**: `/mins/imu/path` (or other SLAM/VIO algorithm output)

It calculates multiple error metrics including:
- **Position errors**: Euclidean distance between estimated and ground truth positions
- **Orientation errors**: Angular differences in roll, pitch, yaw
- **Velocity errors**: Speed differences between estimated and ground truth
- **Statistical summaries**: Mean, median, standard deviation, min/max errors
- **Real-time monitoring**: Live error visualization and reporting

## Features

- ✅ **Real-time error calculation** with configurable update rates
- ✅ **Multiple error metrics** (position, orientation, velocity, statistical)
- ✅ **CSV data export** for detailed analysis
- ✅ **Summary reports** with statistical insights
- ✅ **Live monitoring** capabilities during simulation
- ✅ **Python script interface** for easy control
- ✅ **Automatic and manual recording modes**
- ✅ **ROS2 native** with proper QoS handling

## Requirements

- ROS2 (Humble or later)
- Python 3.8+
- Required packages: `rclpy`, `geometry_msgs`, `nav_msgs`
- File system access to `/home/user/shared_volume/error_analysis/` (or configured output directory)

## Installation

The tool is included in the `gps_denied_navigation_sim` package. Build the workspace:

```bash
cd ros2_ws
colcon build --packages-select gps_denied_navigation_sim
source install/setup.bash
```

## Quick Usage Examples

```bash
# Show help and available commands
python3 run_path_error_analysis.py --help

# Start recording manually (you control when to stop)
python3 run_path_error_analysis.py start

# Automatically record for 60 seconds then stop
python3 run_path_error_analysis.py auto --duration 60

# Stop recording and generate summary (if started manually)
python3 run_path_error_analysis.py stop

# Reset all accumulated data
python3 run_path_error_analysis.py reset
```

## Step-by-Step Workflow

### 1. Build the Package
First, build the package (from ros2_ws directory):
```bash
colcon build --packages-select gps_denied_navigation_sim
source install/setup.bash
```

### 2. Start the Path Error Calculator Node
```bash
ros2 run gps_denied_navigation_sim path_error_calculator

# Or using the launch file:
ros2 launch gps_denied_navigation_sim path_error_analysis.launch.py
```

### 3. Start Your Simulation
In another terminal, start your simulation (make sure these topics are publishing):
- `/target/gt_path` (ground truth)
- `/mins/imu/path` (MINS estimated path)

Example simulation launch:
```bash
# Start your drone simulation with SLAM/VIO
ros2 launch gps_denied_navigation_sim dem_stereo.launch.py

# Or for different algorithms
ros2 launch gps_denied_navigation_sim dem_twin_stereo.launch.py
```

### 4. Start Recording Errors
```bash
# For automatic 30-second recording:
python3 run_path_error_analysis.py auto --duration 30

# OR for manual control:
python3 run_path_error_analysis.py start
# ... run your test ...
python3 run_path_error_analysis.py stop
```

## Real-time Monitoring

While recording, you can monitor live error metrics:

```bash
# Position error (meters)
ros2 topic echo /path_error/position_error

# Orientation error (radians) 
ros2 topic echo /path_error/orientation_error

# Velocity error (m/s)
ros2 topic echo /path_error/velocity_error

# Running average error
ros2 topic echo /path_error/cumulative_error
```

## Python Script Commands

The `run_path_error_analysis.py` script provides these commands:

| Command | Description |
|---------|-------------|
| `--help` | Show help and available commands |
| `start` | Start recording manually (you control when to stop) |
| `stop` | Stop recording and generate summary |
| `auto --duration <seconds>` | Automatically record for specified duration then stop |
| `reset` | Reset all accumulated data |

### Command Examples
```bash
# Get help
python3 run_path_error_analysis.py --help

# Manual recording workflow
python3 run_path_error_analysis.py start
# ... perform your test scenario ...
python3 run_path_error_analysis.py stop

# Automatic recording for 2 minutes
python3 run_path_error_analysis.py auto --duration 120

# Clear all data and start fresh
python3 run_path_error_analysis.py reset
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gt_topic` | `/target/gt_path` | Ground truth path topic |
| `estimated_topic` | `/mins/imu/path` | Estimated path topic |
| `output_dir` | `/home/user/shared_volume/error_analysis/` | Output directory for files |
| `update_rate` | `10.0` | Error calculation frequency (Hz) |
| `position_threshold` | `0.1` | Position error threshold for warnings (m) |
| `orientation_threshold` | `5.0` | Orientation error threshold for warnings (degrees) |
| `buffer_size` | `1000` | Maximum number of error samples to store |

### Example Launch with Parameters
```bash
ros2 launch gps_denied_navigation_sim path_error_analysis.launch.py \
    gt_topic:="/target/gt_path" \
    estimated_topic:="/fast_lio/path" \
    update_rate:=20.0 \
    position_threshold:=0.05
```

## Output Files

The analysis creates two files in `/home/user/shared_volume/error_analysis/`:

### 1. Detailed Error Data: `path_error_analysis.csv`
Contains timestamped error data with columns:
```csv
timestamp,pos_error_x,pos_error_y,pos_error_z,pos_error_magnitude,
orient_error_roll,orient_error_pitch,orient_error_yaw,orient_error_magnitude,
velocity_error_magnitude
```

Example data:
```csv
1234567890.123,0.05,-0.02,0.01,0.054,1.2,-0.8,0.3,1.5,0.12
1234567890.223,0.06,-0.01,0.02,0.063,1.1,-0.9,0.2,1.4,0.15
```

### 2. Statistical Summary: `path_error_analysis_summary.txt`
Contains comprehensive statistical analysis:
```
Path Error Analysis Summary
===========================
Analysis Duration: 120.5 seconds
Total Samples: 1205

Position Error Statistics (meters):
  Mean: 0.045
  Median: 0.039
  Std Dev: 0.023
  Min: 0.001
  Max: 0.156
  95th Percentile: 0.089

Orientation Error Statistics (degrees):
  Mean: 1.23
  Median: 1.15
  Std Dev: 0.67
  Min: 0.05
  Max: 4.52
  95th Percentile: 2.34

Velocity Error Statistics (m/s):
  Mean: 0.125
  Median: 0.118
  Std Dev: 0.045
  Min: 0.002
  Max: 0.324
  95th Percentile: 0.198

Performance Metrics:
  Samples below position threshold (0.1m): 95.2%
  Samples below orientation threshold (5.0°): 98.8%
  Error trend: Stable
```

## Algorithm Comparison Workflow

To compare multiple SLAM/VIO algorithms:

```bash
# 1. Start simulation with first algorithm (e.g., MINS)
ros2 launch gps_denied_navigation_sim dem_stereo.launch.py use_mins:=true

# 2. Start error analysis node
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p estimated_topic:="/mins/imu/path" \
    -p output_dir:="/home/user/shared_volume/error_analysis/mins/"

# 3. Record MINS trajectory
python3 run_path_error_analysis.py auto --duration 60

# 4. Repeat for other algorithms (FastLIO, ORB-SLAM, etc.)
ros2 launch gps_denied_navigation_sim dem_stereo.launch.py use_fast_lio:=true
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p estimated_topic:="/fast_lio/path" \
    -p output_dir:="/home/user/shared_volume/error_analysis/fast_lio/"
python3 run_path_error_analysis.py auto --duration 60
```

## Troubleshooting

### Common Issues

**1. No data being recorded**
- Check that both ground truth and estimated path topics are publishing:
```bash
ros2 topic list | grep path
ros2 topic hz /target/gt_path
ros2 topic hz /mins/imu/path
```

**2. Output directory not found**
- Ensure the output directory exists and has write permissions:
```bash
mkdir -p /home/user/shared_volume/error_analysis/
chmod 755 /home/user/shared_volume/error_analysis/
```

**3. Python script not found**
- Make sure you're in the correct directory and the script exists:
```bash
ls run_path_error_analysis.py
# If not found, check the package installation
```

**4. High error values**
- Check coordinate frame alignment between ground truth and estimated paths
- Verify time synchronization between topics
- Ensure proper sensor calibration

**5. Tool not starting**
- Verify ROS2 environment is sourced:
```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

### Debug Mode
Enable verbose logging for troubleshooting:
```bash
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p verbose:=true \
    --log-level debug
```

## Integration with Other Tools

### RQT Plot - Real-time Charts
Create real-time plots with time on X-axis and position/error on Y-axis:

```bash
# Launch RQT Plot for position comparison
rqt_plot /target/gt_path/poses[0]/pose/position/x /mins/imu/path/poses[0]/pose/position/x /path_error/position_error/x

# Or launch with a configuration file
rqt_plot --perspective-file path_error_plots.perspective
```

**Multi-axis plotting examples:**
```bash
# X, Y, Z positions (GT vs Estimated)
rqt_plot /target/gt_path/poses[0]/pose/position/x:y:z /mins/imu/path/poses[0]/pose/position/x:y:z

# Position errors over time
rqt_plot /path_error/position_error/x:y:z /path_error/position_error/magnitude

# Orientation errors (roll, pitch, yaw)
rqt_plot /path_error/orientation_error/x:y:z

# Combined position and velocity errors
rqt_plot /path_error/position_error/magnitude /path_error/velocity_error/magnitude
```

**Save/Load Plot Configurations:**
- Save your plot setup: `Plugins → Configuration → Save Configuration`
- Load saved plots: `rqt_plot --perspective-file your_config.perspective`

### RViz Visualization
Add path error visualization to RViz with custom markers and paths:

```bash
# Launch RViz with path error display
ros2 launch gps_denied_navigation_sim rviz_path_analysis.launch.py
```

**Manual RViz Setup:**
1. **Add Path displays:**
   - Topic: `/target/gt_path` (Color: Green)
   - Topic: `/mins/imu/path` (Color: Blue)
   - Topic: `/path_error/error_path` (Color: Red)

2. **Add Marker displays:**
   - Topic: `/path_error/error_markers` (Error magnitude visualization)
   - Topic: `/path_error/position_markers` (3D position comparison)

3. **Add Text displays:**
   - Topic: `/path_error/status_text` (Current error statistics)

### RViz Error Markers
The tool can publish visual error markers to RViz:

```bash
# Enable RViz marker publishing
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p publish_markers:=true \
    -p marker_scale:=0.1 \
    -p error_color_threshold:=0.05
```

**Marker types available:**
- **Sphere markers**: Error magnitude at each position
- **Arrow markers**: Direction and magnitude of position error
- **Line strips**: Connecting GT and estimated positions
- **Text markers**: Numerical error values

### PlotJuggler Analysis
Import CSV files into PlotJuggler for advanced visualization:

```bash
ros2 run plotjuggler plotjuggler
# File → Load Data → select path_error_analysis.csv
```

**PlotJuggler Features:**
- **Time-synchronized plots** of multiple variables
- **3D trajectory visualization** 
- **Custom mathematical operations** on data
- **Export capabilities** for publication-quality plots
- **Real-time streaming** from ROS topics

**PlotJuggler Live Streaming:**
```bash
# Stream live data to PlotJuggler
ros2 run plotjuggler plotjuggler
# Streaming → Start ROS2 Topic Subscriber
# Add topics: /path_error/position_error, /target/gt_path, /mins/imu/path
```

### Custom Visualization Dashboard
Create a comprehensive monitoring dashboard combining multiple tools:

```bash
# Terminal 1: Start the simulation
ros2 launch gps_denied_navigation_sim dem_stereo.launch.py

# Terminal 2: Start path error calculator with visualization
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p publish_markers:=true \
    -p publish_error_topics:=true \
    -p visualization_rate:=10.0

# Terminal 3: Launch RViz with custom config
rviz2 -d path_error_analysis.rviz

# Terminal 4: Launch RQT Plot for real-time charts
rqt_plot /path_error/position_error/magnitude /path_error/velocity_error/magnitude

# Terminal 5: Monitor with Python script
python3 run_path_error_analysis.py start
```

### Enhanced Topics for Visualization

When `publish_error_topics:=true` is enabled, additional topics are published:

| Topic | Type | Description |
|-------|------|-------------|
| `/path_error/position_error` | `geometry_msgs/Vector3` | X, Y, Z position errors |
| `/path_error/position_error/magnitude` | `std_msgs/Float64` | Euclidean position error |
| `/path_error/orientation_error` | `geometry_msgs/Vector3` | Roll, pitch, yaw errors (radians) |
| `/path_error/velocity_error` | `geometry_msgs/Vector3` | Velocity error components |
| `/path_error/cumulative_error` | `std_msgs/Float64` | Running average error |
| `/path_error/error_markers` | `visualization_msgs/MarkerArray` | RViz error visualization |
| `/path_error/status_text` | `visualization_msgs/Marker` | Text display of statistics |

### RQT Dashboard Setup
Create a comprehensive RQT dashboard with multiple plugins:

```bash
# Launch RQT with multiple plugins
rqt --perspective-file path_analysis_dashboard.perspective
```

**Dashboard Components:**
1. **RQT Plot**: Time-series error plots
2. **RQT Topic**: Live topic monitoring
3. **RQT Service Caller**: Control recording start/stop
4. **RQT Console**: Error and warning logs
5. **RQT Graph**: Node/topic connectivity

**Creating the Dashboard:**
1. Launch `rqt`
2. Add plugins: `Plugins → Visualization → Plot`, `Plugins → Topics → Topic Monitor`
3. Configure plot topics and ranges
4. Save perspective: `Perspectives → Export`

### Batch Processing
For automated testing across multiple scenarios:
```bash
# Use the batch analysis script
ros2 run gps_denied_navigation_sim batch_path_analysis.py \
    --scenarios scenario1.yaml scenario2.yaml \
    --algorithms mins fast_lio orb_slam \
    --output-dir /home/user/batch_results/
```

## Advanced Usage

### Custom Error Metrics
Extend the tool with custom error calculations by modifying the node parameters:
```bash
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p custom_metrics:=true \
    -p include_velocity_error:=true \
    -p include_acceleration_error:=true
```

### Multi-Agent Analysis
For comparing paths from multiple drones:
```bash
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args \
    -p gt_topic:="/drone1/gt_path" \
    -p estimated_topic:="/drone1/mins/path" \
    -p namespace:="drone1"
```

## Related Tools

- **Adaptive Image Stitcher**: For multi-camera visualization during path analysis
- **Pose Utilities**: For coordinate frame transformations
- **IMU Noise Configuration**: For proper sensor calibration

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review ROS2 logs: `ros2 run rqt_console rqt_console`
3. Verify topic compatibility with: `ros2 interface show nav_msgs/msg/Path`

---

*This tool is part of the GPS-Denied Navigation Simulation package for evaluating SLAM and VIO algorithms in challenging environments.*

## Quick Visualization Reference

### Most Common Commands

**Real-time Position Error Chart (X, Y, Z):**
```bash
rqt_plot /path_error/position_error/x:y:z /path_error/position_error/magnitude
```

**GT vs Estimated Position Comparison:**
```bash
rqt_plot /target/gt_path/poses[0]/pose/position/x /mins/imu/path/poses[0]/pose/position/x
```

**Complete Error Dashboard:**
```bash
# Terminal 1: Start error calculator with visualization
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args -p publish_error_topics:=true

# Terminal 2: Launch multi-plot dashboard
rqt_plot /path_error/position_error/magnitude /path_error/orientation_error/magnitude /path_error/velocity_error/magnitude

# Terminal 3: Start recording
python3 run_path_error_analysis.py auto --duration 60
```

**RViz with Error Markers:**
```bash
# Enable markers and launch RViz
ros2 run gps_denied_navigation_sim path_error_calculator --ros-args -p publish_markers:=true
rviz2 -d path_error_analysis.rviz
```

### Topic Quick List
```bash
# Check available error topics
ros2 topic list | grep path_error

# Monitor real-time error magnitude
ros2 topic echo /path_error/position_error/magnitude

# View current error statistics
ros2 topic echo /path_error/cumulative_error
```

