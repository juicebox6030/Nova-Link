from pathlib import Path
import FreeCAD as A,Part,json
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());V=A.Vector
ann=Part.makeCylinder(30.581,20.002,V(24.199,0,0),V(1,0,0)).cut(Part.makeCylinder(24.919,20.004,V(24.198,0,0),V(1,0,0)))
exclude={'insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose0','collar_pose90','screen','UNMET_INTERFACE'};rows=[];exceptions=[]
for n,s in S.items():
 if G[n] in exclude or G[n].endswith('_landing_reserve'):continue
 if n.startswith('COL_'):exceptions.append({'part':n,'basis':'Frozen mechanism, or purely subtractive spool/tail repair; inherited active-path proof'});continue
 if n.startswith(('FixedFanoutCopper','FixedFanoutDielectric','MovingFanoutCopper','MovingFanoutDielectric')):exceptions.append({'part':n,'basis':'Explicit finite-ribbon181 position check in active-fanout-check.json'});continue
 if n.startswith(('FixedTailCopper','MovingTailCopper')):exceptions.append({'part':n,'basis':'Copper is cut from the frozen static-tail laminate; contained in its original envelope'});continue
 v=s.common(ann).Volume if s.BoundBox.intersect(ann.BoundBox) else 0;rows.append({'part':n,'volume':v});assert v<1e-7,(n,v)
(P/'active-envelope-check.json').write_text(json.dumps({'status':'PASS','new_part_rows':rows,'specific_inherited_or_numeric_proofs':exceptions,'annulus':{'x':[24.199,44.201],'r':[24.919,30.581]},'basis':'Conservative all-angle finite-thickness active annulus; each newly added non-fanout part excluded by actual Boolean. Specific fanout/tail/inherited mechanisms retain separate evidence.'},indent=2)+'\n');print('ACTIVE ENVELOPE',len(rows),'PASS',flush=True)
