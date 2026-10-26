"""Current power-only electrical corner arithmetic; not firmware or measured runtime."""
from pathlib import Path
import json,itertools
P=Path(__file__).resolve().parent
# TPS2553 SLVS841F equations3/4; add 0.1% initial +25ppm/C*100C resistor allowance.
r=60.4;rt=.001+25e-6*100
imin=25230/(r*(1+rt))**1.016;imax=22980/(r*(1-rt))**.94
vin=4.4-(.135+.060)*imax/1000 # TPS2116 replaces the 0.5V series diode.
main=1.1/.85/vin*1000;charge=.030*2.652/.80/vin*1000;aux=2
# Conservative comparator uncertainty: reference initial+drift, offset, full hysteresis,
# common-mode and supply terms. These are conservative additive design allocations.
e=1.242*100e-6*100+.009+.008+.0025+.0037
lo_ref=1.223-e;hi_ref=1.260+e
threshold=lambda top:(lo_ref*(1+top*.999/(100*1.001)),hi_ref*(1+top*1.001/(100*.999)))
caplo,caphi=threshold(20)
# TPS3700 SBVS187G p6: rising 396..404mV; falling 387..400mV.
# 0.1% initial + 25ppm/C*100C each divider resistor; include +/-25nA input bias.
divider_rt=.001+25e-6*100
ratio_lo=1+93.1*(1-divider_rt)/(10*(1+divider_rt))
ratio_hi=1+93.1*(1+divider_rt)/(10*(1-divider_rt))
bias=25e-9*93100*(1+divider_rt)
vblo=.387*ratio_lo-bias;vbhi=.404*ratio_hi+bias
vbrise_lo=.396*ratio_lo-bias;vbfall_hi=.400*ratio_hi+bias
# D-A: stable GOOD must survive hysteresis and a separately allocated 50mV sag.
# The 3.5% regulation envelope is deliberately stricter than the 2% OSEL target.
backup_max=3.6*1.035;entry_max=backup_max+.150
droop=.050;qualified_vin=vblo-droop
bypass_r_allocated=.300 # Datasheet gives typical only: measured bound remains a gate.
qualified_current=(1.1/.85+.030*2.652/.80)/qualified_vin+aux/1000
qualified_backup=qualified_vin-qualified_current*bypass_r_allocated
buck_vin_required=3.41 # Engineering allocation, not a newly guaranteed low-VIN RDS(on).
c=15*.9*.7;eta=.8;floor=1.7
charge_hysteresis_max=.100 # TPS61094 VSUP_HYS 50..100mV after charge termination.
start=2.548-charge_hysteresis_max
energy=lambda v:.5*c*(v*v-floor*floor)*eta
out={'status':'CALCULATED_ASSUMPTIONS_NOT_HARDWARE_QUALIFICATION','architecture':'USB-C power-only PSD <=500mA design basis; one buffered domain; no USB data recovery',
'input':{'limiter':'TPS2553DBVR','R_ILIM_kohm':r,'resistor_combined_fraction_allowance':rt,'limit_min_mA':imin,'limit_max_mA':imax,'switch_IQ_max_allowance_mA':.14,'whole_VBUS_static_bound_mA':imax+.14,'USB_PSD_allowance_mA':500,'inrush_qualified':False,'source_low_at_receptacle_V_assumed':4.4,'series_diode_drop_V_assumed':0,'reverse_barrier':'TPS2116DRLR channel1 only, channel2 grounded','reverse_barrier_Ron_ohm':.060,'Ron_conditions':'TPS2116 table at VIN=3.3/5V, IOUT=200mA, -40..105C; load/board thermal qualification remains open','limiter_Ron_max_ohm':.135,'normal_converter_input_V':vin,'main_SYS_load_W_ASSUMED':1.1,'buck_efficiency_ASSUMED':.85,'main_current_mA':main,'charge_input_current_mA_at_30mA_2p652V_80pct_eff':charge,'auxiliary_allowance_mA':aux,'total_required_mA':main+charge+aux,'margin_to_minimum_limit_mA':imin-main-charge-aux,'load_measured':False,'radio':'One CC1352R shared radio: 2.4GHz plus US915MHz; no independent simultaneous RF load assumed'},
'charge':{'nominal_mA':25,'tolerance_fraction':.20,'min_mA':20,'max_mA':30,'ICHG_resistor_kohm':9.53,'VCHG_resistor_kohm':9.53,'nominal_target_V':2.6,'min_target_V':2.548,'max_target_V':2.652,'ideal_nominal_seconds':15*2.6/.025,'ideal_plus30pct_C_plus2pct_V_minus20pct_I_seconds':15*1.3*2.652/.020,'termination_tail_and_soft_start_add_time':True,'datasheet_current_accuracy_conditions':'VIN=5V; SUP=0.8..4V. Off-condition charging requires measurement.'},
'cutoff':{'comparator':'TLV3012BIDCKR','nominal_loaded_V':1.242*1.2,'estimated_loaded_low_V':caplo,'estimated_loaded_high_V':caphi,'energy_floor_with_sag_transient_reserve_V':floor,'latch_captured':True,'POR_gated_RUN':True,'rearm':'NORMAL_IN qualified by TPS3700 AND AON POR good; cap rebound alone cannot rearm','VBUS_nominal_V':.4*10.31,'VBUS_estimated_low_V':vblo,'VBUS_estimated_high_V':vbhi,'VBUS_rising_envelope_V':[vbrise_lo,vbhi],'VBUS_falling_envelope_V':[vblo,vbfall_hi],'VBUS_divider_combined_resistor_fraction':divider_rt,'maximum_backup_voltage_for_false_rearm_check_V':backup_max},
'source_mode_proof':{'status':'STATIC_CORNERS_PASS_WITH_EXPLICIT_ENGINEERING_ALLOCATIONS; DYNAMIC_QUALIFICATION_OPEN','sense_node':'NORMAL_IN (TPS61094 VIN), after reverse barrier','OSEL_target_max_V':3.6*1.02,'boost_regulation_envelope_max_V':backup_max,'VBYPASS_max_V':.150,'conservative_bypass_entry_max_V':entry_max,'specified_target_bypass_entry_max_V':3.6*1.02+.15,'additional_sag_allocation_V':droop,'lowest_qualified_input_after_sag_V':qualified_vin,'entry_margin_after_sag_V':qualified_vin-entry_max,'source_to_highest_assert_margin_V':vin-vbhi,'qualified_input_current_mA':qualified_current*1000,'min_limiter_margin_at_qualified_input_mA':imin-qualified_current*1000,'bypass_Ron_ALLOCATION_ohm_NOT_DS_MAX':bypass_r_allocated,'minimum_qualified_backup_with_Ron_allocation_V':qualified_backup,'buck_input_required_ALLOCATION_V':buck_vin_required,'buck_headroom_normal_V':qualified_backup-buck_vin_required,'buck_headroom_boost_V':3.6*.98-buck_vin_required,'no_false_rearm_margin_V':vblo-backup_max,'no_slow_sense_filter':True,'dynamic_status_is_commit_authority':False,'propagation_delay_max_specified':False,'arbitrary_source_steps_proven':False},
'startup':{'acceptance':'UNMET: empty-cap repeatable startup is not proven','TPS61094_ISS_min_mA_at_3p6V_VIN_1p8V_VOUT':500,'TPS61094_ISS_max_mA':None,'TPS61094_ISS_over_all_startup_conditions_bounded':False,'ISS_min_exceeds_limiter_max_mA':500-imax,'output_precharge_effective_uF':32,'input_storage_and_filter_effective_uF':11.1,'guaranteed_max_precharge_time_s':None,'converter_EN_and_buck_EN_share_RUN':True,'new_barrier_softstart_fixes_output_precharge':False,'needed_evidence':'Worst-case startup current or source-backed sequence redesign; waveform proof of single cold attach, no RUN cycling/sag, and USB inrush/load/temperature sweep. Eventual convergence does not pass.'},
'buffer':{'cap_F':15,'effective_aged_F':c,'nominal_delivered_J_at_2p6V_1p5Vfloor':.5*15*(2.6**2-1.5**2)*eta,'nominal_seconds_at_0p8W':.5*15*(2.6**2-1.5**2)*eta/.8,'nominal_after75mV_hysteresis_seconds_at_0p8W':.5*15*((2.6-.075)**2-1.5**2)*eta/.8,'charge_termination_low_V':2.548,'charge_hysteresis_max_V':charge_hysteresis_max,'minimum_full_charge_start_V_after_hysteresis':start,'aged_delivered_J_at_2p6V':energy(2.6),'aged_delivered_J_at_low_charge_2p548V':energy(start),'low_charge_energy_key_definition':'Legacy key retained for package reader: now subtracts maximum 100mV recharge hysteresis from 2.548V before integrating.','aged_low_charge_seconds_at_1p11W':energy(start)/1.11,'estimated_margin_over10s_seconds':energy(start)/1.11-10,'max_total_W_for10s_with_all_assumptions':energy(start)/10,'minimum_combined_efficiency_for10s':10*1.11/(.5*c*(start*start-floor*floor)),'efficiency_ASSUMED':eta,'total_load_with_supervision_W_ASSUMED':1.11,'measured':False,'runtime_guaranteed':False,'whole_transfer_energy_guarantee':False},
'states':[
{'state':'No VBUS; cap valid; previously armed','RUN':1,'commit_permission':'NO; resident loader must defer commit','service':'RDM can operate while ride-through remains'},
{'state':'No VBUS; cap below loaded threshold','RUN':0,'commit_permission':'NO','service':'off; cutoff latch persists through cap rebound'},
{'state':'No VBUS; cap charged but never armed / AON lost','RUN':0,'commit_permission':'NO','service':'requires VBUS to start'},
{'state':'Default Type-C source; VBUS good; AON POR released','RUN':1,'commit_permission':'only future loader after stable VBUS_GOOD + BUCK_PG and integrity policy','service':'normal or resident RDM loader'},
{'state':'1.5A /3A advertised','RUN':1,'commit_permission':'same as default; no increased current drawn','service':'same circuit; no decoder required for increased draw'},
{'state':'Physical SERVICE held across RESET','RUN':'unchanged','commit_permission':'unchanged','service':'distinct GPIO to future resident loader; not ROM DIO3'},
{'state':'USB host suspended','RUN':'unchanged while valid VBUS supplied','commit_permission':'same voltage/integrity conditions','service':'PSD has no USB communication function; qualification pending'},
{'state':'AON brownout / power-on','RUN':0,'commit_permission':'NO','service':'POR holds off; stable VBUS can rearm after POR'}]}
assert imax+.14<500 and main+charge+aux<imin
assert caphi<floor and vblo>backup_max and vbhi<vin
assert qualified_vin>entry_max+.025 # 25mV remaining AFTER a 50mV sag allocation.
assert qualified_current*1000<imin
assert qualified_backup>backup_max+.050 # VOUT must also exceed target to charge SUP.
assert qualified_backup>buck_vin_required and 3.6*.98>buck_vin_required
assert vin-vbhi>.100 and vin-droop>vbhi # source can assert GOOD at low input.
assert start==2.548-.100 and out['buffer']['charge_hysteresis_max_V']==.100
assert not out['startup']['new_barrier_softstart_fixes_output_precharge']
assert 500>imax and not out['source_mode_proof']['arbitrary_source_steps_proven']
assert out['buffer']['aged_low_charge_seconds_at_1p11W']>10
(P/'power-budget.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'limit_range_mA':[imin,imax],'whole_static_bound_mA':imax+.14,'required_input_mA':main+charge+aux,'min_limit_margin_mA':imin-main-charge-aux,'normal_VIN_V':vin,'entry_margin_after50mV_sag_V':qualified_vin-entry_max,'charge_nominal_s':out['charge']['ideal_nominal_seconds'],'aged_low_charge_runtime_s':out['buffer']['aged_low_charge_seconds_at_1p11W'],'cap_trip_estimate_V':[caplo,caphi],'VBUS_trip_estimate_V':[vblo,vbhi],'cold_cap_startup_accepted':False},indent=2))
