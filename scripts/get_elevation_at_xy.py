#!/usr/bin/env python3

import argparse
import os
import rasterio

# Reuse the parser from gps_to_enu.py
from gps_to_enu import get_gazebo_map_size

def main():
    parser = argparse.ArgumentParser(description="Find the ground elevation at any Gazebo (X, Y) coordinate.")
    parser.add_argument("--x", type=float, required=True, help="Target Gazebo X coordinate")
    parser.add_argument("--y", type=float, required=True, help="Target Gazebo Y coordinate")
    parser.add_argument("--tif-file", type=str, required=True, help="Path to the .tif heightmap file")
    
    args = parser.parse_args()
    
    try:
        dataset = rasterio.open(args.tif_file)
    except Exception as e:
        print(f"Failed to open TIF file: {e}")
        return

    map_dims, map_pos = get_gazebo_map_size(args.tif_file)
    if not map_dims or not map_pos:
        print("Error: Could not find model.sdf to read Gazebo map dimensions.")
        return
        
    size_x, size_y, size_z = map_dims
    pos_x, pos_y, pos_z = map_pos

    img_width, img_height = dataset.width, dataset.height
    
    # Calculate pixel offset from the image center
    # Center of the image is physically at (pos_x, pos_y)
    dx = args.x - pos_x
    dy = args.y - pos_y
    
    px = img_width / 2.0 + dx * (img_width / size_x)
    py = img_height / 2.0 - dy * (img_height / size_y) # Y goes down in images
    
    if not (0 <= px < img_width and 0 <= py < img_height):
        print("Error: The requested (X, Y) coordinate falls outside the map bounds!")
        return
        
    data = dataset.read(1)
    val = data[int(py), int(px)]
    
    # Z elevation in Gazebo maps: scale pixel values (0-max) to 0-size_z.
    data_max = 255.0 if data.dtype == 'uint8' else 65535.0
    if data.dtype not in ['uint8', 'uint16']:
        data_max = data.max() if data.max() > 1.1 else 1.0
        
    elev = (val / data_max) * size_z + pos_z
    
    print(f"Coordinate: X={args.x}, Y={args.y}")
    print(f"Ground Elevation: Z={elev:.3f} meters")
    print(f"Recommended Spawn Z: {elev + 0.5:.1f} meters (adds 0.5m buffer)")

if __name__ == "__main__":
    main()
