# TERCOM — Terrain Contour Matching

**TERCOM (Terrain Contour Matching)** is the default GPS-denied navigation algorithm used by this simulator. It estimates UAV position without GPS by correlating a live terrain elevation profile (baro + rangefinder) against a pre-loaded Digital Elevation Model (DEM), fused with an **Error-State Kalman Filter (ESKF)** running on IMU prediction.

GPS is used only **once at startup** to initialize the filter; after that, position comes from IMU + TERCOM + baro + velocity updates.

This page is a high-level entry point. Full reference documentation lives in the two companion repositories:

- [`tercom_nav`](https://github.com/mzahana/tercom_nav) — the estimator package (4 nodes)
- [`tercom_rviz_plugins`](https://github.com/mzahana/tercom_rviz_plugins) — the dockable RViz2 panels
- [`tercom_nav/docs/TERCOM_MERMAID_DIAGRAMS.md`](../../tercom_nav/docs/TERCOM_MERMAID_DIAGRAMS.md) — in-depth architecture diagrams
- [`tercom_nav/docs/MAP_OFFSET.md`](../../tercom_nav/docs/MAP_OFFSET.md) — DEM / TF alignment for new worlds

---

## Quick start on `taif_test4`

```bash
# Terminal 1
zenoh

# Terminal 2 — sim
mono_taif4

# Terminal 3 — TERCOM
tercom
```

The `tercom` alias expands to:

```bash
ros2 launch tercom_nav tercom_nav.launch.py \
    params_file:=$(ros2 pkg prefix tercom_nav)/share/tercom_nav/config/taif_test4_params.yaml \
    mavros_ns:=target/mavros
```

The pre-configured RViz layout (loaded automatically by `dem.launch.py`) docks the custom panels from `tercom_rviz_plugins`:

| Panel | Shows |
|-------|-------|
| **Filter Status** | ESKF state machine, NIS sparkline, pos σ / innovation gauges, IMU biases |
| **TERCOM Quality** | Pipeline state, per-match MAD / discrimination / roughness / noise, accepted / rejected counters |
| **Error History** | Live horizontal + vertical error vs. ground truth with RMS / max overlays |
| **Profiling** | Per-callback exec time and call rate for all three `tercom_nav` nodes |

---

## Nodes

| Node | Responsibility |
|------|----------------|
| `dem_server_node` | Loads the GeoTIFF DEM once, publishes metadata on a latched topic, exposes ROS services for elevation queries |
| `tercom_node` | Collects time-synchronised baro + rangefinder + IMU + odometry samples; runs vectorised NumPy TERCOM correlation matching against the DEM |
| `eskf_node` | 15-state ESKF (position / velocity / attitude / accel bias / gyro bias); fuses IMU prediction with TERCOM, baro, and velocity updates |
| `diagnostics_node` | Ground-truth error metrics, RViz visualisations (paths, fixes, covariance ellipse, DEM cloud), CSV logging, and the aggregated `/profiling` topic |

---

## System architecture

```mermaid
graph TD
    subgraph SENSORS [Sensor Inputs]
        S1[Barometer] -->|"/target/mavros/altitude"| N3[tercom_node]
        S2[Rangefinder] -->|"/target/mavros/distance_sensor/rangefinder_pub"| N3
        S3[IMU] -->|"/target/mavros/imu/data"| N1[eskf_node]
        S3 --> N3
        S4[GPS - init only] -->|"/target/mavros/global_position/global"| N1
        S5[Local Velocity] -->|"/target/mavros/local_position/velocity_local"| N1
        S6[Local Odom] -->|"/target/mavros/local_position/odom"| N3
    end

    subgraph DEM [Terrain database]
        DT[(GeoTIFF DEM)] --> DS[dem_server_node]
        DT --> N3
    end

    subgraph ESTIMATOR [Estimation]
        N1 -- "/tercom/eskf_node/pose (covariance feedback)" --> N3
        N3 -. "/tercom/tercom_node/position_fix + match quality" .-> N1
    end

    subgraph DIAG [Diagnostics]
        N1 --> D[diagnostics_node]
        N3 --> D
        D --> RVIZ[(RViz2 + tercom_rviz_plugins)]
        D -->|CSV| LOG[/tmp/tercom_logs/]
    end
```

## ESKF state machine

```mermaid
stateDiagram-v2
    [*] --> WAITING_GPS
    WAITING_GPS --> INITIALIZING : GPS fix acquired
    INITIALIZING --> RUNNING : N GPS samples averaged
    INITIALIZING --> WAITING_GPS : timeout
    RUNNING --> DIVERGED : NIS window > threshold
    RUNNING --> DIVERGED : pos σ > max
    DIVERGED --> RESETTING : divergence_action
    RESETTING --> RUNNING : soft reset (inflate P, zero biases)
    RESETTING --> WAITING_GPS : hard reset (reset_with_gps)
```

## TERCOM match lifecycle

```mermaid
sequenceDiagram
    participant S as Sensors (baro + laser + IMU)
    participant C as ProfileCollector
    participant M as Vectorised Matcher
    participant E as eskf_node

    S->>C: h_baro, h_agl, pos_enu, t
    Note over C: wait until Δdistance ≥ min_spacing
    C-->>C: h_terrain = h_baro − h_agl·cos(roll)·cos(pitch)
    C-->>C: store (h_terrain, dx, dy)
    alt profile full (N samples)
        C->>M: array of samples, predicted UTM
        M-->>M: build M × N search grid
        M-->>M: mask NoData, compute MAD, disc., roughness
        M->>C: keep last N/2 samples for continuity
        M->>E: /tercom_node/position_fix (if accepted)
        M->>E: /tercom_node/match_quality
    else rejected
        M->>E: (nothing — reason published on /rejection_reason)
    end
```

## Filter lifecycle (predict + update)

```mermaid
graph TD
    A[Start loop] --> B{Data received?}
    B -->|IMU| C[Predict]
    C --> C1[Integrate nominal state p,v,q,b]
    C1 --> C2["P = F·P·Fᵀ + Q"]
    C2 --> B
    B -->|TERCOM / baro / velocity| D[Update]
    D --> D1["y = z − H·x"]
    D1 --> D2[Gate by NIS + health]
    D2 --> D3["K = P·Hᵀ · (H·P·Hᵀ + R)⁻¹"]
    D3 --> D4["δx = K·y"]
    D4 --> D5[Inject δx into nominal state]
    D5 --> D6["P = (I−KH)·P·(I−KH)ᵀ + K·R·Kᵀ"]
    D6 --> D7[Reset error state δx = 0]
    D7 --> B
```

## Coordinate chain

```mermaid
graph LR
    WGS((WGS84<br>lat/lon/alt)) -- latlon_to_utm --> UTM((UTM<br>E/N))
    UTM -- utm_to_local_enu --> ENU((Local ENU<br>X/Y/Z))
    UTM -- utm_to_pixel --> PIX((DEM Pixel<br>col/row))
    ENU -- local_enu_to_utm --> UTM
```

---

## Topics (the ones you care about)

| Topic | Type | Description |
|-------|------|-------------|
| `/tercom/eskf_node/odom` | `nav_msgs/Odometry` | **Primary output** — position/orientation in `map` frame |
| `/tercom/eskf_node/global` | `sensor_msgs/NavSatFix` | Estimated lat/lon/alt (1 Hz) |
| `/tercom/eskf_node/health` | `std_msgs/Float32MultiArray` | `[avg_NIS, max_pos_std, innov_norm, is_healthy]` |
| `/tercom/eskf_node/state` | `std_msgs/String` | Filter state machine |
| `/tercom/tercom_node/position_fix` | `geometry_msgs/PointStamped` | Accepted UTM fix |
| `/tercom/tercom_node/match_quality` | `std_msgs/Float32MultiArray` | `[MAD, disc., roughness, noise]` |
| `/tercom/tercom_node/status` | `std_msgs/String` | `WAITING_SENSORS` / `COLLECTING` / `MATCHING` |
| `/tercom/diagnostics_node/estimated_path` | `nav_msgs/Path` | ESKF trajectory |
| `/tercom/diagnostics_node/ground_truth_path` | `nav_msgs/Path` | MAVROS trajectory (frame-aligned) |
| `/tercom/diagnostics_node/error_arrow` | `visualization_msgs/MarkerArray` | Live error arrow GT → EST |
| `/tercom/diagnostics_node/dem_surface` | `sensor_msgs/PointCloud2` | DEM cloud (satellite-coloured if configured) |
| `/tercom/diagnostics_node/profiling` | `std_msgs/Float32MultiArray` | 16-float aggregated timing for all nodes |

A full topic + service + parameter reference is in the `tercom_nav` [README](https://github.com/mzahana/tercom_nav#readme).

---

## Using a different world

1. Produce a georeferenced GeoTIFF DEM covering the flight area ([`generate_dem.md`](../generate_dem.md)).
2. Copy it next to the world model (e.g. `models/<world>/textures/<world>_tercom_dem.tif`).
3. Duplicate `tercom_nav/config/taif_test4_params.yaml` as `<world>_params.yaml`; update:
   - `dem_file:` absolute path to the new GeoTIFF
   - `world_origin_lat/lon/alt:` matches the world SDF's `<spherical_coordinates>`
   - `dem_pos_offset:` computed per [`MAP_OFFSET.md`](../../tercom_nav/docs/MAP_OFFSET.md)
   - `dem_satellite_image:` + `dem_satellite_bounds:` if you want satellite-coloured DEM cloud
4. Launch:
   ```bash
   ros2 launch tercom_nav tercom_nav.launch.py params_file:=/abs/path/<world>_params.yaml
   ```

---

## See also

- [`ALGORITHMS.md`](ALGORITHMS.md) — other estimators you can benchmark against TERCOM
- [`ALGORITHM_ANALYSIS.md`](ALGORITHM_ANALYSIS.md) — CSV / figure pipeline for per-run analysis
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — where TERCOM sits in the full simulator graph
