import FreeCAD as A,Part,json
from pathlib import Path
P=Path(__file__).resolve().parent
old=A.openDocument(str(P.parent/'integrated25/integrated25.FCStd'));s={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')};A.closeDocument(old.Name)
d=A.openDocument(str(P/'protected25-attempt.FCStd'));o={x.Name:x.Shape for x in d.Objects if hasattr(x,'Shape')}
valid={n:q.isValid() and len(q.Solids)==1 and q.isClosed() for n,q in o.items()};assert all(valid.values()),valid
preserved=[]
for n,q in s.items():
 if n=='Base_integral_cradles':
  assert o[n].cut(q).Volume<1e-7
  removed=q.cut(o[n]);bb=removed.BoundBox
  assert bb.XMin>=54.6-1e-6 and bb.XMax<=58.4+1e-6 and bb.YMin>=37.4-1e-6 and bb.YMax<=44.6+1e-6 and bb.ZMin>=6.6-1e-6 and bb.ZMax<=7+1e-6
 else:assert q.cut(o[n]).Volume<1e-7 and o[n].cut(q).Volume<1e-7;preserved.append(n)
pairs=[];threads=[]
for i,(n,a) in enumerate(o.items()):
 for m,b in list(o.items())[i+1:]:
  common=a.common(b);v=common.Volume
  if v>1e-7:
   screw=n if n.startswith('M2x22_screw') else m if m.startswith('M2x22_screw') else None
   assert screw and 'Base_integral_cradles' in [n,m],(n,m,v)
   assert common.BoundBox.ZMin>=7-1e-6 and common.BoundBox.ZMax<=10+1e-6
   threads.append([n,m,v])
  pairs.append([n,m,v])
step=Part.Shape();step.read(str(P/'protected25-attempt.step'));assert len(step.Solids)==40 and all(x.isValid() and x.isClosed() for x in step.Solids)
out={'native_shapes':len(o),'valid':valid,'source_shapes_exactly_preserved':len(preserved),'base_difference_confined_to_relief':True,'full_pairs':len(pairs),'thread_engagements':threads,'unexpected_intersections':0,'STEP_closed_solids':len(step.Solids)}
(P/'reopen.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
