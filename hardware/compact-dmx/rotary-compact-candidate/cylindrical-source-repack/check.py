from pathlib import Path
import math,json,hashlib
P=Path(__file__).resolve().parent;R=P.parents[3];s=json.loads((P/'screen.json').read_text());protected=json.loads((P/'protected-inputs.json').read_text());bad=[k for k,v in protected.items() if hashlib.sha256((R/k).read_bytes()).hexdigest()!=v];assert not bad,bad
# Exact two circular arcs, R12; shared tangent at midpoint; finite OD5.5 screen.
r=12;th=math.acos(11/24);run=24*math.sin(th);pts=[]
for i in range(1001):
 t=th*i/1000;pts.append([-run+r*math.sin(t),-29+r*(1-math.cos(t))])
for i in range(1,1001):
 t=th*(1-i/1000);pts.append([-r*math.sin(t),-16-r*(1-math.cos(t))])
gap=min((35.1+(21.5-35.1)*(x+run)/run)-math.hypot(y,z)-2.75 for x,z in pts for y in [-8,0,8])

# Report the failed conical-neck fit; never suppress it as a pass.
# Physical sources are read-only; no invented new netlist or integrated board.
sourcecheck={k:hashlib.sha256((P.parent/k).read_bytes()).hexdigest()==v['sha256'] for k,v in json.loads((P/'sources.json').read_text()).items()};assert all(sourcecheck.values())
proof={'protected_hash_count':len(protected),'protected_failures':bad,'source_hashes':sourcecheck,'s_bend_samples_per_lane':len(pts),'lanes':3,'continuous_arc_radius':12,'arc_join_tangent_continuous':True,'endpoints_xz':[pts[0],pts[-1]],'minimum_conical_bore_wire_screen_gap':gap,'conical_bore_not_retained_or_released':True,'wire_to_wire_surface_gap':8-5.5,'transition_pass':gap>0,'CAD_generated':False,'phase0':'HOLD: no demonstrated materially compact complete construction; bounded screen ends before CAD','unclosed':['retained carrier and its installation-spacing crossings','primary branch/fuse/termination construction','secondary reroute to actual S12 J0 after source Z recenter','variant terminal/tool and molded NEMA cord interfaces','final housing/USB/endcap obstruction and whole-assembly motion']}
(P/'checks.json').write_text(json.dumps(proof,indent=2)+'\n');(P/'trunk-centrelines.json').write_text(json.dumps({'units':'mm','radius':12,'screen_OD':5.5,'paths':{str(y):[[x,y,z] for x,z in pts] for y in [-8,0,8]},'bounds':'source-bay trunk to core only; not electrical endpoint connections'},indent=2)+'\n');print(json.dumps(proof,indent=2))
