"""Independent numerical proof, reading exported nets/values (not generator).
Specified DC ranges, engineering allocations and unspecified maxima separated.
"""
from pathlib import Path
from itertools import product
import xml.etree.ElementTree as E,json,re,math,runpy
P=Path(__file__).resolve().parent;r=E.parse(P/'qualified15.net')
cs={c.attrib['ref']:c for c in r.findall('./components/comp')}
roles={c.findtext('./fields/field[@name="Role"]'):ref for ref,c in cs.items()}
def resistor(role):
    return float(re.search(r' ([\d.]+)ohm',cs[roles['R_'+role]].findtext('value'))[1])
pin={x.attrib['ref']+'.'+x.attrib['pin']:n.attrib['name'].rsplit('/',1)[-1] for n in r.findall('./nets/net') for x in n}
assert pin['U6.1']=='CC_ALLOW' and pin['U6.5']=='VBUS_RAW'
assert pin['U6.6']==pin['U3.1']==pin['U19.3']=='LIMITED_5V'
assert pin['U5.3']==pin['U3.8']=='CAP_POS'
assert pin['U40.3']==pin['U40.5']=='AON_USB_LIMITED' and pin['U40.6']=='BOOST_3V9'
mux=runpy.run_path(str(P/'mux-mode-proof.py'))
assert pin['U24.1']=='CC_RAW' and pin[roles['R_CC_FEED']+'.1']=='VBUS_RAW'
tol=.001+100*25e-6 # initial0.1% and100K worst25ppm; not RSS.
out={};allcorners=0
for pre in ['CAP','CAP_START','USB','MAIN','RAW','BOOST_MON']:
    vals={}
    for edge,vs in [('rise',(.396,.404)),('fall',(.387,.400))]:
        vv=[]
        for a,b,i,v in product((-tol,tol),(-tol,tol),(-25e-9,25e-9),vs):
            top=resistor(pre+'_TOP')*(1+a);bottom=resistor(pre+'_BOTTOM')*(1+b)
            vv.append(v*(1+top/bottom)+i*top);allcorners+=1
        vals[edge+'_min_V']=min(vv);vals[edge+'_max_V']=max(vv)
    out[pre]=vals
assert allcorners==192
# A source status cannot be sustained by the cap-fed common node. Both raw and
# post-eFuse sides must exceed sourceUV. Back-feed is blocked, not a sensed OR.
assert out['RAW']==out['USB']
assert out['CAP_START']['rise_min_V']>1.8+.3 # TPS61023 guaranteed startup1.8V max + allocation margin.
assert out['CAP_START']['rise_min_V']>out['CAP']['rise_max_V']+.4
assert out['CAP']['fall_min_V']>.5+1.1 # .5V IC run minimum is not cell discharge target.
assert out['MAIN']['fall_min_V']-.05>3.41 # 50mV allocated undershoot, not propagation guarantee.
assert out['BOOST_MON']['rise_max_V']<.580*(1+resistor('BOOST_TOP')*(1-tol)/(resistor('BOOST_BOTTOM')*(1+tol)))-25e-9*resistor('BOOST_TOP')*(1+tol)
# eFuse current table atRILM3.32k, full temperature, default VIN12V test point.
# Apply inverse-resistance tolerance outside tabulated fixed resistor.
assert resistor('EFUSE_ILM')==3320
trip_min=.850/(1+tol);trip_max=1.150/(1-tol)
cc_fault=5.5/(resistor('CC_FEED')*(1-tol))
aon_fault=5.5/(resistor('AON_FEED')*(1-tol))
raw_div=5.5/(resistor('RAW_TOP')+resistor('RAW_BOTTOM'))/(1-tol)
raw_bleed=5.5/resistor('RAW_BLEED')/(1-tol)
cc_detect=5.5/resistor('CC_VBUS')/(1-tol)
efuse_iq=.000610 # specified max atVIN12; applicability at5V is a supplier/bench gate.
direct=cc_fault+aon_fault+raw_div+raw_bleed+cc_detect+efuse_iq
dc_total=trip_max+direct
assert dc_total<1.5-.28
assert direct<.060 # default/invalid mainoff; hard resistor-limited detect/AON current.
# Feed resistor short powers at5.5V: must meet TNPW size rating before any thermal
# derating. CC1206 .25W and AON0805 .125W per e3 datasheet.
assert cc_fault**2*resistor('CC_FEED')*(1-tol)<.25
assert aon_fault**2*resistor('AON_FEED')*(1-tol)<.125
source_floor=out['USB']['fall_min_V']
# RON45mohm eFuse acrossVIN2.7..23V at3A; TPS2116 60mohm at5V/200mA.
# Using mux RON atdifferent current/VIN and eta85% is an allocation, not guarantee.
usb_normal_min=4.4-trip_max*.045
assert usb_normal_min>out['USB']['rise_max_V']+.25
buck_qualified=source_floor-trip_max*.060-.050
assert buck_qualified>3.41+.2
ichg_min=270/(12000*(1+tol));ichg_max=330/(12000*(1-tol))
# KISETaccuracy table testsOUT3.8/7.6, not this0..2.65Vcell; conditionalonly.
normal_buck_input=1.11/.85/buck_qualified
normal_main=normal_buck_input+ichg_max+.003 # BQ and main-divider ancillary allocation3mA.
assert normal_main<trip_min-.40
normal_source=normal_main+.002+.002+efuse_iq+raw_div+raw_bleed+cc_detect
charge_nom_s=15*2.6/.025
charge_corner_s=15*1.3*2.652/ichg_min
# Effective outputC allocation excludes nominal-only bias claims.
ss_min=10e-9*.9*.85*.8/2.7e-6
buck_cmax=20e-6*1.1*1.15
buck_inrush_out=buck_cmax*3.3/ss_min
buck_start_input=(1.11+buck_inrush_out*3.3)/.85/buck_qualified
assert buck_start_input+.003<trip_min-.40
dvd_cmin=10e-9*.9*.85;dvd_cmax=10e-9*1.1*1.15
itimer_min=dvd_cmin*1.286/2.5e-6;itimer_max=dvd_cmax*1.741/1.2e-6
# dVdt current is specified, internal gain/output slew transfer has only a
# typical equation. This is an allocation screen, not a guaranteed maxslew.
slew_alloc=3.82e-6/dvd_cmin
load_c_nom=10e-6+1e-6 # eFuseout+BQin only; conditional on U19 already in manual VIN2 state.
# As AON rises, external-low MODE with PR1low can select VIN1 early. Do not
# guarantee that the20uFcommon is isolated during every input ramp/order.
load_c_max=load_c_nom*1.1*1.15
inrush_alloc=load_c_max*slew_alloc
assert inrush_alloc<.030
common_cmax=20e-6*1.1*1.15
early_common_inrush_alloc=(load_c_max+common_cmax)*slew_alloc
assert early_common_inrush_alloc<.030 # same conditional slew allocation, not a max-current bound
# U19 selection is later than eFuse turnon. Its softstart applies withVOUT<1V
# per7.3.2, but table hastyp1.7ms at5V only, NO minimumramp/currentmax. The
# upstreamdVdt cap cannot be counted as limiting this late capacitance.
common_typ_current=common_cmax*5.5/.0017
assert common_typ_current+buck_start_input<trip_min-.3
common_Q=common_cmax*5.5
OC_duration_charge_bound=common_Q/(trip_min-buck_start_input)
assert OC_duration_charge_bound<itimer_min/10 # conditional backgroundload .390A, not peakbound
# Raw-first AON priority corners; no boost-to-CC path. Reverseleak test atVOUT5.5
# andVINx0/VINyopen; dynamic response has no specified maximum.
priority=[]
for a,b,i,v in product((-tol,tol),(-tol,tol),(-.1e-6,.1e-6),(.92,1.08)):
    t=resistor('AON_PRIORITY_TOP')*(1+a);bot=resistor('AON_PRIORITY_BOTTOM')*(1+b)
    priority.append(v*(1+t/bot)+i*t)
aon_feed_min=4.4-.002*resistor('AON_FEED')*(1+tol)
assert aon_feed_min>max(priority)+.20
assert mux['u40_selection'](pin,aon_feed_min,0,True)=='VIN1'
assert mux['u40_selection'](pin,aon_feed_min,3.9,True)=='VIN1'
assert mux['u40_selection'](pin,0,3.9,False)=='VIN2'
assert mux['u40_selection'](pin,0,0,False)=='unpowered'
raw_backfeed=.15e-6*resistor('RAW_BLEED')*(1+tol)
# Direct TPS3808G33 ODreset drives EN: no gate with unspecified sub1.65V
# output is allowed to enable eFuse. Leakage and valid-reset load calculated.
assert cs['U26'].findtext('value')=='TPS3808G33DBVR'
assert pin['U26.1']==pin['U6.1']=='CC_ALLOW' and pin['U26.3']=='CC_ADVERT_OK'
assert pin['U26.5']==pin['U26.6']=='CC_3V3'
rpu=resistor('CC_ALLOW_PU');rpd=resistor('CC_ALLOW_PD');bleed=resistor('CC_BLEED')
assert (rpu,rpd)==(115000,249000)
# Include worst AONlogicinput5uA, eFuseEN.1uA, and allrawRCB.15uA
# conservatively injected at the enable node even though somegoes rawbleed.
leak_off=5.25e-6
off_r=1/(1/rpd+1/(rpu+bleed))*(1+tol)
cc_allow_off=leak_off*off_r
assert raw_backfeed<.002 and cc_allow_off<.45
cc_off_rail=leak_off*rpd/(rpu+rpd+bleed)*bleed*(1+tol)+raw_backfeed
assert cc_off_rail<.05
high=[]
for a,b,i in product((-tol,tol),(-tol,tol),(-5.4e-6,5.4e-6)):
    u=rpu*(1+a);d=rpd*(1+b);high.append(3.3*.98*d/(u+d)+i/(1/u+1/d))
cc_high_min=min(high)
assert cc_high_min>1.7+.07 and cc_high_min>1.223+.5
# Below.8V even an open RESET cannot raise EN aboveUVLO. From.8..1.3,
# supervisor VOL<=.2V at15uA; worstexternal sink current stays below15uA.
# At1.3..1.8 VOL<=.3 at.4mA, above1.8 VOL<=.4 at1mA, all <VSDmin.45.
cc_prepor_max=.8*rpd*(1+tol)/(rpu*(1-tol)+rpd*(1+tol))+leak_off/(1/(rpu*(1+tol))+1/(rpd*(1+tol)))
por_sink_max=(1.3-.2)/(rpu*(1-tol))+leak_off # omit helpfulpulldown
assert cc_prepor_max<1.183 and por_sink_max<15e-6
cc_reset_rise_max=3.07*(1+.015+.025)
assert 3.3*.98>cc_reset_rise_max+.04
# Historical conservative reserve includes TPS61094's100mVtermination droop,
# even though BQ25173 stays CV and has no termination. Not a newBQ hysteresis spec.
cmin=15*.9*.7;start=2.6*.98-.100;floor=out['CAP']['fall_max_V']
runtime=cmin*(start*start-floor*floor)/2*.8/1.11
assert 10.4<runtime<10.6
# Arm only nearfullcharge. Loaded runtime still depends onESR/eta; this is not
# an exported/guaranteed ten-second energyqualification.
firstarm_runtime=cmin*(out['CAP_START']['rise_min_V']**2-floor**2)/2*.8/1.11
assert firstarm_runtime>runtime
# Additional explicit ESR screen:80% electronics efficiency BEFOREcellESR.
# This is distinct from the historical80%combined-efficiency assumption.
# Eaton maxinitialESR30mohm at20C, EOL200%=60mohm; colder unknown.
def esr_runtime(esr,eta=.8):
    power=1.11/eta;end=floor+esr*power/floor;n=10000;h=(start-end)/n
    def f(v):return (v+math.sqrt(v*v-4*esr*power))/2
    return cmin/power*h/3*(f(end)+f(start)+sum((4 if i%2 else 2)*f(end+i*h) for i in range(1,n)))
assert 9<esr_runtime(.06)<10
vchg=[]
for a,b,i,v in product((-tol,tol),(-tol,tol),(-25e-9,25e-9),(.792,.808)):
    top=resistor('VCHG_TOP')*(1+a);bot=resistor('VCHG_BOTTOM')*(1+b)
    vchg.append(v*(1+top/bot)+i*top)
assert min(vchg)>out['CAP_START']['rise_max_V']+.025
assert max(vchg)+.05<2.7 # includes50mV allocated overshoot, not guaranteed FBbias.
report={'status':'PASS enumerated DC inequalities + explicitly conditional engineering screens; no transient/USB/release guarantee',
 'threshold_corners':allcorners,'thresholds':out,'resistor_total_allowance':tol,
 'source_current':{'advertised_A':1.5,'main_trip_min_A':trip_min,'main_trip_max_A':trip_max,'raw_feeds_fault_max_A':direct,'steady_trip_plus_raw_A':dc_total,'margin_to_1p5_A':1.5-dc_total,'default_mainoff_resistor_limited_A':direct,'instantaneous_max_A':None,'quiescent_test_limit':'TPS25947 IQ610uA atVIN12V, not a published full-range5V max; other unbounded dynamic current not included','finite_fault':'Circuitbreaker ITIMER finite interval allows overload; fasttrip ratios/response times typical only. No instantaneous1.5A claim.'},
 'healthy_allocations':{'buck_input_min_if_source_good_V':buck_qualified,'normal_raw_min_V':usb_normal_min,'main_normal_input_A':normal_main,'normal_source_A':normal_source,'headroom_to_min_trip_A':trip_min-normal_main,'application_load_W':1.11,'buck_efficiency':.85,'buck_start_input_A':buck_start_input,'buck_softstart_min_screen_s':ss_min,'eFuse_initial_C_nom_uF':load_c_nom*1e6,'eFuse_initial_C_max_alloc_uF':load_c_max*1e6,'eFuse_slew_alloc_V_s':slew_alloc,'eFuse_cap_inrush_alloc_A':inrush_alloc,'eFuse_slew_guaranteed':False,'later_mux_common_C_max_alloc_uF':common_cmax*1e6,'later_mux_common_inrush_typ5V1p7ms_screen_A':common_typ_current,'later_mux_common_inrush_max_A':None,'later_mux_charge_C':common_Q,'later_mux_continuous_OC_time_charge_bound_s_conditional':OC_duration_charge_bound,'recovery_live_mux_charge_max_A':None,'inrush_boundary':'eFuse dVdt controlsinitial11uF only, NOT later20uFmainmux common precharge orlivebackup-to-USBhandoff. ThosehaveNOspecifiedmaximumcurrent.','ITIMER_cap_formula_min_s':itimer_min,'ITIMER_cap_formula_max_s':itimer_max,'ITIMER_total_shutdown_max_guaranteed':False},
 'charge':{'nominal_A':.025,'conditional_min_A':ichg_min,'conditional_max_A':ichg_max,'nominal_empty_to2p6_min_before_tail':charge_nom_s/60,'corner_empty_to2p652_min_before_tail':charge_corner_s/60,'regulation_min_with25nA_bias_allocation_V':min(vchg),'regulation_max_with25nA_bias_allocation_V':max(vchg),'guaranteed':False,'gate':'KISET has270..330 generalrow but accuracy rows onlyOUT3.8/7.6 and ICHG_RANGE refers to undefinedVBAT_LOWV; empty-cell curve is typical. FBbias fulltemp max absent; thermal/dropout/leakage/tail require validation'},
 'off_and_AON':{'priority_max_V':max(priority),'priority_min_V':min(priority),'raw_feed_under2mA_allocation_min_V':aon_feed_min,'raw_voltage_reverseleak_test_V':raw_backfeed,'CC_ALLOW_off_leak_bound_V':cc_allow_off,'CC_3V3_off_leak_bound_V':cc_off_rail,'CC_ALLOW_high_min_V':cc_high_min,'CC_ALLOW_prePOR_max_V':cc_prepor_max,'CC_supervisor_lowV_sink_max_A':por_sink_max,'CC_supervisor_rising_max_V':cc_reset_rise_max,'VPOR_condition':'TPS3808 Trise>=15us/V; actualramp measurementgate, alongside TUSB<=25ms ramp','reverse_transient_max_s':None},
 'runtime':{'conditional_s':runtime,'first_arm_conditional_s':firstarm_runtime,'explicit_ESR_electronics_eta0p8':{'initial30mohm_s':esr_runtime(.03),'aged60mohm_s':esr_runtime(.06)},'capacitance_F':cmin,'start_V':start,'loaded_floor_V':floor,'efficiency':.8,'load_W':1.11,'historical_extra_start_reserve_V':.1,'guaranteed':False,'gate':'10.50 uses80%combined efficiency. If80%electronics BEFORE60mohmcellESR, only9.73s. Cold/aging/lowVINefficiency andRF+DMXload unmeasured; armisNOTguaranteed10sready, bothradios shareoneCC1352R'},
 'unclosed_maxima':['CC VDD ramp25ms and debounce/downgrade response','eFuse transfer/slew, peak and fault-response maxima','TPS61023 startup current/time and PFM voltage upper bound','TPS2116 switchover/RCB timing and effectiveC ride-through','sub1.65V AON logic and SR propagation hazards','bootload, current/thermal, capESR, RF/DMX, USB compliance'],
 'manufacturing_release':False}
report['healthy_allocations']['early_U19_common_plus_initial_C_max_alloc_uF']=(load_c_max+common_cmax)*1e6
report['healthy_allocations']['early_U19_cap_inrush_alloc_A']=early_common_inrush_alloc
report['healthy_allocations']['initial_C_assumption']='11uF screen requires U19 already in manual VIN2 state; at low AON, MODE<=.35V/PR1low can connect VIN1 early, adding20uF common (31uFnominal total). Neither sequencing order nor slew maximum is guaranteed.'
report['off_and_AON']['MODE_connection']='U40.5=U40.3=AON_USB_LIMITED; priority mode per7.3.1, independently evaluated for coldboot/reattach/detach'
report['off_and_AON']['priority_margin_under2mA_allocation_V']=aon_feed_min-max(priority)
(P/'corner-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
