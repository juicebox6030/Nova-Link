"""Inspect frozen supplier faces and meridian contours, never manufacture a mating transform."""
from pathlib import Path
import FreeCAD as App,Part,json,hashlib,math
ROOT=Path(__file__).resolve().parent; OLD=ROOT.parent/'connector-interface-candidate'
source=App.openDocument(str(OLD/'sources/manufacturer-models.FCStd'))
keys=['pc-in','pc-mate-a','pc-out','pc-mate-b','true1-in','true1-mate-f','true1-out','true1-mate-m']
axes={'pc-in':(2,1),'pc-out':(2,1),'pc-mate-a':(2,1),'pc-mate-b':(2,1),'true1-in':(1,1),'true1-out':(2,1),'true1-mate-f':(1,1),'true1-mate-m':(0,-1)}
planes={'pc-in':[337,466,365,368,560,460],'pc-mate-a':[2435,2432,2615,247,244,255],'pc-out':[620,4,680,126],'pc-mate-b':[2413,2410,2593,247,244,255],'true1-in':[203,195,88,178],'true1-mate-f':[1,499,2225,2223,497],'true1-out':[416,516,18,105],'true1-mate-m':[326,1386,1267,2001,2000,410]}
out=App.newDocument('UnplacedSupplierReferences')
report={'FreeCAD':App.Version(),'purpose':'Independent unplaced source face/section atlas. Not a placed or latched assembly.','items':{}}
for key in keys:
 obj=source.getObject(key.replace('-','_'));shape=obj.Shape.copy();ax,sign=axes[key];trans=[i for i in range(3) if i!=ax]
 ref=out.addObject('Part::Feature',key.replace('-','_'));ref.Label=key+' — UNPLACED original coordinates';ref.Shape=shape
 ref.addProperty('App::PropertyString','OriginalSHA256').OriginalSHA256=obj.SourceSHA256
 ref.addProperty('App::PropertyString','SourceFile').SourceFile=str(OLD/'sources'/(key+'.step'))
 data={'source_sha256':obj.SourceSHA256,'source_axis_index':ax,'source_outward_sign':sign,'valid':shape.isValid(),'solids':len(shape.Solids),'selected_planes':[],'coaxial_cylinders':[],'meridian_contours':{}}
 for n in planes[key]:
  f=shape.Faces[n-1];u,v=(sum(f.ParameterRange[:2])/2,sum(f.ParameterRange[2:])/2)
  e={'id':'Face'+str(n),'surface':type(f.Surface).__name__,'area_mm2':f.Area,'center_mm':list(f.CenterOfMass),'bbox_mm':[f.BoundBox.XMin,f.BoundBox.YMin,f.BoundBox.ZMin,f.BoundBox.XMax,f.BoundBox.YMax,f.BoundBox.ZMax],'surface_axis':list(f.Surface.Axis),'surface_position_mm':list(f.Surface.Position),'oriented_normal':list(f.normalAt(u,v)),'valid_face':f.isValid(),'boundary_curves':[{'kind':type(e.Curve).__name__,'radius_mm':getattr(e.Curve,'Radius',None)} for e in f.Edges]}
  data['selected_planes'].append(e)
 for n,f in enumerate(shape.Faces,1):
  sf=f.Surface
  if type(sf).__name__=='Cylinder' and abs(sf.Axis[ax])>.9999 and sum(sf.Center[i]**2 for i in trans)<1e-8:
   data['coaxial_cylinders'].append({'id':'Face'+str(n),'radius_mm':sf.Radius,'axis':list(sf.Axis),'center_mm':list(sf.Center),'axial_bounds_mm':[f.BoundBox.XMin,f.BoundBox.YMin,f.BoundBox.ZMin][ax:ax+1]+[f.BoundBox.XMax,f.BoundBox.YMax,f.BoundBox.ZMax][ax:ax+1]})
 for t in trans:
  normal=[0,0,0];normal[t]=1;normal=App.Vector(*normal)
  plane=Part.makePlane(250,250,App.Vector(0,0,0),normal)
  # Infinite geometric Plane through the source origin; finite plane centered from oriented frame.
  pl=Part.Plane(App.Vector(0,0,0),normal);face=pl.toShape(-125,125,-125,125)
  section=shape.section(face)
  radial=next(i for i in trans if i!=t)
  data['meridian_contours']['normal_axis_'+str(t)]={'radial_axis_index':radial,'polylines':[[[sign*p[ax],p[radial]] for p in e.discretize(Deflection=.03)] for e in section.Edges]}
 report['items'][key]=data
 print('inspected',key,'planes',len(data['selected_planes']),'coaxial faces',len(data['coaxial_cylinders']))
# Pair-specific rejected-stop probes: local source planes only, no mating contact or placement claim.
# Faces whose source axial coordinates are equal are translated into a common analytical plane
# to test radial area overlap. This cannot establish final locked geometry.
probes=[]
a=source.getObject('pc_in').Shape;b=source.getObject('pc_mate_a').Shape
for ia,ib in [(337,2435),(466,247),(466,244),(560,2435)]:
 f=a.Faces[ia-1].copy();g=b.Faces[ib-1].copy();dz=f.Surface.Position.z-g.Surface.Position.z;g.translate(App.Vector(0,0,dz))
 common=f.common(g)
 probes.append({'chassis':'pc-in','chassis_face':'Face'+str(ia),'mate':'pc-mate-a','mate_face':'Face'+str(ib),'analytical_plane_coincidence_translation_z_mm':dz,'coplanar_radial_overlap_area_mm2':common.Area,'selected_as_mating_stop':False,'warning':'Isolated planar test at source angular orientation; not a full assembled transform or certified seating datum.'})
report['rejected_stop_probes']=probes
out.recompute();out.saveAs(str(ROOT/'sources/unplaced-references.FCStd'))
(ROOT/'sources/meridian-contours.json').write_text(json.dumps({k:d.pop('meridian_contours') for k,d in report['items'].items()},indent=2)+'\n')
(ROOT/'datum-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print('Saved unplaced references only; no mating transform exported.')
