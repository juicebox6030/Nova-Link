"""Reopen final native and every delivered STEP; do not mutate the CAD."""
import FreeCAD as A,Part,json,hashlib,os
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector;F=P/'integrated.FCStd';h=hashlib.sha256(F.read_bytes()).hexdigest();D=A.openDocument(str(F));rows=[]
for o in D.Objects:
 if hasattr(o,'Shape'):
  s=o.Shape;row={'name':o.Name,'valid':s.isValid(),'solids':len(s.Solids),'closed':all(x.isClosed() for x in s.Solids),'volume_mm3':s.Volume};rows.append(row);assert row['valid'] and row['closed'] and row['solids']==1,o.Name
assert len(rows)==86
threads=[]
for r in json.loads((P/'checks.json').read_text())['allowed_threads']:
 a,b=r['parts'];s=D.getObject(a).Shape.common(D.getObject(b).Shape);bb=s.BoundBox;assert 0<s.Volume<=r['max_mm3']+1e-6
 if a.startswith('BoardRetainer') or b.startswith('BoardRetainer'):assert bb.XMin>=100.4999 and bb.XMax<=102.0001
 elif a.startswith('TailClamp') or b.startswith('TailClamp'):assert bb.YMin>=25.7999 and bb.YMax<=26.4001
 elif 'FrameBolt' in a or 'FrameBolt' in b:assert bb.YMin>=-3.00001 and bb.YMax<=.00001
 elif 'IndexKnob' in [a,b]:assert bb.XMin>=31.69999 and bb.XMax<=32.50001
 elif 'IndexRearCap' in [a,b]:assert bb.XMin>=33.99999 and bb.XMax<=35.00001
 else:
  lo,hi=(24.1,24.7) if any('FixedScrew' in x for x in [a,b]) else (30.8,31.6)
  assert s.common(Part.makeCylinder(lo,142,V(),V(1,0,0))).Volume<1e-6 and s.cut(Part.makeCylinder(hi,142,V(),V(1,0,0))).Volume<1e-6
 threads.append({'parts':[a,b],'volume_mm3':s.Volume,'region_check':True})
A.closeDocument(D.Name);assert hashlib.sha256(F.read_bytes()).hexdigest()==h
steps=[]
paths=sorted(P.glob('locked/*.step'))+sorted(P.glob('released/*.step'))+[P/'exploded.step',P/'assembly-reserves.step']
assert len(paths)==8
group=os.environ.get('REOPEN_GROUP')
if group is not None:paths=paths[int(group)::3]
for p in paths:
 print('REOPEN STEP',p.relative_to(P),flush=True);s=Part.read(str(p));expected=5 if p.name=='assembly-reserves.step' else 77 if p.name=='exploded.step' else 78
 assert len(s.Solids)==expected,(p,len(s.Solids));assert all(q.isValid() and q.isClosed() for q in s.Solids),p
 steps.append({'file':str(p.relative_to(P)),'solids':len(s.Solids),'each_valid_closed':True})
(P/('reopen.json' if group is None else 'reopen-part-'+group+'.json')).write_text(json.dumps({'status':'PASS','native_sha256':h,'native':rows,'bounded_thread_regions':threads,'STEP':steps},indent=2)+'\n');print('REOPEN PASS',len(rows),'native;',len(steps),'STEP;',len(threads),'thread regions',flush=True)
