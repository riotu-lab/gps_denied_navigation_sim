#!/usr/bin/env python3
"""
gazebo_imu2openvins_noise.py
-------------------------------------------------
Turn per‑sample IMU noise figures from Gazebo into spectral densities
that go into kalibr_imu_chain.yaml for OpenVINS.

Input (CLI flags) correspond to the SDF tags:
  --gyro-stddev <σ_g>               (rad/s)
  --gyro-bias-stddev <σ_gb>         (rad/s)
  --accel-stddev <σ_a>              (m/s^2)
  --accel-bias-stddev <σ_ab>        (m/s^2)
  --rate <Hz>

Formulae
--------
white‑noise density     σ_density = σ_stddev / sqrt(rate)
bias random‑walk        σ_rw      = σ_bias_stddev * sqrt(rate)

Usage
--------
python gazebo_imu2openvins_noise.py --rate 250 \
       --gyro-stddev 0.00018665     --gyro-bias-stddev 3.8785e-05 \
       --accel-stddev 0.00186       --accel-bias-stddev 0.006

"""
import argparse, math, textwrap

def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--rate", type=float, required=True, help="IMU update rate [Hz]")
    ap.add_argument("--gyro-stddev",        type=float, required=True,
                    help="angular_velocity stddev [rad/s]")
    ap.add_argument("--gyro-bias-stddev",   type=float, required=True,
                    help="dynamic_bias_stddev for gyro [rad/s]")
    ap.add_argument("--accel-stddev",       type=float, required=True,
                    help="linear_acceleration stddev [m/s^2]")
    ap.add_argument("--accel-bias-stddev",  type=float, required=True,
                    help="dynamic_bias_stddev for accel [m/s^2]")
    args = ap.parse_args()
    f = args.rate
    sqrtf = math.sqrt(f)

    gyro_noise   = args.gyro_stddev  / sqrtf
    accel_noise  = args.accel_stddev / sqrtf
    gyro_rw      = args.gyro_bias_stddev  * sqrtf
    accel_rw     = args.accel_bias_stddev * sqrtf

    yaml = textwrap.dedent(f"""
    # ---- paste below into kalibr_imu_chain.yaml ----
    gyroscope_noise_density:     {gyro_noise:.6g}     # rad/s /√Hz
    accelerometer_noise_density: {accel_noise:.6g}    # m/s^2 /√Hz
    gyroscope_random_walk:       {gyro_rw:.6g}        # rad/s^2 /√Hz
    accelerometer_random_walk:   {accel_rw:.6g}       # m/s^3 /√Hz
    """).strip()
    print(yaml)

if __name__ == "__main__":
    main()
