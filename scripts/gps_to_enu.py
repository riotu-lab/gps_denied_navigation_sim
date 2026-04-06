#!/usr/bin/env python3

import argparse
import os
import rasterio
import warnings
from rasterio.errors import NotGeoreferencedWarning
warnings.filterwarnings('ignore', category=NotGeoreferencedWarning)
from pyproj import Transformer, CRS
import pymap3d
import xml.etree.ElementTree as ET

def get_gazebo_map_size(tif_path):
    # Try to find model.sdf in the parent directory (usually ../model.sdf relative to the texture)
    dir_name = os.path.dirname(os.path.abspath(tif_path))
    model_sdf_path = os.path.join(os.path.dirname(dir_name), 'model.sdf')
    
    if not os.path.exists(model_sdf_path):
        return None
        
    try:
        tree = ET.parse(model_sdf_path)
        root = tree.getroot()
        # Find heightmap size and pos
        for heightmap in root.iter('heightmap'):
            size_elem = heightmap.find('size')
            pos_elem = heightmap.find('pos')
            if size_elem is not None:
                parts = size_elem.text.split()
                if len(parts) == 3:
                    size_x, size_y, size_z = float(parts[0]), float(parts[1]), float(parts[2])
                    
                    pos_x, pos_y, pos_z = 0.0, 0.0, 0.0
                    if pos_elem is not None:
                        p_parts = pos_elem.text.split()
                        if len(p_parts) == 3:
                            pos_x, pos_y, pos_z = float(p_parts[0]), float(p_parts[1]), float(p_parts[2])
                            
                    return (size_x, size_y, size_z), (pos_x, pos_y, pos_z)
    except Exception as e:
        print(f"Warning: Could not parse {model_sdf_path}: {e}")
        
    return None, None

def main():
    parser = argparse.ArgumentParser(description="Convert lat/lon to ENU (x, y, z) using a DEM (.tif)")
    parser.add_argument("--center-lat", type=float, required=True, help="Center latitude (degrees)")
    parser.add_argument("--center-lon", type=float, required=True, help="Center longitude (degrees)")
    parser.add_argument("--target-lat", type=float, required=True, help="Target latitude (degrees)")
    parser.add_argument("--target-lon", type=float, required=True, help="Target longitude (degrees)")
    parser.add_argument("--tif-file", type=str, required=True, help="Path to the .tif elevation map")
    parser.add_argument("--map-width", type=float, help="Manual override: Physical width of the map in meters (East-West)")
    parser.add_argument("--map-height", type=float, help="Manual override: Physical height of the map in meters (North-South)")
    parser.add_argument("--map-z-scale", type=float, help="Manual override: Physical max elevation scale in meters (Z-axis)")
    
    args = parser.parse_args()
    
    # 1. Open the TIF dataset
    try:
        dataset = rasterio.open(args.tif_file)
    except Exception as e:
        print(f"Failed to open TIF file: {e}")
        return

    # 2. Try to find physical map dimensions (from SDF or manual override)
    size_x, size_y, size_z = None, None, None
    pos_x, pos_y, pos_z = 0.0, 0.0, 0.0
    
    if args.map_width and args.map_height and args.map_z_scale:
        size_x, size_y, size_z = args.map_width, args.map_height, args.map_z_scale
        print(f"Using manually provided map dimensions: {size_x}m x {size_y}m x {size_z}m")
    else:
        map_dims, map_pos = get_gazebo_map_size(args.tif_file)
        if map_dims:
            size_x, size_y, size_z = map_dims
            print(f"Map physical dimensions (from SDF): {size_x}m x {size_y}m x {size_z}m")
            if map_pos:
                pos_x, pos_y, pos_z = map_pos
                print(f"Map pos offset (from SDF): {pos_x}m, {pos_y}m, {pos_z}m")

    # 3. Handle georeferenced TIFs
    tif_crs = dataset.crs
    if tif_crs is not None and str(tif_crs) != "":
        try:
            if tif_crs != CRS.from_epsg(4326):
                transformer = Transformer.from_crs("EPSG:4326", tif_crs, always_xy=True)
                cx, cy = transformer.transform(args.center_lon, args.center_lat)
                tx, ty = transformer.transform(args.target_lon, args.target_lat)
            else:
                cx, cy = args.center_lon, args.center_lat
                tx, ty = args.target_lon, args.target_lat
                
            center_val = float(next(dataset.sample([(cx, cy)]))[0])
            target_val = float(next(dataset.sample([(tx, ty)]))[0])
            
            # Decide how to interpret the pixel values (absolute elevation vs normalized heightmap)
            dtype = dataset.dtypes[0]
            if size_z is not None and dtype in ['uint8', 'uint16']:
                data_max = 255.0 if dtype == 'uint8' else 65535.0
                # Calculate absolute elevation (assuming 0 is minimum in Gazebo coordinate system)
                center_alt = (center_val / data_max) * size_z + pos_z
                target_alt = (target_val / data_max) * size_z + pos_z
                print(f"(Scaling {dtype} pixels by size_z={size_z} and offset pos_z={pos_z})")
            else:
                center_alt = center_val
                target_alt = target_val
            
        except Exception as e:
            print(f"Error sampling elevation from georeferenced TIF: {e}")
            return
            
        # Calculate ENU: Use pymap3d for X and Y, but use absolute target_alt for Z
        e, n, _ = pymap3d.geodetic2enu(
            args.target_lat, args.target_lon, target_alt,
            args.center_lat, args.center_lon, center_alt,
            deg=True
        )
        print(f"Center Elevation: {center_alt:.3f} m")
        print(f"Target Elevation: {target_alt:.3f} m")
        print("\nCorresponding ENU coordinates (Z is absolute elevation):")
        print(f"X (East) : {e:.6f}")
        print(f"Y (North): {n:.6f}")
        print(f"Z (Elev) : {target_alt:.6f}")
        return

    # 4. Handle non-georeferenced Gazebo texture TIFs
    print("Notice: The provided TIF file is not geographically referenced. Assuming it is a Gazebo heightmap.")
    
    if size_x is None or size_y is None or size_z is None:
        print("Error: Could not find model.sdf to read Gazebo map dimensions, and manual dimensions were not provided.")
        print("Please provide --map-width, --map-height, and --map-z-scale manually.")
        return
        
    img_width, img_height = dataset.width, dataset.height
    
    # In Gazebo, the heightmap 'pos' determines the physical location of the IMAGE CENTER relative to the world origin (0,0).
    # This means the WGS84 center coordinate (0,0) actually falls at distance -pos_x, -pos_y relative to the image center.
    
    # Absolute positions from Gazebo origin (0,0):
    center_e = 0.0
    center_n = 0.0
    
    target_e, target_n, _ = pymap3d.geodetic2enu(
        args.target_lat, args.target_lon, 0.0,
        args.center_lat, args.center_lon, 0.0,
        deg=True
    )
    
    # Calculate pixel coords
    # Image exact center coordinate:
    img_center_x_px = img_width / 2.0
    img_center_y_px = img_height / 2.0
    
    # Center GPS coordinate mapped to pixel (offset by pos_x, pos_y):
    center_px_x = img_center_x_px + (-pos_x) * (img_width / size_x)
    center_px_y = img_center_y_px - (-pos_y) * (img_height / size_y)
    
    # Target GPS coordinate mapped to pixel (offset by target_e - pos_x):
    dx_pixels = (target_e - pos_x) * (img_width / size_x)
    dy_pixels = (target_n - pos_y) * (img_height / size_y)
    
    target_px_x = img_center_x_px + dx_pixels
    target_px_y = img_center_y_px - dy_pixels # subtract because image Y goes from top to bottom
    
    # Check bounds
    if not (0 <= target_px_x < img_width and 0 <= target_px_y < img_height):
        print("Error: The target GPS coordinate falls outside the mapped physical bounds of the TIF image.")
        return

    # Sample pixels using integer indices
    # We read all data since it's likely a smallGazebo heightmap, or just read the specific window
    data = dataset.read(1)
    
    # Z elevation in Gazebo maps: scale pixel values (0-max) to 0-size_z.
    data_max = 255.0 if data.dtype == 'uint8' else 65535.0
    if data.dtype not in ['uint8', 'uint16']:
        data_max = data.max() if data.max() > 1.1 else 1.0

    center_val = data[int(center_px_y), int(center_px_x)]
    target_val = data[int(target_px_y), int(target_px_x)]
    
    center_alt = (center_val / data_max) * size_z + pos_z
    target_alt = (target_val / data_max) * size_z + pos_z
    
    print(f"Center pixel: ({int(center_px_x)}, {int(center_px_y)}) -> Elevation: {center_alt:.3f} m")
    print(f"Target pixel: ({int(target_px_x)}, {int(target_px_y)}) -> Elevation: {target_alt:.3f} m")
    
    # ENU outputs: X and Y are relative, Z is absolute elevation in Gazebo world coordinates
    print("\nCorresponding ENU coordinates (Z is absolute elevation):")
    print(f"X (East) : {target_e:.6f}")
    print(f"Y (North): {target_n:.6f}")
    print(f"Z (Elev) : {target_alt:.6f}")

if __name__ == "__main__":
    main()
