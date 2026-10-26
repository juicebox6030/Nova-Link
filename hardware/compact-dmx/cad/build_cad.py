"""Rev B parametric RFQ solids. Run with freecadcmd from repository root.
Supplier components are bounding envelopes, not reverse-engineered production CAD.
"""
import FreeCAD as A, Part, math, json, os
from pathlib import Path
ROOT=Path(os.environ.get('NOVA_CAD_ROOT',Path.cwd()/'hardware/compact-dmx'))
OUT=ROOT/'exports'; OUT.mkdir(exist_ok=True)
V=A.Vector
D=A.newDocument('NOVA_Compact_RevB')
params=D.addObject('Spreadsheet::Sheet','Dimensions')
for i,(k,v) in enumerate([('Revision','B-RFQ'),('Sidecar length',98),('Sidecar width',34),('Sidecar height',24),('Wall',2),('Core OD',48),('Barrel length',142),('Collar OD',84),('Collar width',26),('Inner wire radius',26),('Outer wire radius',40),('Loop radius',7),('Rotation degrees',180)],1):
 params.set('A'+str(i),str(k));params.set('B'+str(i),str(v))
objects={}; physical=[]
def obj(n,s,group='mechanical',note='Proposed RFQ solid; requires DFM'):
 o=D.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Status');o.Status=note;objects[n]=o
 if group=='packing':physical.append(o)
 return o
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cx(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def ring(ro,ri,l,x):return cx(ro,l,x).cut(cx(ri,l+.02,x-.01))
# Dongle coordinates: fixture face z=0; XLR axis x=y=0; body beside intact connector.
base=box(0,20,5,98,34,22).cut(box(2,22,7,94,30,21))
# USB at +y and short DMX lead at x=72 / y=20.
base=base.cut(box(36,51,9.5,14,4,6)).cut(Part.makeCylinder(3,4,V(72,19,18),V(0,1,0)))
for x,y in [(7,26),(73,26),(7,48),(73,48)]:
 boss=Part.makeCylinder(2.4,3,V(x,y,7));boss=boss.cut(Part.makeCylinder(.85,4,V(x,y,7)))
 base=base.fuse(boss)
obj('D01_Sidecar_base',base)
lid=box(0,20,27,98,34,2)
for x,y in [(7,26),(73,26),(7,48),(73,48)]:lid=lid.cut(Part.makeCylinder(1.1,3,V(x,y,26.5)))
obj('D02_Sidecar_lid',lid)
pcb=box(4,23,10,90,28,1.0)
for x,y in [(7,26),(73,26),(7,48),(73,48)]:pcb=pcb.cut(Part.makeCylinder(1.1,2,V(x,y,9.5)))
# Provisional mid-mount connector slot; exact manufacturer footprint still required.
pcb=pcb.cut(box(36.5,45.1,9.5,12.4,7,2))
obj('D03_PCB_envelope',pcb,'envelope','90 x 28 x 1.0 board outline; layout NOT released')
obj('D04_ISOW1412_max',box(8,29,11,12.93,10.63,3.55),'packing','TI DFM0020A maximum package envelope')
obj('D05_CC1352R',box(62,27,11,7,7,1),'packing','TI RGZ 7 x 7 nominal; reserve 16 x 18 RF placement region')
obj('D06_SPI_NOR_max',box(52,40,11,5.1,6.1,.6),'packing','AT25SF161B-MHB-T DFN maximum 5.10 x 6.10 x 0.60; EP to ground; land pattern/decoupling placement open')
obj('D07_USB_CX70M',box(37,45.65,10,11.4,8.35,3.66),'packing','POWER ONLY; data pins NC; supplier envelope; midmount detail/footprint to import')
obj('D08_Cap_max',cx(6.75,28.4,26,30.25,18.75),'packing','HV1325-2R7156-R maximum 13.5 diameter x 28.4; lead reserve x=54.4..61')
obj('D09_Power_zone',box(25,38,11,25,6,4),'packing','Legacy 25 x 6 reservation ONLY: complete EDA power/latch passives not placed; fit not demonstrated; do not infer full packing')
obj('D10_RF_passive_zone',box(61,35,11,15,8,3),'packing','RF network/crystals allocation; antenna must be tuned')
obj('D11_Antenna_keepout',box(78,22,7,18,30,20),'keepout','No metal/ground/cap/fasteners in this volume; antenna design pending')
# Intact NC5FRX supplier envelope; 41 axial and 72.9 transverse dimensions verified.
xlr=Part.makeCylinder(9.5,15,V(0,0,0)).fuse(Part.makeCylinder(10.15,26,V(0,0,15)))
xlr=xlr.fuse(box(-10.15,-10.15,20.7,72.9,20.3,20.3))
obj('D12_NC5FRX_envelope',xlr,'envelope','Conservative union envelope, NOT supplier connector surfaces; full intact boot retained')
obj('D13_Latch_finger_keepout',box(-25,-17,0,18,34,34),'keepout','Proposed 18 mm finger approach; fixture/latch fit must be tested')
# Barrel separate coordinate system translated +180 y for assembly display.
B=180
def bobj(n,s,group='mechanical',note='Proposed RFQ solid; requires DFM'):
 s.translate(V(0,B,0));return obj(n,s,group,note)
core=ring(24,21.5,138,2)
# Port feedthrough only for insulated secondary; partitioned from primary inside.
core=core.cut(Part.makeCylinder(2,5,V(92,0,20),V(0,0,1)))
bobj('B01_Stationary_core',core)
# Endcaps remain uncut blanks: connector-specific exact cutouts cannot be faked.
for x,n in [(0,'B02_Input_endcap_blank'),(140,'B03_Output_endcap_blank')]:
 bobj(n,cx(24,2,x),note='RFQ endcap blank: supplier cutout/flange and terminal clearance approval required before machining')
# Central collar shell and axial faces, independent retained bearing rings.
collar=ring(42,40.9,26,58)
collar=collar.cut(box(65.5,37,-4,12.5,8,8)) # 0.7 mm separation from lane-2 edge x64.8
bobj('B04_Rotary_collar',collar)
for x,n in [(58,'B05_Collar_left_cheek'),(82,'B06_Collar_right_cheek')]:
 cheek=ring(40.9,24.35,2,x)
 if x==58:cheek=cheek.cut(cx(1.9,2.2,57.9,29,0)) # lock guide sleeve seats here
 if x==82:cheek=cheek.cut(cx(2.05,2.2,81.9,30,0)) # separate stop-peg passage
 bobj(n,cheek)
for x,n in [(55.9,'B07_POM_left_bush'),(84.1,'B08_POM_right_bush')]:bobj(n,ring(27,24.1,2,x))
# Steel lock ring bolted to core, holes 15 degree pitch for 13 lock positions.
lock=ring(32,24.05,2,53.5)
for deg in range(-90,91,15):
 a=math.radians(deg);lock=lock.cut(cx(1.6,2.2,53.4,29*math.cos(a),29*math.sin(a)))
bobj('B09_304_lock_ring',lock,note='2 mm 304 ring; 13 holes diameter 3.20 +0.05/0 at R29; 15 degree pitch')
# pin slides axially, engages 2 mm ring; spring/hood envelope reserved rather than fabricated.
bobj('B10_Lock_pin_17_4PH',cx(1.5,9,52.5,29,0),note='Diameter 3.00 -0.02/0 pin; 4.2 mm axial release stroke; spring return 8-15 N target; enclosed by B19 through both wire lanes')
# Stop peg is separate from lock; stops external to wire cassette.
bobj('B11_Stop_peg',cx(2,6,83,30,0),note='4 mm steel peg through 4.10 mm cheek bore; retention/shoulder details remain open; independent of lock release')
# Analytic half-annulus swept slot with endpoint pin-radius allowance not shown as machining ready.
track=ring(34,26,4,86.3)
# limit semicircle y>=0, slot from -90 to90 with finite peg center endpoints
slot=ring(32.15,27.85,4.2,86.2).common(box(86.1,-.01,-35,6,36,70))
slot=slot.fuse(cx(2.15,4.2,86.2,0,30)).fuse(cx(2.15,4.2,86.2,0,-30))
track=track.cut(slot)
bobj('B12_Stop_track',track,note='R30 slot centerline +/-90 degrees with R2.15 ends; 4 mm peg yields nominal 180.57 degrees travel, target 180 +/-1')
# Electronics and mains allocations inside fixed core; separated bounding boxes.
bobj('B13_IRM10_5_envelope',box(45,-12.7,-10.75,45.7,25.4,21.5),'packing','Verified module nominal envelope; allocate tolerance +0.5 each dimension')
bobj('B14_PSU_board',box(39,-16,-13,61,32,1.6),'envelope','Proposed board outline; primary-secondary partition/slots not routed')
bobj('B15_Mains_trunk_keepout',box(6,-8,-19.5,130,16,5),'keepout','Stationary L/N/PE wires; wire bending and connector terminal paths require full harness design')
bobj('B16_USB_board_envelope',box(65.8,27,-3.5,15,11,1),'envelope','Rotating low-voltage board lowered 1 mm to clear lock guide; posts/footprints pending')
bobj('B17_USB_envelope',box(66,32,-3,11.4,8.35,3.66),'packing','CX70M envelope lowered with board; orientation to be confirmed against manufacturer mid-mount model')
# Divider and cassette covers must terminate/seal at this solid tube's OD.
# A continuous divider through the tube is forbidden; attachment remains DFM work.
guide=cx(1.9,9,58,29,0).cut(cx(1.6,9.2,57.9,29,0))
bobj('B19_Lock_pin_guide',guide,note='Proposed metal sleeve OD3.80 +0.05/0 ID3.20 +0.05/0 x9; attachment and divider/cover seals require DFM')
# Reversing rolling wire loop centerline at neutral. Inner arc 0->pi, outer pi->0, U fold R7 at -y.
def arc_pts(r,a,b,n=70):return [V(61,r*math.cos(a+(b-a)*i/n),r*math.sin(a+(b-a)*i/n)) for i in range(n+1)]
pts=arc_pts(26,0,math.pi)
# Fold joins (-26,0) to (-40,0), bending through negative z.
pts += [V(61,-33+7*math.cos(t),-7*math.sin(t)) for t in [math.pi*i/35 for i in range(1,36)]]
pts += arc_pts(40,math.pi,0)[1:]
path=Part.makePolygon(pts)
bobj('B18_Wire_centerline_NEUTRAL',path,'reference','Centerline ONLY. Separate two axial lanes x=61/64; Rmin 7; 229.34 mm active plus 20 mm tails')
# Exploded copies of key custom parts, spaced in y for review only.
for i,n in enumerate(['B02_Input_endcap_blank','B01_Stationary_core','B09_304_lock_ring','B04_Rotary_collar','B06_Collar_right_cheek','B12_Stop_track','B03_Output_endcap_blank']):
 s=objects[n].Shape.copy();s.translate(V(i*13,150,0));obj('EXP_'+n,s,'exploded')
D.recompute()
D.saveAs(str(OUT/'compact-dmx-revb.FCStd'))
for prefix,name in [('D','sidecar-assembly'),('B','barrel-assembly'),('EXP','barrel-exploded')]:
 selected=[o for n,o in objects.items() if n.startswith(prefix) and 'keepout' not in n and 'centerline' not in n]
 Part.export(selected,str(OUT/(name+'.step')))
# Export custom solids individually, preserving analytic surfaces.
for n in ['D01_Sidecar_base','D02_Sidecar_lid','B01_Stationary_core','B04_Rotary_collar','B06_Collar_right_cheek','B09_304_lock_ring','B12_Stop_track','B19_Lock_pin_guide']:
 Part.export([objects[n]],str(OUT/(n+'.step')))
checks={'valid_solids':{},'package_intersections_mm3':[],'notes':['Package check excludes shell/PCB supporting contacts and unmodeled passives/harness. No DRC/ERC/fixture fit validation.']}
for n,o in objects.items():
 if o.Shape.Solids:checks['valid_solids'][n]=o.Shape.isValid()
for i,a in enumerate(physical):
 for b in physical[i+1:]:
  v=a.Shape.common(b.Shape).Volume
  if v>1e-5:checks['package_intersections_mm3'].append([a.Name,b.Name,v])
# Explicit support/contact, package-shell, package-PCB and antenna-volume checks.
checks['clearance_checks']=[]
def clearance(a,b,minimum=0):
 sa,sb=objects[a].Shape,objects[b].Shape
 volume=sa.common(sb).Volume;gap=sa.distToShape(sb)[0]
 checks['clearance_checks'].append(dict(a=a,b=b,intersection_mm3=volume,gap_mm=gap,minimum_gap_mm=minimum,passed=volume<1e-5 and gap+1e-6>=minimum))
clearance('D01_Sidecar_base','D03_PCB_envelope') # face contact at boss top is intended
clearance('D02_Sidecar_lid','D03_PCB_envelope',1)
clearance('B11_Stop_peg','B06_Collar_right_cheek',.05)
clearance('B19_Lock_pin_guide','B05_Collar_left_cheek') # cylindrical seating contact
clearance('B10_Lock_pin_17_4PH','B19_Lock_pin_guide',.1)
clearance('B19_Lock_pin_guide','B16_USB_board_envelope',.6)
clearance('B19_Lock_pin_guide','B17_USB_envelope',1.1)
for part in physical:
 if part.Name.startswith('D'):
  for shell in ['D01_Sidecar_base','D02_Sidecar_lid']:
   clearance(part.Name,shell)
  clearance(part.Name,'D03_PCB_envelope') # zero-volume seating contact allowed
  clearance(part.Name,'D11_Antenna_keepout')
for part in physical:
 if part.Name.startswith('B'):
  for shell in ['B01_Stationary_core','B02_Input_endcap_blank','B03_Output_endcap_blank','B04_Rotary_collar','B05_Collar_left_cheek','B06_Collar_right_cheek']:
   clearance(part.Name,shell)
clearance('D08_Cap_max','D03_PCB_envelope',1)
clearance('D08_Cap_max','D02_Sidecar_lid',1.5)
checks['notes'].append('Antenna check excludes the intentional dielectric PCB substrate and plastic shell; copper layout remains unverified. USB PCB slot is provisional. Contacts may have zero gap but must have zero intersection volume.')
# Earlier package-only grouping missed the stop peg/cheek collision. Check all
# modeled barrel mechanical solids together at neutral, allowing face contact.
checks['barrel_mechanical_intersections_mm3']=[]
mechanical=[objects[n] for n in ['B01_Stationary_core','B02_Input_endcap_blank','B03_Output_endcap_blank','B04_Rotary_collar','B05_Collar_left_cheek','B06_Collar_right_cheek','B07_POM_left_bush','B08_POM_right_bush','B09_304_lock_ring','B10_Lock_pin_17_4PH','B11_Stop_peg','B12_Stop_track','B19_Lock_pin_guide']]
checks['barrel_mechanical_pair_count']=len(mechanical)*(len(mechanical)-1)//2
for i,a in enumerate(mechanical):
 for b in mechanical[i+1:]:
  if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
   v=a.Shape.common(b.Shape).Volume
   if v>1e-5:checks['barrel_mechanical_intersections_mm3'].append([a.Name,b.Name,v])
# Maximum displacement includes stroke tolerance, endplay and guide registration.
checks['lock_release_checks']=[]
for dx in [0,4.2-.15-.35-.15,4.2,4.2+.15+.35+.15]:
 pin=objects['B10_Lock_pin_17_4PH'].Shape.copy();pin.translate(V(dx,0,0))
 for n in ['B19_Lock_pin_guide','B05_Collar_left_cheek','B16_USB_board_envelope']+(['B09_304_lock_ring'] if dx else []):
  other=objects[n].Shape;v=pin.common(other).Volume;gap=pin.distToShape(other)[0]
  checks['lock_release_checks'].append(dict(displacement_mm=dx,other=n,intersection_mm3=v,gap_mm=gap,passed=v<1e-5 and (n!='B09_304_lock_ring' or gap>=.5)))
# Exact arc centerlines at 181 positions, two axial lanes. Subtract max insulation
# radius from distance to solid sleeve. Excludes tails, wire dynamics and covers.
checks['guide_wire_sweep']={'sample_angles':181,'wire_OD_max_mm':1.2,'minimum_nominal_clearance_mm':1000}
for deg in range(-90,91):
 theta=math.radians(deg);phi=math.pi+40*theta/66
 sleeve=objects['B19_Lock_pin_guide'].Shape.copy();sleeve.rotate(V(0,B,0),V(1,0,0),deg)
 for lane in [61,64]:
  def polar(r,a):return V(lane,B+r*math.cos(a),r*math.sin(a))
  e=V(0,math.cos(phi),math.sin(phi));t=V(0,-math.sin(phi),math.cos(phi))
  center=V(lane,B,0)+33*e
  fold=Part.Arc(polar(26,phi),center+7*t,polar(40,phi)).toShape()
  path=Part.makeCompound([Part.Arc(polar(26,0),polar(26,phi/2),polar(26,phi)).toShape(),fold,Part.Arc(polar(40,phi),polar(40,(phi+theta)/2),polar(40,theta)).toShape()])
  gap=sleeve.distToShape(path)[0]-.6
  checks['guide_wire_sweep']['minimum_nominal_clearance_mm']=min(checks['guide_wire_sweep']['minimum_nominal_clearance_mm'],gap)
checks['guide_wire_sweep']['radial_tolerance_allowance_mm']=.125 # R29 and ri +/-0.05; sleeve OD +0.05
checks['guide_wire_sweep']['minimum_after_allocated_tolerances_mm']=checks['guide_wire_sweep']['minimum_nominal_clearance_mm']-.125
checks['guide_wire_sweep']['passed']=checks['guide_wire_sweep']['minimum_after_allocated_tolerances_mm']>=.3-1e-6
checks['usb_window_lane_axial_gap_mm']=65.5-(64+.8)
checks['notes'].append('78 modeled barrel mechanical pairs checked at neutral; lock release displacement and ideal guide/wire sweep added. Cassette covers/divider seals, fasteners, tails and dynamic wire behavior remain unmodeled/unverified.')
(OUT/'cad-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
assert all(checks['valid_solids'].values()) and not checks['package_intersections_mm3'] and all(c['passed'] for c in checks['clearance_checks'])
assert not checks['barrel_mechanical_intersections_mm3'] and all(c['passed'] for c in checks['lock_release_checks'])
assert checks['guide_wire_sweep']['passed'] and checks['usb_window_lane_axial_gap_mm']>=.3
print('EXPORT_RESULT',len(objects),'objects;',len(checks['valid_solids']),'validity checks; packing intersections',checks['package_intersections_mm3'])
