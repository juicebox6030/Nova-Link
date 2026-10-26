from pathlib import Path
import pcbnew as K,json,hashlib,math
P=Path(__file__).resolve().parent;i=json.loads((P/'board-input.json').read_text());src=Path(i['path']);assert hashlib.sha256(src.read_bytes()).hexdigest()==i['sha256']
a=K.LoadBoard(str(src));b=K.LoadBoard(str(P/'integrated25.kicad_pcb'));fa={f.GetReference():f for f in a.GetFootprints()};fb={f.GetReference():f for f in b.GetFootprints()};assert fa.keys()==fb.keys()
def pads(f):return sorted((p.GetNumber(),p.GetPosition().x,p.GetPosition().y,p.GetSize().x,p.GetSize().y,p.GetDrillSize().x,p.GetDrillSize().y,p.GetNetname(),str(p.GetLayerSet().FmtHex()),str(p.GetShape())) for p in f.Pads())
count=0
for ref in fa:
 if ref=='C23':continue
 assert pads(fa[ref])==pads(fb[ref]),ref
 assert fa[ref].GetValue()==fb[ref].GetValue() and str(fa[ref].GetFPID().GetLibNickname())==str(fb[ref].GetFPID().GetLibNickname()) and str(fa[ref].GetFPID().GetLibItemName())==str(fb[ref].GetFPID().GetLibItemName()) and fa[ref].GetOrientationDegrees()==fb[ref].GetOrientationDegrees(),ref
 count+=len(pads(fb[ref]))
f=fb['C23'];assert f.GetValue()=='HV1625-2R7256-R 25F 2.7V'
for p in f.Pads():
 no=p.GetNumber();assert no in ['1','2'];assert p.GetNetname()=={'1':'CAP_POS','2':'GND_USB'}[no]
 assert abs(K.ToMM(p.GetPosition().x)-57.9)<1e-6
 assert abs(K.ToMM(p.GetPosition().y)-{'1':26.9,'2':34.4}[no])<1e-6
 assert [round(K.ToMM(x),6) for x in [p.GetSize().x,p.GetSize().y,p.GetDrillSize().x,p.GetDrillSize().y]]==[1.7,2.7,1.1,2.1]
 # Entire copper + .15 courtyard ends before RFx59.
 assert K.ToMM(p.GetPosition().x)+.85+.15<59
# Exact baseline outer edge segments preserved; exactly8new edges,4true arcs.
def edges(board):return [(str(x.GetShape()),x.GetStart().x,x.GetStart().y,x.GetEnd().x,x.GetEnd().y) for x in board.GetDrawings() if x.GetLayer()==K.Edge_Cuts]
e1=edges(a);e2=edges(b)
for x in e1:e2.remove(x)
assert len(e2)==8;assert sum(x.GetShape()==K.SHAPE_T_ARC for x in b.GetDrawings() if x.GetLayer()==K.Edge_Cuts)==4
# Conservative rectangular envelope of aperture: positive pad-AABB gaps prove rounded-hole copper separation.
gaps=[]
for f in b.GetFootprints():
 for p in f.Pads():
  bb=p.GetBoundingBox();x,y,x2,y2=[K.ToMM(v) for v in [bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom()]]
  dx=max(26.5-x2,x-55.9,0);dy=max(25.5-y2,y-35.8,0)
  assert dx>0 or dy>0,(f.GetReference(),p.GetNumber())
  gaps.append((math.hypot(dx,dy),f.GetReference(),p.GetNumber()))
r=json.loads((P/'drc.json').read_text());assert not r['violations'];assert len(b.GetTracks())==0
report={'unchanged_noncell_footprints':len(fa)-1,'unchanged_pad_checks':count,'C23_pads':2,'new_edges':8,'arc_radius_mm':.5,'minimum_conservative_pad_to_aperture_gap':min(gaps),'DRC_violations':len(r['violations']),'unconnected':len(r['unconnected_items']),'ignored_checks':r['ignored_checks'],'tracks':0,'source_sha256':i['sha256'],'board_sha256':hashlib.sha256((P/'integrated25.kicad_pcb').read_bytes()).hexdigest(),'ERC':'Not applicable to PCB-only local derivative; no new schematic/full-design ERC claim.'}
(P/'board-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
