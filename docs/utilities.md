
## README – `pose2openvins_matrix.py`

```markdown
# pose2openvins_matrix.py
Convert an SDF `<pose>` (camera relative to `base_link`) into the **T_imu_cam** 4 × 4
homogeneous transform that OpenVINS expects (*camera‐optical → IMU*).

## Why
OpenVINS uses ROS optical‑frame conventions (RDF: +X right, +Y down, +Z forward).
SDF poses follow FLU (+X forward, +Y left, +Z up).  
This script applies the fixed optical rotation plus your pitch/roll/yaw to deliver a
matrix you can paste directly into `kalibr_imucam_chain.yaml`.

## Requirements
* Python ≥ 3.8  
* `numpy` (only dependency)

```bash
pip install numpy
```

## Usage
```bash
python pose2openvins_matrix.py x y z roll pitch yaw
```
*All angles in **degrees**; axes in **meters**.*

### Example  
```bash
python pose2openvins_matrix.py 0.20 0 0.10 0 10 0
```

**Output**
```yaml
# ---- paste below into kalibr_imucam_chain.yaml ----
T_imu_cam:
  - [ 0.0000, -0.1736, 0.9848, 0.200]
  - [-1.0000,  0.0000, 0.0000, 0.000]
  - [ 0.0000, -0.9848,-0.1736, 0.100]
  - [ 0.0000,  0.0000, 0.0000, 1.000]
```

## Math reference
``T_imu_cam = R_sdf · R_optical , t``  
where  
* `R_sdf` = Rz(yaw) Ry(pitch) Rx(roll)  
* `R_optical` = Rz(180°) Rx(−90°)

(see script source for details).


---

## README – `gazebo_imu2openvins_noise.py`


# gazebo_imu2openvins_noise.py
Translate per‑sample IMU noise values from a Gazebo `<sensor>` plugin into the
spectral‑density parameters required by OpenVINS (`kalibr_imu_chain.yaml`).

## Why
* Gazebo: `<stddev>` and `<dynamic_bias_stddev>` are **sample** standard‑deviations.
* OpenVINS: needs **per‑√Hz densities** (`noise_density`, `random_walk`).

This utility performs the conversion:


white‑noise density = stddev / √rate
bias random‑walk    = dynamic_bias_stddev × √rate


## Requirements
Pure Python 3 (no external packages).

## Usage
```bash
python gazebo_imu2openvins_noise.py \
       --rate <Hz> \
       --gyro-stddev <rad_s_stddev> \
       --gyro-bias-stddev <rad_s_bias_stddev> \
       --accel-stddev <m_s2_stddev> \
       --accel-bias-stddev <m_s2_bias_stddev>
```

### Example (matches PX4 X500 SDF)
```bash
python gazebo_imu2openvins_noise.py --rate 250 \
       --gyro-stddev 1.8665e-4 --gyro-bias-stddev 3.8785e-5 \
       --accel-stddev 0.00186  --accel-bias-stddev 0.006
```

**Output**
```yaml
# ---- paste below into kalibr_imu_chain.yaml ----
gyroscope_noise_density:     1.18048e-05     # rad/s /√Hz
accelerometer_noise_density: 0.000117637     # m/s^2 /√Hz
gyroscope_random_walk:       0.000613245     # rad/s^2 /√Hz
accelerometer_random_walk:   0.095057        # m/s^3 /√Hz
```

## Practical workflow

```bash
# 1. Generate the camera extrinsic matrix
python pose2openvins_matrix.py 0.20 0 0.10 0 10 0 >> kalibr_imucam_chain.yaml

# 2. Generate matching IMU noise densities
python gazebo_imu2openvins_noise.py --rate 250 \
       --gyro-stddev 1.8665e-4 \
       --gyro-bias-stddev 3.8785e-5 \
       --accel-stddev 0.00186 \
       --accel-bias-stddev 0.006 >> kalibr_imu_chain.yaml
```

Commit the updated YAML files, rebuild, and relaunch OpenVINS in your simulation.


---
