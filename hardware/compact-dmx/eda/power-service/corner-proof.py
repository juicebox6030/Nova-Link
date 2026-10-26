"""Independent, netlist-based D-A/D-C corner enumeration; D-B deliberately unmet.

Does not import the generator or power_budget.py. Datasheet limits are separately
transcribed here; hashes/pages are in source-evidence.json. No transient solver,
bench result, or manufacturing acceptance is implied by a passing static check.
"""
from pathlib import Path
from itertools import product
import json, math, re, xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
root = ET.parse(P / 'power-service.net')
values = {c.attrib['ref']: c.findtext('value') for c in root.findall('./components/comp')}
pins = {p.attrib['ref']+'.'+p.attrib['pin']: n.attrib['name'].removeprefix('/')
        for n in root.findall('./nets/net') for p in n}

def kohm(ref):
    return float(re.match(r'([\d.]+)k', values[ref]).group(1))

# Tie the independent equations to actual populated values and exported nets.
assert values['U19'] == 'TPS2116DRLR' and values['U10'] == 'TPS3700DDCR'
assert pins['U19.3'] == pins['U19.4'] == pins['U19.5'] == 'LIMITED_5V'
assert pins['U19.2'] == pins['U19.7'] == pins['U3.4'] == pins['R_VBUS_TOP.1'] == 'NORMAL_IN'
assert pins['U19.6'] == pins['U19.1'] == 'GND_USB'
assert pins['U10.3'] == pins['R_VBUS_TOP.2'] == pins['R_VBUS_BOTTOM.1'] == 'VBUS_SENSE'
assert pins['U10.1'] == pins['R_VBUS_PU.2'] == 'VBUS_OK'
assert pins['U3.2'] == 'AON_RAW' and pins['U3.3'] == 'RUN'
assert kohm('R_OSEL') == 17.4 and kohm('R_ICHG') == kohm('R_VCHG') == 9.53
assert 'D_MAIN' not in values and 'C_VBUS_FILTER' not in values
assert values['C_BUF'] == 'HV1325-2R7156-R 15F 2.7V'

# Independent corner set: initial+temperature allowances for each resistor.
Rallow = 0.001 + 100*25e-6
corners = []
for edge, thresholds in [('rising', (.396, .404)), ('falling', (.387, .400))]:
    for top_error, bottom_error, bias, vt in product(
            (-Rallow, Rallow), (-Rallow, Rallow), (-25e-9, 25e-9), thresholds):
        top = kohm('R_VBUS_TOP')*1000*(1+top_error)
        bottom = kohm('R_VBUS_BOTTOM')*1000*(1+bottom_error)
        corners.append((edge, vt*(1+top/bottom)+bias*top))
fall_min = min(v for edge,v in corners if edge == 'falling')
rise_max = max(v for edge,v in corners if edge == 'rising')
assert len(corners) == 32
assert .387 > 0 and .387 <= .400 <= .404 # already includes worst charge-detector hysteresis

limits = [25230/(kohm('R_ILIM')*(1+Rallow))**1.016,
          22980/(kohm('R_ILIM')*(1-Rallow))**.940]
normal_min = 4.4-limits[1]/1000*(.135+.060)
# Test both the target specification and a stricter full boost regulation envelope.
mode_corners = []
for edge, threshold in corners:
    for output_error, vbypass, sag in product((.02, .035), (.050, .150), (0., .050)):
        mode_margin = threshold-sag-(3.6*(1+output_error)+vbypass)
        assert mode_margin > .025
        assert threshold-sag > 3.6*1.035  # a cap-fed boost cannot satisfy source GOOD
        mode_corners.append(mode_margin)
assert normal_min > rise_max+.100 and normal_min-.050 > rise_max
assert limits[1]+.140 < 500

# Load/efficiency and 0.3ohm bypass resistance are allocations, not measured bounds.
qualified_vin = fall_min-.050
current = (1.1/.85 + .030*2.652/.80)/qualified_vin+.002
backup_min = qualified_vin-.300*current
assert current < limits[0]/1000 and backup_min > 3.41
assert backup_min > 3.6*1.035+.050 # loaded VOUT condition for cap charging, not just VIN
assert 3.6*.98 > 3.41  # preserve boost setting; lowering OSEL is not a free fix

# Confirm the two old false-good counterexamples and lost sag margin.
old_ref_error = 1.242*.0001*100+.009+.008+.0025+.0037
old_good = (1.223-old_ref_error)*(1+221*.999/(100*1.001))
old_vin_at_good = old_good-.500
assert old_vin_at_good < 3.6*1.02+.150
old_full_input = 4.4-.500-.135*limits[1]/1000
assert old_full_input-(3.6*1.02+.150) < .050

capacitance = 15*.9*.7
start_voltage = 2.6*.98-.100
floor = 1.700
energy = capacitance*(start_voltage**2-floor**2)/2*.8
runtime = energy/1.11
assert math.isclose(start_voltage, 2.448) and 10 < runtime < 11
# Cross-check the exported budget, without executing/importing its implementation.
budget = json.loads((P.parent/'power-budget.json').read_text())
assert math.isclose(budget['buffer']['aged_low_charge_seconds_at_1p11W'], runtime)
assert budget['buffer']['charge_hysteresis_max_V'] == .100
# Budget intentionally also uses maximum top resistance for the adverse bias
# term, even when the divider ratio uses minimum top resistance: a looser bound.
assert 0 <= min(mode_corners)-budget['source_mode_proof']['entry_margin_after_sag_V'] < .0001
assert 0 <= fall_min-budget['cutoff']['VBUS_estimated_low_V'] < .0001
assert math.isclose(budget['cutoff']['VBUS_estimated_high_V'], rise_max)
assert not budget['buffer']['runtime_guaranteed']

# D-B counterexample: source cannot furnish the specified minimum precharge point.
# Maximum precharge current/time is unknown. Do NOT turn this inequality into a
# guarantee about actual waveforms, duration, or eventual-start acceptance.
assert 500 > limits[1] and budget['startup']['TPS61094_ISS_max_mA'] is None
assert budget['startup']['acceptance'].startswith('UNMET')
input_reservoir = 11.1e-6
deficit_at_min_limit = .500-limits[0]/1000
time_to_exhaust_50mV = input_reservoir*.050/deficit_at_min_limit

result = {
    'static_corner_check': 'PASS', 'scope': 'Netlist-derived static arithmetic only',
    'detector_corners': len(corners), 'mode_corners': len(mode_corners),
    'normal_input_min_at_assumed_4p4V_source_V': normal_min,
    'GOOD_falling_min_V': fall_min, 'GOOD_rising_max_V': rise_max,
    'minimum_mode_margin_after50mV_sag_V': min(mode_corners),
    'input_demand_at_qualified_floor_mA': current*1000,
    'input_margin_at_qualified_floor_mA': limits[0]-current*1000,
    'buck_headroom_with_explicit_Ron_allocation_V': backup_min-3.41,
    'old_false_GOOD_normal_input_V': old_vin_at_good,
    'old_full_source_entry_margin_V': old_full_input-(3.6*1.02+.150),
    'start_after_worst_charge_hysteresis_V': start_voltage,
    'aged_runtime_estimate_s': runtime,
    'runtime_margin_over10s_s': runtime-10,
    'input_50mV_reserve_exhaustion_s_at500mA_and_min_limiter': time_to_exhaust_50mV,
    'startup_counterexample_is_waveform_proof': False,
    'cold_cap_startup_acceptance': 'UNMET',
    'transient_timing_thermal_load_and_efficiency_qualified': False,
    'manufacturing_acceptance': 'NOT_RELEASED',
}
(P/'corner-proof.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
