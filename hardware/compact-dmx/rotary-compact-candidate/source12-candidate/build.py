"""One unrouted source-dimensioned allocation pass, not a routed collar fit."""
from pathlib import Path
import pcbnew as K,xml.etree.ElementTree as E,json,csv,math
P=Path(__file__).resolve().parent;iu=K.FromMM;mm=K.ToMM
tree=E.parse(P/'source12.net');rows={r['reference']:r for r in csv.DictReader((P/'component-ledger.csv').open()) if r['footprint']};lands=json.loads((P/'land-sources.json').read_text())
pin_nets={(x.attrib['ref'],x.attrib['pin']):n.attrib['name'].rsplit('/',1)[-1] for n in tree.findall('./nets/net') for x in n}
sizes={'rotating':(32.,26.),'stationary':(24.,16.)}
fixed={
 'rotating':{'J1':(32,13,90),'J3':(11,23.5,0),'U2':(6,5.5,0),'L1':(11.5,4.2,0),'C2':(2.25,4.2,0),'C3':(6,2,0),'C4':(15.9,3,0),'C5':(15.9,5.3,0),'U4':(17.4,9.5,180),'U3':(22.5,13,0),'U5':(6,13,0),'C6':(15.9,16.6,0),'C7':(28.8,21,0),'D1':(25.7,20.8,90),'C8':(22.5,18,0),'C9':(2.5,13,0),'C10':(7.5,9,0),'C12':(20,3,0),'C13':(20,4.3,0),'C15':(3,6.8,0),'C16':(20.5,6,0),'C17':(20.5,7.3,0),'TP1':(30,24,0),'TP2':(26.5,24,0)},
 'stationary':{'J0':(5,3.5,0),'J2':(12,13.8,0),'U1':(14,4,0),'C1':(5,8.3,0),'C11':(17,7,0),'C14':(9.5,8,0)}}
preferred={'R7':(9,8),'R8':(10,9.5),'R9':(3,9),'R10':(3,10.5),
 'R11':(9,12),'R12':(9,13.4),'R13':(9,15),'R14':(9,16.4),'R15':(12,10),'R16':(12,11.4),'R17':(17,13),'R18':(19,13),'R19':(13,9),
 'R20':(20,10),'R21':(20,11.4),'R22':(24,17),'R23':(24,18.4),'R24':(23,7),'R25':(28,5),'R26':(25,3),'R27':(23,21),
 'R1':(11,6),'R2':(11,7.5),'R3':(14,7.5),'R4':(14,9),'R5':(17,4),'R6':(19,7)}
def gap(a,c):return math.hypot(max(a[0]-c[2],c[0]-a[2],0),max(a[1]-c[3],c[1]-a[3],0))
reports=[];ledger=[]
for zone,(W,H) in sizes.items():
 b=K.BOARD();nets={}
 for net in sorted(set(pin_nets.values())):z=K.NETINFO_ITEM(b,net);b.Add(z);nets[net]=z
 footprints={};boxes={}
 def make(ref,position):
  row=rows[ref];f=K.FootprintLoad(str(P/'Source12.pretty'),row['footprint']);f.SetReference(ref);f.SetValue(row['value']);f.SetFPID(K.LIB_ID('S12',row['footprint']));f.Value().SetVisible(False);f.Reference().SetLayer(K.F_Fab);f.Reference().SetTextSize(K.VECTOR2I(iu(.45),iu(.45)));f.Reference().SetTextThickness(iu(.07))
  for pad in f.Pads():
   if pad.GetNumber():pad.SetNet(nets[pin_nets[(ref,pad.GetNumber())]])
  x,y,a=position;f.SetOrientationDegrees(a);f.SetPosition(K.VECTOR2I(iu(x),iu(y)));f.BuildCourtyardCaches();bb=f.GetCourtyard(K.F_CrtYd).BBox();box=[mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())]
  return f,box
 refs=[r for r,v in rows.items() if v['zone']==zone]
 for ref in refs:
  if ref not in fixed[zone]:continue
  f,box=make(ref,fixed[zone][ref]);assert all(gap(box,c)>=.09 for c in boxes.values()),(zone,ref,'fixed overlap',box,boxes)
  b.Add(f);footprints[ref]=f;boxes[ref]=box
 for ref in refs:
  if ref in footprints:continue
  assert ref.startswith('R'),ref
  px,py=preferred[ref]
  candidates=sorted(((x/4,y/4) for x in range(4,int(W*4)-3) for y in range(4,int(H*4)-3)),key=lambda v:(math.hypot(v[0]-px,v[1]-py),v))
  for x,y in candidates:
   f,box=make(ref,(x,y,0))
   if box[0]>=.4 and box[1]>=.4 and box[2]<=W-.4 and box[3]<=H-.4 and all(gap(box,c)>=.20 for c in boxes.values()):break
  else:raise AssertionError((zone,ref,'no allocation slot'))
  b.Add(f);footprints[ref]=f;boxes[ref]=box
 for ref,box in boxes.items():
  if ref=='J1':continue # supplier-specified mouth overhang, explicit below
  assert box[0]>=0 and box[1]>=0 and box[2]<=W and box[3]<=H,(ref,box)
 pairs=sorted((gap(a,c),r,rr) for i,(r,a) in enumerate(boxes.items()) for rr,c in list(boxes.items())[i+1:]);assert pairs[0][0]>=.09
 for a,c in [((0,0),(W,0)),((W,0),(W,H)),((W,H),(0,H)),((0,H),(0,0))]:
  s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetLayer(K.Edge_Cuts);s.SetWidth(iu(.05));s.SetStart(K.VECTOR2I(iu(a[0]),iu(a[1])));s.SetEnd(K.VECTOR2I(iu(c[0]),iu(c[1])));b.Add(s)
 b.GetDesignSettings().SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(iu(1))
 path=P/f'source12-{zone}.kicad_pcb';K.SaveBoard(str(path),b)
 # Independently reopen actual saved board and compare every numbered pad to exported netlist.
 saved=K.LoadBoard(str(path));pad_count=0
 assert len(saved.GetTracks())==0
 for f in saved.GetFootprints():
  ref=f.GetReference();expected={pin:net for (rr,pin),net in pin_nets.items() if rr==ref};actual={}
  for pad in f.Pads():
   if pad.GetNumber():
    assert pad.GetNetname()==expected[pad.GetNumber()],(ref,pad.GetNumber(),pad.GetNetname(),expected[pad.GetNumber()])
    actual[pad.GetNumber()]=pad.GetNetname();pad_count+=1
  assert actual==expected,(ref,actual,expected)
  assert not f.IsFlipped()
  info=lands[rows[ref]['footprint']];x,y=f.GetPosition();box=boxes[ref];ledger.append({'reference':ref,'zone':zone,'footprint':rows[ref]['footprint'],'x_mm':mm(x),'y_mm':mm(y),'angle_deg':f.GetOrientationDegrees(),'height_allocation_mm':info['height_allocation_mm'],'body_area_mm2':math.prod(info['body_allocation_mm']),'actual_courtyard_BBox_area_mm2':(box[2]-box[0])*(box[3]-box[1])})
 reports.append({'zone':zone,'PCB_LWH_mm':[W,H,1],'board_area_mm2':W*H,'footprints':len(footprints),'saved_numbered_pad_checks':pad_count,'min_courtyard_gap_mm':pairs[0][0],'closest_pair':pairs[0][1:],'max_component_height_allocation_mm':max(lands[rows[r]['footprint']]['height_allocation_mm'] for r in refs),'body_area_sum_mm2':sum(math.prod(lands[rows[r]['footprint']]['body_allocation_mm']) for r in refs),'actual_courtyard_BBox_area_sum_mm2':sum((box[2]-box[0])*(box[3]-box[1]) for box in boxes.values()),'tracks':0,'vias':0,'routing_or_thermal_or_collar_acceptance':False,'positions':{r:[mm(f.GetPosition().x),mm(f.GetPosition().y),f.GetOrientationDegrees()] for r,f in footprints.items()}})
with (P/'placement-ledger.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=ledger[0]);w.writeheader();w.writerows(sorted(ledger,key=lambda x:(x['zone'],x['reference'])))
(P/'placement-check.json').write_text(json.dumps({'revision':'S12-R1','one_pass_allocation':reports,'port_datum':{'rotating_board_mm':[32,26,1],'connector_origin_mm':[32,13],'angle_deg':90,'mate_direction':'+X','conservative_body_X_max_mm':34.17,'exact_supplier_matingface_alignment':'UNMET; this body-envelope edge is not an asserted mating plane','max_component_height_above_top_mm':3.46,'PCB_thickness_and_GCT_stake_assembly_gate':'1mm nominal; retain original supplier stake/NPTH geometry, fabrication and solder process not accepted'},'external_FPC_clamp_allocation':{'each_end_width_depth_height_mm':[20.5,5,2],'status':'Engineering reserve only, outside back edge, not manufactured clamp or bend/strain-relief proof'},'scope':'Complete component lands/net allocation, unrouted two-zone prototype. No integrated sourcepod/collar fit, safety or thermal acceptance.'},indent=2)+'\n')
print(json.dumps([{k:v for k,v in a.items() if k!='positions'} for a in reports],indent=2))
