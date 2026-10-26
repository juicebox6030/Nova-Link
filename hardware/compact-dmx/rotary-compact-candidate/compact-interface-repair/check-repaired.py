from pathlib import Path
import FreeCAD as A,Part,json,hashlib,difflib,re
P=Path(__file__).resolve().parent;oldD=A.openDocument(str(P/'before-head-clearance.FCStd'));d=A.openDocument(str(P/'before-wire-radius.FCStd'));old={o.Name:o.Shape for o in oldD.Objects if hasattr(o,'Shape')};S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());changes=['StationaryCoreWithSupports','RotorHalfPositiveY'];equal=[]
for n in S:
 if n in changes:continue
 a,b=old[n],S[n]
 x=a.cleaned().exportBrepToString().split();y=b.cleaned().exportBrepToString().split();assert len(x)==len(y),(n,'token count')
 max_delta=0
 for u,v in zip(x,y):
  if u==v:continue
  try:delta=abs(float(u)-float(v))
  except ValueError:raise AssertionError((n,'non-numeric BRep change',u,v))
  assert delta<1e-12,(n,delta,u,v);max_delta=max(max_delta,delta)
 equal.append(n);print('IDENTICAL',n,flush=True)
prior={tuple(sorted((r['a'],r['b']))) for r in json.loads((P/'local-pairs.json').read_text())['positive']};rows=[];counts=0;zero_by_subset=0;exclude={'insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose90','screen','UNMET_INTERFACE'}
for name in changes:
 assert S[name].isValid() and len(S[name].Solids)==1
 added=S[name].cut(old[name]).Volume;assert added<1e-7,(name,added)
 print('SUBSET',name,added,flush=True)
 for n,s in S.items():
  if n==name or G[n] in exclude or G[n].endswith('_landing_reserve') or n.startswith('COL_Flex_'):continue
  counts+=1
  if tuple(sorted((name,n))) not in prior:zero_by_subset+=1;continue
  if not s.BoundBox.intersect(S[name].BoundBox):continue
  v=s.common(S[name]).Volume
  if v>1e-7:rows.append({'a':name,'b':n,'volume':v});print('CONTACT',name,n,v,flush=True)
(P/'repaired-pairs.json').write_text(json.dumps({'changed':changes,'unchanged_BRep_structure_numeric_tolerance_1e12':equal,'pairs':counts,'zero_by_verified_subtractive_subset':zero_by_subset,'positive':rows,'native_sha256':hashlib.sha256((P/'before-wire-radius.FCStd').read_bytes()).hexdigest()},indent=2)+'\n');print('REPAIRED CHECK DONE',counts,flush=True)
