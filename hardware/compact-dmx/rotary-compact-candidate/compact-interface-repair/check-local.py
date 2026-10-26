from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'before-head-clearance.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());V=A.Vector
# Every newly changed physical object checked against all neutral physical geometry.
nonphysical={'insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose90','screen','UNMET_INTERFACE'}
phys=[n for n in S if G[n] not in nonphysical and not G[n].endswith('_landing_reserve') and not n.startswith('COL_Flex_')]
new=[n for n in phys if not n.startswith('COL_') or n=='COL_StationarySpool']
rows=[];pairs=set()
for a in new:
 for b in phys:
  if a==b:continue
  key=tuple(sorted([a,b]))
  if key in pairs:continue
  pairs.add(key);s,t=S[a],S[b]
  if not s.BoundBox.intersect(t.BoundBox):continue
  v=s.common(t).Volume
  if v>1e-7:rows.append({'a':a,'b':b,'volume':v});print('OVERLAP',a,b,v,flush=True)
 print('CHECKED',a,flush=True)
(P/'local-pairs.json').write_text(json.dumps({'pairs':len(pairs),'positive':rows,'status':'raw allpair findings; no exceptions applied'},indent=2)+'\n')
print('PAIRCOUNT',len(pairs),'POSITIVE',len(rows),flush=True)
