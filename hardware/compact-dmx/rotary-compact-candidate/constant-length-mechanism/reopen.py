"""Independent saved-document validity/solid closure check, not assembly acceptance."""
import FreeCAD as A,json,os
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']);D=A.openDocument(str(P/'mechanism.FCStd'))
rows=[]
for o in D.Objects:
 if hasattr(o,'Shape'):
  rows.append({'name':o.Name,'valid':o.Shape.isValid(),'solid_count':len(o.Shape.Solids),'closed_solids':all(s.isClosed() for s in o.Shape.Solids),'volume_mm3':o.Shape.Volume})
assert len(rows)==40 and all(r['valid'] and r['closed_solids'] and r['solid_count']>0 for r in rows)
b=D.getObject('PowerBoard_TARGET').Shape.BoundBox
assert abs(b.XMin-73.8)<1e-8 and abs(b.XMax-98.8)<1e-8
res={'status':'SAVED BREP VALIDITY ONLY PASS; known assembly failures retained','rows':rows,'solid_total':sum(r['solid_count'] for r in rows),'target_board_x_mm':[b.XMin,b.XMax]}
(P/'reopen-checks.json').write_text(json.dumps(res,indent=2)+'\n');print('SAVED',len(rows),'objects',res['solid_total'],'closed solids')
A.closeDocument(D.Name)
