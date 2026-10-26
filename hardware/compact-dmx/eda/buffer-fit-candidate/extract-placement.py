from pathlib import Path
import pcbnew as K,json,hashlib
P=Path(__file__).resolve().parent
src=P.parent/'power-service/qualified15-candidate/qualified15-placement.kicad_pcb'
b=K.LoadBoard(str(src));out=[]
for f in b.GetFootprints():
 if f.GetReference()=='C23':continue
 f.BuildCourtyardCaches();bb=f.GetCourtyard(K.F_CrtYd if f.GetLayer()==K.F_Cu else K.B_CrtYd).BBox()
 out.append({'ref':f.GetReference(),'side':'top' if f.GetLayer()==K.F_Cu else 'bottom','bounds':[K.ToMM(bb.GetLeft()),K.ToMM(bb.GetTop()),K.ToMM(bb.GetRight()),K.ToMM(bb.GetBottom())]})
(P/'placement-boxes.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'parts':out},indent=2)+'\n')
print(len(out),'courtyards extracted; C23 replacement excluded explicitly')
