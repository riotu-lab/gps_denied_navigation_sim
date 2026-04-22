# Taif DEM Geographic Coordinates Documentation

## Overview
This document contains the geographic coordinate information for the Taif Digital Elevation Model (DEM) used in the GPS-denied navigation simulation.

## Source File Information
- **Primary DEM File**: `taif1.tif`
- **Location**: `models/taif_dem/media/taif1.tif`
- **Data Type**: GeoTIFF (Int16)
- **NoData Value**: -32768

## Geographic Coordinates

### Corner Coordinates (Decimal Degrees)

| Corner | Longitude (E) | Latitude (N) | DMS Format |
|--------|---------------|--------------|------------|
| **Upper Left** | 40.1670833° | 21.3076389° | 40°10'1.50"E, 21°18'27.50"N |
| **Lower Left** | 40.1670833° | 21.2645833° | 40°10'1.50"E, 21°15'52.50"N |
| **Upper Right** | 40.2823611° | 21.3076389° | 40°16'56.50"E, 21°18'27.50"N |
| **Lower Right** | 40.2823611° | 21.2645833° | 40°16'56.50"E, 21°15'52.50"N |

### Center Point
- **Longitude**: 40.2247222°E (40°13'29.00"E)
- **Latitude**: 21.2861111°N (21°17'10.00"N)

## Bounding Box Summary

### Extent
- **West Boundary**: 40.1670833°E
- **East Boundary**: 40.2823611°E
- **North Boundary**: 21.3076389°N
- **South Boundary**: 21.2645833°N

### Dimensions
- **Longitude Span**: 0.1152778° (~12.8 km)
- **Latitude Span**: 0.0430556° (~4.8 km)
- **Approximate Area**: ~61.4 km²

## Technical Specifications

### Raster Properties
- **Block Size**: 415x9 pixels
- **Data Type**: 16-bit signed integer
- **Color Interpretation**: Grayscale
- **Overviews**: 208x78 pixels

### Coordinate Reference System
- **Projection**: Geographic (WGS84)
- **EPSG Code**: 4326 (assumed)
- **Units**: Decimal degrees

## Usage in Simulation

### World File Integration
These coordinates are used in the following world files:
- `taif1_world.sdf`
- `taif_world.sdf`
- `dem_world.sdf`

### Gazebo Integration
The DEM is integrated into Gazebo simulation environments for:
- Terrain visualization
- Physics collision detection
- GPS-denied navigation testing
- Realistic topographic simulation

## Geographic Context

### Location
- **Region**: Taif, Saudi Arabia
- **Province**: Makkah Province
- **Terrain Type**: Mountainous/Highland region
- **Elevation**: Variable (stored in DEM data)

### Real-World Features
The area covered includes:
- Urban areas of Taif city
- Surrounding mountainous terrain
- Agricultural areas
- Transportation networks

## Coordinate Conversion

### For Gazebo/ROS Usage
When using these coordinates in simulation:

```xml
<!-- Example world coordinate reference -->
<spherical_coordinates>
  <surface_model>EARTH_WGS84</surface_model>
  <latitude_deg>21.2861111</latitude_deg>
  <longitude_deg>40.2247222</longitude_deg>
  <elevation>0</elevation>
</spherical_coordinates>
```

### UTM Coordinates (Approximate)
- **UTM Zone**: 37R
- **Easting**: ~739,000 - 752,000 m
- **Northing**: ~2,354,000 - 2,359,000 m

## Related Files

### Media Files
- `taif1.tif` - Primary DEM data
- `geo_EXPORT_GOOGLE_SAT_WM.tif` - Satellite imagery overlay
- `EXPORT_GOOGLE_SAT_WM.tif` - Additional satellite data
- `taif1.dae` - 3D mesh model
- `taif.dae` - Simplified 3D model
- `Image_0.png` - Texture/reference image

### World Files
- `taif1_world.sdf` - Primary simulation world
- `taif_world.sdf` - Alternative world configuration
- `dem_world.sdf` - DEM-focused world setup

## Notes

### Data Quality
- High-resolution DEM suitable for detailed simulation
- Coordinate precision to 7 decimal places
- Proper NoData handling for invalid regions

### Simulation Considerations
- Coordinate system must match between DEM and world files
- Elevation data provides realistic terrain physics
- Geographic accuracy enables GPS simulation testing

### Updates
- Last verified: [Current Date]
- Source: GDAL analysis of taif1.tif
- Coordinate system: WGS84 Geographic

---
*This documentation was generated from GeoTIFF metadata analysis using GDAL tools.* 