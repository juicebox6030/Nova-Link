"""CYL-R1 single arrangement; engineering screens, not qualified construction."""
from pathlib import Path
import json,math,hashlib
P=Path(__file__).resolve().parent;R=P.parents[3]
# Cross-section is recentered by -2 mm Z. No source dimension is reduced.
reserve=(81,52,44);tol=.5;wall=3;inner=35.1;outer=inner+wall
corner=math.hypot(26+tol,22+tol)
# Three finite OD4.5 trunks plus 0.5 radial assembly allowance below reservation.
lanes=[(-8,-29),(0,-29),(8,-29)];rwire=2.75
# Two equal, opposite R12 arcs lower trunks by 13mm, with tangential straight ends.
rad=12;delta=13;theta=math.acos(1-delta/(2*rad));run=2*rad*math.sin(theta)
source_length=81+2*(tol+wall);core=87;term=20
base=source_length+run+core+2*term
variants={'classic':(30.4,30.4),'TRUE1':(31.2,32.8),'NEMA_flange_comparison_NOT_selected':(45.3,43.6)}
results={}
for k,d in variants.items():
 L=base+sum(d);results[k]={'rear_depths':d,'panel_to_panel_allocation':L,'bounding_box':[L,2*outer,2*outer],'bounding_volume_mm3':L*(2*outer)**2,'vs_CIR_volume_fraction':L*(2*outer)**2/(275*91*74),'finished_product_envelope':False}
out={'status':'PARTIAL: radial/axial screen only; source retention crossings and terminal construction unqualified','whole_carrier_reservation':reserve,'tolerance_each_face':tol,'wall_proposal':wall,'bore_radius':inner,'outside_diameter':2*outer,'max_reserved_corner_radius':corner,'nominal_corner_gap':inner-corner,'allocated_bore_radius_minus_point2_gap':inner-.2-corner,'film_outer_corner_radius':math.hypot(26.5,22.75),'film_gap_at_bore_minus_point2':inner-.2-math.hypot(26.5,22.75),'trunk_centres_yz':lanes,'wire_screen_radius':rwire,'trunk_max_radius':max(math.hypot(*p)+rwire for p in lanes),'trunk_to_reservation_bottom_gap':29-rwire-22.5,'transition_radius':rad,'transition_angle_deg':math.degrees(theta),'transition_axial_run':run,'source_axial_length':source_length,'retained_CIR_core_length':core,'each_terminal_access_allowance':term,'variants':results,'baseline_CIR':[275,91,74],'baseline_330':[330,89,72],'sources_are_not_mating_planes':True,'S12_electrical_unchanged':True}
(P/'screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
