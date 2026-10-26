from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text())
def rot(s,a):
 q=s.copy();q.rotate(V(),V(1,0,0),a);return q
# Independent stop and lock checks on actual saved mechanism regions.
track=S['COL_StationarySpool'].common(Part.makeBox(1.4,70,70,V(49.6,-35,-35)))
peg=Part.makeCylinder(1,1.3,V(49.7,-28.5,0),V(1,0,0));assert abs(S['RotorHalfNegativeY'].common(peg).Volume-peg.Volume)<1e-6
stops=[]
for angle in range(-90,91):
 q=rot(peg,angle);vol=q.common(track).Volume;stops.append({'angle':angle,'volume':vol});assert vol<1e-7,(angle,vol)
stop_beyond={str(a):rot(peg,a).common(track).Volume for a in [-90.5,90.5]};assert min(stop_beyond.values())>1e-5
print('STOPS181 PASS',stop_beyond,flush=True)
locks=[]
for angle in range(-90,91,15):
 vols=[rot(S[n],angle).common(S['COL_IndexPin']).Volume for n in ['RotorHalfPositiveY','RotorHalfNegativeY']];assert max(vols)<1e-7,(angle,vols);locks.append({'angle':angle,'volumes':vols})
print('LOCKS13 PASS',flush=True)
# Changed wires, boards, static copper/clamps against complete actual rotating parts.
# Body/pad/self-relative contacts are checked separately at neutral; their transforms are rigid.
rotors=[n for n in S if G[n] in ['rotating','rotating_pad','rotating_stake','collar_rotor']]
statics=[n for n in S if G[n] in ['housing','module','film','carrier','pin','trunk','joint','branch','stationary_wire','stationary','stationary_pad','collar_stationary']]
# Certified axisymmetric envelopes: exact Boolean containment, never vertex-only radii.
def cyl(r,x0,x1):return Part.makeCylinder(r,x1-x0,V(x0,0,0),V(1,0,0))
# Only X>=19.19 can meet a rotor (actual minimum19.2); retain the full wires in native/access checks.
assert min(S[n].BoundBox.XMin for n in rotors)>19.19
for n in ['Trunk_L','Trunk_N','Trunk_PE']:
 S[n]=S[n].common(Part.makeBox(200,200,200,V(19.19,-100,-100)))
cert={};proofs=[]
for n in rotors+statics:
 s=S[n];b=s.BoundBox;x0=b.XMin-.001;x1=b.XMax+.001
 # conservative bbox radial bounds; tighten only with checked cylinders.
 rlo=math.hypot(max(0,b.YMin,-b.YMax),max(0,b.ZMin,-b.ZMax));rhi=max(math.hypot(y,z) for y in [b.YMin,b.YMax] for z in [b.ZMin,b.ZMax])
 if n.startswith('Trunk_'):
  assert s.cut(cyl(21,x0,x1)).Volume<1e-7;rhi=21
 if n.startswith('SourceWire'):
  assert s.cut(cyl(24,x0,x1)).Volume<1e-7;rhi=24
 if n=='COL_StationarySpool':
  assert s.cut(cyl(31.6,x0,x1)).Volume<1e-7;rhi=31.6
 if n.startswith('COL_CoreBond'):
  assert s.cut(cyl(24.1,x0,x1)).Volume<1e-7;rhi=24.1
 if n=='StationaryCoreWithSupports':
  assert s.cut(cyl(24,x0,x1)).Volume<1e-7;rhi=24
 if n in ['RotorHalfPositiveY','RotorHalfNegativeY']:
  assert s.common(cyl(24.29,x0,x1)).Volume<1e-7;rlo=24.29
 if n.startswith(('FixedFanout','FixedTail','COL_Fixed')):
  for r in [25.1,25.6,26]:
   if s.cut(cyl(r,x0,x1)).Volume<1e-7:rhi=min(rhi,r);break
 if n.startswith(('MovingFanout','MovingTail','COL_Moving')):
  for r in [26.1,25.5,24.9]:
   if s.common(cyl(r,x0,x1)).Volume<1e-7:rlo=max(rlo,r);break
 cert[n]=[x0,x1,rlo,rhi]
print('CERTIFIED',len(cert),flush=True)
# Axially resolved spool bounds; each finite cylinder union is checked against actual saved solid.
spool_bounds=[(-10,20,31.6),(20,23,25.6),(23,45,24.61),(45,49.4,25.6),(49.4,50.6,30.8),(50.6,50.71,30.8),(50.71,52,25.6)]
spool_pieces=[]
for lo,hi,r in spool_bounds:
 part=S['COL_StationarySpool'].common(Part.makeBox(hi-lo,80,80,V(lo,-40,-40)))
 v=part.cut(cyl(r,lo-.001,hi+.001)).Volume
 assert v<1e-7,('spool bound',lo,hi,r,v)
 spool_pieces.append((lo,hi,r))
print('SPOOL AXIAL BOUNDS PASS',flush=True)
# Pair proofs are valid for every angle because only rotation about X is applied.
preclear={};pending=[];clips={}
for a in rotors:
 for b in statics:
  aa,bb=cert[a],cert[b];xl=max(aa[0],bb[0]);xh=min(aa[1],bb[1])
  if xl>=xh:preclear[a,b]='axial';continue
  if aa[2]>bb[3]+1e-7 or bb[2]>aa[3]+1e-7:preclear[a,b]='certified radial';continue
  # Clip to shared axial range then test a conservative complete stationary annulus.
  ann=cyl(bb[3]+1e-5,xl,xh)
  if bb[2]>1e-5:ann=ann.cut(cyl(bb[2]-1e-5,xl-.001,xh+.001))
  clip=S[a].common(ann)
  if clip.Volume<1e-8:preclear[a,b]='actual rotor outside stationary swept bound';continue
  if b=='COL_StationarySpool':
   vv=0;pieces=[]
   for lo,hi,r in spool_pieces:
    l=max(xl,lo);h=min(xh,hi)
    if h<=l:continue
    ann=cyl(r,l,h).cut(cyl(24.1,l-.001,h+.001))
    piece=S[a].common(ann);vv+=piece.Volume
    if piece.Volume>1e-8:pieces.append(piece)
   if vv<1e-8:preclear[a,b]='actual rotor outside independently certified axial spool annuli';continue
   clip=Part.makeCompound(pieces)
  # Changed spool is only a removal from old spool; unchanged mechanism evidence retained below.
  pending.append((a,b));clips[a,b]=clip
(P/'motion-pending.json').write_text(json.dumps(pending,indent=2)+'\n')
print('PRECLEAR',len(preclear),'PENDING',len(pending),flush=True)
rows=[];bad=[];exact=0
for angle in range(-90,91):
 posed={n:rot(S[n],angle) for n in rotors};checks=0
 released=S['COL_IndexPin'].copy();released.translate(V(-4.2,0,0));assert min(q.BoundBox.XMin for q in posed.values())-released.BoundBox.XMax>1.8
 for a,b in pending:
  q,t=rot(clips[a,b],angle),S[b];v=q.common(t).Volume if q.BoundBox.intersect(t.BoundBox) else 0;exact+=1;checks+=1
  # Explicit existing moving screw preload into stationary? No such permitted interface.
  if v>1e-7:bad.append({'angle':angle,'a':a,'b':b,'volume':v})
 rows.append({'angle':angle,'cross_domain_pairs':len(rotors)*len(statics),'certified_zero_pairs':len(preclear),'exact_remaining_pairs':checks})
 if angle%5==0:print('ANGLE',angle,'bad',len(bad),flush=True)
(P/'motion-check.json').write_text(json.dumps({'status':'PASS' if not bad else 'FAIL','rotors':len(rotors),'statics':len(statics),'rows':rows,'bad':bad,'exact_remaining_checks':exact,'preclear':[{'a':a,'b':b,'basis':v} for (a,b),v in preclear.items()],'certified_bounds':cert,'stop_rows':stops,'stop_overtravel':stop_beyond,'lock_rows':locks},indent=2)+'\n')
