"""One complete unrouted 25x18x1 placement. No whole collar packing claim."""
from pathlib import Path
import pcbnew as K,xml.etree.ElementTree as E,json,csv,math
P=Path(__file__).resolve().parent;iu=K.FromMM;mm=K.ToMM;b=K.BOARD();r=E.parse(P/'regulated-source.net');pn={};nets={}
for n in r.findall('./nets/net'):
 name=n.attrib['name'].rsplit('/',1)[-1];o=K.NETINFO_ITEM(b,name);b.Add(o);nets[name]=o
 for node in n:pn[(node.attrib['ref'],node.attrib['pin'])]=name
rows={x['reference']:x for x in csv.DictReader((P/'component-ledger.csv').open())};lands=json.loads((P/'land-sources.json').read_text());fs={}
for c in r.findall('./components/comp'):
 if not c.findtext('footprint'):continue
 ref=c.attrib['ref'];fp=rows[ref]['footprint'];f=K.FootprintLoad(str(P/'Regulated.pretty'),fp);assert f
 f.SetReference(ref);f.SetValue(c.findtext('value'));f.SetFPID(K.LIB_ID('RS',fp));f.Value().SetVisible(False);f.Reference().SetLayer(K.F_Fab);f.Reference().SetTextSize(K.VECTOR2I(iu(.45),iu(.45)));f.Reference().SetTextThickness(iu(.07))
 for pad in f.Pads():
  if pad.GetNumber():pad.SetNet(nets[pn[(ref,pad.GetNumber())]])
 b.Add(f);fs[ref]=f
# Rigid connector+major-component placement, then one deterministic greedy pass.
fixed={'J1':(12.5,0,180),'J0':(12.5,16.4,0),'U1':(20.7,12,0),'U2':(3.3,7.6,0),'U3':(12.5,8.5,0),'L1':(3,2.8,0),'C8':(21.2,4.7,90)}
boxes=[];placed={}
def box(f):
 f.BuildCourtyardCaches();bb=f.GetCourtyard(K.F_CrtYd).BBox();return [mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())]
def move(f,x,y,angle):f.SetOrientationDegrees(angle);f.SetPosition(K.VECTOR2I(iu(x),iu(y)));return box(f)
def gap(a,c):return math.hypot(max(a[0]-c[2],c[0]-a[2],0),max(a[1]-c[3],c[1]-a[3],0))
for ref,(x,y,angle) in fixed.items():
 bb=move(fs[ref],x,y,angle);assert all(gap(bb,c)>.09 for rr,c in boxes),(ref,boxes,bb)
 boxes.append((ref,bb));placed[ref]=[x,y,angle]
rest=sorted(set(fs)-set(fixed),key=lambda ref:-(lands[rows[ref]['footprint']]['courtyard_mm'][0]*lands[rows[ref]['footprint']]['courtyard_mm'][1]))
for ref in rest:
 f=fs[ref];target=(4,9) if ref in ['C1','C2','C3','C11','R6','R7'] else (14,9) if ref in ['C4','C5','C6','C7','C9','C10','D1','R8','R9','R10','R11','TP1'] else (20,12)
 options=[]
 for angle in [0,90]:
  for ix in range(3,98):
   for iy in range(3,58):
    x=ix*.25;y=iy*.25;bb=move(f,x,y,angle)
    if bb[0]<.25 or bb[1]<.25 or bb[2]>24.75 or bb[3]>14.8:continue
    if any(gap(bb,c)<.1-1e-8 for rr,c in boxes):continue
    options.append(((x-target[0])**2+(y-target[1])**2,x,y,angle,bb))
 assert options,('No placement space',ref,'do not silently shrink parts')
 _,x,y,angle,bb=min(options);move(f,x,y,angle);boxes.append((ref,bb));placed[ref]=[x,y,angle]
for a,c in [((0,0),(25,0)),((25,0),(25,18)),((25,18),(0,18)),((0,18),(0,0))]:
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetLayer(K.Edge_Cuts);s.SetWidth(iu(.05));s.SetStart(K.VECTOR2I(iu(a[0]),iu(a[1])));s.SetEnd(K.VECTOR2I(iu(c[0]),iu(c[1])));b.Add(s)
b.GetDesignSettings().SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(iu(1))
K.SaveBoard(str(P/'regulated-source.kicad_pcb'),b)
saved=K.LoadBoard(str(P/'regulated-source.kicad_pcb'));actual={f.GetReference():f for f in saved.GetFootprints()};padchecks=0;physicalpads=0;ledger=[]
assert set(actual)==set(fs)
for ref,f in actual.items():
 assert f.GetLayer()==K.F_Cu and f.GetValue()==rows[ref]['value'];bb=box(f);info=lands[rows[ref]['footprint']]
 for pad in f.Pads():
  physicalpads+=1
  if pad.GetNumber():assert pad.GetNetname()==pn[(ref,pad.GetNumber())];padchecks+=1
 assert set(p.GetNumber() for p in f.Pads() if p.GetNumber())=={n for rr,n in pn if rr==ref}
 ledger.append({'ref':ref,'footprint':rows[ref]['footprint'],'x':placed[ref][0],'y':placed[ref][1],'degrees':placed[ref][2],'body_area_mm2':math.prod(info['body_max_mm']),'court_area_mm2':(bb[2]-bb[0])*(bb[3]-bb[1]),'height_max_mm':info['height_max_mm']})
assert len(actual)==32
smallest=min(gap(a,c) for i,(rr,a) in enumerate(boxes) for ss,c in boxes[i+1:]);assert smallest>=.1-1e-8
with (P/'placement-ledger.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=ledger[0]);w.writeheader();w.writerows(sorted(ledger,key=lambda v:v['ref']))
out={'status':'PASS actual32 fullfootprints, savedpadnet/courtyard checks; one unrouted25x18x1placement. Heighttarget FAIL.', 'physical_footprints':len(actual),'purchased_parts':30,'numbered_pad_primitives_checked':padchecks,'physical_pad_primitives_including_NPTH':physicalpads,'minimum_courtyard_gap_mm':smallest,'body_sum_mm2':sum(x['body_area_mm2'] for x in ledger),'complete_courtyard_sum_mm2':sum(x['court_area_mm2'] for x in ledger),'PCB_mm':[25,18,1],'all_components_top':True,'tracks':len(saved.GetTracks()),'component_height_max_mm':3.46,'height_target_mm':3.2,'height_target_pass':False,'connector_body_overhang_alloc_mm':2.17,'complete_front_to_back_envelope_alloc_mm':20.17,'stake_protrusion_below1mmPCB_with0p1thickness_allowance_max_mm':.2,'FPC_clamp_and_solder_courts':'External mechanical/strainrelief unqualified; no bottom component allowance.','whole_collar_fit':False,'routing_thermal_qualification':False}
(P/'placement-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
