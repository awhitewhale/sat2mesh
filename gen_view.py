import bpy
import math
from mathutils import Vector
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Generate multi-view')
    parser.add_argument('-lat', type=float, default=float(22.315), help='Latitude')
    parser.add_argument('-lon', type=float, default=float(114.173), help='Longitude')
    args = parser.parse_args()
    lat = float(args.lat)
    lon = float(args.lon)
    output_dir = Path("output")
    glb_file = output_dir / f"sat2mesh_output.glb"

    image_prefix = "satview"                       
    render_resolution = (1024, 1024)              
    radius = 1.0 

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_file))
    scene = bpy.context.scene
    objs = [obj for obj in scene.objects if obj.type in {'MESH', 'EMPTY'}]
    bbox_min = Vector((float('inf'), float('inf'), float('inf')))
    bbox_max = Vector((float('-inf'), float('-inf'), float('-inf')))

    for obj in objs:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            bbox_min = Vector(map(min, bbox_min, world_corner))
            bbox_max = Vector(map(max, bbox_max, world_corner))

    model_center = (bbox_min + bbox_max) / 2

    # ====== 添加摄像机 ======
    cam_data = bpy.data.cameras.new(name='Camera')
    cam = bpy.data.objects.new('Camera', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # ====== 添加光源 ======
    light_data = bpy.data.lights.new(name="Light", type='SUN')
    light = bpy.data.objects.new(name="Light", object_data=light_data)
    light.location = model_center + Vector((0, 0, 10))
    scene.collection.objects.link(light)

    # ====== 渲染设置 ======
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = render_resolution[0]
    scene.render.resolution_y = render_resolution[1]
    scene.render.film_transparent = True

    script_dir = Path(__file__).parent / "output"

    for i in range(36):
        angle_deg = i * 10
        angle_rad = math.radians(angle_deg)
        cam_x = model_center.x + radius * math.cos(angle_rad)
        cam_y = model_center.y + radius * math.sin(angle_rad)
        cam_z = model_center.z + 250.0
        cam.location = Vector((cam_x, cam_y, cam_z))
        direction = model_center - cam.location + Vector((0, 0, 400))
        rot_euler = direction.to_track_quat('Z', 'Y').to_euler()
        cam.rotation_euler = rot_euler
        scene.render.filepath = str(script_dir / f"{image_prefix}_{angle_deg:03d}.png")  # 输出路径
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()