from pathlib import Path
import pcbnew as K,json,hashlib,xml.etree.ElementTree as E,csv
P=Path(__file__).resolve().parent;S=P.parent/'source12-candidate';mm=K.ToMM
rows={r['reference']:r for r in csv.DictReader((S/'component-ledger.csv').open())};lands=json.loads((S/'land-sources.json').read_text());nettree=E.parse(S/'source12.net');nets={(x.attrib['ref'],x.attrib['pin']):n.attrib['name'].rsplit('/',1)[-1] for n in nettree.findall('./nets/net') for x in n};out={};count=0
for zone in ['rotating','stationary']:
 p=S/f'source12-{zone}.kicad_pcb';b=K.LoadBoard(str(p));fs=[]
 for f in b.GetFootprints():
  ref=f.GetReference();pads=[]
  for pad in f.Pads():
   no=pad.GetNumber()
   if no:assert pad.GetNetname()==nets[ref,no];count+=1
   pads.append({'number':no,'x':mm(pad.GetPosition().x),'y':mm(pad.GetPosition().y),'size':[mm(pad.GetSize().x),mm(pad.GetSize().y)],'drill':[mm(pad.GetDrillSize().x),mm(pad.GetDrillSize().y)],'angle':pad.GetOrientationDegrees(),'shape':int(pad.GetShape()),'round_radius':mm(pad.GetRoundRectCornerRadius()) if pad.GetShape()==K.PAD_SHAPE_ROUNDRECT else 0,'net':pad.GetNetname(),'layers':pad.GetLayerSet().FmtHex()})
  fs.append({'ref':ref,'value':f.GetValue(),'footprint':f.GetFPIDAsString(),'x':mm(f.GetPosition().x),'y':mm(f.GetPosition().y),'angle':f.GetOrientationDegrees(),'pads':pads,'body':lands[rows[ref]['footprint']]})
 assert len(b.GetTracks())==0
 out[zone]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'components':fs,'size':[32,26,1] if zone=='rotating' else[24,16,1]}
(P/'actual-boards.json').write_text(json.dumps(out,indent=2)+'\n');print('actual footprints',sum(len(x['components']) for x in out.values()),'numbered pads/net assertions',count)
