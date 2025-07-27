import bpy
import os
import sys
import math
import sys
from utils.get_map import getpic
from pathlib import Path
import argparse

def deg_to_rad(degrees):
    return degrees * math.pi / 180

def rad_to_deg(radians):
    return radians * 180 / math.pi

def calculate_new_longitude(lon, lat, distance=111.32*2):
    lat_rad = deg_to_rad(lat)
    delta_lon_rad = distance / (6378137 * math.cos(lat_rad))
    new_lon = lon + rad_to_deg(delta_lon_rad)
    return new_lon

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate mesh from lat/lon')
    parser.add_argument('-lat', type=float, default=float(22.316685431645908), help='Latitude')
    parser.add_argument('-lon', type=float, default=float(114.17411622004772), help='Longitude')
    args = parser.parse_args()

    root_path = Path(__file__).resolve().parent
    sys.path.append(root_path)
    addon_name = "blosm"
    addon_zip_path = os.path.join(root_path, "blosm_2.7.8.zip")
    bpy.ops.preferences.addon_install(filepath=addon_zip_path)
    bpy.ops.preferences.addon_enable(module="blosm")
    bpy.ops.wm.save_userpref()

    if addon_name in bpy.context.preferences.addons:
        preferences = bpy.context.preferences.addons[addon_name].preferences
        preferences.dataDir = str(root_path)
        preferences.googleMapsApiKey = 'AIzaSyA8C9_h4ZqzKWDRJNNG3677SYaZgZ9XSWg'
        bpy.ops.wm.save_userpref()
    bpy.data.scenes["Scene"].blosm.dataType = 'google-3d-tiles'
    lat_step = args.lat
    lon_step = args.lon
    maxlat = lat_step + 0.002
    minlat = lat_step
    maxlon = calculate_new_longitude(lon_step, lat_step)
    minlon = lon_step

    bpy.data.scenes["Scene"].blosm.maxLat = maxlat
    bpy.data.scenes["Scene"].blosm.minLat = minlat
    bpy.data.scenes["Scene"].blosm.maxLon = maxlon
    bpy.data.scenes["Scene"].blosm.minLon = minlon
    bpy.context.view_layer.update()

    sources = ['google', 'tianditu', 'arcgisonline', 'amap']
    for source in sources:
        getpic(minlon, maxlat, maxlon, minlat, 18, source=source, style='s',
                outfile=os.path.join(root_path, 'output', 'lat{:.3f}_lon{:.3f}_{}.tif'.format(minlat, minlon, source)))

    for lodof3dtile in ['lod6']:
        bpy.data.scenes["Scene"].blosm.lodOf3dTiles = lodof3dtile
        bpy.ops.blosm.import_data()
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.export_scene.gltf(filepath=os.path.join(root_path, 'output', 'lat{:.3f}_lon{:.3f}.glb'.format(minlat, minlon)))
    bpy.ops.object.delete()
