from pathlib import Path
import FreeCAD as A,Part,json,hashlib
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());valid={}
for n,s in S.items():
 valid[n]={'valid':s.isValid(),'closed':s.isClosed(),'solids':len(s.Solids)};assert valid[n]=={'valid':True,'closed':True,'solids':1},(n,valid[n])
print('NATIVE VALID',len(valid),flush=True)
exclude={'UNMET_INTERFACE','screen','collar_reserve','insulation','tolerance','trunk_tolerance','support','access'}
base=[n for n in S if G[n] not in exclude and not G[n].endswith('_pad') and not n.startswith('COL_Flex_')]
Part.export([d.getObject(n) for n in base]+[d.getObject('COL_Flex_0')],str(P/'interface-prototype.step'))
exports=[]
for angle,released in [(-90,False),(90,False),(0,True)]:
 td=A.newDocument('ExportPose');items=[]
 for n in base:
  s=S[n].copy()
  if G[n] in ['rotating','rotating_pad','rotating_stake','rotating_landing_reserve','collar_rotor']:s.rotate(V(),V(1,0,0),angle)
  if G[n]=='collar_pin' and released:s.translate(V(-4.2,0,0))
  if G[n]=='collar_spring' and released:s=Part.makeCylinder(1.6,1.6,V(12.2,28.5,0),V(1,0,0)).cut(Part.makeCylinder(1.4,1.62,V(12.19,28.5,0),V(1,0,0)))
  o=td.addObject('PartDesign::Feature',n);o.Shape=s;items.append(o)
 flex='COL_Flex_'+('minus90' if angle==-90 else str(angle));o=td.addObject('PartDesign::Feature','ActiveFlex');o.Shape=S[flex];items.append(o)
 path=P/('assembly-'+str(angle).replace('-','minus')+('-released' if released else '-locked')+'.step');Part.export(items,str(path));exports.append(path);A.closeDocument(td.Name)
# Actual copper detail kept separate from assembly-body allocations.
td=A.newDocument('ActualS12Lands');items=[]
for n in S:
 if G[n].endswith('_pad') or n in ['rotating_PCB','stationary_PCB']:
  o=td.addObject('PartDesign::Feature',n);o.Shape=S[n];items.append(o)
Part.export(items,str(P/'actual-source-lands.step'));exports.append(P/'actual-source-lands.step');A.closeDocument(td.Name)
# Exploded view is explicitly not a motion/assembly-clearance proof.
td=A.newDocument('Exploded');items=[]
for n in base+['COL_Flex_0']:
 s=S[n].copy();shift=V()
 if n=='RotorHalfPositiveY':shift=V(0,45,0)
 elif n=='RotorHalfNegativeY':shift=V(0,-45,0)
 elif n.startswith('rotating_'):shift=V(10,20,0)
 elif n.startswith('stationary_'):shift=V(-10,0,15)
 elif n.startswith('SourceEndGate'):shift=V(20,0,0)
 elif n.startswith('MovingFanout') or n.startswith('MovingClamp'):shift=V(0,0,-25)
 elif n.startswith('FixedFanout'):shift=V(0,0,-15)
 s.translate(shift);o=td.addObject('PartDesign::Feature',n);o.Shape=s;items.append(o)
Part.export(items,str(P/'assembly-exploded.step'));exports.append(P/'assembly-exploded.step');A.closeDocument(td.Name)
# Reopen saved STEP solids, not merely in-memory pre-export objects.
steps=[]
for path in [P/'interface-prototype.step']+exports:
 q=Part.read(str(path));bad=[i for i,s in enumerate(q.Solids) if not(s.isValid() and s.isClosed())];assert not bad,(path.name,bad)
 steps.append({'file':path.name,'solids':len(q.Solids),'invalid_or_open':bad,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()});print('STEP REOPEN',path.name,len(q.Solids),flush=True)
(P/'reopen-check.json').write_text(json.dumps({'native_sha256':hashlib.sha256((P/'interface-prototype.FCStd').read_bytes()).hexdigest(),'native_parts':valid,'STEP':steps,'status':'PASS saved geometry validity ONLY'},indent=2)+'\n')
