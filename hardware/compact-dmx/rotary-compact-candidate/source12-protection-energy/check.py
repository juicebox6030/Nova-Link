"""Bounded PE-R1 energy/threshold feasibility checks; no circuit generator import.

All examples with C, L, current or timing assumptions are explicitly conditional.
Unspecified maximum current/response/ESR is never converted to a finite guarantee.
Only this directory is written. Frozen S12 is verified but never regenerated.
"""
from pathlib import Path
from itertools import product
import hashlib,json,math,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[3];S12=P.parent/'source12-candidate'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='b42c0e6284aac734fde851c69146abf73920f337'
assert sha(S12/'receipt.json')=='51393c2a663f8cc206af64d4d0aa09d541832f1a5ac542f7a93bc06f95e2e519'
lines=(S12/'SHA256SUMS').read_text().splitlines();assert len(lines)==73
for line in lines:
 digest,name=line.split('  ',1);assert sha(ROOT/name)==digest,name
e=json.loads((S12/'electrical-check.json').read_text())
assert e['physical_components']==57 and e['all_exported_nodes_checked']==185
# Consume the frozen result only to audit our independently literal inherited constants.
trip=5.476745480961925;healthy_max=5.304424430941883;port_min=4.783143570778441
assert abs(e['thresholds_V']['buck_OV_rise'][1]-trip)<1e-12
assert abs(e['regulation']['conditional_port_V'][0]-port_min)<1e-12
assert abs(e['regulation']['conditional_port_V'][1]-healthy_max)<1e-12
Cref=120e-6;Iillustration=3.81/.998;healthy_stress=1.5+.410+.010
Q=Cref*(5.5-trip);energy=.5*Cref*(5.5**2-trip**2)
assert 2.7905e-6<Q<2.7906e-6 and 15.315e-6<energy<15.316e-6
deadline=Q/Iillustration;assert .730e-6<deadline<.732e-6
windows=[]
for c,ceiling in product([60e-6,120e-6,180e-6],[5.5,7.]):
 windows.append({'C_assumed_F':c,'ceiling_V':ceiling,'charge_headroom_C':c*(ceiling-trip),'energy_headroom_J':.5*c*(ceiling**2-trip**2),'deadline_at_assumed3p8176A_s':c*(ceiling-trip)/Iillustration,'scope':'Conditional constant-current illustration only. 60/180uF sensitivity is not a capacitor guarantee. 7V is absolute stress, not allowed USB operation.'})
cap_required=[]
for t in [1e-6,5e-6,20e-6]:
 cap_required.append({'assumed_response_s':t,'C_required_only_for_flat3p8176A_F':Iillustration*t/(5.5-trip),'scope':'No ESR/ESL/inductor/continued source or aging allowance. Does not establish an implementable remedy.'})
stored=[]
for i in [2.6379340942962926,6.5,10.]:
 E=.5*1.8e-6*i*i
 stored.append({'L_assumed_H':1.8e-6,'I_assumed_A':i,'E_J':E,'V_if_entire_E_reaches120uF_start_at_latest_trip':math.sqrt(trip*trip+2*E/Cref),'scope':'Conservative full transfer envelope; actual C4/U4 sharing is not modeled as an exact trajectory. None of these currents is a guaranteed fault ceiling.'})
assert stored[1]['E_J']>energy
a=(12.59-trip)/1.2e-6;i0=stored[0]['I_assumed_A']
t_ramp=(-i0+math.sqrt(i0*i0+2*a*Q))/a
assert t_ramp<deadline
local_energy={'buck_input20uF_plus20percent_at12p59_J':.5*24e-6*12.59**2,'same_with_additional15percent_temp_allocation_J':.5*27.6e-6*12.59**2,'SAFE150uF_plus20percent_at_healthymax_J':.5*180e-6*healthy_max**2,'scope':'Reference/allocated upper examples, not guaranteed life/temp/bias maxima. ESR minimum, local loopL and module internal C/peak-current waveform are unspecified. Upstream input caps can discharge through the failed buck independently of U1 trip.'}
# Remedy1: exact LT4363IDE-1#PBF active series clamp/current limiting,
# one CSD17577Q3A passFET, keep U4 true reverse blocking. Published LT reference
# interval is at OUT8V/GATE12V and VCC12V; even its optimistic direct use fails
# the unchanged healthy allocation. Do not label it guaranteed at OUT5.4V.
lt_ref=(1.25,1.3);gain_needed=healthy_max/lt_ref[0];gain_allowed=5.5/lt_ref[1]
lt_min_latest=healthy_max*lt_ref[1]/lt_ref[0]
assert gain_needed>gain_allowed and lt_min_latest>5.5
Radd=(port_min-4.75)/healthy_stress
assert 17e-3<Radd<18e-3
port_with10m_andFET25C=port_min-healthy_stress*(.010+.0048)
port_with20m_shunt_alone=port_min-healthy_stress*.020
assert port_with10m_andFET25C>4.75 and port_with20m_shunt_alone<4.75
lt={'parts_screened':['LT4363IDE-1#PBF','CSD17577Q3A'],'arrangement':'Additional active series clamp/current-limit in SAFE5 before U3; retain U4 true reverse blocking. VCC from FPC12, not clamped output. Not captured.',
 'published_reference_test_V':[1.25,1.3],'reference_test_condition':'VCC12V, GATE12V, OUT8V; full-temperature marked specification. Applying it at5.4V is optimistic, not a new guaranteed condition.',
 'ideal_gain_lower_for_no_nuisance':gain_needed,'ideal_gain_upper_for5p5':gain_allowed,'earliest_possible_latest_clamp_if_min_above_healthymax_V':lt_min_latest,'unchanged_S12_DC_window':'FAIL even ideal divider/no FB bias under the retained50mV engineering allowance',
 'published_tOFF_OV_max_s':1e-6,'tOFF_test_condition':'FB step0->1.5V, OUT0V,VCC12V; not a near-threshold5.4V ramp or total external-FET isolation deadline',
 'published_gate_pull_down_min_A':.075,'gate_test':'FB1.5V,GATE12V,OUT5V; cannot extend this current over the full turnoff trajectory/near-threshold condition',
 'pass_FET_max_R25C_at10V_ohm':.0048,'pass_FET_max_Qg_at10V_C':35e-9,'Qg_scope':'VDS15V,ID16A,TA25C; LT gate can reach16V over SNS, hot/full-trajectory Qg is not bounded by this35nC value. Qgd and switching times are typical only.',
 'optional_shunt10mohm_limit_test_A':[.045/.010,.055/.010],'optional_shunt20mohm_limit_test_A':[.045/.020,.055/.020],'limit_scope':'LT steady test at VCC12V,OUT3..12V; not instantaneous or a guaranteed range at all actual source voltages. Resistor tolerance not included in these illustrative values.',
 'allowed_added_R_ohm':Radd,'conditional_port_with10m_shunt_and4p8m_FET_V':port_with10m_andFET25C,'conditional_port_with20m_shunt_alone_V':port_with20m_shunt_alone,
 'static_retuning_could_change_window':True,'retuning_closes_dynamic_gate':False,'capture_permitted_by_max_energy_evidence':False}
# Remedy2: TL431BIDBZR precision trigger plus TS820-600B-TR SCR on SAFE5,
# retain U4/U5 and request shutdown. Not a fuse and not presumed sacrificial.
# 25C ref initial plus entire max34mV peak-to-peak deviation is a conservative
# absolute envelope around an arbitrary25C value over the I-grade range.
ref25=(2.483,2.507);dev=.034;refs=(ref25[0]-dev,ref25[1]+dev)
tl_gain_needed=healthy_max/refs[0];tl_gain_allowed=5.5/refs[1]
assert tl_gain_needed>tl_gain_allowed
def tl_interval(references,bias):
 vals=[ref*(1+1160*(1+x)/(1000*(1+y)))+ib*1160*(1+x) for ref,x,y,ib in product(references,[-.002,.002],[-.002,.002],[0,bias])]
 return min(vals),max(vals)
tl25=tl_interval(ref25,4e-6);tlI=tl_interval(refs,6.5e-6)
assert tl25[0]>healthy_max and tl25[1]<5.5 and tlI[0]<healthy_max and tlI[1]>5.5
scr_examples=[]
for I in [1.8,Iillustration]:
 v=.85+.046*I;power=v*I
 scr_examples.append({'assumed_I_A':I,'V_at_source_Vt0_Rd_model':v,'on_loss_W':power,'illustrative_rise_at70K_perW':power*70,'I2t_at1ms_A2s':I*I*.001,'scope':'Not a guaranteed application I/V/duration/temperature bound; source Vt0/Rd atTj125C,70K/W at specified0.5cm2 copper. No sealed-collar inference.'})
tl={'parts_screened':['TL431BIDBZR','TS820-600B-TR'],'arrangement':'Precision trigger with inverted gate drive fires SCR across SAFE5 after U4; existing U5/U4 interrupt persistent high pre-rail. Gate driver/pulse/holdoff not qualified and not captured.',
 'reference25C_V':ref25,'max_reference_full_I_temp_deviation_V':dev,'conservative_absolute_full_I_range_V':refs,'ideal_gain_lower_for_no_nuisance':tl_gain_needed,'ideal_gain_upper_for5p5':tl_gain_allowed,
 'example_divider_ohm':[1160,1000],'divider_initial_plus_TCR_fraction':.002,'optimistic_trip25C_V':tl25,'optimistic_trip_full_I_temp_V':tlI,
 'reference_scope':'VKA=Vref,IKA10mA test, not every open-loop comparator/gate-driver bias. Iref25Cmax4uA plus full-temp deviation2.5uA used conservatively. Cathode-voltage/reference dependence and driver error add further requirements; not guaranteed application trips.',
 '25C_static_window':'Fits optimistic reference/divider model only','full_I_temp_static_window':'Not established; conservative published envelope fails unchanged S12 non-nuisance and ceiling conditions',
 'max_trigger_response_s':None,'max_SCR_turnon_s':None,'source_note':'TL431 comparator response curves typical; >10% reference overdrive guidance is not a maximum delay. TS820 specifies IGTmax200uA at25C,VD12V/RL140ohm, not a maximum turnon time at5.4V/fulltemp.',
 'SCR_ratings':{'I2t_A2s':24.5,'I2t_test':'10ms nonrepetitive, Tj25C; not a fuse clearing time or a hot/repetitive arbitrary-waveform grant','surge70A_test':'10ms, Tj25C','di_dt_A_per_us':50,'di_dt_test':'IG=2IGT, gate tr<=100ns, Tj125C','VTMmax_test':'1.6V at16A/380us,Tj25C','Vt0max_V':.85,'Rdmax_ohm':.046,'Ihold_max25C_A':.005,'Ilatch_max25C_A':.006},
 'source_breaker_ceiling_A':e['current_paths']['source_breaker_formula_A'][1],'source1p8A_cannot_guarantee_breaker_trip':1.8<e['current_paths']['source_breaker_formula_A'][1],
 'source_module_overload_power_ratio':[1.15,1.60],'not_module_peak_current_bound':True,'SCR_thermal_examples':scr_examples,'capture_permitted_by_max_energy_evidence':False}
def bounded_flat_peak(Cmin,initial,Imax,tmax,ESRmax):
 # This deliberately refuses to promote missing maxima into typ/zero values.
 if any(x is None for x in [Cmin,initial,Imax,tmax,ESRmax]):return None
 return initial+Imax*tmax/Cmin+Imax*ESRmax
negative={
 '20us_at_test_current_can_exceed5p5':bounded_flat_peak(Cref,trip,Iillustration,20e-6,0)>5.5,
 'even_misapplied1us_at_test_current_exceeds5p5':bounded_flat_peak(Cref,trip,Iillustration,1e-6,0)>5.5,
 'missing_Imax_does_not_become_a_testpoint_ceiling':bounded_flat_peak(Cref,trip,None,1e-6,0) is None,
 'missing_tmax_does_not_become_typical_delay':bounded_flat_peak(Cref,trip,Iillustration,None,0) is None,
 'missing_Cmin_does_not_become120uF_reference':bounded_flat_peak(None,trip,Iillustration,1e-6,0) is None,
 'missing_ESRmax_does_not_become_zero':bounded_flat_peak(Cref,trip,Iillustration,1e-6,None) is None,
 'inductor_energy_cannot_be_silently_discarded':stored[1]['E_J']>energy,
 'source1p8A_does_not_guarantee_U1trip':1.8<e['current_paths']['source_breaker_formula_A'][1],
 'a6V_pin_survival_result_would_still_fail_USB':6<7 and 6>5.5,
 '25C_TL_fit_is_not_full_I_temp_fit':tl25[0]>healthy_max and tl25[1]<5.5 and tlI[0]<healthy_max and tlI[1]>5.5}
assert all(negative.values())
protected=json.loads((P/'protected-inputs.json').read_text());deltas=[]
for name,digest in protected.items():
 now=sha(ROOT/name) if (ROOT/name).is_file() else None
 if now!=digest:deltas.append({'path':name,'snapshot_sha256':digest,'current_sha256':now})
assert not any(x['path'].startswith(str(S12.relative_to(ROOT))+'/') for x in deltas)
report={'revision':'PE-R1','verdict':'NOT ESTABLISHED: neither of two screened remedies has primary maximum bounds establishing USB<=5.5V or7V absolute-limit survival for the defined fault set; no new network captured','unchanged_S12_inventory_verified':73,'S12_receipt_sha256':sha(S12/'receipt.json'),'protected_snapshot_count':len(protected),'protected_exact_matches':len(protected)-len(deltas),'external_deltas_not_accepted':deltas,
 'requirements':{'healthy_port_V':[4.75,5.5],'healthy_upper_engineering_allocation_V':healthy_max,'normal_stress_A':healthy_stress,'USB_VBUS_limit_plus_VCONN_aux_A':1.82+.410+.010,'USB_fault_transient_above5p5_permitted_by_examined_sources':False,'TPS25810_pin_absolute_limit_V':7,'pin_survival_proven':False,'cold_socket_and_CC_preserved_by_no_circuit_change':True,'reverse_blocking_preserved_by_no_circuit_change':True},
 'inherited_reference_window':{'C_reference_tolerance_only_F':Cref,'latest_static_trip_V':trip,'charge_to5p5_C':Q,'energy_to5p5_J':energy,'flat_assumed_current_A':Iillustration,'flat_model_deadline_s':deadline,'not_an_instantaneous_current_or_C_guarantee':True},
 'window_sensitivity':windows,'capacitor_only_examples':cap_required,'stored_inductor_examples':stored,'local_cap_energy_examples':local_energy,'conditional_inductor_ramp_deadline_s':t_ramp,'condition_for_ramp':'L1.2uH constant unsaturated, source12.59V, rail frozen at trip, initialI2.638A, no helpful load. Does not bound real saturation or direct VIN-output bridge.',
 'fault_current_max_A':None,'fault_isolation_max_s':None,'L_after_saturation_min_H':None,'module_internal_C_max_F':None,'MLCC_or_polymer_ESR_min_ohm':None,'remedies':[lt,tl],'negative_checks':negative,
 'new_network_captured':False,'actual_added_parts':0,'actual_added_body_or_land_area_mm2':0,'actual_changed_board_dimensions':None,'hypothetical_network_area_height_BOM':'Not qualified or allocated; zero means no implemented change, not zero cost for a hypothetical remedy. Existing32x26/24x16 allocations remain unapproved.',
 'provisional100nF_MPN':'TMK105B7104MV-FR remains unqualified exactly as S12; no substitution or source-qualification claim','no_hardware_tests':True,'manufacturing_release':False}
(P/'numeric-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'revision':report['revision'],'verdict':report['verdict'],'Q_headroom_C':Q,'E_headroom_J':energy,'flat_model_deadline_s':deadline,'LT_ideal_gain_interval':[gain_needed,gain_allowed],'TLBI_ideal_gain_interval':[tl_gain_needed,tl_gain_allowed],'S12_inventory':73,'protected_exact_matches':report['protected_exact_matches'],'protected_total':len(protected),'external_deltas':[x['path'] for x in deltas]},indent=2))
