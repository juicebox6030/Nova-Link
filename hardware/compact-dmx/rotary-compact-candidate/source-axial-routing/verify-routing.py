"""Independent saved-copper/netlist/endpoint/connectivity/short/path checks. No builder/router imports."""
from pathlib import Path
import pcbnew as K,math,json,xml.etree.ElementTree as E,hashlib,collections
P=Path(__file__).resolve().parent;old=P.with_name('regulated-source');mm=K.ToMM;iu=K.FromMM;b=K.LoadBoard(str(P/'source-axial.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
def xmlmap(path):
 r=E.parse(path);pins={(n.attrib['ref'],n.attrib['pin']):z.attrib['name'].rsplit('/',1)[-1] for z in r.findall('./nets/net') for n in z};values={c.attrib['ref']:c.findtext('value') for c in r.findall('./components/comp')};return pins,values
pn,values=xmlmap(P/'regulated-source.net');op,ov=xmlmap(old/'regulated-source.net')
delta={key:(val,pn.get(key)) for key,val in op.items() if pn.get(key)!=val};assert delta=={('U2','14'):('PROTECTED_IN','REG_EN_SERIES'),('C12','1'):('INPUT_DVDT','INPUT_DVDT_C')},delta
assert set(pn)-set(op)=={('R12','1'),('R12','2'),('R13','1'),('R13','2')};assert pn['R12','1']=='PROTECTED_IN' and pn['R12','2']=='REG_EN_SERIES';assert values['R12']=='TNPW040210K0BYED 10000ohm';assert all(values[r]==v for r,v in ov.items())
assert pn['R13','1']=='INPUT_DVDT' and pn['R13','2']=='INPUT_DVDT_C' and values['R13']=='TNPW0402100RBYED 100ohm'
assert len(fs)==34 and all(f.GetLayer()==K.F_Cu for f in fs.values())
assert all(hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256((old/'Regulated.pretty'/f.name).read_bytes()).digest() for f in (P/'Regulated.pretty').glob('*.kicad_mod'))
settings=json.loads((P/'source-axial.kicad_pro').read_text());rules=settings['board']['design_settings'];assert not rules['drc_exclusions'];assert len(settings['net_settings']['classes'])==1 and settings['net_settings']['classes'][0]['clearance']==.2
assert all(rules['rule_severities'][n]=='error' for n in ['clearance','shorting_items','hole_clearance','unconnected_items','solder_mask_bridge','copper_edge_clearance','track_width'])
assert rules['rules']['min_track_width']==.2 and rules['rules']['min_hole_clearance']==.25 and rules['rules']['min_copper_edge_clearance']==.5 and rules['rules']['min_through_hole_diameter']==.3
assert b.GetCopperLayerCount()==4 and abs(mm(b.GetDesignSettings().GetBoardThickness())-1)<1e-8
j=fs['J1'];assert abs(mm(j.GetPosition().x)-27)<1e-8 and abs(mm(j.GetPosition().y)-10)<1e-8 and j.GetOrientationDegrees()==90
# Primary pad datum disambiguates mouth direction: solder row is LEFT of X27.
assert all(abs(mm(p.GetPosition().x)-22.245)<1e-6 for p in j.Pads() if p.GetNumber() in ['A1_B12','B1_A12','A5','B5'])
obj=[];padchecks=0;holes=[]
def xy(v):return (mm(v.x),mm(v.y))
alllayers={K.F_Cu,K.In1_Cu,K.In2_Cu,K.B_Cu}
for ref,f in fs.items():
 assert f.GetValue()==values[ref]
 for p in f.Pads():
  if p.GetNumber():
   assert p.GetNetname()==pn[ref,p.GetNumber()];padchecks+=1;bb=p.GetBoundingBox();obj.append({'kind':'rect','net':p.GetNetname(),'ls':{K.F_Cu} if p.GetAttribute()==K.PAD_ATTRIB_SMD else alllayers,'rect':(mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())),'xy':xy(p.GetPosition()),'key':ref+'.'+p.GetNumber()})
  if p.GetDrillSize().x:
   dw,dh=mm(p.GetDrillSize().x),mm(p.GetDrillSize().y)
   if round(f.GetOrientationDegrees())%180:dw,dh=dh,dw
   holes.append({'ref':ref,'number':p.GetNumber(),'xy':xy(p.GetPosition()),'size_mm':[dw,dh],'NPTH':p.GetAttribute()==K.PAD_ATTRIB_NPTH})
tracks=[];vias=[]
for t in b.GetTracks():
 if t.GetClass()=='PCB_VIA':
  a={'kind':'circle','net':t.GetNetname(),'ls':alllayers,'xy':xy(t.GetPosition()),'r':mm(t.GetWidth(K.F_Cu))/2,'key':'via'+str(len(vias))};obj.append(a);vias.append(a);assert mm(t.GetDrillValue())>=.3-1e-7
  holes.append({'ref':'via','number':'','xy':a['xy'],'size_mm':[mm(t.GetDrillValue())]*2,'NPTH':False})
 else:
  a={'kind':'line','net':t.GetNetname(),'ls':{t.GetLayer()},'a':xy(t.GetStart()),'c':xy(t.GetEnd()),'r':mm(t.GetWidth())/2,'key':'track'+str(len(tracks))};obj.append(a);tracks.append(a);assert a['r']>=.1-1e-7
# Geometric contact graph over actual saved pad/track/via copper. Zones added separately.
def pseg(p,a,c):
 dx,dy=c[0]-a[0],c[1]-a[1];l=dx*dx+dy*dy;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l)) if l else 0;return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
def cross(a,c,d,e):
 def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 return orient(a,c,d)*orient(a,c,e)<0 and orient(d,e,a)*orient(d,e,c)<0
def segseg(a,c,d,e):return 0 if cross(a,c,d,e) else min(pseg(a,d,e),pseg(c,d,e),pseg(d,a,c),pseg(e,a,c))
def prect(p,r):return math.hypot(max(r[0]-p[0],p[0]-r[2],0),max(r[1]-p[1],p[1]-r[3],0))
def edges(r):
 a=[(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])];return list(zip(a,a[1:]+a[:1]))
def contact(a,c):
 if a['kind']=='circle' and c['kind']=='line':return pseg(a['xy'],c['a'],c['c'])<=a['r']+c['r']+1e-6
 if c['kind']=='circle' and a['kind']=='line':return contact(c,a)
 if a['kind']==c['kind']=='line':return segseg(a['a'],a['c'],c['a'],c['c'])<=a['r']+c['r']+1e-6
 if a['kind']==c['kind']=='circle':return math.dist(a['xy'],c['xy'])<=a['r']+c['r']+1e-6
 if a['kind']=='rect' and c['kind']=='circle':return prect(c['xy'],a['rect'])<=c['r']+1e-6
 if c['kind']=='rect' and a['kind']=='circle':return contact(c,a)
 if a['kind']=='rect' and c['kind']=='line':return min([prect(c['a'],a['rect']),prect(c['c'],a['rect'])]+[segseg(c['a'],c['c'],d,e) for d,e in edges(a['rect'])])<=c['r']+1e-6
 if c['kind']=='rect' and a['kind']=='line':return contact(c,a)
 r,s=a['rect'],c['rect'];return max(r[0]-s[2],s[0]-r[2],r[1]-s[3],s[1]-r[3])<=1e-6
parent=list(range(len(obj)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def join(i,j):parent[find(i)]=find(j)
# Isolate the deliberate bottom star strap while checking quiet trees before their power join.
strap=[a for a in tracks if a['net']=='GND_ISO' and a['ls']=={K.B_Cu} and all(x<4.1 and 13.0<y<15.2 for x,y in [a['a'],a['c']])]
assert strap
for i,a in enumerate(obj):
 for j in range(i):
  c=obj[j]
  if a not in strap and c not in strap and a['net']==c['net'] and a['ls']&c['ls'] and contact(a,c):join(i,j)
keys={a['key']:i for i,a in enumerate(obj)}
u1=find(keys['U1.4']);u2=find(keys['U2.4']);assert u1!=u2,'Quiet returns touch before their distinct plane stars'
for name,rr in [('U1',['U1.8','R2.2','R4.2','R5.2','C12.2']),('U2',['U2.1','U2.15','R7.2','C11.2'])]:
 root=find(keys[name+'.4']);assert all(find(keys[n])==root for n in rr),(name,rr)
 assert all(find(keys[n])!=root for n in ['C1.2','C3.2','C7.2','C8.2','J0.2','U2.10','U3.21']),'Quiet return unintentionally shares power-ground copper before its plane star'
zones=list(b.Zones());assert len(zones)==1 and zones[0].GetNetname()=='GND_ISO';poly=zones[0].GetFilledPolysList(K.In1_Cu)
def plane(p):return bool(poly.Contains(K.VECTOR2I(iu(p[0]),iu(p[1]))))
def ringconnected(p):return any(plane((p[0]+math.cos(k*math.pi/4)*.25,p[1]+math.sin(k*math.pi/4)*.25)) for k in range(8))
for p in [(6.2,8.1),(6.75,9.45),(11.7,9.725),(1.975,8),(1.975,15.2),(6.625,10.75),(6.1,15)]:assert not ringconnected(p),('Quiet via bypasses star',p)
assert ringconnected((3.5,8.55)), 'Actual C13 bypass return must join power plane'
assert ringconnected((9.35,8.7)) and ringconnected((2.,13.5))
# Bottom star strap touches only its two intended through-vias; no bypass of another quiet terminal.
touches=[a for a in obj if a not in strap and K.B_Cu in a['ls'] and a['net']=='GND_ISO' and any(contact(a,c) for c in strap)]
assert len(touches)==2 and {tuple(round(v,4) for v in a['xy']) for a in touches}=={(2.,13.5),(3.4,14.6)},touches
for a in strap:
 for c in obj:
  if a is not c and a['net']==c['net'] and a['ls']&c['ls'] and contact(a,c):join(keys[a['key']],keys[c['key']])
planeitems=[]
for i,a in enumerate(obj):
 if a['net']=='GND_ISO' and K.In1_Cu in a['ls'] and ringconnected(a['xy']):planeitems.append(i)
for i in planeitems[1:]:join(planeitems[0],i)
components=collections.defaultdict(set)
for i,a in enumerate(obj):components[a['net']].add(find(i))
assert all(len(v)==1 for n,v in components.items()),[(n,len(v)) for n,v in components.items() if len(v)>1]
endpoint_checks=0
for a in tracks:
 for p in [a['a'],a['c']]:
  probe={'kind':'circle','xy':p,'r':a['r'],'ls':a['ls'],'net':a['net']}
  assert any(c is not a and c['net']==a['net'] and c['ls']&a['ls'] and contact(probe,c) for c in obj),(a['key'],p,'dangling endpoint')
  endpoint_checks+=1
minimum=100
for i,a in enumerate(tracks):
 for c in tracks[:i]:
  if a['net']!=c['net'] and a['ls']&c['ls']:minimum=min(minimum,segseg(a['a'],a['c'],c['a'],c['c'])-a['r']-c['r'])
assert minimum>=.2-1e-6,minimum
# Passive data short: total path copper is an upper bound for any two contacts; no data processor.
d=[a for a in tracks if a['net']=='USB_D_SHORT'];assert all(a['ls']=={K.F_Cu} for a in d);length=sum(math.dist(a['a'],a['c']) for a in d);rho=1.75e-8*(1+.00393*60);res=sum(rho*math.dist(a['a'],a['c'])*.001/(a['r']*2*.001*63e-6) for a in d);assert res<.1 and res<200
for n in ['A6','A7','B6','B7']:assert pn['J1',n]=='USB_D_SHORT'
drc=json.loads((P/'drc.json').read_text());assert len(drc['unconnected_items'])==0
assert len(drc['violations'])==4 and all(v['type']=='hole_clearance' and all('J1' in n['description'] for n in v['items']) for v in drc['violations']),[(v['type'],v['description']) for v in drc['violations']]
epvias=[a for a in vias if abs(a['xy'][0]-18.5)<.8 and abs(a['xy'][1]-12.5)<1.3];assert len(epvias)==6 and all(a['net']=='GND_ISO' and abs(a['r']-.3)<1e-8 for a in epvias)
lands=json.loads((P/'land-sources.json').read_text());bodyarea=0;courtarea=0
for f in fs.values():
 info=lands[str(f.GetFPID().GetLibItemName())];bodyarea+=math.prod(info['body_max_mm']);f.BuildCourtyardCaches();bb=f.GetCourtyard(K.F_CrtYd).BBox();courtarea+=mm(bb.GetWidth())*mm(bb.GetHeight())
cc={n:sum(math.dist(a['a'],a['c']) for a in tracks if a['net']==n) for n in ['USB_CC1','USB_CC2']}
result={'status':'PASS actual saved copper/netlist/contact graph, endpoint and nativeDRC checks; function/thermal/fit UNMET','physical_footprints':len(fs),'purchased_parts':32,'saved_pad_net_checks':padchecks,'tracks':len(tracks),'vias':len(vias),'endpoint_checks':endpoint_checks,'electrical_net_components':{n:len(v) for n,v in components.items()},'independent_track_to_track_foreign_net_clearance_min_mm':minimum,'physical_body_area_including_fabricated_lands_mm2':bodyarea,'complete_courtyard_sum_mm2':courtarea,'PCB_area_mm2':540,'proposed_U3_EP_vias':6,'DRC_rules_exclusions_or_severity_relaxations_added':False,'DRC_new_violations':0,'retained_GCT_NPTH_errors':4,'unconnected':0,'quiet_return_star_and_plane_void_checks':True,'USB_D_SHORT':{'total_copper_length_mm':length,'pairwise_resistance_upper_screen_ohm':res,'copper_min_allocation_um':63,'copper_C':80,'contact_or_open_defect_included':False,'limit_ohm':200},'CC_total_trace_length_mm':cc,'circuit_delta':{'R12':'10kohm EN series required byTPS63070 section11.1','old_U2_14':'PROTECTED_IN','new_U2_14':'REG_EN_SERIES','R13':'100ohm DVDT series perTPS25947 section7.3.5.1; C12max11nF','C12_1':'INPUT_DVDT_C','all_original_values_and_pin_nets_except_two_documented_deltas_unchanged':True},'port_datum':{'PCB_edge_X_mm':27,'center_Y_mm':10,'solder_row_X_mm':22.245,'direction':'+X','body_height_max_mm':3.46},'board_mm':[27,20,1],'all_components_top':True,'release':False}
(P/'routing-check.json').write_text(json.dumps(result,indent=2)+'\n');(P/'physical-geometry.json').write_text(json.dumps({'holes':holes},indent=2)+'\n');print(json.dumps(result,indent=2))
