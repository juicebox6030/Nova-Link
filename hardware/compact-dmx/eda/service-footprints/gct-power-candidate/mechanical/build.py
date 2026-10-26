import FreeCAD as A,Part,json,math,os
from pathlib import Path
P=Path(os.environ['NOVA_GCT_MECH']);V=A.Vector;D=A.newDocument('GCT_Flush_Prototype');O={}
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def add(n,s,note):
 o=D.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Basis');o.Basis=note;O[n]=o;return s
def slot(x,y,z,w,l,h):
 return box(x-w/2,y-(l-w)/2,z,w,l-w,h).fuse(Part.makeCylinder(w/2,h,V(x,y-(l-w)/2,z))).fuse(Part.makeCylinder(w/2,h,V(x,y+(l-w)/2,z)))
base=box(0,20,5,98,34,22).cut(box(2,22,7,94,30,21)).cut(box(36,51,9.5,14,4,6)).cut(Part.makeCylinder(3,4,V(72,19,18),V(0,1,0)))
for x,y in [(7,26),(73,26),(7,48),(73,48)]:base=base.fuse(Part.makeCylinder(2.4,3,V(x,y,7)).cut(Part.makeCylinder(.85,4,V(x,y,7))))
# Integral cantilever bridge transfers rearward insertion load to front wall above port.
bridge=box(37.5,44.6,16,10.4,9.4,3).fuse(box(38,44.6,11.5,9.4,2,7.5))
base=base.fuse(bridge)
# Two underside support rails, no holes through PCB; compliant shims are separate.
for x in [36.9,48.0]:base=base.fuse(box(x,49,7,.5,3.7,2.6))
add('Base_with_bridge',base.removeSplitter(),'Prototype PA12 integral bridge; external98x34x22 base; force/creep unqualified')
add('Lid',box(0,20,27,98,34,2),'External total98x34x24 unchanged')
pcb=box(4,23,10,90,28,1).fuse(box(36.5,51,10,12.4,2.3,1))
for x,y in [(7,26),(73,26),(7,48),(73,48)]:pcb=pcb.cut(Part.makeCylinder(1.1,2,V(x,y,9.5)))
for x in [38.38,47.02]:
 for y in [47.6,51.4]:pcb=pcb.cut(slot(x,y,9.5,.6,1.2,2))
add('PCB_tongue',pcb.removeSplitter(),'Main90x28x1;12.4x2.3 tongue; old notch filled;4plated slots')
for i,x in enumerate([36.9,48.]):add('Shim'+str(i),box(x,49,9.6,.5,3.7,.4),'Design .4 compliant foam support shim; nominal contact PCBbottom; compression/stiffness gate')
# Supplier external envelope only, no invented internal housing. Separate test cavity visualization is not supplier geometry.
add('Rear_stop_pad',box(38.3,46.6,11.5,8.8,.6,2.4),'Design .6 backed compliant pad; nominal shell contact; compression and adhesive retention qualification OPEN')
add('Connector_external_envelope',box(38.23,47.2,11,8.94,6.8,3.16),'GCT A6 external bounding envelope; not supplier solid;facey54')
for i,(x,y) in enumerate([(x,y) for x in [38.38,47.02] for y in [47.6,51.4]]):add('Stake'+str(i),box(x-.15,y-.4,9.75,.3,.8,1.25),'Design screening crosssection .3x.8; width .8±.1 sourced; thickness .3 ASSUMED; supplier thickness/section approval OPEN;maxlength1.25')
add('Cap_envelope',Part.makeCylinder(6.75,28.4,V(26,30.25,18.75),V(1,0,0)),'Existing15F cap envelope')
add('NOR_envelope',box(28.95,38.65,11,6.1,5.1,.6),'Retained candidate x32 y41.2 max package, rotation per footprint')
# Engineering plug body only: stop at outer mating plane, swept external approach.
add('Plug_test_overmold',box(36.7,54.4,9.5,12,12,6),'ENGINEERING TEST ONLY12x6 overmold at.4 setback; NOT universal cable envelope')
checks=[]
def pair(a,b,allow=False):
 sa=O[a].Shape;sb=O[b].Shape;vol=sa.common(sb).Volume;dist=sa.distToShape(sb)[0];checks.append({'a':a,'b':b,'intersection_mm3':vol,'distance_mm':dist,'intended_surface_contact':allow,'passed':vol<1e-7});assert vol<1e-7,(a,b,vol)
main=['Base_with_bridge','Lid','PCB_tongue','Connector_external_envelope','Cap_envelope','NOR_envelope','Shim0','Shim1','Rear_stop_pad']+[f'Stake{i}' for i in range(4)]
for i,a in enumerate(main):
 for b in main[i+1:]:
  # Envelope includes hypothetical shell/interior; stakes contact its underside at z11 only.
  pair(a,b,a.startswith('Shim') or b.startswith('Shim') or a=='PCB_tongue' or b=='PCB_tongue')
# Finite overmold swept toward mating plane; nearest stop .4mm away, not claiming internals.
sweep=[]
for offset in [0,1,3,6,10]:
 plug=O['Plug_test_overmold'].Shape.copy();plug.translate(V(0,offset,0))
 for name in main:
  v=plug.common(O[name].Shape).Volume;assert v<1e-7;sweep.append({'offset':offset,'solid':name,'intersection_mm3':v})
worst=box(38.005,46.95,11,9.39,7.3,3.51)
base_worst=O['Base_with_bridge'].Shape.copy();base_worst.translate(V(0,.1,-.1))
assert worst.common(base_worst).Volume<1e-7
worst_clearance=worst.distToShape(base_worst)[0]
valid={n:o.Shape.isValid() and all(s.isClosed() for s in o.Shape.Solids) and len(o.Shape.Solids)>0 for n,o in O.items()};assert all(valid.values())
params=D.addObject('Spreadsheet::Sheet','Design_parameters')
for i,(k,v) in enumerate([('PCB tongue width',12.4),('PCB tongue depth',2.3),('Connector origin Y',47.6),('Mating face Y',54),('Rear stop gap',.6),('Bridge underside',16),('Support shim',.4)],1):params.set('A'+str(i),k);params.set('B'+str(i),str(v))
D.recompute();D.saveAs(str(P/'flush-prototype.FCStd'));Part.export(list(O.values()),str(P/'flush-assembly.step'));Part.export([O['Base_with_bridge']],str(P/'base-proposal.step'));Part.export([O['PCB_tongue']],str(P/'pcb-tongue.step'))
(P/'solid-checks.json').write_text(json.dumps({'valid_closed_solids':valid,'pairs':checks,'plug_approach':sweep,'allocated_worst_connector_to_base':{'intersection_mm3':worst.common(base_worst).Volume,'minimum_distance_mm':worst_clearance},'scope':'Actual BRep intersections of explicit geometry; connector/stakes/plug are envelope approximations; no strength or universalfit proof','tolerance_gates':{'rear_stop_nominal_gap':.6,'rear_stop_allocated_stack':.35,'rear_stop_worst_gap':.25,'underside_shim_stack':'compliant contact; compression needs specification','stake_thickness':'not dimensioned in drawing; assumed .3 screening only'}},indent=2)+'\n')
print('VALID',len(valid),'PAIRS',len(checks),'SWEEP',len(sweep))
