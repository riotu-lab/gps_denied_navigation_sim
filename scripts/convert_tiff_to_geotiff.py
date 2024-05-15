import sys
import os
from osgeo import gdal, osr
import numpy as np

def print_metadata(dataset):
    metadata = dataset.GetMetadata()
    print("Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    geotransform = dataset.GetGeoTransform()
    print("GeoTransform:")
    print(f"  Origin (top left x, top left y): ({geotransform[0]}, {geotransform[3]})")
    print(f"  Pixel Size (x, y): ({geotransform[1]}, {geotransform[5]})")
    
    projection = dataset.GetProjection()
    print("Projection:")
    print(f"  {projection}")

def calculate_gps_coordinates(width, height, center_lat, center_lon, pixel_width, pixel_height):
    latitudes = np.linspace(center_lat + (height // 2) * pixel_height, center_lat - (height // 2) * pixel_height, height)
    longitudes = np.linspace(center_lon - (width // 2) * pixel_width, center_lon + (width // 2) * pixel_width, width)
    lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing='ij')
    return lat_grid, lon_grid

def add_gps_metadata(image_path, output_path, center_lat, center_lon):
    # Open the original TIFF file
    dataset = gdal.Open(image_path)
    if dataset is None:
        print("Failed to open file.")
        return

    # Print metadata
    print_metadata(dataset)
    
    geotransform = dataset.GetGeoTransform()
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    num_bands = dataset.RasterCount
    data_type = dataset.GetRasterBand(1).DataType

    # Extract resolution (pixel size)
    resolution_x = dataset.GetMetadataItem('TIFFTAG_XRESOLUTION')
    resolution_y = dataset.GetMetadataItem('TIFFTAG_YRESOLUTION')
    resolution_unit = dataset.GetMetadataItem('TIFFTAG_RESOLUTIONUNIT')

    if resolution_x is None or resolution_y is None or resolution_unit is None:
        print("Resolution information is missing.")
        return

    resolution_x = float(resolution_x)
    resolution_y = float(resolution_y)

    # Extract numeric part from the resolution unit string
    resolution_unit = int(resolution_unit.split()[0])

    # Convert pixels/inch to pixels/degree
    # 1 degree = 111,139 meters at the equator
    meters_per_degree = 111139

    if resolution_unit == 2:  # pixels/inch
        inches_per_meter = 39.3701
        pixel_width = (1 / resolution_x) * inches_per_meter / meters_per_degree
        pixel_height = (1 / resolution_y) * inches_per_meter / meters_per_degree
    else:
        print("Unsupported resolution unit.")
        return

    # Calculate GPS coordinates for each pixel
    lat_grid, lon_grid = calculate_gps_coordinates(width, height, center_lat, center_lon, pixel_width, pixel_height)

    # Print the coordinates for the corners
    print("Corner Coordinates:")
    print(f"  Top-left:     ({lat_grid[0, 0]}, {lon_grid[0, 0]})")
    print(f"  Top-right:    ({lat_grid[0, -1]}, {lon_grid[0, -1]})")
    print(f"  Bottom-left:  ({lat_grid[-1, 0]}, {lon_grid[-1, 0]})")
    print(f"  Bottom-right: ({lat_grid[-1, -1]}, {lon_grid[-1, -1]})")

    # Create a new TIFF file with the same dimensions and number of bands
    options = ['PHOTOMETRIC=RGB'] if num_bands >= 3 else []
    driver = gdal.GetDriverByName('GTiff')
    out_dataset = driver.Create(output_path, width, height, num_bands, data_type, options)

    # Write the image data to the new file
    for band in range(1, num_bands + 1):
        in_band = dataset.GetRasterBand(band)
        out_band = out_dataset.GetRasterBand(band)
        out_band.WriteArray(in_band.ReadAsArray())

        # Check if a NoData value is set and copy it
        no_data_value = in_band.GetNoDataValue()
        if no_data_value is not None:
            out_band.SetNoDataValue(no_data_value)

        # Copy color interpretation
        out_band.SetColorInterpretation(in_band.GetColorInterpretation())

    # Copy metadata
    out_dataset.SetMetadata(dataset.GetMetadata())

    # Set the geotransform to the new file (adjusting to match the center lat/lon)
    out_geotransform = (
        center_lon - (width // 2) * pixel_width,  # top left x
        pixel_width,                              # w-e pixel resolution
        0,                                        # rotation, 0 if image is "north up"
        center_lat + (height // 2) * pixel_height, # top left y
        0,                                        # rotation, 0 if image is "north up"
        -pixel_height                             # n-s pixel resolution (negative value)
    )
    out_dataset.SetGeoTransform(out_geotransform)

    # Set the projection to WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)  # EPSG code for WGS84
    out_dataset.SetProjection(srs.ExportToWkt())

    # Ensure the TIFFTAG_SOFTWARE tag matches what might be expected in the .dae file
    out_dataset.SetMetadataItem('TIFFTAG_SOFTWARE', 'Blender 3.6.0')

    # Add GPS metadata
    out_dataset.SetMetadataItem('LATITUDES', str(lat_grid))
    out_dataset.SetMetadataItem('LONGITUDES', str(lon_grid))

    out_dataset = None  # Close the file
    print(f"New TIFF file with GPS metadata created: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <input_file> <center_lat> <center_lon>")
        sys.exit(1)

    image_path = sys.argv[1]
    center_lat = float(sys.argv[2])
    center_lon = float(sys.argv[3])

    # Generate the output filename as geo_<input_file_name>.tif
    input_basename = os.path.basename(image_path)
    input_filename, input_ext = os.path.splitext(input_basename)
    output_filename = f"geo_{input_filename}.tif"
    input_dir = os.path.abspath(os.path.dirname(image_path))
    output_path = os.path.join(input_dir, output_filename)

    add_gps_metadata(image_path, output_path, center_lat, center_lon)
