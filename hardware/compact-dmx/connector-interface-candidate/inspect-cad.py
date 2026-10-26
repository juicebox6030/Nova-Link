"""Run using existing FreeCADCmd. Inspect unmodified manufacturer STEP geometry.
Face IDs are stable only for these source hashes and this OCCT import version.
No panel/mating datums are inferred by this automated inventory.
"""
import FreeCAD as App, Part, json, hashlib, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES={'pc-in':'NAC3MPXXA','pc-out':'NAC3MPXXB','true1-in':'NAC3MPX-TOP','true1-out':'NAC3FPX-TOP','nema-in':'5278-C','nema-out':'5279-C','pc-mate-a':'NAC3FXXA-W-S','pc-mate-b':'NAC3FXXB-W-S','true1-mate-f':'NAC3FX-W-TOP','true1-mate-m':'NAC3MX-W-TOP','nema-mate-f':'5269-C','nema-mate-m':'5266-C'}
report={'FreeCAD':App.Version(),'units':'mm after STEP unit import','items':{}}
doc=App.newDocument('ManufacturerInterfaceInspection')
def box(b):return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
for i,(stem,pn) in enumerate(NAMES.items()):
 f=ROOT/'sources'/(stem+'.step');src=f.read_text(errors='replace')
 shape=Part.read(str(f))
 o=doc.addObject('Part::Feature',stem.replace('-','_'));o.Label=pn+' — unmodified vendor geometry';o.Shape=shape
 o.addProperty('App::PropertyString','SourceFile').SourceFile='sources/'+f.name
 o.addProperty('App::PropertyString','SourceSHA256').SourceSHA256=hashlib.sha256(f.read_bytes()).hexdigest()
 o.addProperty('App::PropertyString','DatumWarning').DatumWarning='Local vendor coordinates. See contracts.json for independently read drawing datums; not a mated assembly.'
 faces=[]
 for n,face in enumerate(shape.Faces,1):
  surf=face.Surface;typ=type(surf).__name__;entry={'id':'Face'+str(n),'surface':typ,'bbox_mm':box(face.BoundBox),'area_mm2':face.Area,'center_mm':list(face.CenterOfMass)}
  if typ=='Plane':entry.update(position=list(surf.Position),axis=list(surf.Axis))
  elif typ in ['Cylinder','Cone']:entry.update(position=list(surf.Center),axis=list(surf.Axis),radius_mm=getattr(surf,'Radius',None))
  faces.append(entry)
 report['items'][stem]={'part':pn,'source_sha256':o.SourceSHA256,'step_header':src[:src.index('DATA;')].strip(),'unit_entities_first_6':re.findall(r'#\d+\s*=\s*\([^;]*(?:SI_UNIT|CONVERSION_BASED_UNIT)[^;]*;',src)[:6], 'conversion_inch_count':src.count("'INCH'"), 'declares_millimetres':bool(re.search(r'SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)',src)),'valid':shape.isValid(),'solids':len(shape.Solids),'shells':len(shape.Shells),'bbox_mm':box(shape.BoundBox),'face_count':len(faces),'faces':sorted([x for x in faces if x['surface']=='Plane'],key=lambda x:-x['area_mm2'])[:12]}
 (ROOT/'sources'/(stem+'-all-faces.json')).write_text(json.dumps(faces,indent=2)+'\n')
 # Local orthographic projections of actual edges; coordinate axes labelled in SVG wrappers.
 import TechDraw
 axis={'pc-in':2,'pc-out':2,'true1-in':1,'true1-out':2,'nema-in':0,'nema-out':0}.get(stem,max(range(3),key=lambda j:shape.BoundBox.XLength if j==0 else shape.BoundBox.YLength if j==1 else shape.BoundBox.ZLength))
 vec=[App.Vector(1,0,0),App.Vector(0,1,0),App.Vector(0,0,1)]
 report['items'][stem]['projection_axis_index']=axis
 verts,tri=shape.tessellate(0.03)
 report['items'][stem]['sampled_mesh_bbox_mm']=[min(v[j] for v in verts) for j in range(3)]+[max(v[j] for v in verts) for j in range(3)]
 report['items'][stem]['mesh_warning']='0.03 mm tessellation sample only; no dimensional tolerance or certified maximum'
 report['items'][stem]['sampled_radial_diameter_mm']=2*max(sum(v[j]**2 for j in range(3) if j!=axis)**0.5 for v in verts)
 for view,direction,labels in [('front',vec[axis],'vendor transverse axes'),('side',vec[(axis+2)%3],'vendor axial and transverse axes')]:
  svg=TechDraw.projectToSVG(shape,direction)
  title=pn+' / '+view+' / vendor coordinates / NOT a mated assembly'
  wrapper='<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="110mm" viewBox="-90 -55 180 110"><title>'+title+'</title><rect x="-90" y="-55" width="180" height="110" fill="white"/><text x="-86" y="-49" font-family="sans-serif" font-size="3">'+title+'</text>'+svg.replace('stroke-width="1.0"','stroke-width="0.18"')+'</svg>'
  (ROOT/'views'/(stem+'-'+view+'-edges.svg')).write_text(wrapper)
 print(stem,shape.isValid(),len(shape.Solids),box(shape.BoundBox))
doc.recompute();doc.saveAs(str(ROOT/'sources'/'manufacturer-models.FCStd'))
(ROOT/'cad-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print('Saved 6 candidate + 6 mating-reference models; no assembly fit inferred.')
