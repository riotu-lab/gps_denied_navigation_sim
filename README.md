# gps_denied_navigation_sim

Simulation environment that can be used for GPS-denied navigation frameworks.

>Note To learn how to create DEM model for gazebo follow instruction [here](generate_dem.md)

## Dependencies

* ROS 2 humble + Gazebo `garden`
* PX4 Atuopilot

## Installation

A Docker image for the simulation development environment is available at [gps_denied_navigation_docker](https://github.com/riotu-lab/gps_denied_navigation_docker.git). It includes Ubuntu 22.04, ROS 2 Humble + Gazebo Garden, and PX4 Autopilot.

## Run

* Combile the workspace using `colcon build`

* Source the workspace source `install/setup.bash`

* Launch Simulation: In your first terminal, initiate the simulation by running:

```bash
ros2 launch gps_denied_navigation_sim dem.launch.py
```
Upon execution, Gazebo should display a `quadcopter` and `DEM`.