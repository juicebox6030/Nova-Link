"""Axial +X placement; unchanged supplier lands, two source-backed series resistor additions."""
from pathlib import Path
import pcbnew as K,xml.etree.ElementTree as E,json,csv,math
P=Path(__file__).resolve().parent;iu=K.FromMM;mm=K.ToMM
W,H=27.,20.
pos={'J1':(W,10,90),'J0':(10.5,18.4,0),'U1':(3.5,12.1,0),'U2':(8.5,6.9,90),'U3':(18.5,12.5,0),'L1':(8.5,2.55,0),'C8':(10.95,14.15,180),
'C1':(1.8,3.3,90),'C2':(4.3,3.3,90),'C3':(4.8,5.9,180),'C4':(13,2.1,0),'C5':(15.7,4.3,90),'C6':(18,4.3,90),'C7':(12.2,6.8,0),'C9':(23.3,3.5,0),'C10':(15.8,12,90),'C11':(7.15,9.45,180),'C12':(6.1,14.6,270),'C13':(3.5,8.95,90),
'R1':(1.2,10.3,90),'R2':(1.5,8,0),'R3':(1.2,12.7,90),'R4':(1.5,15.2,0),'R5':(6.15,10.75,0),'R6':(10.1,9.9,90),'R7':(11.7,10.2,90),'R8':(15.8,14.1,90),'R9':(16.4,15.9,0),'R10':(19,16,180),'R11':(17.7,9.2,0),'R12':(5.3,7.85,90),'R13':(4.75,14.8,270),'D1':(20,8.95,90),'TP1':(26,2,0)}
r=E.parse(P/'regulated-source.net');b=K.BOARD();nets={};pn={};rows={x['reference']:x for x in csv.DictReader((P/'component-ledger.csv').open())};lands=json.loads((P/'land-sources.json').read_text());fs={}
for n in r.findall('./nets/net'):
 name=n.attrib['name'].rsplit('/',1)[-1];z=K.NETINFO_ITEM(b,name);b.Add(z);nets[name]=z
 for node in n:pn[(node.attrib['ref'],node.attrib['pin'])]=name
for ref,row in rows.items():
 if not row['footprint']:continue
 f=K.FootprintLoad(str(P/'Regulated.pretty'),row['footprint']);f.SetReference(ref);f.SetValue(row['value']);f.SetFPID(K.LIB_ID('RS',row['footprint']));f.Value().SetVisible(False);f.Reference().SetLayer(K.F_Fab);f.Reference().SetTextSize(K.VECTOR2I(iu(.45),iu(.45)));f.Reference().SetTextThickness(iu(.07))
 for pad in f.Pads():
  if pad.GetNumber():pad.SetNet(nets[pn[(ref,pad.GetNumber())]])
 x,y,a=pos[ref];f.SetOrientationDegrees(a);f.SetPosition(K.VECTOR2I(iu(x),iu(y)));b.Add(f);fs[ref]=f
boxes={};ledger=[]
for ref,f in fs.items():
 f.BuildCourtyardCaches();bb=f.GetCourtyard(K.F_CrtYd).BBox();boxes[ref]=[mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())]
 info=lands[rows[ref]['footprint']];x,y,a=pos[ref];ledger.append({'ref':ref,'footprint':rows[ref]['footprint'],'x':x,'y':y,'degrees':a,'height_max_mm':info['height_max_mm']})
def gap(a,c):return math.hypot(max(a[0]-c[2],c[0]-a[2],0),max(a[1]-c[3],c[1]-a[3],0))
gaps=sorted((gap(a,c),ref,rr) for i,(ref,a) in enumerate(boxes.items()) for rr,c in list(boxes.items())[i+1:]);print('Minimumcourt gaps',gaps[:8]);assert gaps[0][0]>=.09,gaps[:8]
for a,c in [((0,0),(W,0)),((W,0),(W,H)),((W,H),(0,H)),((0,H),(0,0))]:
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetLayer(K.Edge_Cuts);s.SetWidth(iu(.05));s.SetStart(K.VECTOR2I(iu(a[0]),iu(a[1])));s.SetEnd(K.VECTOR2I(iu(c[0]),iu(c[1])));b.Add(s)
b.GetDesignSettings().SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(iu(1))
K.SaveBoard(str(P/'source-axial.kicad_pcb'),b)
with (P/'placement-ledger.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=ledger[0]);w.writeheader();w.writerows(sorted(ledger,key=lambda x:x['ref']))
(P/'placement-check.json').write_text(json.dumps({'PCB_mm':[W,H,1],'top_only':True,'physical_footprints':len(fs),'minimum_courtyard_gap_mm':gaps[0][0],'connector_origin_mm':[W,10],'connector_angle_deg':90,'mate_direction':'+X','supplier_lands_unchanged':True,'body_height_max_mm':3.46,'25x18_target_achieved':False,'routing_and_fit_acceptance_pending':True},indent=2)+'\n')
print('Saved axial placement',W,H,len(fs))
