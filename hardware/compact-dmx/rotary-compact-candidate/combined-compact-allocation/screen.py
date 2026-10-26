"""Two arrangements only. Millimetres; bounds are allocations, not approvals."""
from pathlib import Path
import json,hashlib,math
P=Path(__file__).resolve().parent;root=P.parents[3]
if not (P/'protected-inputs.json').exists():
 files=[]
 for f in ['stationary-source-pod','collar-source-integrated','power-architecture-screen']:
  files += [p for p in (P.parent/f).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 files += [p for p in (P.parents[1]/'eda/buffer-fit-candidate/protected25-placement').rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 sources=json.loads((P.parent/'stationary-source-pod/sources.json').read_text())
 files += [root/s['path'] for s in sources]
 (P/'protected-inputs.json').write_text(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
 (P/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
baseline=[330,89,72]
# Existing pod and actual collar retained. Delete60mm of empty core allocation:
# collar shift -22.8; core shortened142 ->82; output blank142 ->82.
inline=[270,89,72]
# Same128-long pod, offset to negativeY clear ofR33 by2mm:
# pod originalY[-31,51], translate -86 ->[-117,-35].
# Align pod X[-12,116], inputblank[-36,-12], outputblank[82,106].
# Both24mm end blanks retained. Connector inputY[-78,-30], Z[-39,9].
offset=[152,150,72]
out={'units':'mm','baseline':{'dimensions':baseline,'volume_mm3':math.prod(baseline)},
 'inline':{'dimensions':inline,'volume_mm3':math.prod(inline),'length_reduction_mm':60,'volume_reduction_percent':100*(1-math.prod(inline)/math.prod(baseline)), 'pod_x':[-140,-12],'input_blank_x':[-164,-140],'neck_x':[-12,0],'core_x':[0,82],'collar_released_x':[4,81.37],'output_blank_x':[82,106],'collar_translation_x':-22.8,'reason':'Retains finite oldpod branch and R12 trunk allocations; removes empty core instead of appending source. Does not prove shortest globally.'},
 'offset':{'dimensions':offset,'volume_mm3':math.prod(offset),'pod_x':[-12,116],'pod_y':[-117,-35],'collar_x':[4,81.37],'source_side_gap_to_R33':2,'reason_rejected':'Length improves but transverse width150 exceeds inline89; bounding volume22.37percent below baseline versus inline18.18percent, only5.12percent better than inline while68.54percent wider. NegativeY placement avoids the forward180degree USB sector, but requires a new transverse harness neck and source mounting; those can only increase this optimistic bound. Select narrower inline for fixture-adjacent development. Actual181-position screen below.'},
 'lower_bounds':{'source_only_reservation':[72.9,47.7,44], 'whole_carrier_conservative':[81,52,44], 'inline_axial_sum_source_only_plus_collar_plus_two_blanks':72.9+77.37+48,'inline_axial_sum_carrier_plus_collar_plus_two_blanks':81+77.37+48,'excluded_from_lower_bound':'walls, film, assembly tolerances, finite primary/secondary termination bends, neck, lock access, source carrier retention; therefore NOT achievable housing dimensions'},
 'selection':'Inline conditional allocation for one CAD attempt; continuous branch/terminal construction must be checked, not implied by labels.'}
(P/'screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
# Completed S12 update: dimensions only, no integration or altered source circuit.
r=math.hypot(28.1,18);dims=[275,56+r+1.25,39+r+1.25]
p=P/'source12-dimension-screen.json'
if p.exists():
 d=json.loads(p.read_text());d.update(outer_clamp_radius_at_transform=r,radial_excess_before_wall=r-33,illustrative_OD_at_transform=2*(r+1.25),illustrative_combined_dimensions=dims,illustrative_volume_mm3=math.prod(dims),reduction_vs_rejected_baseline_percent=100*(1-math.prod(dims)/math.prod(baseline)))
 p.write_text(json.dumps(d,indent=2)+'\n')
