from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;D=A.newDocument('WireProbe');O={};G={};notes={}
s=(P/'build.py').read_text();exec(s[s.index('def box'):s.index('old=A.openDocument')]);exec(s[s.index('def rounded'):s.index('for zone,b in boards.items():')])
old=A.openDocument(str(P/'interface-prototype.FCStd'));add('Core',old.getObject('StationaryCoreWithSupports').Shape.copy(),'fixed')
a=(P/'attachments.py').read_text();exec(a[a.index('# Real source wires'):])
for n,o in O.items():
 for m,p in O.items():
  if m<=n:continue
  if not o.Shape.BoundBox.intersect(p.Shape.BoundBox):continue
  v=o.Shape.common(p.Shape).Volume
  if v>1e-7:print('COLLISION',n,m,v,str(o.Shape.common(p.Shape).BoundBox),flush=True)
D.recompute();D.saveAs(str(P/'wire-probe.FCStd'))
