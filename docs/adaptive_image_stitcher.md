# Adaptive Image Stitcher

## Overview

The Adaptive Image Stitcher is a robust ROS2 node that automatically detects and stitches camera feeds from various drone configurations. Unlike the original hardcoded 4-camera stitcher, this adaptive version can handle:

- **Single camera** (mono setup)
- **Stereo camera** (left/right pair)
- **Dual stereo cameras** (front stereo + rear stereo = 4 cameras)
- **Multiple cameras** (any number, arranged in optimal grid)

The node **always publishes to the same output topic** regardless of the input camera configuration, making it perfect for switching between different drone models without changing your visualization setup.

## Key Features

### 🔄 **Automatic Camera Discovery**
- Scans ROS topics to find available camera feeds
- Intelligently categorizes cameras based on topic names
- Supports namespace filtering for multi-drone scenarios

### 🧩 **Adaptive Layouts**
- **Single**: Full-screen view for mono cameras
- **Stereo Horizontal**: Side-by-side for left/right cameras  
- **Stereo Vertical**: Top/bottom for front/rear cameras
- **Quad Layout**: 2x2 grid for dual stereo setups
- **Multi-Grid**: Optimal grid arrangement for 5+ cameras

### 🏷️ **Smart Camera Recognition**
Automatically recognizes camera types using pattern matching:

| Category | Patterns Detected |
|----------|------------------|
| `front_left` | `front.*left`, `stereo.*left`, `left_cam` |
| `front_right` | `front.*right`, `stereo.*right`, `right_cam` |
| `rear_left` | `rear.*left`, `back.*left` |
| `rear_right` | `rear.*right`, `back.*right` |
| `front` | `front_cam`, `forward`, `mono.*front` |
| `rear` | `rear_cam`, `back`, `backward` |

### 📊 **Robust Operation**
- Graceful handling of missing cameras (shows placeholders)
- Automatic recovery when cameras come online
- Configurable discovery timeout and refresh rates
- Detailed logging and status reporting

## Usage Examples

### Basic Usage (Auto-detect all cameras)
```bash
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py
```

### Drone-specific Usage (Filter by namespace)
```bash
# For /target/ namespace drone
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    namespace_filter:="/target/"

# For /uav1/ namespace drone  
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    namespace_filter:="/uav1/"
```

### Custom Output Configuration
```bash
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    output_topic:="/my_drone/camera/stitched" \
    output_width:=1200 \
    output_height:=800 \
    stitch_rate:=15.0
```

### High-Performance Setup
```bash
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    discovery_timeout:=10.0 \
    stitch_rate:=30.0 \
    verbose:=false
```

## Supported Drone Configurations

### 1. Single Camera Drones
**Examples**: Basic quadcopters, simple inspection drones
```
Topics detected: /camera/image_raw
Layout: Full-screen single view
```

### 2. Stereo Camera Drones  
**Examples**: Depth-sensing drones, SLAM-capable vehicles
```
Topics detected: 
  - /stereo/left_cam/image_raw
  - /stereo/right_cam/image_raw
Layout: Side-by-side stereo view
```

### 3. Dual Stereo Drones (Current simulation default)
**Examples**: Advanced surveying drones, research platforms
```
Topics detected:
  - /target/front_stereo/left_cam/image_raw
  - /target/front_stereo/right_cam/image_raw  
  - /target/rear_stereo/left_cam/image_raw
  - /target/rear_stereo/right_cam/image_raw
Layout: 2x2 quad grid with labels
```

### 4. Multi-Camera Inspection Drones
**Examples**: 360° inspection platforms, security drones
```
Topics detected: 5+ camera feeds
Layout: Optimal NxM grid arrangement
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_topic` | `/camera/stitched_image` | Output topic for stitched image |
| `output_width` | `800` | Output image width (pixels) |
| `output_height` | `600` | Output image height (pixels) |
| `discovery_timeout` | `5.0` | Time to wait for camera discovery (seconds) |
| `verbose` | `true` | Enable detailed logging |
| `stitch_rate` | `10.0` | Stitching rate (Hz) |
| `namespace_filter` | `""` | Filter cameras by namespace (e.g., `/target/`) |

## RViz Integration

The adaptive stitcher always publishes to a consistent topic, making RViz configuration simple:

1. **Add Image Display**
2. **Set Topic**: `/camera/stitched_image` (or your custom topic)
3. **The view automatically adapts** to your drone's camera configuration

```xml
<!-- RViz config snippet -->
<display>
  <property name="Image Topic" value="/camera/stitched_image"/>
  <property name="Transport Hint" value="raw"/>
</display>
```

## Technical Details

### Camera Detection Algorithm
1. **Topic Discovery**: Scans for `sensor_msgs/msg/Image` topics containing `image_raw`
2. **Pattern Matching**: Uses regex patterns to categorize camera positions
3. **Layout Decision**: Selects optimal layout based on detected configuration
4. **Subscriber Creation**: Creates dynamic subscribers for discovered cameras

### Layout Algorithms

#### Grid Calculation for Multiple Cameras
```python
# Optimal grid dimensions
if num_cameras <= 4:
    rows, cols = 2, 2
elif num_cameras <= 6:
    rows, cols = 2, 3  
elif num_cameras <= 9:
    rows, cols = 3, 3
else:
    cols = ceil(sqrt(num_cameras))
    rows = ceil(num_cameras / cols)
```

#### Image Processing Pipeline
1. **Receive**: Individual camera images via callbacks
2. **Resize**: Scale images to fit layout cells
3. **Stitch**: Combine into unified output image
4. **Label**: Add camera identification overlays
5. **Publish**: Send stitched result at configured rate

## Troubleshooting

### No Cameras Detected
```bash
# Check available image topics
ros2 topic list | grep image_raw

# Verify namespace filtering
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    namespace_filter:="" discovery_timeout:=10.0 verbose:=true
```

### Partial Camera Coverage
- Some cameras may start later than others
- The stitcher shows placeholders until cameras come online
- Check individual camera topics: `ros2 topic echo /camera/topic/image_raw`

### Performance Issues
```bash
# Reduce stitching rate for better performance
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    stitch_rate:=5.0 output_width:=640 output_height:=480
```

### Layout Not Optimal
- The node uses pattern matching to detect camera positions
- For custom camera naming, the fallback is chronological grid arrangement
- Consider renaming topics to match expected patterns (e.g., `front_left_cam`)

## Migration from Original Stitcher

### Quick Migration
Replace your existing launch:
```bash
# Old (hardcoded 4-camera)
ros2 run gps_denied_navigation_sim image_stitcher

# New (adaptive)  
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py
```

### Parameter Mapping
| Old Parameter | New Parameter | Notes |
|---------------|---------------|-------|
| `front_left_topic` | Auto-detected | Based on topic patterns |
| `front_right_topic` | Auto-detected | Based on topic patterns |
| `rear_left_topic` | Auto-detected | Based on topic patterns |
| `rear_right_topic` | Auto-detected | Based on topic patterns |
| `output_width` | `output_width` | Same |
| `output_height` | `output_height` | Same |
| `verbose` | `verbose` | Same |

## Examples by Drone Model

### PX4 x500_stereo_cam_3d_lidar
```bash
# Single camera setup
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    namespace_filter:="/target/"
# Expected: Single full-screen camera view
```

### PX4 x500_twin_stereo_twin_velodyne  
```bash
# Dual stereo setup (4 cameras)
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    namespace_filter:="/target/"
# Expected: 2x2 quad layout with front/rear stereo pairs
```

### Custom Multi-Camera Setup
```bash
# 6+ camera inspection drone
ros2 launch gps_denied_navigation_sim adaptive_image_stitcher.launch.py \
    namespace_filter:="/inspection_drone/" \
    output_width:=1600 \
    output_height:=1200
# Expected: Optimal grid layout (e.g., 3x2 or 2x3)
```

The Adaptive Image Stitcher makes your visualization robust and drone-agnostic - set it up once and it works with any camera configuration! 