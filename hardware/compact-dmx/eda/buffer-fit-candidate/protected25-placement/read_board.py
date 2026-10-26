import pcbnew as K,json
from pathlib import Path
P=Path(__file__).resolve().parent;b=K.LoadBoard(str(P.parent/'integrated25/integrated25.kicad_pcb'))
a=[]
for f in b.GetFootprints():
 f.BuildCourtyardCaches();layer=K.B_CrtYd if f.IsFlipped() else K.F_CrtYd;s=f.GetCourtyard(layer);bb=s.BBox();a.append({'ref':f.GetReference(),'value':f.GetValue(),'xy':[K.ToMM(f.GetPosition().x),K.ToMM(f.GetPosition().y)],'side':'B' if f.IsFlipped() else 'F','bounds':[K.ToMM(bb.GetLeft()),K.ToMM(bb.GetTop()),K.ToMM(bb.GetRight()),K.ToMM(bb.GetBottom())],'pads':{p.GetNumber():p.GetNetname() for p in f.Pads()}})
(P/'baseline-board.json').write_text(json.dumps(a,indent=2))
print(len(a));print([(x['ref'],x['pads']) for x in a if x['ref'] in ['U3','C23','R20','R21','C7']])
