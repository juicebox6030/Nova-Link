"""Actual tool cylinders against saved parts, with explicit assembly stages."""
import FreeCAD as A,Part,math,json,os
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector;D=A.openDocument(str(P/'integrated.FCStd'))
G=json.loads((P/'groups.json').read_text());S={o.Name:o.Shape.copy() for o in D.Objects if hasattr(o,'Shape')};tools=[]
for x in [45.25,68.9]:
 for z in [-29.5,29.5]:tools.append((f'FrameDriver{x}_{z}',Part.makeCylinder(.6,31.69,V(x,3.31,z),V(0,1,0)),'assembled'))
for x in [45.75,68.25]:
 a=-.15;tools.append((f'FixedEarDriver{x}',Part.makeCylinder(.6,10.19,V(x,25.81*math.cos(a),25.81*math.sin(a)),V(0,math.cos(a),math.sin(a))),'stationary_before_rotor'))
 a=.15;tools.append((f'MovingEarDriver{x}',Part.makeCylinder(.6,5.69,V(x,24*math.cos(a),24*math.sin(a)),V(0,math.cos(a),math.sin(a))),'rotor_before_core'))
for z in [-2.6,2.6]:tools.append((f'CapSpanner{z}',Part.makeCylinder(.2,3.79,V(30,28.5,z),V(1,0,0)),'assembled'))
tools.append(('KnobSlotDriver',Part.makeBox(1.29,1.6,.5,V(30,27.7,-.25)),'assembled'))
for z in [-11,11]:tools.append((f'BoardRetainerDriver{z}',Part.makeCylinder(.6,12,V(103.41,25.65,z),V(1,0,0)),'assembled'))
for x in [74.4,96.6]:tools.append((f'TailClampDriver{x}',Part.makeCylinder(.6,12,V(x,27.81,-13),V(0,1,0)),'assembled'))
# Tool above solder tongue; target contact begins below this screen.
tools.append(('FPCSolderAccess',Part.makeBox(20.5,12,2,V(75.25,26.57,-9.4)),'assembled'))
rows=[]
for name,t,stage in tools:
 for n,s in S.items():
  g=G[n]
  if g.startswith('pose') or g in ['screen','placeholder','reserve']:continue
  if stage=='stationary_before_rotor' and g=='rotor':continue
  if stage=='rotor_before_core' and g!='rotor':continue
  vol=t.common(s).Volume if t.BoundBox.intersect(s.BoundBox) else 0.
  rows.append({'tool':name,'stage':stage,'part':n,'intersection_mm3':vol})
res={'status':'PASS' if all(r['intersection_mm3']<1e-6 for r in rows) else 'FAIL','checks':rows,'tool_diameter_mm':1.2,'cap_spanner_pin_diameter_mm':.4,'assembly_stage_limits':['Fixed ears assembled before rotor installation','Moving ears assembled on rotor half before insertion around core','Frame bores and cap spanner accessible on assembled neutral mechanism']}
(P/'access.json').write_text(json.dumps(res,indent=2)+'\n');print('TOOLS',len(tools),'PAIRS',len(rows),'RESIDUAL',[r for r in rows if r['intersection_mm3']>=1e-6])
A.closeDocument(D.Name)
