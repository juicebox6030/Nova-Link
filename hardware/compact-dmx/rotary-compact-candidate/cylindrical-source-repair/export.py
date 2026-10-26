from pathlib import Path
import FreeCAD as A,Part,json,hashlib
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'prototype.FCStd'));G=json.loads((P/'groups.json').read_text());exclude={'reserve','tool','corridor','unbuilt','access','collar_pose-90','collar_pose90','rotating_landing_reserve','stationary_landing_reserve'}
objs=[o for o in d.Objects if hasattr(o,'Shape') and G[o.Name] not in exclude and not G[o.Name].endswith('_pad')]
Part.export(objs,str(P/'prototype.step'));print('STEP exported',len(objs),flush=True)
q=A.newDocument('STEP_reopen');Part.insert(str(P/'prototype.step'),q.Name);solids=[s for o in q.Objects if hasattr(o,'Shape') for s in o.Shape.Solids];assert len(solids)==len(objs);assert all(s.isValid() and s.isClosed() for s in solids)
(P/'export-check.json').write_text(json.dumps({'exported_objects':len(objs),'reopened_solids':len(solids),'valid_closed':True,'STEP_sha256':hashlib.sha256((P/'prototype.step').read_bytes()).hexdigest(),'scope':'Constructed partialassembly; explicit unbuiltinterfaces excluded, not a manufacturing assembly'},indent=2)+'\n');print('REOPEN PASS',len(solids),flush=True)
