import numpy as np
from math import sin, cos, radians
import argparse

def sdf_pose_to_transform_matrix(x, y, z, roll, pitch, yaw, in_degrees=True):
    """
    Convert SDF pose (x, y, z, roll, pitch, yaw) to a 4x4 homogeneous transformation matrix.
    SDF rotation order is applied: yaw (z) → pitch (y) → roll (x)
    
    Args:
        x, y, z: Translation components
        roll, pitch, yaw: Rotation angles
        in_degrees: If True, angles are in degrees; otherwise in radians
    
    Returns:
        4x4 homogeneous transformation matrix
    """
    # Convert angles to radians if they're in degrees
    if in_degrees:
        roll = radians(roll)
        pitch = radians(pitch)
        yaw = radians(yaw)
    
    # Create rotation matrices for each axis
    # Roll (rotation around X-axis)
    R_x = np.array([
        [1, 0, 0],
        [0, cos(roll), -sin(roll)],
        [0, sin(roll), cos(roll)]
    ])
    
    # Pitch (rotation around Y-axis)
    R_y = np.array([
        [cos(pitch), 0, sin(pitch)],
        [0, 1, 0],
        [-sin(pitch), 0, cos(pitch)]
    ])
    
    # Yaw (rotation around Z-axis)
    R_z = np.array([
        [cos(yaw), -sin(yaw), 0],
        [sin(yaw), cos(yaw), 0],
        [0, 0, 1]
    ])
    
    # Combine rotations according to SDF order: yaw → pitch → roll
    # This means we apply the matrices in the order: R_x * R_y * R_z
    R = R_x @ R_y @ R_z
    
    # Create the full transformation matrix
    T = np.eye(4)
    T[0:3, 0:3] = R
    T[0:3, 3] = [x, y, z]
    
    return T

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert SDF pose to transformation matrix')
    parser.add_argument('--x', type=float, required=True, help='X translation')
    parser.add_argument('--y', type=float, required=True, help='Y translation')
    parser.add_argument('--z', type=float, required=True, help='Z translation')
    parser.add_argument('--roll', type=float, required=True, help='Roll angle')
    parser.add_argument('--pitch', type=float, required=True, help='Pitch angle')
    parser.add_argument('--yaw', type=float, required=True, help='Yaw angle')
    parser.add_argument('--radians', action='store_true', help='If set, angles are in radians; otherwise in degrees')
    
    args = parser.parse_args()
    
    # Convert to transformation matrix
    T = sdf_pose_to_transform_matrix(
        args.x, args.y, args.z, 
        args.roll, args.pitch, args.yaw, 
        in_degrees=not args.radians
    )
    
    # Print with nice formatting
    print("Transformation matrix from SDF pose:")
    print(np.array2string(T, precision=6, suppress_small=True))
    
    # Format as a YAML-like output
    print("\nYAML format for transformation matrix:")
    print("transformation_matrix:")
    for row in T:
        print(f"    - {list(row)}")