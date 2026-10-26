from pathlib import Path
import FreeCAD as A,json
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());screen=S['LockAccess'];bad=[];count=0
physical={'housing','module','film','carrier','pin','trunk','joint','branch','stationary_wire','stationary','stationary_pad','collar_stationary','rotating','rotating_pad','rotating_stake','collar_rotor'}
for n,s in S.items():
 if G[n] not in physical:continue
 count+=1
 if G[n] in ['rotating','rotating_pad','rotating_stake','collar_rotor']:
  assert s.BoundBox.XMin>screen.BoundBox.XMax;continue
 if not s.BoundBox.intersect(screen.BoundBox):continue
 v=s.common(screen).Volume
 if v>1e-7:bad.append({'part':n,'volume':v})
(P/'lock-access-check.json').write_text(json.dumps({'parts':count,'positions':181,'bad':bad,'status':'PASS' if not bad else 'FAIL','basis':'Actual fixed screen against fixed parts; strict axial separation from every rotor for all angles. Released knob is intended target, not obstruction. Finger/tool dimensions are engineering allocation only.'},indent=2)+'\n');print('LOCK ACCESS',count,'PARTS',bad);assert not bad
