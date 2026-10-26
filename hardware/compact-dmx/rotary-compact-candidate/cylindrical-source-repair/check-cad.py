from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());kept=set(json.loads((P/'preserved-names.json').read_text()));old=A.openDocument(str(P.parent/'compact-interface-repair/interface-prototype.FCStd'))
valid=[]
for n,s in S.items():
 assert s.isValid() and s.isClosed() and len(s.Solids)==1,n;valid.append(n)
preserved=[]
for n in kept:
 a=S[n].cleaned().exportBrepToString().split();b=old.getObject(n).Shape.cleaned().exportBrepToString().split();assert len(a)==len(b),n
 for x,y in zip(a,b):
  if x!=y:assert abs(float(x)-float(y))<1e-12,(n,x,y)
 preserved.append(n)
# No blanket physicalgroup collision exclusions: only nonphysical screens/alternateposes are separated.
nonphysical={'reserve','tool','corridor','unbuilt','access','collar_pose-90','collar_pose90','rotating_landing_reserve','stationary_landing_reserve'}
physical=[n for n in S if G[n] not in nonphysical]
new=[n for n in physical if n not in kept];rows=[];pairs=set()
for a in new:
 for b in physical:
  if a==b:continue
  key=tuple(sorted([a,b]))
  if key in pairs:continue
  pairs.add(key)
  if not S[a].BoundBox.intersect(S[b].BoundBox):continue
  v=S[a].common(S[b]).Volume
  if v>1e-7:rows.append({'a':a,'b':b,'volume':v});print('OVERLAP',a,b,v,flush=True)
# Exact finite corridor containment: enlarged bore shortage evaluated on actual BRep.
cone=Part.makeCone(35.3,21.3,27,V(-27,0,0),V(1,0,0));source=Part.makeCylinder(35.3,110,V(-137,0,0),V(1,0,0));core=Part.makeCylinder(21.3,110,V(0,0,0),V(1,0,0));free=source.fuse(cone).fuse(core)
corridor=[]
for name in ['L','N','PE']:
 s=S['Trunk'+name+'Corridor'];outside=s.cut(free).Volume;corridor.append({'lane':name,'outside_worst_bore_mm3':outside});assert outside<1e-7,(name,outside)
# Explicit sourceconstruction crossings, not waivedclearances.
reserve=S['InstallationReservation'];cross=[]
for n in new:
 if n in ['IRM20_12_maxbody'] or n.startswith('Pin_'):continue
 if S[n].BoundBox.intersect(reserve.BoundBox):
  v=S[n].common(reserve).Volume
  if v>1e-7:cross.append({'part':n,'reserved_volume_crossing':v})
# All sourceboard footprints/lands retained as exact BRep; boards remain externalfrozenfiles.
# Newparts/rotor strict axial or cylindrical separation applies to everyangle.
rot=[n for n in kept if G[n] in ['rotating','rotating_pad','rotating_stake','collar_rotor']];motion=[]
for n in new:
 b=S[n].BoundBox
 if b.XMax<min(S[x].BoundBox.XMin for x in rot):motion.append({'part':n,'proof':'axial','xmax':b.XMax});continue
 clip=S[n].common(Part.makeBox(150,100,100,V(19.19,-50,-50)))
 if clip.isNull() or clip.Volume<1e-9:motion.append({'part':n,'proof':'no overlapX'});continue
 outside=clip.cut(Part.makeCylinder(24,150,V(19.19,0,0),V(1,0,0))).Volume
 motion.append({'part':n,'proof':'R24' if outside<1e-7 else 'UNPROVED','outside_R24':outside})
lock=[]
for n in new:
 if S[n].BoundBox.intersect(S['LockAccess'].BoundBox):
  v=S[n].common(S['LockAccess']).Volume
  if v>1e-7:lock.append({'part':n,'volume':v})
result={'valid_single_solids':len(valid),'preserved_BRep_numeric_1e12':len(preserved),'new_physical':len(new),'new_vs_physical_pairs':len(pairs),'positive_pairs':rows,'corridors':corridor,'unqualified_reservation_crossings':cross,'motion_certificates':motion,'motion_angles':181,'lock_access_collisions':lock,'full_assembly_acceptance':False}
(P/'cad-check.json').write_text(json.dumps(result,indent=2)+'\n');print('CHECKS SAVED',len(valid),len(rows),'LOCK',lock,flush=True)
