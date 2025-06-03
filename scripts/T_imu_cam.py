#!/usr/bin/env python3
"""
T_imu_cam.py
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
    R_optical from SDF: roll=-90°, pitch=0°, yaw=-90°

Transformation Calculation
---------------------------
T_imu_cam = T_imu_stereo * T_stereo_cam

1. T_imu_stereo is calculated based on the SDF pose.
2. The left and right cameras are positioned along the Y-axis of the stereo frame:
   - Left Camera: offset by +0.5 * separation along the Y-axis.
   - Right Camera: offset by -0.5 * separation along the Y-axis.
3. T_stereo_cam applies the camera's optical frame transformation (R_optical).

Usage
----
python3 T_imu_cam.py 0.20 0.0 -0.1 0 10 0 0.18

where 0.20 0.0 -0.1 is the translation of the stereo camera frame relative to the IMU frame
and 0 10 0 is the rotation of the stereo camera frame relative to the IMU frame
and 0.12 is the separation between the two cameras
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

# Fixed rotation from camera body frame to optical frame (from SDF: -90°, 0°, -90°)
R_OPTICAL = rpy2R(-90, 0, -90)

def stereo2cam(offset_y):
    """Return (translation in *stereo body* axes) ∘ (optical rotation)."""
    T = np.eye(4)
    T[1, 3]  = offset_y          # translate along stereo +Y
    T[:3,:3] = R_OPTICAL         # then rotate into optical frame
    return T

def print_yaml(name, T):
    print(f"{name}:")
    for r in T:
        print(f"  - [{r[0]:.9f}, {r[1]:.9f}, {r[2]:.9f}, {r[3]:.9f}]")

# ---------- main ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="SDF pose ➜ OpenVINS T_cam_imu matrices",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("x", type=float, help="stereo-centre X [m]")
    ap.add_argument("y", type=float, help="stereo-centre Y [m]")
    ap.add_argument("z", type=float, help="stereo-centre Z [m]")
    ap.add_argument("roll",  type=float, help="roll  [deg]")
    ap.add_argument("pitch", type=float, help="pitch [deg]")
    ap.add_argument("yaw",   type=float, help="yaw   [deg]")
    ap.add_argument("separation", type=float, help="camera baseline [m]")
    args = ap.parse_args()

    if args.separation <= 0:
        sys.exit("Error: separation must be positive.")

    # IMU ➜ stereo-body
    T_imu_stereo = np.eye(4)
    T_imu_stereo[:3,:3] = rpy2R(args.roll, args.pitch, args.yaw)
    T_imu_stereo[:3, 3] = [args.x, args.y, args.z]

    half_sep = 0.5 * args.separation
    T_left_cam  = T_imu_stereo @ stereo2cam(+half_sep)
    T_right_cam = T_imu_stereo @ stereo2cam(-half_sep)

    print("# ---- paste below into kalibr_imucam_chain.yaml for LEFT camera ----")
    print_yaml("T_imu_cam", T_left_cam)
    print("# ---- paste below into kalibr_imucam_chain.yaml for RIGHT camera ----")
    print_yaml("T_imu_cam", T_right_cam)