from pathlib import Path
import json,math,numpy as np
P=Path(__file__).resolve().parent
th=math.acos(11/24);run=24*math.sin(th);p=np.linspace(0,2*math.pi,1441);best=1e9;where=None
for arc in [0,1]:
 for t in np.linspace(0,th,1001):
  if arc==0:x=-27+12*math.sin(t);z=-29+12*(1-math.cos(t))
  else:x=-27+run-12*math.sin(t);z=-16-12*(1-math.cos(t))
  xx=x-2.75*math.sin(t)*np.cos(p);zz=z+2.75*math.cos(t)*np.cos(p)
  bore=35.5-.2-14*(xx+27)/27
  for y in [-8,0,8]:
   yy=y+2.75*np.sin(p);gap=np.where((xx>=-27)&(xx<=0),bore-np.hypot(yy,zz),1e9);j=int(np.argmin(gap))
   if gap[j]<best:best=float(gap[j]);where=[float(xx[j]),float(yy[j]),float(zz[j])]
# Sampling is supplementary to exact swept BRep containment, never independent fit certification.
cir={'sourcepod':128,'neck':12,'core':87,'old_end_blanks_removed':48};cyl={'sourcebay':88,'neck':27,'core':87};rows={}
for name,rear in [('classic',60.8),('TRUE1',64),('NEMA_flanged_comparison_only',88.9)]:
 rows[name]={}
 for term in [0,20,40]:
  a=sum(cir[k] for k in ['sourcepod','neck','core'])+rear+term;b=sum(cyl.values())+rear+term
  rows[name][str(term)]={'CIR_panel_allocation':a,'CYL_panel_allocation':b,'conditional_length_reduction':a-b,'CIR_box_volume':a*91*74,'CYL_box_volume':b*77**2,'conditional_volume_reduction_fraction':1-b*77**2/(a*91*74)}
o={'revision':'CYL-R2','source_shell_OD':77,'source_bore':71,'nominal_wall':3,'allocated_bore_radial_tolerance':.2,'outer_radius_plus_tolerance':38.7,'minimum_source_shell_wall_allocated':2.6,'neck_lock_relief_min_nominal_wall':24.7-(21.5+14*4.3/27),'neck_lock_relief_allocated_wall_after_point3':24.7-(21.5+14*4.3/27)-.3,'film_radius':math.hypot(26.5,22.75),'film_worst_bore_clearance':35.3-math.hypot(26.5,22.75),'whole_reservation_corner_clearance':35.3-math.hypot(26.5,22.5),'neck_length':27,'two_arc_axial_run':run,'core_end_straight':27-run,'sampled_full_corridor_radial_gap_after_bore_allowance':best,'worst_sample_surface_point':where,'CIR_domains':cir,'CYL_domains':cyl,'matched_allowance_sensitivity':rows,'access_accounting':'0/20/40mm added total sensitivity. 40 means two disjoint20mm terminal/tool regions. Existing CIRpod spareaccess may overlap; unproved, hence not a finished comparison. No access reused twice in CYL coordinates.','source_pin_translation':[4.5,0,-2],'molded_NEMA_intent_unchanged':True,'no_final_mated_envelope':True,'no_electrical_changes':True}
(P/'comparison.json').write_text(json.dumps(o,indent=2)+'\n');print('MATCHED CLASSIC',rows['classic']['40'],'FILM',o['film_worst_bore_clearance'],'FULLRING',best)
