"""FreeCAD 1.1.3: source-topology census; never repositions source geometry.
Run from repo root: ~/.local/bin/freecadcmd hardware/fixture-fit/measurements/analyze_glp.py
Set NOVA_FIT_RENDER_MESH=1 to also emit the temporary whole-fixture review mesh.
"""
import json, re, hashlib, os
from collections import Counter
from pathlib import Path
import Part, Mesh
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'hardware/fixture-fit/source-cache/glp-impression-x5-shell.stp'
OUT = Path(__file__).resolve().parent/'glp-x5'
OUT.mkdir(exist_ok=True)
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '25fed40decfcf0a511e4f6f78657a2386962d98e7a1f58fcea01bb32823af8e3'
text = raw.decode('ascii')
entities = {int(k): v.replace('\n',' ').replace('\r',' ') for k,v in re.findall(r'#(\d+)\s*=\s*(.*?);', text, re.S)}
def vec(v): return [v.x,v.y,v.z]
def bounds(s):
    b=s.BoundBox
    return {'min': [b.XMin,b.YMin,b.ZMin], 'max': [b.XMax,b.YMax,b.ZMax], 'size': [b.XLength,b.YLength,b.ZLength]}
s = Part.read(str(SOURCE))
records=[]
for n,f in enumerate(s.Faces,1):
    surf=f.Surface
    r={'face':n,'type':type(surf).__name__,'area_mm2':f.Area,'bounds_mm':bounds(f),'center_of_mass_mm':vec(f.CenterOfMass),'wires':len(f.Wires),'edges':len(f.Edges)}
    for name in ['Radius','Center','Axis','Position']:
        if hasattr(surf,name):
            v=getattr(surf,name)
            r[name]=vec(v) if hasattr(v,'x') else v
    records.append(r)
edges=[]
for n,e in enumerate(s.Edges,1):
    try:
        c=e.Curve
    except Exception as exc:
        edges.append({'edge':n,'unreadable_curve':str(exc)})
        continue
    if type(c).__name__=='Circle':
        edges.append({'edge':n,'radius_mm':c.Radius,'center_mm':vec(c.Center),'axis':vec(c.Axis),'length_mm':e.Length,'closed':e.isClosed()})
shells=[{'shell':i,'faces':len(x.Faces),'closed':x.isClosed(),'bounds_mm':bounds(x)} for i,x in enumerate(s.Shells,1)]
# Source shell-face entity IDs, independent of importer order.
source_shells={str(k):v for k,v in entities.items() if v.startswith(('OPEN_SHELL(', 'CLOSED_SHELL(', 'SHELL_BASED_SURFACE_MODEL('))}
assembly={str(k):v for k,v in entities.items() if any(t in v for t in ['NEXT_ASSEMBLY_USAGE_OCCURRENCE(', 'CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(', 'ITEM_DEFINED_TRANSFORMATION(', 'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(', 'MAPPED_ITEM(', 'REPRESENTATION_MAP(', 'PRODUCT(', 'SHAPE_REPRESENTATION_RELATIONSHIP(', 'UNCERTAINTY_MEASURE_WITH_UNIT('])}
report={'source':str(SOURCE.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'header_file_name_entity':text.split('FILE_NAME(',1)[1].split(';',1)[0], 'units':'mm; STEP #269269 SI_UNIT(.MILLI.,.METRE.)','coordinate_policy':'Original supplied XYZ, identity transform. No assembly or installed transform invented.', 'valid':s.isValid(),'shape_type':s.ShapeType,'solids':len(s.Solids),'shells':shells,'faces':len(s.Faces),'surface_counts':dict(Counter(r['type'] for r in records)), 'bounds_mm':bounds(s),'circle_edge_count':sum('radius_mm' in x for x in edges),'unreadable_edge_curves':sum('unreadable_curve' in x for x in edges),'assembly_entities':assembly,'source_shell_entities':source_shells}
report['closed_imported_shells']=sum(x['closed'] for x in shells)
report['optimal_bounds_triangulation_mm']=bounds_proxy=s.optimalBoundingBox()
report['optimal_bounds_triangulation_mm']={'min':[bounds_proxy.XMin,bounds_proxy.YMin,bounds_proxy.ZMin],'max':[bounds_proxy.XMax,bounds_proxy.YMax,bounds_proxy.ZMax],'size':[bounds_proxy.XLength,bounds_proxy.YLength,bounds_proxy.ZLength]}
(OUT/'topology.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'faces.json').write_text(json.dumps(records,indent=2)+'\n')
(OUT/'circles.json').write_text(json.dumps(edges,indent=2)+'\n')
# Derived review mesh only. No source B-rep payload is copied into measurements.
# A line-based JSON view gives renderer numeric geometry without needing STL binaries.
if os.environ.get('NOVA_FIT_RENDER_MESH') == '1':
    vertices, triangles=s.tessellate(0.4)
    (OUT/'view-mesh.json').write_text(json.dumps({'vertices':[vec(v) for v in vertices], 'triangles':triangles},separators=(',',':')))
# Select model-native local panel faces; these are mounting features, not connector mating faces.
selected=[160,161,165,187,188,215,216,229,243,244,247,248,249,250,253,254,257,258,259,260,273,274,280]
features=[]
for n in selected:
    face=s.Faces[n-1]
    vs,ts=face.tessellate(0.05)
    features.append({'face':n,'vertices':[vec(v) for v in vs],'triangles':ts})
(OUT/'selected-panels-mesh.json').write_text(json.dumps(features,separators=(',',':')))
try:
    print('OPTIMAL_BOUNDS',s.optimalBoundingBox.__doc__)
    print('OPTIMAL_BOUNDS_RESULT',s.optimalBoundingBox())
except Exception as exc:
    print('OPTIMAL_BOUNDS_UNAVAILABLE',str(exc))
print(json.dumps({k:v for k,v in report.items() if k not in ['assembly_entities','source_shell_entities','shells']},indent=2))
print('Shell count',len(shells),'shell face counts',Counter(x['faces'] for x in shells))
