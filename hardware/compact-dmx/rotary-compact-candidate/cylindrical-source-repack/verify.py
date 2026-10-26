from pathlib import Path
import json,hashlib,math
P=Path(__file__).resolve().parent;R=P.parents[3]
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((P/'protected-inputs.json').read_text());assert all(h(R/k)==v for k,v in protected.items())
s=json.loads((P/'screen.json').read_text());q=json.loads((P/'checks.json').read_text());n=json.loads((P/'native-screen.json').read_text())
assert abs(s['max_reserved_corner_radius']-math.sqrt(26.5**2+22.5**2))<1e-12
assert s['film_gap_at_bore_minus_point2']<0 and not q['transition_pass']
assert len(n['motion_screen'])==181 and n['native_shapes']==360
assert all(min(x['source_bay_to_rotor_axial_gap'],x['source_bay_to_USB_body_axial_gap'],x['source_bay_to_lock_access_axial_gap'])>0 for x in n['motion_screen'])
for v in s['variants'].values():assert abs(v['bounding_volume_mm3']-math.prod(v['bounding_box']))<1e-6
if (P/'receipt.json').exists():
 receipt=json.loads((P/'receipt.json').read_text());assert all(h(P/k)==v for k,v in receipt['artifacts'].items())
print('INTEGRITY PASS:',len(protected),'protected; 181 source-only axial screens. GEOMETRY HOLD: film/neck fail, incomplete construction. No CAD release.')
