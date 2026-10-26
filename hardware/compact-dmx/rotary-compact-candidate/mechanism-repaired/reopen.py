"""Reopen native and STEP artifacts; independently bound intentional thread interfaces."""
import FreeCAD as A,Part,json,os
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']);D=A.openDocument(str(P/'mechanism.FCStd'));print('NATIVE OPEN',flush=True)
# Metadata correction only: parent frozen source uses default .95 stake USB4105-GF-A.
D.getObject('Parameters').set('A11','GCT nominal stake');D.getObject('Parameters').set('B11','0.95')
D.getObject('USB4105ShellEnvelope').Qualification='USB4105-GF-A B4 maximum envelope9.09x7.65x3.46; axial source layout PLACEHOLDER'
for name in ['FixedScrew0','FixedScrew1','MovingScrew0','MovingScrew1']:D.getObject(name).Qualification='M1 prototype envelope;0.4mm nominal engagement; strip/preload not qualified'
D.recompute();D.save()
rows=[]
for o in D.Objects:
 if hasattr(o,'Shape'):
  print('CHECK NATIVE',o.Name,flush=True)
  s=o.Shape;rows.append({'name':o.Name,'valid':s.isValid(),'solids':len(s.Solids),'closed':all(q.isClosed() for q in s.Solids),'volume_mm3':s.Volume})
assert len(rows)==43 and all(r['valid'] and r['solids']==1 and r['closed'] for r in rows)
old=json.loads((P/'validity.json').read_text())
assert all(abs(r['volume_mm3']-old[r['name']]['volume'])<1e-7 for r in rows)
threads=[]
for pair in json.loads((P/'checks.json').read_text())['allowed_thread_pairs']:
 a,b=pair['parts'];print('CHECK THREAD',a,b,flush=True);c=D.getObject(a).Shape.common(D.getObject(b).Shape);bb=c.BoundBox
 assert c.Volume<=pair['max_mm3']+1e-6 and c.Volume>0
 if 'FrameBolt' in a or 'FrameBolt' in b:assert bb.YMin>=-3.00001 and bb.YMax<=.00001
 elif 'IndexKnob' in [a,b]:assert bb.XMin>=31.69999 and bb.XMax<=32.50001
 elif 'IndexRearCap' in [a,b]:assert bb.XMin>=33.99999 and bb.XMax<=35.00001
 else:
  fixed=any('FixedScrew' in x for x in [a,b]);rlo,rhi=(24.1,24.7) if fixed else (30.8,31.6)
  # Volumetric cylindrical bounds, independent of vertex sampling.
  axis=A.Vector(1,0,0)
  assert c.common(Part.makeCylinder(rlo,142,A.Vector(),axis)).Volume<1e-6
  assert c.cut(Part.makeCylinder(rhi,142,A.Vector(),axis)).Volume<1e-6
 threads.append({'parts':[a,b],'volume_mm3':c.Volume,'bounded_region_check':True})
A.closeDocument(D.Name)
steps=[]
for p in sorted(P.glob('*/*.step'))+list(P.glob('exploded.step')):
 print('READ STEP',str(p.relative_to(P)),flush=True)
 s=Part.read(str(p));expected=38 if p.name=='exploded.step' else 39
 assert len(s.Solids)==expected,(p,len(s.Solids))
 assert all(q.isValid() and q.isClosed() for q in s.Solids),str(p)
 steps.append({'path':str(p.relative_to(P)),'solids':len(s.Solids),'each_solid_valid_closed':True})
(P/'reopen.json').write_text(json.dumps({'status':'PASS','native':rows,'thread_regions':threads,'STEP':steps},indent=2)+'\n')
print('REOPEN',len(rows),'native parts;',len(steps),'STEP files;',len(threads),'specific thread regions PASS')
