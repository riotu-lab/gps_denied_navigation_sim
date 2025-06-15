# GPS-Denied Navigation Simulation Worlds Documentation

## Overview
This document provides detailed parameters, dimensions, and characteristics for all simulation worlds in the GPS-denied navigation simulation package.

---

## 1. Tugbot Depot World (`tugbot_depot.sdf`)

### Environment Type
**Indoor Warehouse/Depot Simulation**

### Physical Dimensions
- **Building Length**: 30.167 meters (X-axis)
- **Building Width**: 15.360 meters (Y-axis)
- **Building Height**: 9.0 meters (Z-axis)

### Areas and Volumes
- **Floor Area**: **463.36 m²** (30.167 × 15.360)
- **Total Volume**: **4,170.24 m³** (30.167 × 15.360 × 9.0)
- **Navigable Area**: ~400 m² (considering obstacles)

### Structure Details
#### Main Building Envelope
- **North Wall**: 30.167 × 0.08 × 9.0 m @ Y = -7.6129m
- **South Wall**: 30.167 × 0.08 × 9.0 m @ Y = 7.2875m
- **West Wall**: 0.08 × 15.360 × 9.0 m @ X = -15.0m
- **East Wall**: 0.08 × 15.360 × 9.0 m @ X = 15.0m

#### Internal Objects
- **Storage Boxes**: 11 units @ 1.288 × 1.422 × 1.288 m each
- **Structural Pillars**: 4 units @ 0.465 × 0.465 × 2.0 m each
- **Shelving Poles**: 18 cylindrical poles (radius: 0.03m, height: 1.0m)
- **Equipment**: Pallet movers, stairs, various warehouse equipment

### Geographic Coordinates
- **Frame**: ENU (East-North-Up)
- **Latitude**: 47.397971° N
- **Longitude**: 8.546163° E
- **Altitude**: 0 meters
- **Location**: Switzerland region

### Physics Parameters
- **Physics Engine**: ODE
- **Max Step Size**: 0.004 seconds
- **Real Time Factor**: 1.0
- **Update Rate**: 250 Hz
- **Gravity**: 0, 0, -9.8 m/s²

### Use Cases
- Indoor navigation testing
- Warehouse robotics simulation
- Obstacle avoidance algorithms
- SLAM in structured environments

---

## 2. Taif World (`taif_world.sdf`)

### Environment Type
**Outdoor Terrain/DEM Simulation**

### Terrain Characteristics
- **Type**: Digital Elevation Model (DEM) based terrain
- **Model**: External `taif_dem` model
- **Environment**: Mountainous/hilly terrain simulation

### Geographic Coordinates
- **Frame**: ENU (East-North-Up)
- **Latitude**: 21.27081° N
- **Longitude**: 40.34730° E
- **Altitude**: 1,874.6 meters
- **Location**: Taif region, Saudi Arabia

### Physical Properties
- **Terrain Size**: Variable (depends on DEM resolution and extent)
- **Elevation Range**: Variable based on DEM data
- **Surface Type**: Natural terrain mesh

### Lighting and Environment
- **Lighting**: Directional sunlight simulation
- **Sun Position**: (0, 0, 500) meters
- **Light Direction**: (0.001, 0.625, -0.78)
- **Shadows**: Enabled
- **Ambient Lighting**: Medium intensity (0.4, 0.4, 0.4)

### Physics Parameters
- **Physics Engine**: ODE
- **Max Step Size**: 0.004 seconds
- **Real Time Factor**: 1.0
- **Update Rate**: 250 Hz
- **Gravity**: 0, 0, -9.8 m/s²

### Use Cases
- Outdoor navigation testing
- Terrain following algorithms
- GPS-denied navigation in mountainous areas
- Natural environment SLAM

---

## 3. DEM World (`dem_world.sdf`)

### Environment Type
**Generic Digital Elevation Model Simulation**

### Terrain Characteristics
- **Type**: Digital Elevation Model (DEM) based terrain
- **Model**: External `dem` model
- **Environment**: Generic terrain simulation

### Geographic Coordinates
- **Frame**: ENU (East-North-Up)
- **Latitude**: 47.75096° N
- **Longitude**: -123.56506° W
- **Altitude**: 6,378,137 meters (Earth radius level)
- **Location**: Pacific Northwest region (Washington/British Columbia area)

### Physical Properties
- **Terrain Size**: Variable (depends on DEM resolution and extent)
- **Elevation Range**: Variable based on DEM data
- **Surface Type**: Natural terrain mesh

### Lighting and Environment
- **Lighting**: Directional sunlight simulation
- **Sun Position**: (0, 0, 500) meters
- **Light Direction**: (0.001, 0.625, -0.78)
- **Shadows**: Enabled
- **Ambient Lighting**: Medium intensity (0.4, 0.4, 0.4)

### Physics Parameters
- **Physics Engine**: ODE
- **Max Step Size**: 0.004 seconds
- **Real Time Factor**: 1.0
- **Update Rate**: 250 Hz
- **Gravity**: 0, 0, -9.8 m/s²

### Use Cases
- Generic outdoor navigation testing
- Terrain-based navigation algorithms
- Multi-environment testing
- Natural environment simulation

---

## Common Simulation Parameters

### Physics Configuration (All Worlds)
| Parameter | Value | Unit |
|-----------|-------|------|
| Physics Engine | ODE | - |
| Max Step Size | 0.004 | seconds |
| Real Time Factor | 1.0 | - |
| Update Rate | 250 | Hz |
| Gravity | (0, 0, -9.8) | m/s² |

### Environmental Parameters (All Worlds)
| Parameter | Value | Unit |
|-----------|-------|------|
| Magnetic Field | (6e-06, 2.3e-05, -4.2e-05) | Tesla |
| Atmosphere Type | Adiabatic | - |
| Camera Near Clip | 0.25 | meters |
| Camera Far Clip | 50,000 | meters |

### Available Systems (All Worlds)
- Physics System
- User Commands System
- Scene Broadcaster System
- Contact System
- IMU System
- Air Pressure System
- Apply Link Wrench System
- NavSat System
- Sensors System (Ogre2 rendering)

---

## Usage Recommendations

### World Selection Guidelines

| Scenario | Recommended World | Reason |
|----------|-------------------|---------|
| Indoor Navigation | `tugbot_depot.sdf` | Structured environment with known dimensions |
| Warehouse Robotics | `tugbot_depot.sdf` | Realistic warehouse layout with obstacles |
| Outdoor Navigation | `taif_world.sdf` or `dem_world.sdf` | Natural terrain with elevation changes |
| Multi-environment Testing | All three | Comprehensive evaluation across environments |
| Algorithm Development | `tugbot_depot.sdf` | Controlled, predictable environment |

### Performance Considerations
- **Tugbot Depot**: Lowest computational overhead, fastest simulation
- **Taif/DEM Worlds**: Higher computational overhead due to complex terrain mesh
- **Recommended**: Start development with tugbot_depot, then test on terrain worlds

---

## File Information
- **Created**: 2025
- **Last Updated**: January 2025
- **Maintainer**: GPS-Denied Navigation Research Team
- **Version**: 1.0

---

## References
- SDF Format Specification: [http://sdformat.org/](http://sdformat.org/)
- Gazebo Simulation: [https://gazebosim.org/](https://gazebosim.org/)
- ROS 2 Integration: [https://docs.ros.org/](https://docs.ros.org/) 