"""Read-only actual KiCad copper check for proposed 0.20mm board-edge captures."""
from pathlib import Path
import pcbnew as K,json,hashlib
P=Path(__file__).resolve().parent;F=P.parent/'source-axial-routing/source-axial.kicad_pcb';before=hashlib.sha256(F.read_bytes()).hexdigest();assert before=='53b83aa71d1bcd986906509348bc061eb9e334296ddc980340c954eb8305cbcc'
b=K.LoadBoard(str(F));mm=K.ToMM;rows=[]
def check(kind,key,y0,y1):
 gap=min(y0-.2,19.8-y1);rows.append({'kind':kind,'key':key,'Y_min_mm':y0,'Y_max_mm':y1,'capture_gap_mm':gap});assert gap>=-1e-6,(kind,key,gap)
for f in b.GetFootprints():
 for p in f.Pads():
  if p.GetNumber():
   bb=p.GetBoundingBox();check('pad',f.GetReference()+'.'+p.GetNumber(),mm(bb.GetTop()),mm(bb.GetBottom()))
for i,t in enumerate(b.GetTracks()):
 r=mm(max(t.GetWidth(l) for l in [K.F_Cu,K.In1_Cu,K.In2_Cu,K.B_Cu]) if isinstance(t,K.PCB_VIA) else t.GetWidth())/2;ys=[mm(t.GetStart().y),mm(t.GetEnd().y)];check('track/via',str(i),min(ys)-r,max(ys)+r)
for zi,z in enumerate(b.Zones()):
 for layer in [K.F_Cu,K.In1_Cu,K.In2_Cu,K.B_Cu]:
  if not z.IsOnLayer(layer):continue
  ps=z.GetFilledPolysList(layer)
  for i in range(ps.OutlineCount()):
   o=ps.Outline(i);ys=[mm(o.CPoint(j).y) for j in range(o.PointCount())];check('filled-zone',f'{zi}:{layer}:{i}',min(ys),max(ys))
assert hashlib.sha256(F.read_bytes()).hexdigest()==before
holes=json.loads((P.parent/'source-axial-routing/physical-geometry.json').read_text())['holes']
for h in holes:assert h['xy'][1]-h['size_mm'][1]/2>.2 and h['xy'][1]+h['size_mm'][1]/2<19.8
out={'status':'PASS exact saved copper conservatively clear of edge captures','board_sha256':before,'footprints':len(list(b.GetFootprints())),'numbered_pad_primitives':sum(1 for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()),'capture_local_Y_mm':[[0,.2],[19.8,20]],'minimum_copper_gap_mm':min(x['capture_gap_mm'] for x in rows),'rows':rows,'actual_holes_clear':len(holes),'board_modified':False,'limit':'Pad bounding boxes and track capsules conservatively screened; filled zone outlines screened. Copper-safe edge support is not laminate strength/mask wear qualification.'}
out['termination_pads']=[{'pin':q.GetNumber(),'net':q.GetNetname(),'local_xy_mm':[mm(q.GetPosition().x),mm(q.GetPosition().y)],'size_mm':[mm(q.GetSize().x),mm(q.GetSize().y)],'corner_radius_mm':mm(q.GetRoundRectCornerRadius())} for f in b.GetFootprints() if f.GetReference()=='J0' for q in f.Pads()]
(P/'copper-check.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(rows),'objects; minimum gap',out['minimum_copper_gap_mm'])
