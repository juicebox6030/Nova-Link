import FreeCAD as A,Part,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector
old=A.openDocument(str(P.parent/'integrated25/integrated25.FCStd'));d=A.newDocument('Protected25Attempt');objs={}
for o in old.Objects:
 if hasattr(o,'Shape'):
  n=d.addObject('PartDesign::Feature',o.Name);n.Shape=o.Shape.copy();objs[n.Name]=n
A.closeDocument(old.Name)
# One local engineering relief in copied base only; external surface z5 retained.
original_base=objs['Base_integral_cradles'].Shape.copy()
relief=Part.makeBox(3.8,7.2,.4,V(54.6,37.4,6.6))
objs['Base_integral_cradles'].Shape=original_base.cut(relief).removeSplitter()
objs['Base_integral_cradles'].addProperty('App::PropertyString','LocalChange')
objs['Base_integral_cradles'].LocalChange='Engineering fuse relief x54.6..58.4 y37.4..44.6 z6.6..7; floor1.6mm; strength/process unqualified'
new={};placement=json.loads((P/'placement.json').read_text())
for p in placement['added']:
 w,h=p['body'];w,h=(h,w) if p['angle']%180==90 else (w,h);z=10-p['height'] if p['side']=='B' else 11
 o=d.addObject('PartDesign::Feature',p['ref']+'_maxbody');o.Shape=Part.makeBox(w,h,p['height'],V(p['x']-w/2,p['y']-h/2,z));o.addProperty('App::PropertyString','Evidence');o.Evidence='Manufacturer maximum body from frozen land-sources.json; geometric allocation, not supplier 3D';new[p['ref']]=o
checks=[]
for ref,o in new.items():
 for name,z in objs.items():checks.append({'a':ref,'b':name,'volume':o.Shape.common(z.Shape).Volume,'gap':o.Shape.distToShape(z.Shape)[0]})
 for other,z in new.items():
  if ref<other:checks.append({'a':ref,'b':other,'volume':o.Shape.common(z.Shape).Volume,'gap':o.Shape.distToShape(z.Shape)[0]})
# Every new body against conservative old component courtyard envelopes, including both sides.
oldpart_checks=[]
for q in json.loads((P/'baseline-board.json').read_text()):
 if q['ref'] in ['C23','J1'] or q['ref'].startswith('H'):continue
 x,y,x2,y2=q['bounds']
 if x2<=x or y2<=y:continue
 z,h=(11,2.23) if q['side']=='F' else (8.55,1.45)
 shape=Part.makeBox(x2-x,y2-y,h,V(x,y,z))
 for ref,o in new.items():oldpart_checks.append({'new':ref,'existing':q['ref'],'volume':o.Shape.common(shape).Volume})
fuse=new['F101'].Shape;base=objs['Base_integral_cradles'].Shape
worst=fuse.copy();worst.translate(V(0,0,-.2))
bb=fuse.BoundBox;allocated=Part.makeBox(bb.XLength+.5,bb.YLength+.5,bb.ZLength,V(bb.XMin-.25,bb.YMin-.25,bb.ZMin-.2))
# .20 is an allocated board/support/body-process clearance screen, not supplier tolerance.
out={'allocated_XY_0_25_down_0_20_base_overlap':allocated.common(base).Volume,'allocated_XY_0_25_down_0_20_base_gap':allocated.distToShape(base)[0],'existing_courtyard_volume_checks':oldpart_checks,'existing_component_collisions':[x for x in oldpart_checks if x['volume']>1e-7],'nominal_pairs':checks,'nominal_intersections':[x for x in checks if x['volume']>1e-7],'fuse_to_base_nominal_gap':fuse.distToShape(base)[0],'fuse_minus_0_20mm_base_overlap':worst.common(base).Volume,'fuse_bottom_z':fuse.BoundBox.ZMin,'allocated_min_gap_mm':.2,'height_acceptance':'Conditional nominal and .20mm downward allocation clear after local .40mm relief; material/process strength not qualified','original_base_gap':fuse.distToShape(original_base)[0],'relief_bounds':[54.6,58.4,37.4,44.6,6.6,7],'remaining_floor_mm':1.6,'source_objects':len(objs),'new_bodies':len(new),'valid':{o.Name:o.Shape.isValid() and len(o.Shape.Solids)==1 and o.Shape.isClosed() for o in list(objs.values())+list(new.values())}}
d.recompute();d.saveAs(str(P/'protected25-attempt.FCStd'));Part.export(list(objs.values())+list(new.values()),str(P/'protected25-attempt.step'))
(P/'mechanics-check.json').write_text(json.dumps(out,indent=2)+'\n');print('PAIR',len(checks),'COLLISIONS',out['nominal_intersections'],'FUSE GAP',out['fuse_to_base_nominal_gap'],'WORST OVERLAP',out['fuse_minus_0_20mm_base_overlap'])
