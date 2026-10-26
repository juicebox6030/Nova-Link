"""Independent candidate DC/corner/state-current budgets from exported netlist.
All transient-time calculations below are explicitly conditional allocations.
No import of generator, active budget or state verifier.
"""
from pathlib import Path
import itertools,json,math,re,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent
root=E.parse(P/'separated-candidate.net');vals={x.attrib['ref']:x.findtext('value') for x in root.findall('./components/comp')}
def R(ref):return float(re.search(r' (\d+)ohm',vals[ref])[1])
tol=.001+100*25e-6
assert R('R_ILIM')==61900 and R('R_AON_USB')==330
imin=25230/(R('R_ILIM')/1000*(1+tol))**1.016
imax=22980/(R('R_ILIM')/1000*(1-tol))**.940
raw_resistor_max=5.5/(R('R_AON_USB')*(1-tol))*1000
raw_monitor_max=5.5/(R('R_RAW_TOP')+R('R_RAW_BOTTOM'))/(1-tol)*1000
raw_monitor_max+=5.5/(R('R_RAW_PRESENT_TOP')+R('R_RAW_PRESENT_BOTTOM'))/(1-tol)*1000
raw_monitor_max+=5.5/R('R_RAW_BLEED')/(1-tol)*1000
whole_dc_max=imax+.140+raw_resistor_max+raw_monitor_max
assert whole_dc_max<500
# Worst mux/limiter Ron are specified at particular test conditions; extrapolation
# to all currents/low VIN is an engineering allocation, not a new guarantee.
normal_floor=4.4-imax*.001*(.135+.060)
usb_side_floor=4.4-imax*.001*.135
curr_min=270/((R('R_ICHG')+R('R_ICHG_FILTER'))*(1+tol))
curr_max=330/((R('R_ICHG')+R('R_ICHG_FILTER'))*(1-tol))
assert math.isclose(R('R_ICHG')+R('R_ICHG_FILTER'),12000)
thresholds={};count=0
for name,pre in [('raw','RAW'),('raw_present','RAW_PRESENT'),('usb','USB'),('main','MAIN'),('cap','CAP'),('cap_start','CAP_START'),('chgin','CHGIN'),('boost_ready','BOOST_MON')]:
    corners=[]
    for edge,vts in [('rise',(.396,.404)),('fall',(.387,.400))]:
        for te,be,ib,vt in itertools.product((-tol,tol),(-tol,tol),(-25e-9,25e-9),vts):
            top=R('R_'+pre+'_TOP')*(1+te);bottom=R('R_'+pre+'_BOTTOM')*(1+be)
            corners.append((edge,vt*(1+top/bottom)+ib*top))
    thresholds[name]={edge+'_'+which+'_V':fn(v for e,v in corners if e==edge) for edge in ('rise','fall') for which,fn in [('min',min),('max',max)]}
    count+=len(corners)
assert thresholds['raw_present']['rise_max_V']<thresholds['raw']['fall_min_V']
assert thresholds['cap_start']['fall_min_V']>thresholds['cap']['rise_max_V']
assert thresholds['cap_start']['rise_min_V']>1.8+.30
assert usb_side_floor>thresholds['usb']['rise_max_V']+.10
assert 4.4>thresholds['raw']['rise_max_V']+.30
assert thresholds['main']['fall_min_V']>3.41+.070
# Buck EN and SS absolute maximum are VIN+0.3V: steady-state enabled
# EN<=AONmax and SS~1.25V fit below the lowest authorized common input.
# Fast VIN collapse relative to gate/SS discharge is a separate physical gate.
assert 2.5375 < thresholds['main']['fall_min_V']+.3
assert 1.25 < thresholds['main']['fall_min_V']+.3
# Feedback leak limit is only20nA at25C.25nA across temperature is an ALLOCATION.
fb_alloc=25e-9
boost_low=.580*(1+R('R_BOOST_TOP')*(1-tol)/(R('R_BOOST_BOTTOM')*(1+tol)))-fb_alloc*R('R_BOOST_TOP')*(1+tol)
boost_high=.610*(1+R('R_BOOST_TOP')*(1+tol)/(R('R_BOOST_BOTTOM')*(1-tol)))+fb_alloc*R('R_BOOST_TOP')*(1+tol)
boost_nom=.595*(1+R('R_BOOST_TOP')/R('R_BOOST_BOTTOM'))
main_power=1.1/.85
common_low=boost_low-.060*(main_power/boost_low+.002)
assert common_low-.050>thresholds['main']['rise_max_V']
assert boost_low-.050>thresholds['boost_ready']['rise_max_V']
assert thresholds['boost_ready']['fall_min_V']-.060*(main_power/3.4+.002)>3.41+.04
# BQ FB current absent from spec: use25nA allocation for sensitivity only.
bqmax=.808*(1+R('R_VCHG_TOP')*(1+tol)/(R('R_VCHG_BOTTOM')*(1-tol)))+25e-9*R('R_VCHG_TOP')*(1+tol)
bqmin=.792*(1+R('R_VCHG_TOP')*(1-tol)/(R('R_VCHG_BOTTOM')*(1+tol)))-25e-9*R('R_VCHG_TOP')*(1+tol)
assert bqmax<2.7-.05
# AON load inventory: max logic ICC/II, comparator/supervisor and pullups. This
# conservative allocation is not a full-temperature LDO input-current guarantee.
aon_logic=[v for r,v in vals.items() if v.startswith('SN74') and r not in ('U17','U18')]
logic_icc=len(aon_logic)*10e-6
logic_inputs=sum(4 if v.startswith(('SN74LVC2G08','SN74LVC2G32','SN74LVC2G02')) else 2 for v in aon_logic)
logic_ii=logic_inputs*5e-6
od_sink=9*2.5375/(47000*(1-tol)) # even all9 low, including physically impossible combinations
pd_sink=4*2.5375/(47000*(1-tol))
ce_sink=2.5375/(100000*(1-tol))
aon_inventory=logic_icc+logic_ii+od_sink+pd_sink+ce_sink+4*11e-6+.5e-6+5e-6
#2mA reserves space for LDO ground current off test conditions and leakage.
aon_alloc=.002
assert aon_inventory<aon_alloc
v_aon_in=4.4-.700-R('R_AON_USB')*(1+tol)*aon_alloc
assert v_aon_in>=3.0
# Guaranteed pull-up DC levels at buffer inputs using max input/leak data,
# and a conservative2.0V Schmitt positive threshold allocation (3V table).
pu_min=2.4625-7e-6*47000*(1+tol)
assert pu_min>2.0+.10
assert .3<.4 # comparator/switch low <=.3V, Schmitt minVT-=.4 at2.3V table.
# Input budgets are conditional on the load/efficiency allocations.
rows=[]
for name,v in [('normal',normal_floor),('lowest_qualified_after50mV_and_mux_drop',thresholds['usb']['fall_min_V']-.050-imax*.001*.060)]:
    base=main_power/v*1000+2
    healthy=base+curr_max*1000+.600+.140+.100 #100u extra branch/divider allocation
    fault=base+100+.140
    rows.append({'condition':name,'allocated_buck_input_V':v,'base_main_mA':base,'healthy_total_mA':healthy,'healthy_margin_to_main_MIN_mA':imin-healthy,'branch100mA_fault_total_mA':fault,'fault_exceeds_minimum_main_limit':fault>imin})
assert all(x['healthy_margin_to_main_MIN_mA']>15 for x in rows)
assert all(x['fault_exceeds_minimum_main_limit'] for x in rows)
# Healthy input-cap precharge: before BQ CE is enabled, only2.6uF max allocated
# CHG_IN capacitance loads the enabled branch. Estimate maximum deficit charge
# while source can deliver MIN limiter current minus existing healthy base load.
cinmax=2.6e-6; c_limit_min=33e-6
headroom=imin-rows[0]['base_main_mA']-.140
assert 0<headroom<100
q_deficit=cinmax*5.5*(1-headroom/100)
droop=q_deficit/c_limit_min
start_after_droop=usb_side_floor-droop-.050
assert start_after_droop>thresholds['usb']['fall_max_V']
# Time spent in ideal current regulation while charging main/input capacitors;
# these are not maximum converter startup times or hot-plug peak guarantees.
main_c_max=130e-6
cc_main_time=main_c_max*5.5/(imin*.001)
cc_branch_time=cinmax*5.5/.050
assert cc_main_time<.005 and cc_branch_time<.005 # TPS2553 minimum fault deglitch5ms
css_min=100e-9*.90*.85
ramp_min=1.25*css_min/2.7e-6
capramp_max=52e-6*3.3/ramp_min
assert capramp_max<.005
# Keep old conservative2.448V start reserve rather than silently reclaiming it
# for BQ continuousCV, and use new earliest cap UVLO as cutoff allocation.
cutoff=max(1.7,thresholds['cap']['fall_max_V'])
energy=15*.9*.7*(2.448**2-cutoff**2)/2*.8
runtime=energy/1.11
assert runtime>10
result={
 'status':'PASS: netlist-derived DC/corner arithmetic on declared allocations; NOT transient or manufacturing acceptance',
 'guaranteed_component_DC_bounds':{'main_TPS2553_R_kohm':R('R_ILIM')/1000,'main_MIN_mA':imin,'main_MAX_mA':imax,'branch_mode':'ILIM=IN','branch_MIN_mA':50,'branch_MAX_mA':100,'raw_AON_resistor_short_bound_mA':raw_resistor_max,'raw_voltage_monitors_and_bleed_MAX_mA':raw_monitor_max,'whole_static_USB_draw_upper_mA':whole_dc_max,'margin_below500mA_mA':500-whole_dc_max,'caveat':'DC IOS equations and resistor bounds only; no guaranteed peak transient bound, no USB compliance claim'},
 'detector_corners':count,'detectors':thresholds,
 'normal_voltage_and_mode_allocations':{'source_low_V':4.4,'assumed_USB_side_floor_V':usb_side_floor,'assumed_buck_input_floor_V':normal_floor,'Ron_mux60mohm':'Specified200mA3.3/5V; low-input/full-current application remains allocation',
 'boost_nominal_PWM_V':boost_nom,'boost_PWM_low_V_with25nA_FB_allocation':boost_low,'boost_PWM_high_V_with25nA_FB_allocation':boost_high,'full_temperature_FB_and_PFM_upper_limits_closed':False,'common_boost_low_after_mux_V':common_low,'main_ready_rise_margin_after50mV_sag_V':common_low-.050-thresholds['main']['rise_max_V'],'buck_headroom_at_earliest_common_cutoff_V':thresholds['main']['fall_min_V']-3.41,'buck_EN_SS_static_VIN_relative_absolute_max':'EN<=2.5375V and SS~1.25V below common falling_MIN+0.3V; arbitrary fast collapse/gate/SS discharge NOT proved'},
 'charge':{'nominal_mA':25,'KISET_based_MIN_mA':curr_min*1000,'KISET_based_MAX_mA':curr_max*1000,'target2p6_min_with_FB_allocation_V':bqmin,'target2p6_max_with_FB_allocation_V':bqmax,'zero_to2p65V_accuracy_and_FB_bias_guaranteed':False,'ideal_nominal_seconds':15*2.6/.025,'ideal_corner_seconds_before_CV_thermal':15*1.3*2.65/curr_min,'cold_cap_linear_heat_estimate_W':5.5*curr_max,'fault_response':'Branch/mainFAULT wired-OR -> raw-AON SR latch. Charger-arm survives buckPG/USB-qualifier loss while RAW remains valid, allowing real5..10ms switchFAULT deglitch to complete. Main rail may collapse; continued operation is not required.'},
 'aon':{'logic_IC_count':len(aon_logic),'logic_input_count':logic_inputs,'calculated_static_inventory_A':aon_inventory,'load_allocation_A':aon_alloc,'diode_drop_allocation_V':.7,'allocated_AON_input_floor_V':v_aon_in,'diode_full_temperature_and_LDO_ground_current_closed':False,'minimum_OD_high_at_buffer_with7uA_sink_V':pu_min,'Schmitt_threshold_used_V':2.0,'sub1p65V_logic_behavior':'Unspecified; actual startup and pulldown behavior is a bench gate, not a formal proof'},
 'current_state_budgets':rows,
 'healthy_precharge_allocations':{'CHGIN_max_F':cinmax,'LIMITED5V_min_effective_F':c_limit_min,'input_precharge_deficit_charge_C':q_deficit,'estimated_LIMITED5V_droop_V':droop,'remaining_USB_qualifier_falling_margin_after50mV_extra_V':start_after_droop-thresholds['usb']['fall_max_V'],'main_cap_CC_time_scale_s':cc_main_time,'branch_cap_CC_time_scale_s':cc_branch_time,'buck_SS_min_based_ramp_s':ramp_min,'maximum_allocated_output_cap_ramp_A':capramp_max,'is_guaranteed_startup_time_current_or_single_attach_proof':False,'missing':'Actual effectiveC/leakage, main/buck/MCU boot peaks, dynamic current-limit overshoot, mux softstart/reverse/collapse, detector and enable delays; bench single-attach must verify'},
 'runtime':{'start_allocation_V':2.448,'earliest_loaded_cap_cutoff_V':cutoff,'C_effective_F':9.45,'combined_efficiency_assumption':.8,'load_allocation_W':1.11,'conditional_seconds':runtime,'margin_over10s_s':runtime-10,'guaranteed':False,'CAP_arm_rebound':'Source required for arm; loaded cap or proven-rail loss disarms backup, independent of external source status'},
 'physical_gates':['Single-attach cold/partial/full cap at source/cable/temp/load corners with all enables/source/PG/AON traces','Persistent short/failed charger: safe latched shutdown even after PG loss; external cycle only; check fault overshoot/SOA/thermal','Raw-AON startup through330ohm and actual diode/leakage overtemperature, all logic sub1.65V, Schmitt edges and SR hazards','Cap-fed boost startup/ESR, low-VIN switch-current ability and PFM/FB upper limits vs mux5.5V; loaded-cutoff/rebound/switchover','BQ ISET RC stability/current accuracy0..2.65V/FB bias/CV/thermal; no stated max if absent','Buck dropout/stability/magnetics and EN/SS VIN+0.3V during fast collapse; RF shared2.4GHz/US915 and DMX/flash peaks, measured runtime','USB Type-C power-only/current/inrush/detach and inputESD/shell; no interoperability/compliance guarantee','Area/footprints/routing/housing before integration; active BOM/validator untouched'],
 'manufacturing_release':False}
(P/'corner-proof.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'main_limit_mA':[imin,imax],'whole_DC_bound_mA':whole_dc_max,'healthy_MIN_margin_mA':[r['healthy_margin_to_main_MIN_mA'] for r in rows],'detector_corners':count,'healthy_input_precharge_qualifier_margin_V':result['healthy_precharge_allocations']['remaining_USB_qualifier_falling_margin_after50mV_extra_V'],'runtime_conditional_s':runtime},indent=2))
