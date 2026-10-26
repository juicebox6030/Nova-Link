"""Bounded startup architecture arithmetic. PROPOSALS ONLY, not captured circuits.

No firmware, transient simulation or electrical/hardware validation. Sources and
unclosed specifications are recorded in startup-proposal.md and its manifest.
"""
from pathlib import Path
import itertools, json, math, xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
budget = json.loads((P.parent/'power-budget.json').read_text())
netlist = ET.parse(P/'power-service.net')
values = {x.attrib['ref']: x.findtext('value') for x in netlist.findall('./components/comp')}
assert values['U3'] == 'TPS61094DSSR' and values['R_ILIM'] == '60.4k 0.1%'
assert values['R_ICHG'] == '9.53k 1%' # Actual capture stays25mA.

rt = .001+100*25e-6
def current_limits(r_kohm):
    return (25230/(r_kohm*(1+rt))**1.016,
            22980/(r_kohm*(1-rt))**.94)

lo,hi = current_limits(60.4)
vin_full = budget['input']['normal_converter_input_V']
vin_qualified = budget['source_mode_proof']['lowest_qualified_input_after_sag_V']
charge_rows=[]
for nominal, code in [(25,9.53),(40,None),(50,13.0),(75,17.4),(100,22.1)]:
    def demand(v):
        return (1.1/.85+nominal*.001*1.20*2.652/.80)/v*1000+2
    full,low=demand(vin_full),demand(vin_qualified)
    charge_rows.append({'nominal_charge_mA':nominal,'TPS61094_ICHG_resistor_kohm':code,
        'valid_resistor_code':code is not None,'maximum_charge_mA_assuming20percent':nominal*1.2,
        'whole_normal_input_required_mA':full,'qualified_floor_required_mA':low,
        'normal_margin_to_MIN_limiter_mA':lo-full,'qualified_floor_margin_to_MIN_limiter_mA':lo-low,
        'retains25mA_engineering_current_reserve_at_qualified_floor':lo-low>=25,
        'ideal_nominal_charge_s':15*2.6/(nominal*.001),
        'ideal_plus30pctC_plus2pctV_minus20pctI_s':15*1.3*2.652/(nominal*.001*.8),
        'current_accuracy_off5V_test_condition_qualified':False})
assert charge_rows[0]['qualified_floor_margin_to_MIN_limiter_mA'] > 30
assert 0 < charge_rows[2]['qualified_floor_margin_to_MIN_limiter_mA'] < 7
assert all(row['qualified_floor_margin_to_MIN_limiter_mA']<0 for row in charge_rows[3:])
assert charge_rows[4]['normal_margin_to_MIN_limiter_mA']<0
assert not charge_rows[1]['valid_resistor_code']

# Path1 is a retained-IC, externally precharged candidate, NOT a supported fix.
# The minimum precharge time scale alone cannot prove TPS61094 transition behavior.
prelo,prehi=current_limits(210)
c_pre_max=55e-6 # Upper effective cap ALLOCATION, final parts not specified.
pre_time=c_pre_max*5.5/(prelo*.001-.002)
assert prehi+2 < lo and pre_time+.003 < .012

# Path2 changes the source contract; no resistor/gating changes are made here.
high_lo,high_hi=current_limits(22.1)
aux=10 # Upstream AON+CC+LDO/control ALLOCATION, not a measured or fully summed bound.
assert high_hi+aux+.14 < 1500
assert high_lo > 1000
# Proposed100mA linear cap charger, KISET270..330Aohm, 0.35% resistor allowance.
ichg_min=270/(3000*(1+rt));ichg_max=330/(3000*(1-rt))
q_nom=15*2.6/.100
q_corner=15*1.3*2.65/ichg_min # 2.65V is a design ceiling ALLOCATION, FB not closed.
vin_path2_min=4.4-(.135+.060)*high_hi*.001
main_at_low=1.1/.85/vin_path2_min*1000+aux
with_branch_fault=main_at_low+prehi
assert with_branch_fault < high_lo
#100nF +/-20% CSS: TPS62132 ISS/TR max2.7uA, 1.25V softstart equation.
css_min=100e-9*.8
t_buck_min=1.25*css_min/2.7e-6
c_sys_max=44e-6 # Upper output capacitance ALLOCATION, final BOM not specified.
i_csys_max=c_sys_max*3.3/t_buck_min
assert t_buck_min>.030 and i_csys_max<.005
linear_heat=5.5*ichg_max # Cold0V cap, no thermal throttling yet.
# Proposed USB-side detector, independent of cap-fed mux output. Existing93.1k
# cannot be inherited blindly after changing the current limit/topology.
uv_corners=[]
for edge, thresholds in [('rising',(.396,.404)),('falling',(.387,.400))]:
    for te,be,bias,vt in itertools.product((-rt,rt),(-rt,rt),(-25e-9,25e-9),thresholds):
        top=89800*(1+te); bottom=10000*(1+be)
        uv_corners.append((edge,vt*(1+top/bottom)+bias*top))
uv_rise_max=max(v for edge,v in uv_corners if edge=='rising')
uv_fall_min=min(v for edge,v in uv_corners if edge=='falling')
qualified_buck_floor=uv_fall_min-.050-.060*high_hi*.001
assert len(uv_corners)==32
assert vin_path2_min-uv_rise_max>.090
assert qualified_buck_floor>3.41+.250


# Datasheet GPIO truth table, not firmware and not an exported circuit check.
cc_rows=[]
for name,out1,out2 in [('unattached',1,1),('default',1,0),('1p5A',0,1),('3A',0,0)]:
    for audio_absent,cc_por,raw_uv in itertools.product((False,True),repeat=3):
        allow=bool(not out1 and audio_absent and cc_por and raw_uv)
        if name in ('unattached','default'):assert not allow
        if not(audio_absent and cc_por and raw_uv):assert not allow
        cc_rows.append({'advertisement':name,'OUT1':out1,'OUT2':out2,
            'OUT3_audio_absent':audio_absent,'CC_POR_OK':cc_por,'RAW_UV_OK':raw_uv,'SOURCE_ALLOW':allow})

state_cases=0
for source,aon,cap_start,cap_ok,boost_ready,main_ready,buck_pg,old_q in itertools.product((False,True),repeat=8):
    q=bool(aon and cap_ok and (old_q or (source and cap_start)))
    boost_en=q
    buck_en=bool(aon and ((source and main_ready) or (q and cap_ok and boost_ready)))
    charge_en=bool(source and aon and buck_pg)
    commit_status=bool(source and aon and main_ready and buck_pg)
    if not aon or not cap_ok:assert not boost_en
    if not source and not old_q:assert not q # cap rebound cannot rearm.
    if not source:assert not charge_en and not commit_status
    if source and aon and main_ready:assert buck_en # empty cap cannot prevent loader power.
    if source and aon and not buck_pg:assert not charge_en
    state_cases+=1

report={
 'status':'PROPOSAL_ARITHMETIC_AND_STATE_INVARIANTS_PASS; NO_NEW_CIRCUIT_CAPTURE',
 'implementation':'Current25mA TPS61094/500mA-choice hardware remains unchanged; D-B still UNMET in that capture',
 'owner_requirement_correction':'500mA compatibility was an engineering choice, not an explicit owner requirement; 1.5A-only behavior requires product selection',
 'existing_500mA_design':{'limiter_min_mA':lo,'limiter_max_mA':hi,'normal_VIN_V':vin_full,
    'qualified_floor_VIN_V':vin_qualified,'charge_setting_corners':charge_rows},
 'path1_retained500mA':{'source_bound_closed':False,'proposed_precharge_R_ILIM_kohm':210,
    'precharge_switch_min_mA':prelo,'precharge_switch_max_mA':prehi,'upper_cap_ALLOCATION_F':c_pre_max,
    'constant_current_charge_time_scale_s':pre_time,'TPS2553_turnon_max_s':.003,
    'TPS3808_open_CT_delay_min_s':.012,
    'scale_comparison_is_startup_guarantee':False,
    'blockers':['TPS61094 does not explicitly guarantee externally prebiased EN/MODE handoff or its delay/current maximum',
                'Cap upper/leakage/ESR and switched bypass PG/sequence/SOA must be closed',
                'TPS2553 min/max limit equations are DC bounds, not a peak hot-plug guarantee']},
 'path2_CC_qualified1p5A':{'selection':'PROPOSED_ONLY; changes compatibility contract',
    'main_R_ILIM_kohm':22.1,'limiter_min_mA':high_lo,'limiter_max_mA':high_hi,
    'upstream_auxiliary_current_ALLOCATION_mA':aux,
    'whole_static_USB_current_with_aux_ALLOCATION_mA':high_hi+aux+.14,
    'current_safety_margin_to1p5A_mA':1500-high_hi-aux-.14,
    'static_main_input_floor_using_worst_limiter_drop_V':vin_path2_min,
    'main_load_plus_aux_at_floor_mA':main_at_low,
    'with_hard_limited_charge_branch_max_mA':with_branch_fault,
    'margin_to_MAIN_MIN_limit_even_at_branch_limit_mA':high_lo-with_branch_fault,
    'BQ25173_nominal_charge_mA':100,'BQ25173_ISET_kohm':3,
    'KISET_based_charge_min_mA':ichg_min*1000,'KISET_based_charge_max_mA':ichg_max*1000,
    'charge_branch_TPS2553_R_ILIM_kohm':210,'charge_branch_hard_DC_limit_max_mA':prehi,
    'ideal_nominal_full_charge_s':q_nom,'ideal_corner_charge_s_before_CV_and_thermal':q_corner,
    'charge_target_and_FB_bias_closed':False,
    'cold_linear_charger_dissipation_unthrottled_W':linear_heat,
    'JEDEC75p2CperW_temperature_rise_C_INDICATION_ONLY':linear_heat*75.2,
    'TPS62132_proposed_CSS_nF':100,'CSS_min_based_ramp_time_s':t_buck_min,
    'output_cap_ALLOCATION_F':c_sys_max,'derived_output_cap_ramp_current_A':i_csys_max,
    'ramp_math_is_peak_input_current_guarantee':False,
    'proposed_USB_side_UV_top_kohm':89.8,'proposed_USB_side_UV_bottom_kohm':10,
    'USB_UV_detector_corners':len(uv_corners),'USB_UV_rising_max_V':uv_rise_max,
    'USB_UV_falling_min_V':uv_fall_min,
    'USB_qualified_buck_floor_with50mV_sag_and_max_mux_drop_V':qualified_buck_floor,
    'USB_side_UV_is_peak_transient_guarantee':False,
    'mux_Ron60mohm_test_conditions':'IOUT200mA at VIN3.3V/5V; applying at1.256A is an unqualified allocation',
    'input_floor_is_guaranteed_full_current_bound':False,
    'TPS61023_unknown_startup_current_is_USB_input_current':False,
    'TPS61023_unknown_startup_current_location':'CAP_POS15F -> boost-only output capacitor; primary mux stays on USB',
    'CC_truth_cases':len(cc_rows),'proposal_state_cases':state_cases,
    'all_startup_bounds_closed':False,'manufacturing_release':False},
 'CC_truth_table':cc_rows,
 'unresolved_source_gates':['TPS61094 prebias transition guarantee for path1',
    'TPS61023 minimum switch limit test at VIN3.6V/VOUT5V vs required1.7V/3.6V and no PFM maximum/peak startup current/time; cannot infer absent limits',
    'BQ25173 zero-volt start supported in text, but tabulated current-accuracy examples use3.8V/7.6V; obtain0..2.65V accuracy/FB input-bias limits',
    'Output capacitance/ESR, buck startup load/efficiency, branch transient limit response and actual system load need qualification',
    'TUSB320LAI GPIO/UV/POR propagation/current withdrawal timing and source-side CC advertisement must be closed; no arbitrary-step guarantee']}
(P/'startup-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'500mA_charge_margin_at_qualified_floor_mA':
 {row['nominal_charge_mA']:round(row['qualified_floor_margin_to_MIN_limiter_mA'],3) for row in charge_rows},
 'path2_main_limiter_mA':[high_lo,high_hi],'path2_branch_limited_margin_mA':high_lo-with_branch_fault,
 'CC_cases':len(cc_rows),'state_cases':state_cases,'guaranteed_startup_closed':False},indent=2))
