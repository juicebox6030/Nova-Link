import FreeCAD as A,Part,json,math,itertools
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector;D=A.openDocument(str(P/'integrated.FCStd'));G=json.loads((P/'groups.json').read_text());S={o.Name:o.Shape.copy() for o in D.Objects if hasattr(o,'Shape')}
def rot(s,a):s=s.copy();s.rotate(V(),V(1,0,0),a);return s
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
valid={n:{'valid':s.isValid(),'solids':len(s.Solids),'closed':all(q.isClosed() for q in s.Solids)} for n,s in S.items()};assert all(x['valid'] and x['solids']==1 and x['closed'] for x in valid.values()),valid
physical=[n for n in S if G[n] not in ['reserve','screen'] and not G[n].startswith('pose')]
old=json.loads((P.parent/'mechanism-repaired/checks.json').read_text());allowed={tuple(sorted(x['parts'])):x['max_mm3'] for x in old['allowed_thread_pairs']}
for n in physical:
 if n.startswith('BoardRetainerScrew'):allowed[tuple(sorted([n,'RotorHalfPositiveY']))]=.51
 if n.startswith('TailClampScrew'):allowed[tuple(sorted([n,'RotorHalfPositiveY']))]=.21
assert len(allowed)==14
cache={};rows=[];bad=[]
def state(n,a,released):
 s=S[n].copy()
 if G[n]=='rotor':s=rot(s,a)
 if G[n]=='pin' and released:s.translate(V(-4.2,0,0))
 if G[n]=='spring' and released:s=cyl(1.6,1.6,35,28.5,0).cut(cyl(1.4,1.62,34.99,28.5,0))
 return s
for a in [-90,0,90]:
 for released in [False,True]:
  print('POSE',a,released,flush=True)
  sh={n:state(n,a,released) for n in physical};sh['ActiveFlex']=S['Flex_'+str(a).replace('-','minus')]
  for an,bn in itertools.combinations(sh,2):
   ga,gb=G.get(an,'flex'),G.get(bn,'flex');ka=a;kr=released
   if ga==gb and ga in ['rotor','stationary']:ka=kr=None
   elif ga in ['stationary','pin','spring'] and gb in ['stationary','pin','spring']:ka=None
   key=(an,bn,ka,kr)
   if key not in cache:cache[key]=sh[an].common(sh[bn]).Volume if sh[an].BoundBox.intersect(sh[bn].BoundBox) else 0.
   vol=cache[key];limit=allowed.get(tuple(sorted([an,bn])),0)
   row={'angle':a,'released':released,'a':an,'b':bn,'intersection_mm3':vol,'thread_limit_mm3':limit};rows.append(row)
   if vol>max(1e-6,limit):bad.append(row)
  folder=P/('released' if released else 'locked');folder.mkdir(exist_ok=True);Part.makeCompound(list(sh.values())).exportStep(str(folder/('pose-'+str(a)+'.step')))
(P/'checks.json').write_text(json.dumps({'status':'PASS' if not bad else 'FAIL','physical_parts_without_active':len(physical),'native_parts':len(S),'valid':valid,'pairs':rows,'residual':bad,'allowed_threads':[{'parts':list(k),'max_mm3':v} for k,v in allowed.items()]},indent=2)+'\n')
print('PAIRS',len(rows),'RESIDUAL',json.dumps(bad),flush=True)
parts=[]
for n in physical:
 s=S[n].copy();dx=dy=0
 if n=='RotorHalfPositiveY':dy=25
 elif n=='RotorHalfNegativeY':dy=-20
 elif n.startswith('SRC_') or n in ['StaticDevelopedFanout','TailClampShoe','BoardEndRetainer'] or n.startswith(('BoardRetainerScrew','TailClampScrew')):dx=25
 elif G[n] in ['pin','spring'] or n=='IndexRearCap':dx=-15
 s.translate(V(dx,dy,0));parts.append(s)
Part.makeCompound(parts).exportStep(str(P/'exploded.step'));Part.makeCompound([s for n,s in S.items() if G[n]=='reserve']).exportStep(str(P/'assembly-reserves.step'))
assert not bad,'Unintended interference'
A.closeDocument(D.Name)
