from pathlib import Path
import pcbnew,json
P=Path(__file__).resolve().parent;f=P/'sources/tida-cad/TIDA-01560_PCB.PcbDoc'
b=pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER,str(f));box=b.GetBoardEdgesBoundingBox()
mm=pcbnew.ToMM
out={'method':'KiCad10.0.7 Altium importer in memory, no board saved or circuit modified','source':str(f.relative_to(P)),'outline_bbox_mm':{'x':mm(box.GetX()),'y':mm(box.GetY()),'width':mm(box.GetWidth()),'height':mm(box.GetHeight())},'thickness_mm':mm(b.GetDesignSettings().GetBoardThickness()),'footprint_count':len(list(b.GetFootprints())),'outlines':[],'models':[]}
for d in b.GetDrawings():
 if d.GetLayer()==pcbnew.Edge_Cuts:
  out['outlines'].append({'type':str(d.GetShape()),'start':[mm(d.GetStart().x),mm(d.GetStart().y)],'end':[mm(d.GetEnd().x),mm(d.GetEnd().y)],'width':mm(d.GetWidth())})
for fp in b.GetFootprints():
 models=[]
 for m in fp.Models():models.append({'filename':m.m_Filename,'offset':[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],'scale':[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z]})
 if models:out['models'].append({'ref':fp.GetReference(),'models':models})
(P/'cad-extraction.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['outlines','models']},indent=2));print('OUTLINE',len(out['outlines']),'MODELS',len(out['models']))
