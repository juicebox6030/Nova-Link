"""Bounded source/arithmetic screen only. No circuit, CAD, or sibling writes."""
from pathlib import Path
from itertools import product
import hashlib, json, math, subprocess

P = Path(__file__).resolve().parent
R = P.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
protected = json.loads((P / 'protected-inputs.json').read_text())
assert len(protected) == 473
assert all(sha(R / n) == h for n, h in protected.items()), 'Frozen input changed'
assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=R, text=True).strip() == 'main'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == 'b42c0e6284aac734fde851c69146abf73920f337'

rot = 'hardware/compact-dmx/rotary-compact-candidate/'
source_specs = [
 ('RECOM RAC20-K Rev14-2025 pp1–6,9', P/'sources/recom-rac20-k.pdf', 'https://recom-power.com/pdf/Powerline_AC-DC/RAC20-K.pdf'),
 ('TRACO TMLM Rev July1,2026 pp1–3,5', P/'sources/traco-tmlm.pdf', 'https://www.tracopower.com/sites/default/files/products/datasheets/tmlm_datasheet.pdf?download=1'),
 ('MEAN WELL IRM20 specification2025-11-21 pp2–3', R/rot/'regulated-source/sources/irm20.pdf', 'https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF'),
 ('MEAN WELL PCB installation item2; explicitly includes IRM', R/rot/'stationary-irm20-integration/sources/meanwell-pcb-installation.pdf', 'https://www.meanwell.com/Upload/PDF/IRM-01/PCB.pdf'),
 ('TI TPS63070 SLVSC58B §§7.1,7.3,7.5,9.2', R/rot/'regulated-source/sources/tps63070.pdf', 'https://www.ti.com/lit/ds/symlink/tps63070.pdf'),
 ('TI TPS25947 SLVSFC9C §§6.3,7.3', R/rot/'regulated-source/sources/tps25947.pdf', 'https://www.ti.com/lit/ds/symlink/tps25947.pdf'),
 ('TI TPS25810 SLVSCR1C §§6.1,6.3,7.3', R/rot/'regulated-source/sources/tps25810.pdf', 'https://www.ti.com/lit/ds/symlink/tps25810.pdf'),
]
sources = [{'document': title, 'path': str(path.relative_to(R)), 'url': url,
            'sha256': sha(path), 'reused_readonly': not path.is_relative_to(P)}
           for title, path, url in source_specs]
assert sources[0]['sha256'] == '32d5efd6e92e70e4b84b0b7be8da77ee440e9617ea81cf075f9faed62386675b'
assert sources[1]['sha256'] == '97872edd7582b957f006fcfa7c2e414be98c08a0d51808ba3130fce55eb40d0e'
recom = (P/'sources/recom-rac20-k.txt').read_text()
traco = (P/'sources/traco-tmlm.txt').read_text()
assert 'Rev.: 14-2025' in recom and 'RAC20-12SK' in recom
assert 'Rev. July 1, 2026' in traco and 'TMLM 20112' in traco
assert '2 A slow blow type' in traco and 'Avoid routing PCB traces under the converter.' in traco

# Literal drawing dimensions, visually checked against saved rendered primary pages.
# TRACO's3.5 is a lateral offset, NOT pin length: pin projection is8mm!
families = [
 {'family': 'RECOM RAC20-K', 'candidate': 'RAC20-12SK/277', 'W':20.0,
  'body_nominal_LWH_mm':[52.5,27.4,23.0], 'body_max_LWH_mm':[53.0,27.9,23.5],
  'lead_projection_minmax_mm':[5.0,7.0], 'body_plus_max_lead_height_mm':30.5,
  'lead_diameter_minmax_mm':[.95,1.15], 'construction_permission':'UNKNOWN'},
 {'family': 'TRACO POWER TMLM20', 'candidate': 'TMLM 20112', 'W':20.0,
  'body_nominal_LWH_mm':[52.4,27.2,23.5], 'body_max_LWH_mm':[52.9,27.7,24.0],
  'lead_projection_minmax_mm':[7.5,8.5], 'body_plus_max_lead_height_mm':32.5,
  'lead_diameter_minmax_mm':[.5,1.5], 'lead_diameter_note':'Conservative use of general±0.5 drawing tolerance on Ø1.0; unusually broad, manufacturing clarification required.',
  'construction_permission':'UNKNOWN'},
]
assert len(families) == 2 and len({f['candidate'] for f in families}) == 2
for f in families:
 assert f['body_plus_max_lead_height_mm'] == f['body_max_LWH_mm'][2] + f['lead_projection_minmax_mm'][1]

# Independently derive the existing source model; do not import its generator/verifier.
regs = [v*(1+54200*(1+a)/(10000*(1+b)))+i*54200*(1+a)
        for v,a,b,i in product([.792,.808],[-.002,.002],[-.002,.002],[-100e-9,100e-9])]
hi = max(regs)
floor = 3334/(1000*1.002)*.9
flex = 2*1.046167656*1.75e-8/(.0078*70e-6*.9)*(1+.00393*60)
original = flex+.020+.045
tail_nom = .01419924378047946
tail_alloc = .01625024565988206
stationary = .00496436883132149
resistances = [('original',original),('tail_nominal_hot',original+tail_nom),
               ('tail_allocated_hot',original+tail_alloc),
               ('tail_and_stationary_wire_allocated_hot',original+tail_alloc+stationary)]
out_A = 1.5+.410+.001  # unchanged 410mA VCONN +1mA auxiliary allocation
out_W = hi*out_A

def solve(vs, resistance, eta):
 power = out_W/eta+.005
 disc = vs*vs-4*resistance*power
 assert disc > 0
 amps = (vs-math.sqrt(disc))/(2*resistance)
 independent = power/vs
 for _ in range(100):
  independent = power/(vs-independent*resistance)
 assert abs(amps-independent) < 1e-10
 return {'source_V':vs, 'eta_assumption':eta, 'input_A':amps,
         'converter_VIN_V':vs-amps*resistance, 'module_output_W':vs*amps,
         'flex_copper_loss_W':amps*amps*flex, 'total_series_loss_W':amps*amps*resistance,
         'breaker_floor_margin_A':floor-amps}

existing = [dict(case=name, loop_ohm=res, **solve(4.6375,res,.8)) for name,res in resistances]
parent_path = R/'.tools/checks/stationary-and-collar-parent/parent-receipt.json'
parent = json.loads(parent_path.read_text())
for a,b in zip(existing,parent['power_recalculation']):
 assert a['case'] == b['case'] and abs(a['input_A']-b['conditional_input_A']) < 1e-9
 assert abs(a['loop_ohm']-b['loop_ohm']) < 1e-12
assert existing[0]['breaker_floor_margin_A'] > 0
assert all(x['breaker_floor_margin_A'] < 0 for x in existing[1:])
fullR = resistances[-1][1]
eta_to_meet_existing_breaker = out_W/(floor*(4.6375-floor*fullR)-.005)

# 12V source voltage stacks: IRM published total tolerance already includes line/load.
# TRACO has separate set/line/load entries. Its temperature coefficient is treated
# symmetrically over0..50C around25C; this explicit allocation is NOT a startup bound.
irm12 = 12*(1-.025-.0003*25)-.2
traco12 = 12*(1-.02-.005-.01-.0002*25)-.240
buses12 = [dict(case=name, **solve(v,fullR,eta))
           for name,v in [('IRM20-12 parameter stack',irm12),
                          ('TMLM20112 parameter stack',traco12),
                          ('11V engineering sensitivity, NOT a RAC20 guarantee',11.0)]
           for eta in [.8,.85,.9]]
assert all(x['input_A'] < 1.66 and x['converter_VIN_V'] > 10 for x in buses12)
# Fault-voltage counterexamples, not a promise of bounded fault waveforms.
assert 12*1.95 > 20  # RECOM published OVP upper percentage exceeds TPS63070 absolute max
assert 16.2 > 16  # IRM20-12 OVP upper value exceeds TPS63070 recommended operating range
assert out_A < 2  # within published max output rating; NOT a guarantee of useful headroom

# One existing-IRM20 allocation comparison: spacing reservations, not certification.
boxes = []
for name,L,W,H in [('body-face comparison, excludes pins',72.9,47.7,39.5),
                   ('maximum-pin referenced module',72.9,47.7,44.0),
                   ('carrier assembly planning allocation',81.0,52.0,44.0)]:
 boxes.append({'case':name,'LWH_mm':[L,W,H], 'rectangular_bore_ID_mm':math.hypot(W,H),
               'illustrative_OD_2p5mm_wall_mm':math.hypot(W,H)+5})
assert 47.7 > 43
# Keep the original nominal trunk top atZ−14.5 and reserve5 below maximum pin:
module_bottom = -14.5+5+4.5
module_top = module_bottom+24.5
clearance_top = module_top+10
coaxial_reservation_diameter = 2*math.hypot(47.7/2,clearance_top)
assert module_bottom == -5 and clearance_top == 29.5

numeric = {'kind':'Conditional DC/source arithmetic, no functional or manufacturing acceptance',
 'reg_output_max_V':hi,'reg_output_stress_A':out_A,'reg_output_stress_W':out_W,
 'VCONN_stress_A':.410,'auxiliary_output_A':.001,'breaker_floor_A':floor,
 'resistance_ohm':{'flex_hot':flex,'termination':.020,'efuse_max':.045,
                  'tail_nominal_hot':tail_nom,'tail_allocated_hot':tail_alloc,'stationary_hot':stationary},
 'existing_5V_reproduction':existing, 'required_eta_existing_fullR_to_breaker_floor':eta_to_meet_existing_breaker,
 '12V_conditional_comparison':buses12,'12V_warning':'Current headroom is not startup/thermal/fault protection proof; existing board incompatible without redesign.',
 'IRM20_allocation_comparison':boxes,
 'fixed_trunk_coaxial_example':{'module_bottom_Z_mm':module_bottom,'module_top_Z_mm':module_top,
  'top_reservation_Z_mm':clearance_top,'rectangular_corner_bore_ID_mm':coaxial_reservation_diameter,
  'illustrative_OD_2p5mm_wall_mm':coaxial_reservation_diameter+5,
  'limitation':'One conservative body+lead reservation at unchanged trunk coordinates; not an optimized bore or complete assembly.'}}
(P/'numeric-checks.json').write_text(json.dumps(numeric,indent=2)+'\n')
(P/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
receipt = {'revision':'POWER-ARCHITECTURE-SCREEN-R1','HEAD':'b42c0e6284aac734fde851c69146abf73920f337',
 'scope':'Two alternative families, one12V MPN each; one existingIRM20 allocation comparison; no CAD/circuit changes',
 'decision':'No alternative qualified for compact enclosure construction. Prefer a stationary source-pod allocation honoring published IRM20 spacing, with12V internal-bus development conditional on a new regulator/protection qualification.',
 'alternative_families':families,'installation_permission_found_for_tight_system_enclosure':False,
 'permission_elsewhere':'UNKNOWN; no general waiver inferred and no vendor contact',
 'numeric_evidence':'numeric-checks.json','source_manifest':'sources.json','full_findings':'README.md',
 'parent_model_sha256':sha(parent_path),'protected_inputs':473,'all_protected_hashes_match':True,
 'commands':['git status --short --branch','git rev-parse HEAD',
 'curl -fL --max-redirs <3..5> --max-time <20..30> <officialURL> -o <owned>/sources/<file> (URLs/outcomes in retrieval.json)',
 'pdftotext -layout <owned>/sources/recom-rac20-k.pdf <owned>/sources/recom-rac20-k.txt',
 'pdftotext -layout <owned>/sources/traco-tmlm.pdf <owned>/sources/traco-tmlm.txt',
 'pdftoppm -f 9 -singlefile -scale-to 1500 -png <owned>/sources/recom-rac20-k.pdf <owned>/sources/recom-dimension-p9',
 'pdftoppm -f 5 -singlefile -scale-to 1500 -png <owned>/sources/traco-tmlm.pdf <owned>/sources/traco-dimension-p5',
 'python3 hardware/compact-dmx/rotary-compact-candidate/power-architecture-screen/verify.py',
 'sha256sum -c SHA256SUMS (owned directory)'],
 'open_gates':['Applicable alternative-module installation/approval conditions and terminal/system clearances',
 'Stationary pod/carrier/trunk/endcap/PE/insulation and assembly allocation; no actual CAD fit',
 '12V input protection, converter regulation/filter/magnetics, startup and independent5V output fault barrier',
 'Source current floor failure in frozen5V stress model; no resistor/circuit change',
 'Sealed thermal, line derating, load steps/inrush/ESR/reverse leakage/fault response, FPC lifecycle and USB compliance'],
 'no_CAD_circuit_firmware_hardware_install_outreach_children_publication':True,
 'manufacturing_release':False}
(P/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files = sorted(p for p in P.rglob('*') if p.is_file() and p.name != 'SHA256SUMS' and '__pycache__' not in p.parts)
(P/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(P)}\n' for p in files))
print(f'PASS: {len(protected)} frozen inputs, 7 primaryPDF hashes, 2 families/2 MPNs, four parent-model reproductions, nine12V sensitivity cases')
print(f'5V stress {existing[-1]["input_A"]:.9f}A, breaker floor {floor:.9f}A, margin {existing[-1]["breaker_floor_margin_A"]*1000:.6f}mA; FAIL retained')
print(f'12V IRM stack {buses12[0]["input_A"]:.9f}A conditional; module spacing box72.9x47.7x44mm, bore{boxes[1]["rectangular_bore_ID_mm"]:.6f}mm')
print('DECISION: alternative construction UNKNOWN; production gate UNMET; no circuit/CAD changes')
