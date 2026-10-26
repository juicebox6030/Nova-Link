"""Independent literal pin, passive, topology, DC corner/fault/runtime checks.
No generator import. Specifications distinguished from assumptions/gates.
"""
from pathlib import Path
from itertools import product
import xml.etree.ElementTree as E
import re,json,math,hashlib,csv
P=Path(__file__).resolve().parent;root=E.parse(P/'cell-protection.net')
comps={c.attrib['ref']:c for c in root.findall('./components/comp')}
pin={x.attrib['ref']+'.'+x.attrib['pin']:n.attrib['name'].rsplit('/',1)[-1] for n in root.findall('./nets/net') for x in n}
types={x.attrib['ref']+'.'+x.attrib['pin']:x.attrib['pintype'] for n in root.findall('./nets/net') for x in n}
g='GND_USB';v='LIMITED_5V';cp='CAP_POS';tab='CELL_TAB_POS'
expected={
 'U101':{1:None,2:g,3:g,4:'CELL_OV_SENSE',5:v,6:'CHARGER_PERMIT_OD'},
 'U102':{1:'CHARGER_PERMIT_OD',2:g,3:v,4:None,5:v,6:v},
 'U103':{'A1':'CHARGER_IN_PROTECTED','B1':'CHARGER_IN_PROTECTED','A2':v,'B2':v,'C1':g,'C2':'CHARGER_SWITCH_ON'},
 'U104':{1:'CHARGER_IN_PROTECTED',2:'ICHG_PIN',3:'CHARGE_DISABLE',4:g,5:None,6:None,7:'VCHG_FB',8:cp,9:g}}
for ref,mpn in [('U101','TPS3700DDCR'),('U102','TPS3808G33DBVR'),('U103','TPS22963CYZPR'),('U104','BQ25173DSGR')]:
 assert comps[ref].findtext('value')==mpn
 for no,net in expected[ref].items():
  actual=pin.get(ref+'.'+str(no),'')
  assert actual==net if net is not None else actual.startswith('unconnected-'),(ref,no,actual,net)
for key in ['U101.6','U102.1']:assert types[key]=='open_collector'
assert types['X1.3']=='output' # actual existing CE logic represented explicitly
passives={
 'R101':(56500,tab,'CELL_OV_SENSE'),'R102':(10000,'CELL_OV_SENSE',g),
 'R103':(82000,v,'CHARGER_PERMIT_OD'),'R104':(10000,'CHARGER_PERMIT_OD','CHARGER_SWITCH_ON'),'R105':(56000,'CHARGER_SWITCH_ON',g),
 'R201':(22200,cp,'VCHG_FB'),'R202':(10000,'VCHG_FB',g),'R203':(11900,'ICHG_FILTER',g),'R204':(100,'ICHG_PIN','ICHG_FILTER'),
 'C101':('100nF',v,g),'C102':('100nF',v,g),'C103':('1uF',v,g),'C104':('1uF','CHARGER_IN_PROTECTED',g),
 'C201':('1uF','CHARGER_IN_PROTECTED',g),'C202':('1uF',cp,g),'C203':('100nF','ICHG_FILTER',g),
 'F101':('045101.5MRL',tab,cp)}
for ref,(value,a,b) in passives.items():
 val=comps[ref].findtext('value');assert (pin[ref+'.1'],pin[ref+'.2'])==(a,b)
 assert types[ref+'.1']==types[ref+'.2']=='passive'
 if isinstance(value,int):assert float(re.search(r' (\d+)ohm',val)[1])==value
 else:assert value in val
 for r in ['R101','R102','R201','R202']:assert 'BYED' in comps[r].findtext('value') # .1%,10ppm not25ppm
assert len(passives)==17
# Independent fault-path graph: fuse is the ONLY power path between tab and
# protected bus. The deliberately current-limited sense branch is accounted.
tab_nodes={k for k,n in pin.items() if n==tab}
assert tab_nodes=={'X2.1','F101.1','R101.1'},tab_nodes # KiCad netlist omits ERC power flags
assert pin['X3.1']==pin['U104.8']==pin['F101.2']==cp
assert pin['U103.A1']==pin['U104.1']!=v
assert pin['U101.5']==pin['U102.6']==v # independent of protected charger input / AON / MCU
assert pin['U101.4']!=pin['U104.7'] # independent reference and divider
assert all(not comps[x].findtext('footprint') for x in ['X1','X2','X3'])
tol=.001+100*10e-6 # initial0.1% plus allocated100K*10ppm; no lifetime drift bound
def thresholds(top,bottom,refs,bias):
 return [ref*(1+top*(1+a)/(bottom*(1+b)))+i*top*(1+a) for a,b,ref,i in product([-tol,tol],[-tol,tol],refs,[-bias,bias])]
rise=thresholds(56500,10000,[.396,.404],25e-9)
fall=thresholds(56500,10000,[.387,.400],25e-9)
charge=thresholds(22200,10000,[.792,.808],25e-9) # BQ FBbias25nA allocation, not published max
normal_overshoot=.005 # ENGINEERING target requiring measurement; old50mV no longer fits
arm_max=2.533074464609258 # unchanged exported TPS3700 cap-arm rise max, reviewed sibling
rfuse_hot_alloc=.126 # twice0.063 nominal, NOT a specified maximum
ichg_max=330/(12000*(1-.0035)) # conditional KISET use as existing design
assert min(rise)>max(charge)+normal_overshoot+.008
assert max(rise)<2.7
assert min(charge)-ichg_max*rfuse_hot_alloc>arm_max+.006
old_charge_max=2.639335166191044
assert old_charge_max+.05>min(rise) # old healthy overshoot allocation cannot be retained
# ON threshold proof includes both OD leakage plus switch input leakage,
# resistor tolerance (25ppm allocation conservatively.35% here).
rtol=.0035;levels=[]
for a,b,c,leak in product([-rtol,rtol],[-rtol,rtol],[-rtol,rtol],[-.75e-6,.75e-6]):
 pu=82000*(1+a);series=10000*(1+b);pd=56000*(1+c)
 high=3.8357808844058305*pd/(pu+series+pd)+leak/(1/pd+1/(pu+series))
 # Guaranteed supervisor Vpor valid above.8V; below.8 allow output open.
 pre=.8*pd/(pu+series+pd)+leak/(1/pd+1/(pu+series))
 # Output max.4 at1mA; attenuate to meet the switch's stricter.4 atVIN<2.5.
 low=.4*pd/(series+pd)+.15e-6/(1/pd+1/series)
 levels.append((high,pre,low))
assert min(x[0] for x in levels)>1.3+.1
assert max(x[1] for x in levels)<.4-.04
assert max(x[2] for x in levels)<.4-.04
por_sink=(1.3-.2)/(82000*(1-rtol))+.75e-6
assert por_sink<15e-6
# TPS3808G33 max release level includes threshold and hysteresis.
por_rise_max=3.07*(1+.015+.025)
assert por_rise_max<3.8357808844058305-.6
assert .012>.000450*20 # minimum actual-reset delay vs max TPS3700 startup
# Startup delay is an inhibit, never a forced-good SOURCE_VALID interval.
states=[]
for supply_above_reset,monitor_ready,ov,ce,fuse in product([False,True],repeat=5):
 permit=supply_above_reset and monitor_ready and not ov
 switch=permit # OD wired AND, not a software abstract enable
 cell_charge=switch and not ce and fuse
 if ov or not supply_above_reset or not monitor_ready:assert not cell_charge
 states.append({'LIMITED_5V_above_supervisor_release':supply_above_reset,'monitor_startup_complete':monitor_ready,'cell_OV':ov,'existing_CE_disable':ce,'fuse_intact':fuse,'charger_switch':switch,'charge_path':cell_charge})
# Source-independent cell-local output short coverage, exact interruptions.
faults=[
 {'fault':'BQ FB topopen / bottomshort','interruption':'U101 independent cell sense -> U103 OFF -> charger input removed','residual':'Hysteretic retries after falling threshold; no latchedOVP. Max response/overshoot not specified.'},
 {'fault':'BQ IN-OUT short','interruption':'U103 opens upstream5V path after independent cellOV threshold','residual':'U103 disabled reverse blocking applies; leakage/turnoff current maxima not specified. Existing inputbreaker finite current envelope retained.'},
 {'fault':'BQ OUT-GND / boost VIN-GND short','interruption':'F101 in cell-positive power path before branch split','residual':'Clearing against decaying cell current, prospective-current interruption and thermalI2t require tests; nominalI2t not a max.'},
 {'fault':'U103 OUT-GND short','interruption':'Cell path through BQ can blowF101; USB path through U103 remains downstream of existinginputbreaker','residual':'No assertion about BQ reverse-current path impedance or universal fault clearing.'},
 {'fault':'F101 open','interruption':'Cell isolated from all power branches','residual':'No buffer; OVP divider remains cell-connected and current-limited by R101. CAP_POS may still rise on charger output capacitance; existing cap-arm cannot prove fuse continuity and may cycle backup. No protection-good MCU boundary or loader promise is added.'},
 {'fault':'F101 short / bypass copper','interruption':'None for cell shorts','residual':'Single protection-device fault defeats short protection; no all-single-fault claim.'},
 {'fault':'U103 short / ON stuckhigh / U101 wrong reference or R101 open','interruption':'Not independently protected by this singleOVP channel','residual':'BQ normally regulates but a combined charger fault is not covered. R101 short can force nuisance cutoff or stress input.'},
 {'fault':'Cell internalshort / exposed lead ahead ofF101','interruption':'None','residual':'Minimize and insulate tabsegment, route F101 before all branches. Cell internal energy cannot be interrupted externally.'},
 {'fault':'Source absent/brownout','interruption':'U102 pullspermitlow, U103 OFF; no cell-supply control requirement down to1.7V','residual':'Finite response and TPS22963 disabled reverse leakage are physical gates; no boost-fed5V control rail intended.'},
 {'fault':'OVP sense input unpowered/shorttoGND','interruption':'R101 limits sense-path cell current','residual':'Does not provide overvoltage detection under that protection-channel fault.'}]
# Explicit ESR+fuse/trace resistance and added cell-side leakage runtime.
# Constant power P is AFTER protection at boost input. Electronics eta stays.8.
C=15.75;power=1.11/.8;floor=1.705917;esr=.054
cell_sense_max=2.7/(56500*(1-tol))
reverse_leak_alloc=10e-6 # TPS22963 reverse leakage typical-only2.1uA@85; no max claim
cell_self_leak_alloc=45e-6 # Eaton20C after72h hold; not full-temp/earlycharge maximum
leak=cell_sense_max+reverse_leak_alloc+cell_self_leak_alloc
def runtime(start,fuse_r,trace_r=.01,extra=leak,n=20000):
 total_r=esr+fuse_r+trace_r
 end=floor+total_r*power/floor+esr*extra
 def f(v):
  u=v-esr*extra;vb=(u+math.sqrt(u*u-4*total_r*power))/2
  return C/(power/vb+extra)
 if end>=start:return 0
 step=(start-end)/n
 return step/3*(f(end)+f(start)+sum((4 if i%2 else 2)*f(end+i*step) for i in range(1,n)))
start=min(2.448,min(charge)-.1-ichg_max*rfuse_hot_alloc)
nom=runtime(start,.063);hot=runtime(start,rfuse_hot_alloc)
assert abs(nom-runtime(start,.063,n=10000))<1e-7
assert hot>10+2
def forward_runtime():
 # Independent charge-step integration in time, not Simpson energy quadrature.
 vv=start;time=0.;dt=.0001;R=esr+rfuse_hot_alloc+.01
 while True:
  available=vv-esr*leak
  loaded=(available+math.sqrt(available**2-4*R*power))/2
  if loaded<=floor:return time
  vv-=dt*(power/loaded+leak)/C;time+=dt
forward=forward_runtime();assert abs(forward-hot)<.0002
lo,hi=0,.5
for _ in range(45):
 mid=(lo+hi)/2
 if runtime(start,mid)>10:lo=mid
 else:hi=mid
ten_second_fuse_limit=(lo+hi)/2
unprotected=runtime(2.448,0,0,0)
assert abs(unprotected-16.343)<.002
current_floor=power/floor
hot_fuse_W=current_floor**2*rfuse_hot_alloc
def rated_fraction(temp_factor):return current_floor/(1.5*.75*temp_factor)
# Nominal fusing screen is NOT guaranteed transient clearing. 300A interrupt
# at32V from current primary; zero minimumcellESR and min fuseR not provided.
nominal_fault_R=esr+.063+.01
fault_initial=2.448/nominal_fault_R
fault_tau=nominal_fault_R*C
at3A=fault_tau*math.log(fault_initial/3)
assert at3A<5 # explicit counterexample to misusing5s@2x for decaying current
report={
 'status':'PASS literal/DC/static/conditionalruntime checks; protection transient/clearing acceptance UNMET',
 'IC_pin_checks':sum(map(len,expected.values())),'two_terminal_checks':len(passives),'stable_state_cases':len(states),
 'independent_references':True,'software_dependency':False,'OVP_latched':False,
 'thresholds':{'resistor_initial_plus100K_TCR_allowance':tol,'OV_trip_V':[min(rise),max(rise)],'OV_release_envelope_V':[min(fall),max(fall)],'hysteresis':'TI5.5mV typical/12mV max at sense input; no guaranteed minimum. Separate rise/fall extrema are not one device correlated hysteresis.',
  'charger_V':[min(charge),max(charge)],'nominal_charger_V':2.576,'healthy_overshoot_alloc_V':normal_overshoot,'remaining_healthy_nuisance_margin_V':min(rise)-max(charge)-normal_overshoot,
  'fault_overshoot_room_to2p7_V':2.7-max(rise),'charge_FB_bias_A':'25nA engineering allocation, not published full-temp BQ maximum',
  'existing_arm_max_V':arm_max,'arm_min_margin_after_hot_fuse_charge_drop_V':min(charge)-ichg_max*rfuse_hot_alloc-arm_max,'resistor_lifetime_drift_included':False},
 'added_source_current':{'allocated_A':.000250,'resistor_network_max_at5p5V_A':5.5/(82000*(1-rtol)), 'TPS3700_IDD_max_at5V_A':13e-6,'TPS3808_IDD_max_at6p5V_A':6e-6,'TPS22963_IQ_max_at5V_A':96e-6,'full5p5V_max_proven':False,'unclosed':'TPS22963 no5.5V IQ table bound; TPS3808 fixedSENSE current typical-only. 250uA is integration allocation, not guaranteed maximum. Switched2uF input inrush remains unmeasured.'},
 'ON_levels':{'minimum_high_V':min(x[0] for x in levels),'maximum_prePOR_V':max(x[1] for x in levels),'maximum_inhibited_low_V':max(x[2] for x in levels),'POR_lowV_sink_max_A':por_sink,'minimum_reset_hold_s':.012,'TPS3700_max_startup_s':.000450,'TPS3808_rise_max_V':por_rise_max,'POR_ramp_requirement':'TPS3808 Trise>=15us/V perfootnote. Must measure actual independent5V ramp. BelowTPS22963 input1V no functional assertion.'},
 'static_states':states,'faults':faults,
 'runtime':{'cell':'HV1625-2R7256-R','C_F':C,'start_V':start,'requested_2p448V_start_retained':False,'start_derivation':'min(2.448, newcharger_min -100mV historicalreserve -conditional maxcharge*0.126ohm fuseallocation)',
  'loaded_cutoff_V':floor,'load_W':1.11,'electronics_efficiency':.8,'cell_ESR_aged_screen_ohm':esr,'fuse_nominal_ohm':.063,'fuse_hot_alloc_ohm':rfuse_hot_alloc,'extra_trace_alloc_ohm':.01,
  'sense_cell_current_resistor_bound_A':cell_sense_max,'switch_reverse_leak_alloc_A':reverse_leak_alloc,'cell_self_leak_20C72h_reference_A':cell_self_leak_alloc,'runtime_at_nominal_fuse_s':nom,'runtime_at_hot_fuse_alloc_s':hot,'independent100us_time_step_s':forward,'conditional_fuse_resistance_limit_for10s_ohm':ten_second_fuse_limit,'unprotected_requested_basis_s':unprotected,'healthy_10s_guaranteed':False,'fuse_resistance_max_specified':False},
 'fault_current':{'fuse_MPN':'045101.5MRL','nominal_I2t_A2s':.853,'DC_interrupt_primary2025_A_at32V':300,'specified_opening_max_s_at_constant3A':5,'constant1p5A_hold_min_s':4*3600,
  'nominal_fault_initial_A':fault_initial,'nominal_fault_tau_s':fault_tau,'nominal_current_above3A_duration_s':at3A,'interpretation':'Source5s max requires sustained3A; current decays below3A sooner. Cannot turn averageTCC or nominalI2t into a guaranteed clearing integral.',
  'fuse_hot_power_at_cutoff_alloc_W':hot_fuse_W,'cutoff_load_A':current_floor,'minimum_temperature_rerating_factor_after_standard75percent':current_floor/(1.5*.75),'boost_start_max_A':None,'boost_start_I2t_max_A2s':None,'cell_fault_peak_max_A':None},
 'response':{'TPS3700_typ_propagation_s':18e-6,'TPS3700_max_propagation_s':None,'TPS22963_typ_turnoff_s_at5V':2.5e-6,'TPS22963_max_turnoff_s':None,'conditional1p5A_overshoot_time_allowance_s':(2.7-max(rise))*C/1.5,'post_switch_2uF_max_alloc_uF':2*1.1*1.15,'post_cutoff_stored_input_charge_max_alloc_C':2e-6*1.1*1.15*(5.5-max(rise)),'extra_cell_voltage_from_stored_input_charge_alloc_V':2e-6*1.1*1.15*(5.5-max(rise))/C,'closed':False},
 'cell_limits':'2.7V <=65C; 85C needs2.3V derating; neither cold nor full85C operation claimed.118.46J maxreference remains.',
 'concrete_unclosed_source_objections':['TPS3700 tPHL and TPS22963 tOFF are typical-only;2.7V fault overshoot cannot be guaranteed from published maxima.',
 'Littelfuse resistance and meltingI2t are nominal; only5s max at constant200% is published, insufficient for a decaying supercap fault proof.',
 'TPS22963 disabled reverse current has typical-only entries. Added leakage10uA and hotfuse126mohm are test allocations.',
 'Cell leakage45uA applies20C after72h, not fulltemperature/earlycharge maximum. BQ FB bias25nA, healthy5mVovershoot, emptycell charge curve and existing KISET applicability remain conditional. No unconditional runtime/OVP acceptance.'],
 'manufacturing_release':False}
erc=json.loads((P/'erc.json').read_text());assert not any(s['violations'] for s in erc['sheets'])
report['real_ERC_violations']=0;report['ERC_ignored_defaults']=erc['ignored_checks']
(P/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','IC_pin_checks','two_terminal_checks','stable_state_cases','thresholds','ON_levels','runtime','fault_current','response']},indent=2))
