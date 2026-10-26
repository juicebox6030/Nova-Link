from pathlib import Path
import FreeCAD as A,Part,json,hashlib
P=Path(__file__).resolve().parent;oldD=A.openDocument(str(P/'before-wire-radius.FCStd'));d=A.openDocument(str(P/'interface-prototype.FCStd'));old={o.Name:o.Shape for o in oldD.Objects if hasattr(o,'Shape')};S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());change=json.loads((P/'wire-radius-change.json').read_text());names=change['changed'];equal=[]
for n in S:
 if n in names:continue
 x=old[n].cleaned().exportBrepToString().split();y=S[n].cleaned().exportBrepToString().split();assert len(x)==len(y),n
 for a,b in zip(x,y):
  if a!=b:assert abs(float(a)-float(b))<1e-12,(n,a,b)
 equal.append(n)
exclude={'insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose90','screen','UNMET_INTERFACE'};rows=[];pairs=set();rproof=[]
for a in names:
 s=S[a];assert s.isValid() and s.isClosed() and len(s.Solids)==1
 b=s.BoundBox;cyl=Part.makeCylinder(24,b.XLength+.02,A.Vector(b.XMin-.01,0,0),A.Vector(1,0,0));assert s.cut(cyl).Volume<1e-7;rproof.append(a)
 for n,t in S.items():
  if n==a or G[n] in exclude or G[n].endswith('_landing_reserve') or n.startswith('COL_Flex_'):continue
  key=tuple(sorted((a,n)))
  if key in pairs:continue
  pairs.add(key)
  if not s.BoundBox.intersect(t.BoundBox):continue
  v=s.common(t).Volume
  if v>1e-7:rows.append({'a':a,'b':n,'volume':v});print('WIRECONTACT',a,n,v,flush=True)
allowed={frozenset(('Pin_LVplus','SourceWireCopper1')):.089,frozenset(('Pin_LVminus','SourceWireCopper2')):.089}
bad=[r for r in rows if r['volume']>allowed.get(frozenset((r['a'],r['b'])),0)]
out={'status':'PASS' if not bad else'FAIL','before_native_sha256':change['before_native_sha256'],'after_native_sha256':hashlib.sha256((P/'interface-prototype.FCStd').read_bytes()).hexdigest(),'unchanged_BRep_numeric_1e12':len(equal),'changed':names,'pairs':len(pairs),'positive':rows,'unintended':bad,'R24_containment':rproof,'motion_basis':'Existing181 proof uses R24 bound for every sourcewire; new four shapes independently contained in same cylinder. All other shapes numerically unchanged. Active ribbon beginsR25 with .08halfthickness.','wire_min_radii_mm':{k:v['radius_min'] for k,v in json.loads((P/'source-wire-paths.json').read_text()).items()}}
(P/'wire-radius-check.json').write_text(json.dumps(out,indent=2)+'\n');print('WIRE REPAIR',out['status'],len(pairs),flush=True);assert not bad
