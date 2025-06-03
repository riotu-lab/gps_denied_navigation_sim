#!/usr/bin/env python3
"""
T_imu_lidar.py
-------------------------------------------------
Given the pose of a LiDAR frame described in an SDF (<pose>x y z R P Y</pose>),
this script produces the 4×4 homogeneous matrix T_imu_lidar for insertion
in the MINS configuration file.

Conventions
-----------
* SDF pose order: roll(X)‑pitch(Y)‑yaw(Z) **degrees**
* IMU frame (base_link) = FLU  (+X forward, +Y left, +Z up)
* LiDAR frame convention depends on the specific LiDAR:
  - For most LiDARs like Velodyne: +X forward, +Y left, +Z up (FLU)
  - For some LiDARs like Ouster: +X forward, +Y right, +Z up (FRU)
  This script assumes default FLU convention, but includes an option to use FRU.

Transformation Calculation
---------------------------
T_imu_lidar = T_imu_base * T_base_lidar

1. T_imu_base is calculated based on the SDF pose of the IMU.
2. T_base_lidar is calculated based on the SDF pose of the LiDAR relative to the base.

Usage
----
python3 T_imu_lidar.py 0.0 0.0 -0.12 0 90 0

where 0.0 0.0 -0.12 is the translation of the LiDAR frame relative to the IMU frame
and 0 90 0 is the rotation of the LiDAR frame relative to the IMU frame
---------------
"""
import math, argparse, sys
import numpy as np

D2R = math.pi / 180.0

# ---------- elementary rotations ----------
def Rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def Ry(a): c, s = math.cos(a), math.sin(a); return np.array([[ c,0,s],[0,1,0],[-s,0,c]])
def Rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]])

def rpy2R(roll_deg, pitch_deg, yaw_deg):
    return Rz(yaw_deg*D2R) @ Ry(pitch_deg*D2R) @ Rx(roll_deg*D2R)

def print_yaml(name, T):
    print(f"{name}:")
    for r in T:
        print(f"  - [{r[0]:.9f}, {r[1]:.9f}, {r[2]:.9f}, {r[3]:.9f}]")

# ---------- main ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="SDF pose ➜ MINS T_imu_lidar matrix",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("x", type=float, help="lidar X position relative to IMU [m]")
    ap.add_argument("y", type=float, help="lidar Y position relative to IMU [m]")
    ap.add_argument("z", type=float, help="lidar Z position relative to IMU [m]")
    ap.add_argument("roll",  type=float, help="lidar roll angle relative to IMU [deg]")
    ap.add_argument("pitch", type=float, help="lidar pitch angle relative to IMU [deg]")
    ap.add_argument("yaw",   type=float, help="lidar yaw angle relative to IMU [deg]")
    ap.add_argument("--fru", action="store_true", 
                    help="Use FRU convention (X forward, Y right, Z up) for LiDAR")
    args = ap.parse_args()

    # Calculate rotation from IMU to LiDAR
    R_imu_lidar = rpy2R(args.roll, args.pitch, args.yaw)
    
    # If using FRU convention for LiDAR, apply additional rotation (Y axis flip)
    if args.fru:
        # Y-axis flip to convert from FLU to FRU
        R_flu_fru = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 1]])
        R_imu_lidar = R_imu_lidar @ R_flu_fru
    
    # Create 4x4 transformation matrix
    T_imu_lidar = np.eye(4)
    T_imu_lidar[:3,:3] = R_imu_lidar
    T_imu_lidar[:3, 3] = [args.x, args.y, args.z]

    print("# ---- paste below into MINS configuration file ----")
    print_yaml("T_imu_lidar", T_imu_lidar)
    
    # Also output the inverse transformation if needed
    print("\n# ---- T_lidar_imu (inverse transformation) if needed ----")
    print_yaml("T_lidar_imu", np.linalg.inv(T_imu_lidar))