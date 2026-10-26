"""Independent developability, flat artwork and incremental resistance screen."""
from pathlib import Path
import json,numpy as np,math
P=Path(__file__).resolve().parent;d=json.loads((P/'fanout-path.json').read_text());a=np.array(d['samples']);yz=a[:,1:3];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(yz,axis=0),axis=1))];x=a[:,0];dx=np.gradient(x,s);norm=np.sqrt(1+dx*dx)
# Generalized cylindrical sheet S(u,v)=(u,y(v),z(v)): all ruling vectors (1,0,0).
# Exact developable metric du²+dv² when v is transverse arc length; trimming shifts u only.
traces=[]
for center in [-4.5,4.5]:
 edges=[]
 for off in [center-4,center+4]:edges.append(np.column_stack([x+off/norm,s-off*dx/norm]).tolist())
 c=np.column_stack([x+center/norm,s-center*dx/norm]);length=float(np.linalg.norm(np.diff(c,axis=0),axis=1).sum());traces.append({'offset_mm':center,'true_normal_width_mm':8,'centerline_length_mm':length,'edges':edges})
edge_margins=[]
for trace in traces:
 for edge in trace['edges']:
  for xx,ss in edge:
   assert -.001<=ss<=s[-1]+.001
   edge_margins.append(10-abs(xx-float(np.interp(ss,s,x))))
assert min(edge_margins)>.9
rho20=.01724;temperature85factor=1+.00393*65;loop20=sum(t['centerline_length_mm']/1000 for t in traces)*rho20/(8*.07);loop85=loop20*temperature85factor
out={'status':'PASS developable generalized cylinder; engineering pattern not supplier approval','transverse_length_mm':float(s[-1]),'static_centerline_length_mm':float(np.linalg.norm(np.diff(a[:,:3],axis=0),axis=1).sum()),'active_length_mm_unchanged':1046.167655992167,'ruling_direction':[1,0,0],'gaussian_curvature':0,'terminal_bend_radius_mm':2.5,'terminal_inside_radius_mm':2.42,'bend_thickness_ratio':2.5/.16,'RA_copper_um_proposed':70,'polyimide_total_stack_mm_proposed':.16,'minimum_intertrace_gap_mm':1,'sampled_copper_to_blank_edge_min_mm':min(edge_margins),'trace_width_mm':8,'traces':traces,'additional_loop_R20_ohm':loop20,'additional_loop_R85_ohm':loop85,'additional_drop_at_2p987A_V':2.987*loop85,'drop_location':'upstream converter input; not a direct USB VBUS subtraction','allocated_63um_plus3percent_rho_hot_loop_ohm':loop85*70/63*1.03,'allocated_corner_not_supplier_tolerance':True,'additional_heat_at_2p987A_W':2.987**2*loop85,'source_budget_requalification_required':True,'not_in_active_motion_proof':True,'qualification':'Minco design-guide material class only; no approved laminate, stiffness, formed profile, solder process, lifetime or contact resistance.'}
(P/'fanout-proof.json').write_text(json.dumps(out,indent=2)+'\n')
# Millimetre flat blank/copper artwork; not fabrication Gerber.
pts=lambda ar:' '.join(f'{v[0]-40:.4f},{v[1]+10:.4f}' for v in ar)
blank=np.r_[np.column_stack([x-10,s]),np.column_stack([x[::-1]+10,s[::-1]])]
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="80mm" height="{s[-1]+25}mm" viewBox="0 0 80 {s[-1]+25}"><rect width="100%" height="100%" fill="white"/><polygon points="{pts(blank)}" fill="#ead6ad" stroke="black" stroke-width=".15"/>'
for t in traces:svg+=f'<polygon points="{pts(np.r_[t["edges"][0],t["edges"][1][::-1]])}" fill="#b77332"/>'
svg+='<text x="2" y="5" font-size="2">STATIC FANOUT / mm / supplier-unqualified developed artwork</text></svg>'
(P/'fanout-flat.svg').write_text(svg)
print('STATIC LENGTH',out['static_centerline_length_mm'],'ADDED HOT LOOP',loop85,'DROP@2.987A',out['additional_drop_at_2p987A_V'])
