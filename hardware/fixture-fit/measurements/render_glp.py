"""Blender 4.5.13: orthographic review renders of the unmodified GLP mesh.
blender -b -t 4 --python hardware/fixture-fit/measurements/render_glp.py
"""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parent/'glp-x5'
data=json.loads((OUT/'view-mesh.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new('original coordinates, tessellation 0.4mm');mesh.from_pydata(data['vertices'],[],data['triangles']);mesh.update()
obj=bpy.data.objects.new('GLP manufacturer shell',mesh);bpy.context.collection.objects.link(obj)
mat=bpy.data.materials.new('source-shell');mat.diffuse_color=(0.52,0.6,0.68,1);obj.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(0.9,0.92,0.94)
scene.render.resolution_x=1500;scene.render.resolution_y=1500;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.clip_end=10000;scene.camera=cam
center=Vector((-38.02067630953,216.0551466599,0))
for label,normal,up,scale,target in [
 ('plus-x',(1,0,0),(0,1,0),620,center),('minus-x',(-1,0,0),(0,1,0),620,center),
 ('plus-z',(0,0,1),(0,1,0),620,center),('minus-z',(0,0,-1),(0,1,0),620,center),
 ('base-plus-x',(1,0,0),(0,1,0),240,Vector((0,10,0))),('base-minus-x',(-1,0,0),(0,1,0),240,Vector((0,10,0))),
 ('base-plus-z',(0,0,1),(0,1,0),220,Vector((0,-18,0))),('base-minus-z',(0,0,-1),(0,1,0),220,Vector((0,-18,0))),
 ('bottom',(0,-1,0),(0,0,1),500,Vector((0,0,0)))]:
    if (OUT/(label+'.png')).exists(): continue
    back=Vector(normal);up=Vector(up);right=up.cross(back).normalized();rot=Matrix((right,up,back)).transposed()
    cam.rotation_euler=rot.to_euler();cam.location=target+back*1500;cam.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
