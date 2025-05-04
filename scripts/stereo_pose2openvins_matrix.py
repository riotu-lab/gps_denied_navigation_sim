#!/usr/bin/env python3
"""
stereo_pose2openvins_matrix.py
-------------------------------------------------
Given the pose of a stereo camera described in an SDF (<pose>x y z R P Y</pose>)
and the separation between cameras, produce the 4×4 homogeneous matrices 
T_imu_cam for left and right cameras to insert in kalibr_imucam_chain.yaml 
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
python stereo_pose2openvins_matrix.py 0.20 0 0.10 0 10 0 0.3

Where the last parameter (0.3) is the total separation between cameras in meters.
This would mean each camera is 0.15m from the center.
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

def build_matrix(x, y, z, roll_deg, pitch_deg, yaw_deg, cam_offset_y=0):
    """
    Build transformation matrix for a camera
    
    Parameters:
    - x, y, z: Position of the stereo camera center in IMU frame (meters)
    - roll_deg, pitch_deg, yaw_deg: Rotation of the stereo camera in IMU frame (degrees)
    - cam_offset_y: Y-offset of individual camera from stereo center (meters)
             Use negative value for left camera, positive for right camera
    """
    R_sdf = rpy2R(roll_deg*D2R, pitch_deg*D2R, yaw_deg*D2R)
    R_optical = Rz(math.pi) @ Rx(-math.pi/2)
    R_total = R_sdf @ R_optical
    
    # Calculate the position of the individual camera in world frame
    # by applying the rotation to the camera offset and adding to the stereo center
    cam_offset = np.array([0, cam_offset_y, 0])
    rotated_offset = R_sdf @ cam_offset
    
    T = np.eye(4)
    T[:3,:3] = R_total
    T[:3, 3] = [x + rotated_offset[0], y + rotated_offset[1], z + rotated_offset[2]]
    return T

def to_yaml_matrix(T):
    return '\n'.join([f'  - [{row[0]: .4f}, {row[1]: .4f}, {row[2]: .4f}, {row[3]: .3f}]'
                      for row in T])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Convert SDF pose -> OpenVINS T_imu_cam matrices for stereo camera")
    ap.add_argument("x", type=float, help="stereo center x position in meters")
    ap.add_argument("y", type=float, help="stereo center y position in meters")
    ap.add_argument("z", type=float, help="stereo center z position in meters")
    ap.add_argument("roll", type=float, help="stereo camera roll in degrees")
    ap.add_argument("pitch", type=float, help="stereo camera pitch in degrees")
    ap.add_argument("yaw", type=float, help="stereo camera yaw in degrees")
    ap.add_argument("separation", type=float, help="total separation between cameras in meters")
    args = ap.parse_args()

    # Calculate half the separation for each camera's offset
    half_sep = args.separation / 2
    
    # Get transformation matrix for left camera (negative offset in Y direction)
    T_left = build_matrix(args.x, args.y, args.z, args.roll, args.pitch, args.yaw, cam_offset_y=-half_sep)
    
    # Get transformation matrix for right camera (positive offset in Y direction)
    T_right = build_matrix(args.x, args.y, args.z, args.roll, args.pitch, args.yaw, cam_offset_y=half_sep)
    
    print("# ---- paste below into kalibr_imucam_chain.yaml for LEFT camera ----")
    print("T_imu_cam0:")  # Assuming cam0 is left camera in OpenVINS
    print(to_yaml_matrix(T_left))
    
    print("\n# ---- paste below into kalibr_imucam_chain.yaml for RIGHT camera ----")
    print("T_imu_cam1:")  # Assuming cam1 is right camera in OpenVINS
    print(to_yaml_matrix(T_right))