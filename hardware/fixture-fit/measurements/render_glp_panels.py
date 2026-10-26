"""Render isolated analytic-feature faces, deliberately excluding covering surfaces.
blender -b -t 4 --python hardware/fixture-fit/measurements/render_glp_panels.py
This is a selective view, not an installed assembly or clearance overlay.
"""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parent/'glp-x5'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
keep={215,216,243,244,247,248,249,250,253,254,257,258,259,260}
for data in json.loads((OUT/'selected-panels-mesh.json').read_text()):
    if data['face'] not in keep:continue
    mesh=bpy.data.meshes.new('face'+str(data['face']));mesh.from_pydata(data['vertices'],[],data['triangles']);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new(mesh.name);mat.diffuse_color=(.15,.55,.65,1) if data['face'] in [215,216] else (.9,.42,.13,1);obj.data.materials.append(mat)
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD';s.world.color=(.94,.94,.94)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.location=(0,-17.75,1000);cam.rotation_euler=(0,0,0);cam.data.type='ORTHO';cam.data.ortho_scale=142;s.camera=cam
s.render.resolution_x=1700;s.render.resolution_y=650;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(OUT/'selected-paired-panels.png');bpy.ops.render.render(write_still=True)
