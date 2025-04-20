#!/usr/bin/env python3
"""
pose2openvins_matrix.py
-------------------------------------------------
Given the pose of a camera described in an SDF   (<pose>x y z R P Y</pose>)
produce the 4×4 homogeneous matrix T_imu_cam to insert in kalibr_imucam_chain.yaml
for OpenVINS.

Conventions
-----------
* SDF pose order: roll(X)‑pitch(Y)‑yaw(Z) **degrees**
* IMU frame (base_link) = FLU  (+X forward, +Y left, +Z up)
* Camera body frame      = FLU  (same as pose)
* Camera optical frame   = RDF  (+X right, +Y down, +Z forward)  ──> add fixed
  rotation  R_optical =  Rz(180°) · Rx(‑90°)

Formula
-------
T_imu_cam =  [ R_sdf · R_optical ,  t ]   (all expressed in IMU frame)
             [        0 0 0      ,  1 ]
             
Usage
----
python pose2openvins_matrix.py 0.20 0 0.10 0 10 0

"""
import math, argparse, numpy as np
np.set_printoptions(suppress=True, precision=4)

R2D = 180.0 / math.pi
D2R = math.pi / 180.0

def Rx(angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[1, 0, 0],
                     [0, c,-s],
                     [0, s, c]])

def Ry(angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[ c, 0, s],
                     [ 0, 1, 0],
                     [-s, 0, c]])

def Rz(angle_rad):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c,-s, 0],
                     [s, c, 0],
                     [0, 0, 1]])

def rpy2R(roll, pitch, yaw):
    """SDF uses intrinsic Z‑Y‑X (yaw‑pitch‑roll) order."""
    return Rz(yaw) @ Ry(pitch) @ Rx(roll)

def build_matrix(x, y, z, roll_deg, pitch_deg, yaw_deg):
    R_sdf      = rpy2R(roll_deg*D2R, pitch_deg*D2R, yaw_deg*D2R)
    R_optical  = Rz(math.pi) @ Rx(-math.pi/2)
    R_total    = R_sdf @ R_optical
    T = np.eye(4)
    T[:3,:3] = R_total
    T[:3, 3] = [x, y, z]
    return T

def to_yaml_matrix(T):
    return '\n'.join([f'  - [{row[0]: .4f}, {row[1]: .4f}, {row[2]: .4f}, {row[3]: .3f}]'
                      for row in T])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Convert SDF pose -> OpenVINS T_imu_cam matrix")
    ap.add_argument("x", type=float, help="meters")
    ap.add_argument("y", type=float, help="meters")
    ap.add_argument("z", type=float, help="meters")
    ap.add_argument("roll",  type=float, help="deg")
    ap.add_argument("pitch", type=float, help="deg")
    ap.add_argument("yaw",   type=float, help="deg")
    args = ap.parse_args()

    T = build_matrix(args.x, args.y, args.z, args.roll, args.pitch, args.yaw)
    print("# ---- paste below into kalibr_imucam_chain.yaml ----")
    print("T_imu_cam:")
    print(to_yaml_matrix(T))
