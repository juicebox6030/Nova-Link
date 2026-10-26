"""Engineering arithmetic, not firmware execution or measured hardware evidence."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
bridge_min=34/(1.001**1.072);bridge_max=66/(.999**1.072)
cap=15;aged=cap*.9*.7;eta=.8;floor=1.6
energy=lambda c,v,cut=floor: .5*c*(v*v-cut*cut)*eta
# Prospective comparator only: conservative additive estimate, not implemented UVLO.
drift=1.242*100e-6*100;offset=.009;hyst=.008;cm=.0025;ps=.0037
ratio_min=1+20*.999/(100*1.001);ratio_max=1+20*1.001/(100*.999)
uvlo_lo=(1.223-drift-offset-hyst-cm-ps)*ratio_min
uvlo_hi=(1.260+drift+offset+hyst+cm+ps)*ratio_max
r={'status':'DESIGN_OBJECTION_AND_PARTIAL_CANDIDATE_NOT_PRODUCT_ACCEPTANCE',
 'recovery_current_mA':{'bridge_branch_min_est_with_0p1pct_R':bridge_min,'bridge_branch_max_est_with_0p1pct_R':bridge_max,'post_enum_recovery_min_datasheet_1pct_R':262.1,'post_enum_recovery_max_datasheet_1pct_R':342.3,'provisional_raw_CC_logic_allowance_NOT_CLOSED':5,'provisional_switch_IQ_allowance_NOT_CLOSED':.3,'pre_enum_total_allocation':bridge_max+5+.3,'post_enum_total_allocation':bridge_max+342.3+5+.3,'usb_requested_post_enum_mA':500,'usb_suspend_maximum_proven':False,'CP2102N_max_active_current_published':False,'recovery_function_guaranteed':False},
 'buffer':{'cap_F':15,'effective_aged_F':aged,'nominal_delivered_J_at_2p6V':energy(cap,2.6,1.5),'aged_delivered_J_at_2p6V':energy(aged,2.6),'aged_delivered_J_at_low_charge_2p548V':energy(aged,2.6*.98),'nominal_seconds_at_0p8W':energy(cap,2.6,1.5)/.8,'aged_seconds_at_1p1W':energy(aged,2.6)/1.1,'aged_low_charge_seconds_at_1p1W':energy(aged,2.6*.98)/1.1,'nominal_charge_seconds_ideal':15*2.6/.25,'charge_ideal_with_plus30pct_C_plus2pct_V_minus20pct_I_seconds':15*1.3*2.6*1.02/.2,'charge_time_includes_termination_tail':False,'efficiency_assumption':eta,'nominal_floor_without_sag_reserve_V':1.5,'aged_floor_including_sag_reserve_V':floor,'measured':False},
 'prospective_UVLO_not_captured':{'part':'TLV3012B','divider_ohm':[20000,100000],'resistor_tolerance':.001,'nominal_V':1.242*1.2,'conservative_low_V':uvlo_lo,'conservative_high_V':uvlo_hi,'reference_temp_drift_V':drift,'latched_cutoff_implemented':False},
 'required_states':[
 {'condition':'VBUS absent, cap valid and previously armed','normal':'buffer supplies normal loads','recovery':'off','implemented':False},
 {'condition':'VBUS absent, cap depleted or cutoff latched','normal':'off; no cap-rebound restart','recovery':'off','implemented':False},
 {'condition':'default-current PC, not configured','normal':'off, charger off','recovery':'bridge only; MCU off','implemented':'bridge candidate only; normal disable missing'},
 {'condition':'default-current PC, configured 500mA, request held','normal':'off, charger off','recovery':'enabled only after factory qualification link; force ROM boot before MCU power','implemented':'supply gate captured; merger/boot/reset missing'},
 {'condition':'>=1.5A advertised, no recovery request','normal':'normal enabled; charge and rearm permitted','recovery':'MCU recovery rail off','implemented':False},
 {'condition':'>=1.5A advertised, recovery requested','normal':'normal and charge disabled','recovery':'same configured/suspend-qualified recovery sequence','implemented':False},
 {'condition':'USB suspend','normal':'off for PC/recovery; dedicated-source policy still to close','recovery':'MCU rail off; bridge suspended; whole-device suspend-current qualification required','implemented':'SUSPENDb gate captured only'},
 {'condition':'factory link open (as captured)','normal':'not captured','recovery':'MCU recovery rail always off; bridge may enumerate','implemented':True}
 ]}
assert r['recovery_current_mA']['pre_enum_total_allocation']<100
assert r['recovery_current_mA']['post_enum_total_allocation']<500
assert r['buffer']['aged_low_charge_seconds_at_1p1W']>10
assert uvlo_hi<floor
(P/'power-budget.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'pre_enum_allocation_mA':bridge_max+5.3,'post_enum_allocation_mA':bridge_max+347.6,'aged_low_charge_seconds_at_1p1W':energy(aged,2.548)/1.1,'UVLO_candidate_V':[uvlo_lo,uvlo_hi],'product_acceptance':'NOT_MET'},indent=2))
