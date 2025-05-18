#!/usr/bin/env python3
"""
pose2openvins_matrix_stereo.py
-------------------------------------------------
Given the pose of a stereo camera frame described in an SDF (<pose>x y z R P Y</pose>)
and the separation between cameras, this script produces the 4×4 homogeneous matrices 
T_imu_cam for the left and right cameras, formatted for insertion in kalibr_imucam_chain.yaml 
for OpenVINS.

Conventions
-----------
* SDF pose order: roll(X)‑pitch(Y)‑yaw(Z) **degrees**
* IMU frame (base_link) = FLU  (+X forward, +Y left, +Z up)
* Stereo camera frame   = FLU  (same as IMU frame)
  - The stereo camera frame is the central reference frame between the two cameras.
* Camera body frame     = FLU  (same as the stereo camera frame)
* Camera optical frame  = RDF  (+X right, +Y down, +Z forward)
  - A fixed rotation is applied to transform the camera body frame to the camera optical frame:
    R_optical = Rz(180°) · Rx(‑90°)

Transformation Calculation
---------------------------
T_imu_cam = T_imu_stereo * T_stereo_cam

1. T_imu_stereo is calculated based on the SDF pose.
2. The left and right cameras are positioned along the Y-axis of the stereo frame:
   - Left Camera: offset by +0.5 * separation along the Y-axis.
   - Right Camera: offset by -0.5 * separation along the Y-axis.
3. T_stereo_cam applies the camera's optical frame transformation (R_optical).

Implementation
---------------
"""
import math, argparse, numpy as np
np.set_printoptions(suppress=True, precision=4)

R2D = 180.0 / math.pi
D2R = math.pi / 180.0

def Rx(angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[1, 0, 0], [0, c,-s], [0, s, c]])

def Ry(angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[ c, 0, s], [ 0, 1, 0], [-s, 0, c]])

def Rz(angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c,-s, 0], [s, c, 0], [0, 0, 1]])

def rpy2R(roll, pitch, yaw):
    return Rz(yaw) @ Ry(pitch) @ Rx(roll)

def build_matrix(x, y, z, roll_deg, pitch_deg, yaw_deg, cam_offset_y=0):
    R_sdf = rpy2R(roll_deg*D2R, pitch_deg*D2R, yaw_deg*D2R)
    R_optical = Rz(math.pi) @ Rx(-math.pi/2)

    T_imu_stereo = np.eye(4)
    T_imu_stereo[:3, :3] = R_sdf
    T_imu_stereo[:3, 3] = [x, y, z]

    T_stereo_cam = np.eye(4)
    T_stereo_cam[:3, :3] = R_optical
    T_stereo_cam[1, 3] = cam_offset_y

    return T_imu_stereo @ T_stereo_cam

def to_yaml_matrix(T):
    return '\n'.join([f'  - [{row[0]: .4f}, {row[1]: .4f}, {row[2]: .4f}, {row[3]: .3f}]' for row in T])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convert SDF pose -> OpenVINS T_imu_cam matrices for stereo camera")
    ap.add_argument("x", type=float, help="stereo center x position in meters")
    ap.add_argument("y", type=float, help="stereo center y position in meters")
    ap.add_argument("z", type=float, help="stereo center z position in meters")
    ap.add_argument("roll", type=float, help="stereo camera roll in degrees")
    ap.add_argument("pitch", type=float, help="stereo camera pitch in degrees")
    ap.add_argument("yaw", type=float, help="stereo camera yaw in degrees")
    ap.add_argument("separation", type=float, help="total separation between cameras in meters")
    args = ap.parse_args()

    half_sep = args.separation / 2

    T_left = build_matrix(args.x, args.y, args.z, args.roll, args.pitch, args.yaw, cam_offset_y=+half_sep)
    T_right = build_matrix(args.x, args.y, args.z, args.roll, args.pitch, args.yaw, cam_offset_y=-half_sep)

    print("# ---- paste below into kalibr_imucam_chain.yaml for LEFT camera ----")
    print("T_imu_cam0:")
    print(to_yaml_matrix(T_left))

    print("\n# ---- paste below into kalibr_imucam_chain.yaml for RIGHT camera ----")
    print("T_imu_cam1:")
    print(to_yaml_matrix(T_right))