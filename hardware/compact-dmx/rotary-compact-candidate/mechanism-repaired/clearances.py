"""Independent distances from saved final solids; no generator dimensions imported."""
import FreeCAD as A,Part,json,os,math
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']);D=A.openDocument(str(P/'mechanism.FCStd'));S={o.Name:o.Shape for o in D.Objects if hasattr(o,'Shape')}
queries=[('FixedStiffener','StationarySpool',.055),('MovingStiffener','RotorHalfPositiveY',.055),('StationaryCoreEnvelope','StationarySpool',.0999),('FixedScrew0','StationaryCoreEnvelope',.1999),('FixedScrew1','StationaryCoreEnvelope',.1999),('Components_TARGET','RotorHalfPositiveY',.95)]
for n in list(S):
 if n.startswith('FrameBolt'):
  # Head bottom intentionally seats atY3. Measure radial clearance on an interior
  # head slice, avoiding that real bearing-contact plane rather than exempting overlap.
  S[n+'_HeadInterior']=S[n].common(Part.makeBox(142,.20,80,A.Vector(0,3.05,-40)))
  queries.append((n+'_HeadInterior','RotorHalfPositiveY',.0499))
rows=[]
for a,b,minimum in queries:
 d=S[a].distToShape(S[b])[0];assert d>=minimum,(a,b,d,minimum);rows.append({'a':a,'b':b,'distance_mm':d,'minimum_screen_mm':minimum})
for n in ['RotorHalfPositiveY','RotorHalfNegativeY','StationarySpool']:assert len(S[n].Solids)==1
# Integral hard-stop stub is part of the connected negative rotor, not a loose touching pin.
stub=Part.makeCylinder(1,1,A.Vector(72.5,-28.5,0),A.Vector(1,0,0))
v=S['RotorHalfNegativeY'].common(stub).Volume;assert abs(v-math.pi)<1e-6
pcb=S['PowerBoard_TARGET'].BoundBox;usb=S['USB4105ShellEnvelope'].BoundBox
assert all(abs(a-b)<1e-8 for a,b in zip([pcb.XLength,pcb.YLength,pcb.ZLength],[25,1,18]))
assert all(abs(a-b)<1e-8 for a,b in zip([usb.XLength,usb.YLength,usb.ZLength],[7.65,3.46,9.09]))
assert all(abs(pcb.YMin-S['USBStake'+str(i)].BoundBox.YMin-.2)<1e-8 for i in range(4))
(P/'clearances.json').write_text(json.dumps({'status':'PASS','distances':rows,'integral_stop_stub_volume_mm3':v,'source_placeholder_dimensions_verified':True,'note':'Exact saved-solid distances at nominal axial datum; physical tolerances/load equilibrium remain qualified separately'},indent=2)+'\n')
print('SAVED CLEARANCES PASS',len(rows),flush=True);A.closeDocument(D.Name)
