from pathlib import Path
import FreeCAD as A,Part,json,math,os,sys
P=Path(__file__).resolve().parent;V=A.Vector;old=A.openDocument(str(P.parent/'combined-compact-allocation/allocation.FCStd'));d=A.newDocument('PrimaryRepair');O={}
def add(n,s):
 assert s.isValid() and s.isClosed() and len(s.Solids)==1,n
 o=d.addObject('PartDesign::Feature',n);o.Shape=s;O[n]=s
for n in ['Carrier61x32PlanningPlate','IRM20_12_maxbody','Trunk_L','Trunk_N','Trunk_PE','L_TrunkToFuse','PrimaryFuseBranchBay','Pin_L','Pin_N','Pin_LVminus','Pin_LVplus']:
 s=old.getObject(n).Shape.copy()
 if n=='Carrier61x32PlanningPlate':
  for x,y in [(-98.3,-10.4),(-98.3,10.4),(-53.3,-10.4),(-53.3,-2.4)]:s=s.cut(Part.makeCylinder(1,3,V(x,y,-14),V(0,0,1)))
 add(n,s)
controls={'L_FuseToCarrier':[[-124,29,-7],[-124,18,-7],[-114,10.4,-20],[-98.3,10.4,-15]],'N_TrunkToCarrier':[[-132,38,-25],[-132,38,-8],[-120,-10.4,-25],[-98.3,-10.4,-15]]};path={}
for n,points in controls.items():
 c=Part.BezierCurve();c.setPoles([V(*p) for p in points]);e=c.toShape();s=Part.Wire([e]).makePipeShell([Part.Wire(Part.makeCircle(1.5,V(*points[0]),c.tangent(0)[0]))],True,False);add(n,s);rs=[1/c.curvature(i/1000) for i in range(1001) if c.curvature(i/1000)>1e-9];path[n]={'control_points':points,'length':e.Length,'min_bend_radius':min(rs)}
rows=[]
allowed={frozenset(x) for x in [('L_TrunkToFuse','Trunk_L'),('L_TrunkToFuse','PrimaryFuseBranchBay'),('L_FuseToCarrier','PrimaryFuseBranchBay'),('L_FuseToCarrier','Pin_L'),('N_TrunkToCarrier','Trunk_N'),('N_TrunkToCarrier','Pin_N')]}
for i,(a,s) in enumerate(O.items()):
 for b,t in list(O.items())[i+1:]:
  v=s.common(t).Volume if s.BoundBox.intersect(t.BoundBox) else 0
  if v>1e-7:rows.append({'a':a,'b':b,'volume':v,'named_electrical_endpoint':frozenset([a,b]) in allowed})
fail=[r for r in rows if not r['named_electrical_endpoint']]
d.recompute();d.saveAs(str(P/'primary-repair.FCStd'));Part.export(d.Objects,str(P/'primary-repair.step'))
(P/'primary-check.json').write_text(json.dumps({'rows':rows,'failures':fail,'paths':path,'carrier_hole_diameter':2,'pin_nominal_diameter':1,'conservative_pin_diameter_screen':1.5,'nominal_carrier_pin_radial_gap':.5,'screen_radial_gap_at_1p5_pin':.25,'source_pin_tolerance_scope_unqualified':True},indent=2)+'\n');print('PRIMARY',len(rows),'FAIL',fail,'PATHS',path,flush=True);sys.stdout.flush();os._exit(1 if fail else 0)
