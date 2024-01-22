# gps_denied_navigation_sim
Simulation environment that can be used for GPS-denied navigation frameworks.

## How to Generate DEM for Gazebo

### Dependencies

* Ubuntu 22.04
* ROS 2 humble + Gazebo garden
* PX4 Atuopilot 
* Blender
* Blender GIS 

### Installation

#### TODO

simulation deveopment environment docker image (Ubuntu 22.04, ROS 2 humble + Gazebo garden, PX4 Atuopilot).

#### Blender

please make sure that you have a `blender`  with the following version `3.6.0`, from [here](https://download.blender.org/release/Blender3.6/).

once you opend the link select `blender-3.6.0-linux-x64.tar.xz` wait for it to be downloaded. go to Downloads and unzip the `blender-3.6.0-linux-x64.tar.xz`

```bash
cd blender-3.6.0-linux-x64.tar.xz
./blender
```

### Blender GIS 

You need to clone the repository 
```bash
git clone https://github.com/domlysz/BlenderGIS
```

Note : Since 2022, the OpenTopography web service requires an API key. Please register to opentopography.org and request a key. This service is still free.

### How to configure Blender with BlenderGIS

Once the blender will opened you need to `remove`, `cube`, `camera` and `light` ![collection](media/collection.png) ![collection](media/coolectionafter.png
)

Next you need to add the `Blender GIS` plugin you cloned. 

* go to `edit` select `preferences`. 
* select `install` and add the plugin path you should download as .zip file. 
* next you need to select 3D view: Blender GIS
![collection](media/preference.png)
* next inside the search tab search for node and mark it as selected.
![collection](media/node.png)

now you can use the Blender GIS colse the window and back to blinder you will find GIS plugin activated. 

The terrain is made by Blender with an
additional add-on named GIS. This add-on has to be imported from the internet that will allow
me to use the GIS data format. To make the terrain, the GIS data format that I used was
directly connected to Google and satellite.

![collection](media/basemap.png)

this action
allows me to get the picture of a world map that can search specific and can be zoomed in

What I need to do is just simply go through GIS, onto the basemap, and click `Ok`. Afterwards,
![collection](media/ok.png)
![collection](media/map.png)
the Blender will show a planar image of the world map and I pressed `G` to search a specific
location on the map.

![collection](media/g.png)

The terrain that I made is the result of my initial idea about making a
terrain that has hills which most likely to be on a mountain area. I looked up a mountain area
around US and found one that interests me.
![collection](media/mt_wilder.png)

This mountain appears to have lots of hills and looks
beautiful which are my main reasons for choosing this. Then I searched up for this mountain
on the planar map, zoomed in by 15 times, and get its planar picture of the mountain area for
this simulation.
![collection](media/map_wi.png)

once you select ROI click `E` this will bring Planar map of Mt. Wilder.
![collection](media/planer.png)

The next step after this is getting the elevation for the mountain area. I then go onto the
GIS, Web geodata, and select ‘Get elevation (SRTM)’ to get the planar’s height. The elevation
data is using the Shuttle Radar Topography Mission (SRTM) which data is provided by NASA
online.
![collection](media/srtm.png)

After selecting the SRTM, it will show a popup that gives us options about the height.
The options are ‘OpenTopography SRTM 30m’, ‘OpenTopography SRTM 90m’, and ‘Marine-
geo.org GMRT’.

Next we will need to convert the elevation to Mesh by right clicking and choose `convert to` then `mesh`
![collection](media/mesh.png)

then switch to `edit mode` you find the DEM converted to mesh 
![collection](media/edit.png)

now you can export your DEM to collade file `.dae`
![collection](media/collada.png)

it will export 2 files for you `.dae` and `.tif`.
copy theses files to your `world` package.
 
```xml
<?xml version="1.0" ?>
<sdf version="1.5">
  <model name="dem">
    <pose>0 0 0 0 0 0</pose>
    <static>true</static>
    <link name="body">
      <visual name="visual">
        <transparency>0</transparency>
        <geometry>
          <mesh>
            <uri>media/dem.dae</uri>
            <scale>0.001121131 0.001121131 0.001121131</scale>
          </mesh>
        </geometry>

      </visual>
      <collision name="collision">
        <geometry>
          <mesh>
            <uri>media/dem.dae</uri>
            <scale>0.001121131 0.001121131 0.001121131</scale>
          </mesh>

        </geometry>
      </collision>
    </link>
  </model>
</sdf>
```
![collection](media/gazebo.png)