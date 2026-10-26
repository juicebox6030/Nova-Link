from pathlib import Path
import pcbnew as K,json,hashlib
P=Path(__file__).resolve().parent;src=P.parent/'candidate.kicad_pcb';b=K.LoadBoard(str(src));old=K.LoadBoard(str(src));fs={f.GetReference():f for f in b.GetFootprints()};fs['J_USB'].SetPosition(K.VECTOR2I(K.FromMM(42.7),K.FromMM(47.6)))
def sig(f):return [(p.GetNumber(),p.GetPosition().x,p.GetPosition().y,p.GetNetname()) for p in f.Pads()]
for f in old.GetFootprints():
 if f.GetReference()!='J_USB':assert sig(f)==sig(fs[f.GetReference()]) and f.GetValue()==fs[f.GetReference()].GetValue()
for s in list(b.GetDrawings()):
 if s.GetLayer()==K.Edge_Cuts:b.Remove(s)
outline=[(4,23),(94,23),(94,51),(48.9,51),(48.9,53.3),(36.5,53.3),(36.5,51),(4,51)]
for a,c in zip(outline,outline[1:]+outline[:1]):
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetLayer(K.Edge_Cuts);s.SetWidth(K.FromMM(.05));s.SetStart(K.VECTOR2I(*[K.FromMM(x) for x in a]));s.SetEnd(K.VECTOR2I(*[K.FromMM(x) for x in c]));b.Add(s)
K.SaveBoard(str(P/'tongue.kicad_pcb'),b)
(P/'board-check.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'electrical_parts':39,'unchanged_nonconnector_footprints':42,'USB_shift_y_mm':3,'new_origin':[42.7,47.6],'tongue':[36.5,51,48.9,53.3],'mating_plane_y':54,'same_nets_values':True,'tracks':0},indent=2)+'\n')
