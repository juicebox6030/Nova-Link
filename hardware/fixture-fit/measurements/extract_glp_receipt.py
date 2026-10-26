"""Join original STEP analytic entity IDs to selected imported face measurements.
python3 hardware/fixture-fit/measurements/extract_glp_receipt.py
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import re,json,math
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'glp-x5'
p=ROOT/'hardware/fixture-fit/source-cache/glp-impression-x5-shell.stp'
raw=p.read_bytes();assert sha256(raw).hexdigest()=='25fed40decfcf0a511e4f6f78657a2386962d98e7a1f58fcea01bb32823af8e3'
e={int(k):v.replace('\n',' ').replace('\r',' ') for k,v in re.findall(r'#(\d+)\s*=\s*(.*?);',raw.decode('ascii'),re.S)}
def refs(v):return list(map(int,re.findall(r'#(\d+)',v)))
def xyz(k):return list(map(float,re.search(r',\(([^()]*)\)\)$',e[k]).group(1).split(',')))
shells={k:refs(v) for k,v in e.items() if v.startswith(('OPEN_SHELL(', 'CLOSED_SHELL('))}
features=[]
for k,v in e.items():
    if not v.startswith('CYLINDRICAL_SURFACE('):continue
    radius=float(v.rsplit(',',1)[1][:-1]);placement=refs(v)[0];pr=refs(e[placement]);center=xyz(pr[0]);axis=xyz(pr[1])
    # Base mounting features only; exact selections make interpretation reproducible.
    pair=abs(abs(center[0])-43)<1e-6 and abs(center[1]+17.75)<1e-6 and abs(center[2]-57)<1e-6 and abs(radius-11.1)<1e-6
    opposite=abs(center[0]-6.75)<1e-6 and abs(center[1]+17.75)<1e-6 and abs(center[2]+77)<1e-6 and abs(radius-11.9)<1e-6
    screw=abs(center[1]+7.85)<1e-6 or abs(center[1]+27.65)<1e-6
    screw=screw and abs(center[2]-57)<1e-6 and abs(radius-1.6)<1e-6
    if not (pair or opposite or screw):continue
    faces=[n for n,x in e.items() if x.startswith('ADVANCED_FACE(') and refs(x)[-1]==k]
    features.append({'surface_entity':k,'surface_text':v,'placement_entity':placement,'center_mm':center,'axis':axis,'radius_mm':radius,'diameter_mm':2*radius,'advanced_face_entities':faces,'source_shell_entities':[n for n,fs in shells.items() if any(f in fs for f in faces)],'interpretation':'paired mounting feature' if pair else 'opposite central mounting feature' if opposite else 'small adjacent mounting feature'})
top=json.loads((OUT/'topology.json').read_text());faces=json.loads((OUT/'faces.json').read_text())
selected=[160,161,165,187,188,215,216,229,243,244,247,248,249,250,253,254,257,258,259,260,273,274,280]
pair_axes=sorted(set(tuple(x['center_mm']) for x in features if x['interpretation']=='paired mounting feature'))
assert len(pair_axes)==2
paired_radius=next(x['radius_mm'] for x in features if x['interpretation']=='paired mounting feature')
small=next(x for x in features if x['interpretation']=='small adjacent mounting feature')
dx=abs(abs(small['center_mm'][0])-abs(pair_axes[0][0]));dy=abs(small['center_mm'][1]-pair_axes[0][1])
pitch=pair_axes[1][0]-pair_axes[0][0]
r={'source_sha256':sha256(raw).hexdigest(),'source_revision':{'archive':'CAD_Rev20240202-1','member':'GLP impression X5 3D Shell Rev20211111-1.stp','STEP_FILE_NAME':'HUELLE_SW0001','STEP_timestamp':'2021-11-02T12:58:24'},'units':'mm','datum':{'origin':[0,0,0],'axes':'source XYZ unchanged; Y approximately vertical in coherent display orientation; not a connector installation datum','transform':'identity; no shell repositioning'},'error_limits':{'STEP_connectivity_uncertainty_mm':0.05869810163750,'arithmetic_tolerance_mm':1e-6,'published_measurement_rounding_mm':0.01,'render_tessellation_deflection_mm':0.4,'selected_faces_tessellation_deflection_mm':0.05,'physical_manufacturing_tolerance_mm':None,'note':'STEP uncertainty is asserted connectivity accuracy, not a manufacturing tolerance or guaranteed coordinate error bound. Surface parameters are exact nominal values in this export; connector identity and mating-depth uncertainty are unbounded.'},'source_topology_counts':{'OPEN_SHELL':len(shells),'ADVANCED_FACE':sum(v.startswith('ADVANCED_FACE(') for v in e.values()),'PRODUCT':sum(v.startswith('PRODUCT(') for v in e.values()),'NEXT_ASSEMBLY_USAGE_OCCURRENCE':sum(v.startswith('NEXT_ASSEMBLY_USAGE_OCCURRENCE(') for v in e.values()),'CONTEXT_DEPENDENT_SHAPE_REPRESENTATION':sum(v.startswith('CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(') for v in e.values())},'source_analytic_features':features,'imported_local_face_measurements':[faces[n-1] for n in selected], 'derived_nominal_dimensions_mm':{'paired_axis_pitch':pitch,'paired_feature_diameter':2*paired_radius,'between_cylindrical_envelopes_in_X':pitch-2*paired_radius,'small_feature_diameter':2*small['radius_mm'],'small_feature_X_offset_from_large_axis':dx,'small_feature_Y_offset_from_large_axis':dy,'small_feature_diagonal_pitch':math.hypot(2*dx,2*dy),'paired_land_plane_Z':faces[214]['Position'][2],'paired_feature_axial_limits_Z':[faces[242]['bounds_mm']['min'][2],faces[242]['bounds_mm']['max'][2]],'modeled_axial_span':faces[242]['bounds_mm']['size'][2],'paired_land_Y_limits':[faces[214]['bounds_mm']['min'][1],faces[214]['bounds_mm']['max'][1]],'paired_land_height':faces[214]['bounds_mm']['size'][1],'opposite_feature_diameter':2*next(x['radius_mm'] for x in features if x['interpretation']=='opposite central mounting feature'),'opposite_feature_axis_XY':next(x['center_mm'][:2] for x in features if x['interpretation']=='opposite central mounting feature')},'fit_conclusion':'No compactDMX fit conclusion. Local mounting features only; no connector mating face, latch envelope, installed connector protrusion, verified DMX/power assignment, or installed shell transform is established. No comparative overlay performed.'}
(OUT/'measurement-receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'source_shells':len(shells),'selected_source_cylinders':len(features),'source_features':features,'derived_nominal_dimensions_mm':r['derived_nominal_dimensions_mm']},indent=2))
