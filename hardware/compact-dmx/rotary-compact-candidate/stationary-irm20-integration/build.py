"""One conditional stationary prototype, global baseline barrel coordinates (no displayY+180).
No source-family change, existing core/endcap/trunk geometry preserved.
"""
from pathlib import Path
import FreeCAD as A,Part,math,json
P=Path(__file__).resolve().parent;V=A.Vector;d=A.newDocument('Stationary_IRM20_R1');objects={};meta={}
def box(x,y,z,dx,dy,dz):return Part.makeBox(dx,dy,dz,V(x,y,z))
def cyl(r,h,x,y,z,axis=V(0,0,1)):return Part.makeCylinder(r,h,V(x,y,z),axis)
def add(n,s,role,notes=''):
 assert s.isValid() and s.Volume>0,(n,'invalid')
 o=d.addObject('PartDesign::Feature',n);o.Shape=s.copy();o.addProperty('App::PropertyString','Role').Role=role;o.addProperty('App::PropertyString','Qualification').Qualification=notes;objects[n]=o;meta[n]={'role':role,'notes':notes};return o
# Exact protected B01/B02/B03/B15 geometry, only local display translation removed.
core=cyl(24,138,2,0,0,V(1,0,0)).cut(cyl(21.5,138,2,0,0,V(1,0,0))).cut(cyl(2,5,92,0,20))
add('Protected_core_OD48_ID43_x2_140',core,'reference');add('Protected_input_endcap_x0_2',cyl(24,2,0,0,0,V(1,0,0)),'reference');add('Protected_output_endcap_x140_142',cyl(24,2,140,0,0,V(1,0,0)),'reference');add('Protected_L_N_PE_trunk',box(6,-8,-19.5,130,16,5),'keepout','Unchanged envelope; no conductor relocation, branch or certification modeled')
# Nominal carrier/module assembly. Manufacturing/placement bounds checked separately.
pb=-11.00;pt=pb+1.6;mb=pt+.4;mt=mb+24
body=box(45,-13.6,mb,52.4,27.2,24);add('IRM20_nominal_body',body,'module','Primary source 2025-11-21; no heatsink/airflow claim')
pins={'AC_N':(48.4,-10.4,.65,.90),'AC_L':(48.4,10.4,.65,1.40),'V_MINUS':(93.4,-10.4,1.15,.90),'V_PLUS':(93.4,-2.4,1.15,1.40)}
# Rounded-rectangle aperture is rectangular position allowance Minkowski-summed with r.9.
def aperture(x,y,tx,ty,z,h,extra=0):
 r=.9+extra;s=box(x-tx,y-ty-r,z,2*tx,2*(ty+r),h).fuse(box(x-tx-r,y-ty,z,2*(tx+r),2*ty,h))
 for a in [-tx,tx]:
  for b in [-ty,ty]:s=s.fuse(cyl(r,h,x+a,y+b,z))
 return s.removeSplitter()
pcb=box(39,-16,pb,61,32,1.6);cutouts={}
for n,(x,y,tx,ty) in pins.items():
 s=aperture(x,y,tx,ty,pb-.1,1.8);cutouts[n]=s;pcb=pcb.cut(s)
for y in [-6,6]:pcb=pcb.cut(box(42.4,y-1.6,pb-.1,1.2,3.2,1.8))
pcb=pcb.cut(box(69,-14,pb-.1,2,28,1.8)).cut(cyl(.425,1.8,99,.8,pb-.1)) # unpopulated primary/secondary partition slot; not a creepage grant
add('Carrier_PCB_61x32x1p6',pcb,'PCB','Large apertures cover conservative drawing tolerance; NOT a released solder/PTH pattern')
for n,(x,y,tx,ty) in pins.items():
 add('Pin_'+n,cyl(.5,3.5,x,y,mb,V(0,0,-1)),'primary_pin' if n.startswith('AC') else 'secondary_pin')
 for side,z in [('top',pt),('bottom',pb-.07)]:
  land=aperture(x,y,tx,ty,z,.07,.75).cut(aperture(x,y,tx,ty,z-.01,.09));add('Land_'+n+'_'+side,land,'primary_copper' if n.startswith('AC') else 'secondary_copper','70um allocation; termination/PTH and solder bridge explicitly unqualified')
# Simple bottom-layer secondary copper from the real pin lands to underside pigtail lands.
def flatpath(points,width,z,h):
 s=None
 for a,b in zip(points,points[1:]):
  a,b=V(a[0],a[1],z),V(b[0],b[1],z);v=b-a;ln=v.Length;normal=V(-v.y/ln*width/2,v.x/ln*width/2,0);poly=Part.makePolygon([a+normal,b+normal,b-normal,a-normal,a+normal]);part=Part.Face(Part.Wire(poly.Edges)).extrude(V(0,0,h));s=part if s is None else s.fuse(part)
 return s.removeSplitter()
for name,y,start in [('PLUS',.8,(95.7,-2.4)),('MINUS',-.8,(96.2,-10.4))]:
 pts=[start,(97.0,start[1]),(97.0,y),(99,y)] if name=='PLUS' else [start,(99.3,start[1]),(99.3,y),(99,y)]
 z=pt if name=='PLUS' else pb-.07
 trace=flatpath(pts,1.0,z,.07)
 add('Trace_'+name,trace,'secondary_copper','Top PLUS / bottom MINUS,1mm x70um; real KiCad DRC, ampacity and solder release UNMET')
 add('Pigtail_land_'+name,box(97.8,y-.65,pb-.07,2.2,1.3,.07).cut(cyl(.4,.09,99,.8,pb-.08)) if name=='PLUS' else box(97.8,y-.65,pb-.07,2.2,1.3,.07),'secondary_copper')
via=cyl(.425,1.74,99,.8,pb-.07).cut(cyl(.4,1.76,99,.8,pb-.08))
via=via.fuse(cyl(.75,.07,99,.8,pt).cut(cyl(.4,.09,99,.8,pt-.01)))
add('Secondary_PLUS_via_barrel',via,'secondary_copper','Allocated25um platedwall/.8mm finished drill; process not qualified')
# Rigid insulating sled floor/rails/posts; no fastener crosses the existing core.
add('Polyester_film_allocation',box(39,-14.5,-14.4,64,29,.125),'insulation','Unqualified film grade/flammability/dielectric/edge retention; no certified mains barrier claim')
sled=box(39,-14.5,-14.275,64,29,.375)
for y in [-16,14.2]:sled=sled.fuse(box(39,y,-13.9,64,1.8,2.90))
for y in [-6,6]:
 sled=sled.fuse(box(42.5,y-1.5,-13.9,1,3,30.3)).fuse(box(42.5,y-1.5,16.4,3.5,3,1))
 sled=sled.fuse(box(100.2,y-1.5,-13.9,1,3,30.3)).fuse(box(98,y-1.5,16.4,3.2,3,1))
 for x in [44.6,99.0]:sled=sled.cut(cyl(1.05,2,x,y,16.0))
# End/side saddle ribs connect rails to replaceable precompressed friction pads.
for x in [40,100]:
 ring=cyl(21.25,3,x,0,0,V(1,0,0)).cut(cyl(18.5,3,x,0,0,V(1,0,0)))
 for sg in [-1,1]:
  half=box(x,14 if sg>0 else -22,-14,3,8,12);rib=ring.common(half)
  web=box(x,14.2 if sg>0 else -19,-13.9,3,4.8,7).common(cyl(21.25,3,x,0,0,V(1,0,0)))
  sled=sled.fuse(rib).fuse(web)
  shoe=cyl(21.5,3,x,0,0,V(1,0,0)).cut(cyl(21.25,3,x,0,0,V(1,0,0))).common(half)
  add('Core_compression_shoe_'+str(x)+'_'+str(sg).replace('-','m'),shoe,'retention','Captured installed envelope R21.25..21.5; free R21.6 proposal. Material/creep/preload/friction/bond or keyed retention UNMET')
sled=sled.cut(pcb).removeSplitter();add('Custom_dielectric_sled_and_clamp_brackets',sled,'retention','Material/flammability/CTI/temp and friction shoe retention unqualified; positive module jaws, no drilled core')
for i,(x,y) in enumerate([(53,-11.5),(53,11.5),(88,-11.5),(88,11.5)]):add('Standoff_'+str(i),cyl(1.25,.4,x,y,pt),'retention','.40+/- .05 allocated; independent from PCB1.60+/-.10')
for tag,x,xa in [('L',44.6,44.1),('R',99,96.6)]:
 for y in [-6,6]:
  suffix=tag+('m' if y<0 else 'p');add('Pressure_jaw_'+suffix,box(xa,y-1,mt,3,2,.4),'retention','Nominal contact; individually adjustable to source-height corner. Pressure/thermal/locking test UNMET')
  screw=cyl(1,17.4-(mt+.4),x,y,mt+.4).fuse(cyl(1.6,.7,x,y,17.4));add('M2_adjuster_'+suffix,screw,'fastener','Smooth thread envelope; mating thread/locking/torque/process not modeled/qualified')
# Finite single-wire choice, source minimum radius9mm. Circular pieces tangent-continuous.
def arc(a,m,c):return Part.Arc(V(*a),V(*m),V(*c)).toShape()
def edge(a,c):return Part.makeLine(V(*a),V(*c))
def wirepath(y,start=100.4):
 r=9;s=math.sqrt(.5)
 es=[edge((start,y,-11.45),(100.5,y,-11.45)),arc((100.5,y,-11.45),(100.5+9*s,y,-2.45-9*s),(109.5,y,-2.45)),edge((109.5,y,-2.45),(109.5,y,7.55)),arc((109.5,y,7.55),(100.5+9*s,y,7.55+9*s),(100.5,y,16.55)),arc((100.5,y,16.55),(100.5-9*s,y,25.55-9*s),(91.5,y,25.55)),edge((91.5,y,25.55),(91.5,y,27.5))];return Part.Wire(es)
def pipe(path,r):
 p=path.Vertexes[0].Point;circle=Part.Wire([Part.makeCircle(r,p,V(1,0,0))]);return path.makePipeShell([circle],True,False)
for name,y in [('PLUS',.8),('MINUS',-.8)]:
 path=wirepath(y);solid=pipe(path,.4065);bare=cyl(.4065,2.6,97.8,y,-11.45,V(1,0,0));add('Wire_'+name+'_conductor',solid.fuse(bare).removeSplitter(),'secondary_wire','Tensility30-02075 solid20AWG; current/I2t/termination/temperature not qualified')
 jacket=pipe(path,.8).cut(pipe(path,.4065));add('Wire_'+name+'_maximum_OD_insulation',jacket,'secondary_insulation','SourceOD1.5+/-.1, actual minbendR9; stationary formed wire only, no dynamic qualification')
 # Finite solder allocation establishes a modeled connection to pad; source pin-to-land process remains open.
 add('Pigtail_solder_'+name,box(97.8,y-.55,-11.9,2.2,1.1,.83).cut(bare),'joint','Allocation, not qualified solder fillet/strain relief')
# Flared split feedthrough sleeve, actual existing hole untouched. Thin wall is an explicit supplier gate.
outer=Part.makeCone(3.0,1.95,1.15,V(92,0,20.2)).fuse(cyl(1.95,2.75,92,0,21.35)).fuse(cyl(2.75,.8,92,0,23.7)).cut(core.copy())
inner=Part.makeCone(2.7,1.85,1.15,V(92,0,20.2)).fuse(cyl(1.85,3.55,92,0,21.35))
sleeve=outer.cut(inner).removeSplitter()
for side,y in [('m',-4),('p',0)]:add('Bellmouth_sleeve_half_'+side,sleeve.common(box(88,y,20,8,4,8)).removeSplitter(),'secondary_insulation','Curved core seat, split joint/retention, .1mm tube wall and creep unqualified; not a primary isolation barrier')
# Split pigtail strain-relief block and liners, no core penetration. Force/creep remains a test gate.
block=box(101.2,-3.95,-13.25,4.1,7.9,3.4)
for y in [-.8,.8]:block=block.cut(pipe(wirepath(y),.85))
for y in [-2.9,2.9]:block=block.cut(cyl(1.05,4,103.4,y,-13.4))
lower=block.common(box(100,-5,-14,7,10,2.55))
for y in [-3.9,3.3]:lower=lower.fuse(box(101.2,y,-13.9,1.8,.6,.65))
cap=block.common(box(100,-5,-11.45,7,10,2))
add('Secondary_pigtail_clamp_lower',lower.removeSplitter(),'retention','Material/torque/retention to sled/locking UNMET')
add('Secondary_pigtail_clamp_cap',cap.removeSplitter(),'retention','Split cap, smooth thread envelopes; no demonstrated pull/creep capability')
liner=pipe(wirepath(.8),.85).fuse(pipe(wirepath(-.8),.85)).cut(pipe(wirepath(.8),.805).fuse(pipe(wirepath(-.8),.805))).common(box(101.2,-3.95,-13.25,4.1,7.9,3.4))
add('Dual_wire_strain_liner',liner.removeSplitter(),'retention','Dual-wire clearance insert, .005mm maximum-jacket radial clearance; material/compression/minwire holding UNMET')
for y in [-2.9,2.9]:add('Clamp_M2_'+('m' if y<0 else 'p'),cyl(1,3.4,103.4,y,-13.25).fuse(cyl(1.6,.7,103.4,y,-9.85)),'fastener','Thread inserts/torque/locking unqualified; no fastener crosses core')
# Save actual assembly; source limits/extreme pins in a separate editable document, never passed as noncolliding assembly.
d.recompute();d.saveAs(str(P/'stationary-integration.FCStd'));Part.export(list(objects.values()),str(P/'stationary-integration.step'))
e=A.newDocument('Source_lead_extremes')
for n,(x,y,tx,ty) in pins.items():
 for tag,L,z in [('MIN',2.5,-8.8),('MAX',4.5,-9.2)]:
  o=e.addObject('PartDesign::Feature',n+'_'+tag);o.Shape=cyl(.75,L,x,y,z,V(0,0,-1))
o=e.addObject('PartDesign::Feature','Worst_body_placement_envelope');o.Shape=box(44.85,-14,-9.2,53.2,28,24.9)
e.recompute();e.saveAs(str(P/'source-lead-extremes.FCStd'));Part.export(e.Objects,str(P/'source-lead-extremes.step'))
(P/'parts.json').write_text(json.dumps(meta,indent=2)+'\n');(P/'build-geometry.json').write_text(json.dumps({'PCB_bottom':pb,'PCB_top':pt,'module_bottom':mb,'module_top':mt,'source_pin_table':{n:list(a) for n,a in pins.items()},'wire_path_length_mm':wirepath(.8).Length,'source_wire_min_bend_R_mm':9,'physical_parts_including_references':len(objects),'endcap_allocations_unchanged':True},indent=2)+'\n');print('SAVED',len(objects),'objects; wirepath',wirepath(.8).Length)
