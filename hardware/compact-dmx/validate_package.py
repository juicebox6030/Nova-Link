"""Deterministic artifact/math checks only. No electronics/fixture/hardware validation."""
from pathlib import Path
import csv,json,math,xml.etree.ElementTree as E,subprocess,sys
P=Path(__file__).resolve().parent
j=json.loads((P/'exports/cad-validation.json').read_text());assert all(j['valid_solids'].values());assert not j['package_intersections_mm3']
required={('D01_Sidecar_base','D03_PCB_envelope'),('D08_Cap_max','D03_PCB_envelope'),('D08_Cap_max','D02_Sidecar_lid'),('B11_Stop_peg','B06_Collar_right_cheek'),('B10_Lock_pin_17_4PH','B19_Lock_pin_guide'),('B19_Lock_pin_guide','B16_USB_board_envelope')}
assert required <= {(c['a'],c['b']) for c in j['clearance_checks']}
assert j['clearance_checks'] and all(c['passed'] for c in j['clearance_checks']), [c for c in j['clearance_checks'] if not c['passed']]
assert j['barrel_mechanical_pair_count']==78 and not j['barrel_mechanical_intersections_mm3']
assert len(j['lock_release_checks'])==15 and all(c['passed'] for c in j['lock_release_checks'])
assert j['guide_wire_sweep']['sample_angles']==181 and j['guide_wire_sweep']['passed']
assert j['guide_wire_sweep']['minimum_after_allocated_tolerances_mm']>=.3-1e-6
assert j['usb_window_lane_axial_gap_mm']>=.3
for f in (P/'exports').glob('*.step'):
 s=f.read_text();assert 'ISO-10303-21' in s and 'END-ISO-10303-21' in s
for f in (P/'exports').glob('*.svg'):E.parse(f)
subprocess.run([sys.executable,str(P/'eda/verify_kicad.py')],check=True)
subprocess.run([sys.executable,str(P/'eda/power-service/verify.py')],check=True)
subprocess.run([sys.executable,str(P/'eda/power_budget.py')],check=True)
subprocess.run([sys.executable,str(P/'eda/mcu-radio/verify.py')],check=True)
subprocess.run(['flatpak','run','--command=python3','org.kicad.KiCad',str(P/'eda/footprints/verify.py')],check=True)
subprocess.run([sys.executable,str(P/'eda/footprints/termination_budget.py')],check=True)
fpcheck=json.loads((P/'eda/footprints/validation.json').read_text())
assert fpcheck['physical_component_assignments']==37 and fpcheck['numbered_pads_dimension_checked']==113
assert fpcheck['source_backed_assignments']==36 and not fpcheck['full_footprint_acceptance']
mcu=json.loads((P/'eda/mcu-radio/validation.json').read_text())
assert mcu['verified_physical_pins']==49 and mcu['complete_support_capture']
assert mcu['antenna_prototype_capture'] and not mcu['matching_values_qualified']
assert mcu['RF_frontend_capture'] and not mcu['antenna_final_match_captured']
assert not mcu['full_product_acceptance']
power=json.loads((P/'eda/power-service/validation.json').read_text())
budget=json.loads((P/'eda/power-budget.json').read_text())
assert power['capture_check']=='PASS' and power['full_product_release']=='NOT_RELEASED'
assert power['service_separate_from_ROM_backdoor'] and power['USB_data_pins']=='NC'
assert power['control_power_flags']==0 and power['stable_latch_cases']==16
assert budget['input']['whole_VBUS_static_bound_mA']<500
assert budget['input']['margin_to_minimum_limit_mA']>0
assert budget['cutoff']['latch_captured']
assert budget['buffer']['aged_low_charge_seconds_at_1p11W']>10
n=E.parse(P/'eda/dmx-interface.net');nets={x.attrib['name'].removeprefix('/'):{(a.attrib['ref'],a.attrib['pin']) for a in x} for x in n.findall('./nets/net')}
assert ('U5','17') in nets['DMX_P'] and ('U5','20') in nets['DMX_P']
assert ('U5','18') in nets['DMX_N'] and ('U5','19') in nets['DMX_N']
assert not nets['GND_USB'] & nets['GND_ISO']
for deg in range(-90,91):
 theta=math.radians(deg);phi=math.pi+40*theta/66;length=26*phi+40*(phi-theta)+math.pi*7
 assert abs(length-math.pi*73)<1e-9
assert abs(.5*9.45*(2.6**2-1.7**2)*.8-budget['buffer']['aged_delivered_J_at_2p6V'])<1e-9
bom=list(csv.DictReader((P.parents[1]/'docs/hardware/dmx-hardware-bom.csv').open()));assert len(bom)==54
# Compare the repaired power-path procurement entries to the actual CLI export.
# A correct row count alone did not catch the obsolete diode/comparator entries.
power_components={c.attrib['ref']:c.findtext('value') for c in E.parse(P/'eda/power-service/power-service.net').findall('./components/comp')}
dongle_bom={r['reference']:r for r in bom if r['assembly']=='Dongle'}
power_bom_contract={'U8':'TLV3012BIDCKR','U10':'TPS3700DDCR','U19':'TPS2116DRLR'}
for ref,mpn in power_bom_contract.items():
 assert power_components[ref]==mpn, (ref,power_components.get(ref))
 assert dongle_bom[ref]['candidate_mpn']==mpn and int(dongle_bom[ref]['quantity'])==1, ref
assert 'D_MAIN' not in power_components
assert not any('D_MAIN' in r['reference'].split('/') for r in bom if r['assembly']=='Dongle')
assert dongle_bom['D_AON_USB/D_AON_BUF']['candidate_mpn']=='BAT54H,115'
assert int(dongle_bom['D_AON_USB/D_AON_BUF']['quantity'])==2
assert next(r for r in bom if r['reference']=='C_BUF')['candidate_mpn']=='HV1325-2R7156-R'
assert abs(.5*15*(2.6**2-1.5**2)*.8-27.06)<1e-9
assert not any(any(x in str(r) for x in ['ESP32','CP2102','STUSB4500','TUSB320','USB-UART']) for r in bom)
assert next(r for r in bom if r['assembly']=='Dongle' and r['reference']=='U2')['candidate_mpn']=='AT25SF161B-MHB-T'
assert 'D06_SPI_NOR_max' in j['valid_solids'] and 'D06_CP2102N' not in j['valid_solids']
assert j['valid_solids']['D06_SPI_NOR_max']
report={'status':'PASS','product_acceptance':'NOT_RELEASED','solid_validity_count':len(j['valid_solids']),'major_package_intersections':0,'clearance_checks':len(j['clearance_checks']),'barrel_mechanical_pairs_at_neutral':j['barrel_mechanical_pair_count'],'barrel_mechanical_intersections':0,'lock_release_checks':len(j['lock_release_checks']),'guide_wire_sweep':j['guide_wire_sweep'],'usb_window_lane_axial_gap_mm':j['usb_window_lane_axial_gap_mm'],'step_files':len(list((P/'exports').glob('*.step'))),'svg_sheets':3,'bom_rows':len(bom),'partial_DMX_netlist_components':len(n.findall('./components/comp')),'power_service_components':power['components'],'power_service_ERC_errors':power['erc_errors'],'USB_data':'not present','SPI_NOR':'AT25SF161B-MHB-T','charge_nominal_mA':budget['charge']['nominal_mA'],'input_static_bound_mA':budget['input']['whole_VBUS_static_bound_mA'],'rolling_loop_sample_angles':181,'nominal_energy_J':27.06,'derated_energy_J_at_nominal_charge':budget['buffer']['aged_delivered_J_at_2p6V'],'derated_energy_J_at_low_charge':budget['buffer']['aged_delivered_J_at_low_charge_2p548V'],'estimated_aged_low_charge_runtime_at_1p11W_s':budget['buffer']['aged_low_charge_seconds_at_1p11W'],'footprint_set':'37assigned;36source-backed;1switch mounting datum gate; RF replacement retuning open','scope':'Structural/artifact/math checks only; separate DMX and power/buffer/POR/cutoff/SPI/service real KiCad ERC passed; MCU support/dual-band frontend checked, dual-feed antenna prototype captured but tuning/coupling unqualified; product NOT RELEASED. No full-product ERC/PCB DRC, rendered browser, whole-assembly motion, fixture-fit, wire fatigue or hardware tests.'}
(P/'exports/package-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
