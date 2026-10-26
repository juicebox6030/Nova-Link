import FreeCAD as A,Part,json
from pathlib import Path
P=Path(__file__).resolve().parent;D=A.openDocument(str(P/'integrated.FCStd'));V=A.Vector
S={o.Name:o.Shape for o in D.Objects if hasattr(o,'Shape')};rows=[]
for a,b in [('StaticDevelopedFanout','MovingStaticTail'),('StaticDevelopedFanout','TailClampShoe'),('StaticDevelopedFanout','SRC_J0_maximum_body_allocation'),('SRC_PCB_27x20x1_actual_holes_nominal','RotorHalfPositiveY'),('SRC_PCB_27x20x1_actual_holes_nominal','BoardEndRetainer')]:
 distance=S[a].distToShape(S[b])[0];vol=S[a].common(S[b]).Volume
 rows.append({'parts':[a,b],'distance_mm':distance,'intersection_mm3':vol});assert distance<1e-5 and vol<1e-6,(a,b,distance,vol)
# Specific new thread region bounds, no blanket mounting intersection exceptions.
threads=[]
for n in ['BoardRetainerScrew_m11','BoardRetainerScrew_11','TailClampScrew_74_4','TailClampScrew_96_6']:
 c=S[n].common(S['RotorHalfPositiveY']);bb=c.BoundBox
 if n.startswith('Board'):assert bb.XMin>=100.4999 and bb.XMax<=102.0001
 else:assert bb.YMin>=25.7999 and bb.YMax<=26.4001
 threads.append({'part':n,'volume_mm3':c.Volume,'bounded_thread_region':True})
# Nominal retention dimensions and body continuity directly from saved faces are augmented
# by the independently checked copper strips, rather than inventing a drilling keepout.
out={'status':'PASS finite contacts without volumetric intersections; four new bounded thread regions','contacts':rows,'new_threads':threads,'solder_interface':'Source J0 0.3mm land/joint envelope touches exposed flex underside. Actual solder fillet/thickness/process unqualified.','support_tolerance_mm':{'nominal_gap':1.24,'PCB_max_thickness':1.1,'two_surface_allowance':.06,'remaining_normal_gap':.08,'sidewall_clear_span':20.2,'PCB_min_width':19.9,'maximum_float':.15,'copper_nominal_gap':.3005,'rail_allowance':.03,'PCB_edge_copper_allowance':.05,'remaining_copper_gap':.0705},'source_polarity':{'J0.1':'/FPC_5V: localX6 -> globalX81','J0.2':'/GND_ISO: localX15 -> globalX90'}}
(P/'contacts.json').write_text(json.dumps(out,indent=2)+'\n');print('CONTACTS PASS',len(rows),'contacts;',len(threads),'bounded threads',flush=True)
