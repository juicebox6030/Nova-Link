"""Independent exported-circuit/static/corner checks; does not import generators.

PASS means the enumerated checks pass. Unspecified transient limits remain UNMET.
"""
from pathlib import Path
from itertools import product
import xml.etree.ElementTree as E
import hashlib,json,math,csv,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='b42c0e6284aac734fde851c69146abf73920f337'
assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
protected=json.loads((P/'protected-inputs.json').read_text())
preservation_deltas=[name for name,digest in protected.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
# Concurrent parent-owned documentation change is reported, never silently accepted.
# Any protected electrical/mechanical/source change stops the electrical checks.
assert all(name=='hardware/compact-dmx/README.md' for name in preservation_deltas),preservation_deltas
t=E.parse(P/'source12.net');comps={c.attrib['ref']:c for c in t.findall('./components/comp')}
nodes={(n.attrib['ref'],n.attrib['pin']):(net.attrib['name'].rsplit('/',1)[-1],n.attrib['pintype'].split('+')[0]) for net in t.findall('./nets/net') for n in net}
g='GND_ISO';raw='MODULE12_UNPROTECTED';vin='FPC12_PROTECTED';v='BUCK5_18';s='SAFE5_18';usb='USB_VBUS'
expected={
 'U1':{1:'SOURCE_UVLO',2:'SOURCE_OVLO',3:None,4:g,5:raw,6:vin,7:'SOURCE_DVDT',8:g,9:'SOURCE_ILM',10:None},
 'U2':{1:vin,2:'SW',3:g,4:None,5:'REG_FB',6:v,7:'PORT_ENABLE',8:'REG_EN',9:'REG_SS',10:vin,11:g},
 'U3':{1:'PORT_FAULT_N',2:s,3:s,4:s,5:s,6:'PORT_ENABLE',7:s,8:g,9:'REF_RTN',10:'REF',11:'USB_CC1',12:g,13:'USB_CC2',14:usb,15:usb,16:None,17:None,18:None,19:None,20:None,21:g},
 'U4':{1:g,2:'PORT_ENABLE',3:'SAFE_PGTH',**{i:s for i in range(4,9)},**{i:v for i in range(9,14)},14:'BARRIER_EN',15:'BACKSTOP_OVP',16:g,17:'BARRIER_ILIM',18:'BARRIER_DVDT',19:None,20:'PROTECT_FAULT_N',21:g},
 'U5':{1:'BARRIER_EN',2:g,3:'BUCK_UV_SENSE',4:'BUCK_OV_SENSE',5:vin,6:'BARRIER_EN'},
 'J1':{'A1_B12':g,'B1_A12':g,'A4_B9':usb,'B4_A9':usb,'A5':'USB_CC1','B5':'USB_CC2','A6':'USB_D_SHORT','A7':'USB_D_SHORT','B6':'USB_D_SHORT','B7':'USB_D_SHORT','A8':None,'B8':None,**{f'S{i}':g for i in range(1,5)}},
 'J0':{1:raw,2:g},'J2':{1:vin,2:g},'J3':{1:vin,2:g},'L1':{1:'SW',2:v},'D1':{1:usb,2:g},'TP1':{1:'PORT_FAULT_N'},'TP2':{1:'PROTECT_FAULT_N'}}
values={'U1':'TPS259474LRPWR','U2':'TPS62135RGXR','U3':'TPS25810RVCR','U4':'TPS25940LRVCR','U5':'TPS3700DDCR','J1':'USB4105-GF-A','L1':'XAL4020-152MEC 1.5uH','D1':'TPD1E10B06DPYR'}
res=[(68100,raw,'SOURCE_UVLO'),(10000,'SOURCE_UVLO',g),(100000,raw,'SOURCE_OVLO'),(9090,'SOURCE_OVLO',g),(2000,'SOURCE_ILM',g),(100,'SOURCE_DVDT','SOURCE_DVDT_C'),(64000,v,'REG_FB'),(10000,'REG_FB',g),(100000,vin,'REG_EN'),(10000,'REG_EN',g),(100000,v,'BUCK_UV_SENSE'),(9090,'BUCK_UV_SENSE',g),(100000,v,'BUCK_OV_SENSE'),(8000,'BUCK_OV_SENSE',g),(100000,v,'BARRIER_EN'),(100000,'BARRIER_EN',g),(100000,v,'BACKSTOP_OVP'),(20000,'BACKSTOP_OVP',g),(24900,'BARRIER_ILIM',g),(37400,s,'SAFE_PGTH'),(10000,'SAFE_PGTH',g),(100000,s,'PORT_ENABLE'),(100000,'PORT_ENABLE',g),(100000,'REF','REF_RTN'),(100000,s,'PORT_FAULT_N'),(100000,s,'PROTECT_FAULT_N'),(10000,s,g)]
for i,(ohm,a,b) in enumerate(res,1):
 ref=f'R{i}';expected[ref]={1:a,2:b};assert comps[ref].findtext('value').endswith(' '+str(ohm)+'ohm') and comps[ref].findtext('value').startswith('TNPW0402')
caps=[('MSAST21GBB5106MTNA01 10uF',raw),('MSAST21GBB5106MTNA01 10uF',vin),('MSAST21GBB5106MTNA01 10uF',vin),('MSASE21GBB5226MTNA01 22uF',v),('MSASE21GBB5226MTNA01 22uF',v),('T520D157M010ATE055 150uF',s),('MSAST21GBB5106MTNA01 10uF',usb),('TMK105B7104MV-FR 100nF',s),('TMK105B7104MV-FR 100nF',vin),('GRM155R71E103KA01D 10nF','REG_SS'),('GRM155R71E103KA01D 10nF','SOURCE_DVDT_C'),('GRM155R71E103KA01D 10nF','BARRIER_DVDT'),('GRM155R71E103KA01D 10nF','BARRIER_DVDT'),('TMK105B7104MV-FR 100nF',raw),('TMK105B7104MV-FR 100nF',vin),('TMK105B7104MV-FR 100nF',v),('TMK105B7104MV-FR 100nF',s)]
for i,(value,net) in enumerate(caps,1):expected[f'C{i}']={1:net,2:g};values[f'C{i}']=value
for ref,value in values.items():assert comps[ref].findtext('value')==value,(ref,value)
for ref,pins in expected.items():
 for no,net in pins.items():
  actual,typ=nodes[(ref,str(no))]
  assert (actual.startswith('unconnected-') if net is None else actual==net),(ref,no,actual,net)
  if ref[0] in ['R','C','L','D','J','T']:assert typ=='passive'
for ref,pins in {'U1':[3],'U2':[4,7],'U3':[1,16,17,18,19,20],'U4':[2,20],'U5':[1,6]}.items():
 for pin in pins:assert nodes[(ref,str(pin))][1]=='open_collector'
for ref,pin in [('U1',5),('U2',1),('U2',3),('U3',2),('U3',4),('U3',5),('U4',9),('U4',21),('U5',5)]:assert nodes[(ref,str(pin))][1]=='power_in'
for ref,pin in [('U1',6),('U2',2),('U3',14),('U4',4)]:assert nodes[(ref,str(pin))][1]=='power_out'
types={
 'U1':{i:('power_in' if i in [5,8] else 'power_out' if i==6 else 'open_collector' if i==3 else 'input') for i in range(1,11)},
 'U2':{i:('power_in' if i in [1,3] else 'power_out' if i==2 else 'open_collector' if i in [4,7] else 'input') for i in range(1,12)},
 'U3':{i:('power_in' if i in [2,4,5,12,21] else 'passive' if i in [3,9,10,15] else 'power_out' if i==14 else 'bidirectional' if i in [11,13] else 'open_collector' if i in [1,16,17,18,19,20] else 'input') for i in range(1,22)},
 'U4':{i:('power_in' if i in [9,16,21] else 'power_out' if i==4 else 'passive' if i in [5,6,7,8,10,11,12,13] else 'open_collector' if i in [2,20] else 'output' if i==19 else 'input') for i in range(1,22)},
 'U5':{i:('power_in' if i in [2,5] else 'open_collector' if i in [1,6] else 'input') for i in range(1,7)}}
for ref,pins in types.items():
 for pin,typ in pins.items():assert nodes[(ref,str(pin))][1]==typ,(ref,pin,typ)
assert len(comps)==57 and len(expected)==57
assert nodes[('L1','1')][0]==nodes[('U2','2')][0] and nodes[('L1','2')][0]==nodes[('U4','9')][0]
# No circuit flags, NC changes, hidden ERC overrides or firmware stand in for a barrier.
sch=(P/'source12.kicad_sch').read_text();assert sch.count('(reference "#FLG')==3
erc=json.loads((P/'erc.json').read_text());assert not any(x['violations'] for x in erc['sheets'])

tol=.002 # 0.1% initial + 10ppm/K *100K allocation, no life drift
def divider(top,bottom,refs,bias):
 a=[r*(1+top*(1+x)/(bottom*(1+y)))+i*top*(1+x) for r,x,y,i in product(refs,[-tol,tol],[-tol,tol],[-bias,bias])]
 return min(a),max(a)
reg=divider(64000,10000,[.693,.707],70e-9)
uv=divider(100000,9090,[.396,.404],25e-9);ov=divider(100000,8000,[.396,.404],25e-9)
uvfall=divider(100000,9090,[.387,.400],25e-9);ovfall=divider(100000,8000,[.387,.400],25e-9)
back=divider(100000,20000,[.97,1.01],100e-9)
srcuv=divider(68100,10000,[1.183,1.223],100e-9);srcuvfall=divider(68100,10000,[1.076,1.116],100e-9)
srcov=divider(100000,9090,[1.183,1.223],100e-9);srcovfall=divider(100000,9090,[1.076,1.116],100e-9)
pg=divider(37400,10000,[.97,1.01],100e-9)
normal=1.5+.410+.010;fault=1.82+.410+.010
portlo=reg[0]-.064*normal-1.5*(.055+.020+.025)-.050;porthi=reg[1]+.050
assert 4.75<portlo<porthi<5.5 and reg[1]+.05<ov[0] and reg[0]-.05>uv[1]
assert reg[0]-.05-.064*normal>pg[1] and ov[1]<5.5<back[0]
# U1 formula accuracy is +/-10% >1A, NOT an instantaneous fault-current ceiling.
breaker=(3334/2000*.9/(1+tol),3334/2000*1.1/(1-tol))
barrier_overload=(3.25/(1+tol),3.81/(1-tol)) # published24.9k, drop1V test
barrier_short=(3.21/(1+tol),3.77/(1-tol)) # separate published12V/drop5V test
source_min=12*.975-12*.0003*25-.200;source_max=12*1.025+12*.0003*25+.200
assert source_min>srcuv[1] and source_max<srcovfall[0] and srcov[1]<16.2<17<18<20<23
pin_limits={'U1_EN_at16p2_max_V':16.2*(10000*(1+tol))/(68100*(1-tol)+10000*(1+tol)),
 'U1_OVLO_at16p2_max_V':16.2*(9090*(1+tol))/(100000*(1-tol)+9090*(1+tol)),
 'U5_INA_at16p2_max_V':16.2*(9090*(1+tol))/(100000*(1-tol)+9090*(1+tol)),
 'U5_INB_at16p2_max_V':16.2*(8000*(1+tol))/(100000*(1-tol)+8000*(1+tol)),
 'SAFE5_healthy_min_V':reg[0]-.05-.064*normal,'SAFE5_healthy_max_V':reg[1]+.05,
 'U4_EN_low_max_V':.25,'U4_EN_high_min_V':reg[0]*(1-tol)/2-.7e-6*50100}
assert pin_limits['U1_EN_at16p2_max_V']<5 and pin_limits['U1_OVLO_at16p2_max_V']<1.5
assert max(pin_limits['U5_INA_at16p2_max_V'],pin_limits['U5_INB_at16p2_max_V'])<6.5
assert 4.5<pin_limits['SAFE5_healthy_min_V']<pin_limits['SAFE5_healthy_max_V']<5.5
assert pin_limits['U4_EN_low_max_V']<.9 and pin_limits['U4_EN_high_min_V']>1.01
length=1.046167656;flexR=2*length*1.75e-8/(.0078*70e-6*.9)*(1+.00393*60)
R=flexR+.020+.045+.01625024565988206+.00496436883132149
corners=[]
for vs,eff,load in product([source_min,source_max],[.8,.85,.9],[normal,fault]):
 power=reg[1]*load/eff # conditional efficiency, not published minimum
 # Include2mA input auxiliary separately in nonlinear constant-power solution.
 I=.002
 for _ in range(100):I=power/(vs-I*R)+.002
 assert abs((I-.002)*(vs-I*R)-power)<1e-10
 vinmin=vs-I*R;assert vinmin>reg[1]+1 and I<breaker[0] and I<1.8 and load<4
 ripple=(reg[1]*(1-reg[1]/vinmin))/(1.8e6*(1.5e-6*.8*.9)) # f1.8MHz and90% biasL engineering screens
 corners.append({'source_V':vs,'efficiency_assumption':eff,'buck_output_A':load,'FPC_A':I,'buck_input_V':vinmin,'breaker_floor_margin_A':breaker[0]-I,'module1p8A_margin_A':1.8-I,'flex_copper_W':I*I*flexR,'full_path_W':I*I*R,'buck_loss_alloc_W':reg[1]*load*(1/eff-1),'inductor_peak_engineering_A':load+ripple/2})
worst=max(corners,key=lambda x:x['FPC_A']);assert max(c['inductor_peak_engineering_A'] for c in corners)<4.8
reg_en_min=min(c['buck_input_V'] for c in corners)*(10000*(1-tol))/(100000*(1+tol)+10000*(1-tol))-.001
assert reg_en_min>.83;pin_limits['buck_EN_healthy_min_V']=reg_en_min
# Fault-path static state table. Powered valid monitor = settled >450us after VDD>=1.8V.
states=[]
for supply,buck,settled in product([0,5,11.41,12.59,16.2],[0,5.18,5.6,12,16.2],[False,True]):
 input_on=srcuv[1]<supply<srcovfall[0]
 monitor_valid=input_on and settled
 if buck>back[1]:barrier='OFF internal OVP, independent of monitor'
 elif not monitor_valid:barrier='UNKNOWN monitor unpowered/starting; no5p5V startup claim'
 elif buck<uvfall[0] or buck>ov[1]:barrier='OFF'
 elif uv[1]<buck<ovfall[0]:barrier='ON'
 else:barrier='HYSTERESIS/threshold interval'
 if buck>back[1]:assert barrier!='ON'
 states.append({'source_V':supply,'buck_forced_V':buck,'monitor_settled':settled,'input_path_healthy_DC_enabled':input_on,'monitor_powered_in_steady_state':input_on,'output_barrier':barrier,'external_source_good_exported':False})
assert all(x['output_barrier'].startswith('OFF') for x in states if x['monitor_settled'] and x['input_path_healthy_DC_enabled'] and x['buck_forced_V'] in [0,5.6,12,16.2])
assert all(x['output_barrier'].startswith('OFF') for x in states if x['buck_forced_V'] in [12,16.2])
assert any(x['output_barrier'].startswith('UNKNOWN') for x in states) # must not silently qualify startup
# EN low/high with published recommended TPS25810 limits. U2 PG low max0.4V,
# U4 PGOOD Ron max35ohm at5mA. Pullups are <=5.5/100k, far below test current.
enlo=.4;enhi=(reg[0]-.064*normal)*(1-tol)/2-.7e-6*50100
assert enlo<.63 and enhi>1.17
cc=[('open','open',False,None),('Rd','open',True,None),('open','Rd',True,None),('Rd','Ra',True,'CC2'),('Ra','Rd',True,'CC1'),('open','Ra',False,None),('Ra','open',False,None),('Rd','Rd',False,None),('Ra','Ra',False,None)]
ccrows=[{'enable':enabled,'CC1':a,'CC2':b,'VBUS':enabled and attach,'VCONN':vc if enabled and attach else None,'advert_A':1.5 if enabled else None} for enabled,(a,b,attach,vc) in product([False,True],cc)]
# A threshold below5.5 does NOT establish a transient voltage ceiling.
bulk_min=150e-6*.8;headroom=5.5-ov[1];Q=bulk_min*headroom
deadline=Q/barrier_overload[1];typical_dv=barrier_overload[1]*20e-6/bulk_min
assert deadline<1e-6 and ov[1]+typical_dv>5.5
# Required negative evidence: thresholds alone fail to constrain transient surge;
# removing the actual series barrier passes a sustained12V fault directly to USB.
negative_tests={'no_series_barrier_12V_fault_exceeds_USB_abs7V':12>7,'static_trip_below5p5_does_not_prove20us_fault_below5p5':ov[1]<5.5 and ov[1]+typical_dv>5.5,'PG_threshold_not_source_valid':pg[0]<4.75,'unsettled_monitor_not_promoted_to_valid':any(x['output_barrier'].startswith('UNKNOWN') for x in states)}
assert all(negative_tests.values())
report={'revision':'S12-R1','status':'PASS exported literal/static/conditional checks; transient OVP protection and manufacturing qualification UNMET','protected_inputs_verified':len(protected)-len(preservation_deltas),'unaccepted_external_preservation_deltas':preservation_deltas,'physical_components':len(comps),'purchased_components':52,'IC_pins_literal':sum(len(expected[x]) for x in ['U1','U2','U3','U4','U5']),'USB_physical_lands':16,'all_exported_nodes_checked':len(nodes),'resistors_checked':27,'capacitors_checked':17,
 'regulation':{'nominal_V':5.18,'reference_divider_bias_corners_V':reg,'resistor_fractional_allocation':tol,'one_sided_line_load_ripple_transient_alloc_V':.050,'conditional_port_V':[portlo,porthi],'conditional_OVP_nonnuisance_margin_V':ov[0]-reg[1]-.05,'output_aux_alloc_A':.010,'input_aux_alloc_A':.002,'healthy_stress_A':normal,'VBUS_limit_fault_stress_A':fault,'current_rating_healthy_VCONN_recommended_A':.250,'VCONN_0p410_is_fault_stress_not_healthy_entitlement':True,'line_load_ripple_efficiency_or_connector_R_guaranteed':False},
 'thresholds_V':{'source_UV_rise':srcuv,'source_UV_fall':srcuvfall,'source_OV_rise':srcov,'source_OV_fall':srcovfall,'buck_UV_rise':uv,'buck_UV_fall':uvfall,'buck_OV_rise':ov,'buck_OV_fall':ovfall,'output_internal_OVP_backstop':back,'safe_PG_rise':pg,'TPS3700_input_bias_scope':'25nA both inputs is a conservative engineering allocation from INA6.5V max25nA and INB0.1V max15nA testpoints. Full bias behavior at0.4V needs confirmation; not an invented guaranteed full-bias limit.'},
 'current_paths':{'source_breaker_formula_A':breaker,'output_overload_test_A':barrier_overload,'output_short_test_A':barrier_short,'full_path_R_ohm':R,'flex_loop_R_ohm':flexR,'tail_R_ohm':.01625024565988206,'stationary_wire_R_ohm':.00496436883132149,'source_healthy_screen_V':[source_min,source_max],'corners':corners,'worst':worst,'breaker_neither_instantaneous_nor_FPC_I2t_proof':True},
 'state_rows':states,'CC_rows':ccrows,'negative_tests':negative_tests,'pin_operating_limit_screen':pin_limits,'port_enable_V':[enlo,enhi],'recommended_EN_limits_V':[.63,1.17],
 'output_fault_energy':{'min_polymer_C_25C_tolerance_only_F':bulk_min,'headroom_at_latest_static_trip_to5p5_V':headroom,'remaining_charge_C':Q,'time_if_current_at_overload_max_s':deadline,'illustrative20us_at_testlimit_deltaV':typical_dv,'max_response_spec_s':None,'overshoot_or_USB_pin_survival_guaranteed':False,'source_note':'TPS3700 propagation18/29us typical only; TPS25940 OVP2us typical to FLT, not isolation. Current limits also have delays. 20us illustration is not a bound.'},
 'startup':{'U5_correct_output_startup_max_s':450e-6,'buck_SS_nominal_s':.7*10e-9/2.5e-6,'buck_SS_current_minmax_guaranteed':False,'output_slew_gain_spec':[11.65,12.05],'output_dvdt_I_A':[.85e-6,1.15e-6],'output_slew_max_model_V_per_s':12.05*1.15e-6/18e-9,'output_polymer_only_inrush_max_model_A':180e-6*12.05*1.15e-6/18e-9,'healthy_cold_start_transient_proven':False},
 'effective_caps':{'input_nominal_uF':20,'input3uF_min_required':True,'input_effective_uF_if80percent_total_bias_temp_loss_after_tol':20*.8*.2,'output_direct_effective_uF_same_assumption':44*.8*.2,'vendor_guaranteed_bias_temp_minimum':False,'polymer_and_switched_bank_loop_stability_proven':False},
 'gates':['OVP response/injected energy into USB must be bounded by additional evidence; static barrier is not5.5V transient qualification','Effective ceramic capacitance at bias/temp, inductor hot saturation, compensation/stability and distributed load capacitance','Startup/inrush/hotplug/brownout/detach/rebound/reverse and unloaded forcedPWM energy, including USB backdrive','FPC/clamps/trace I2t/current capability, module transient/overload coordination; latch reset behavior','Routing, hot-loop/Kelvin/thermal copper, sealed collar thermal, EMI/ESD and USB electrical/compliance','Supplier land/stencil/component heights and connector PCB1mm/stake/NPTH process; allocation is not integrated fit','Stationary sourcepod insulation, mains/PE/endcaps/install guidance and line/temperature derating'],
 'manufacturing_release':False}
(P/'electrical-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','protected_inputs_verified','physical_components','IC_pins_literal','all_exported_nodes_checked','regulation','thresholds_V','output_fault_energy']},indent=2))
print('Worst conditional FPC current',worst['FPC_A'],'A; margin',worst['breaker_floor_margin_A'],'A')
