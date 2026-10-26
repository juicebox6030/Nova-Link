"""One complete land/area coupon, NOT placement on the sidecar or routing."""
from pathlib import Path
import pcbnew as K,json,csv,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent;mm=K.ToMM;iu=K.FromMM
r=E.parse(P/'cell-protection.net');b=K.BOARD();nets={};pn={}
for n in r.findall('./nets/net'):
 name=n.attrib['name'].rsplit('/',1)[-1];o=K.NETINFO_ITEM(b,name);b.Add(o);nets[name]=o
 for p in n:pn[(p.attrib['ref'],p.attrib['pin'])]=name
rows={x['reference']:x for x in csv.DictReader((P/'component-ledger.csv').open())}
fs={}
for c in r.findall('./components/comp'):
 ref=c.attrib['ref'];fn=c.findtext('footprint')
 if not fn:continue
 fp=fn.split(':')[1];f=K.FootprintLoad(str(P/'CellProtection.pretty'),fp);assert f
 f.SetReference(ref);f.SetValue(c.findtext('value'));f.SetFPID(K.LIB_ID('CP',fp))
 for pad in f.Pads():pad.SetNet(nets[pn[(ref,pad.GetNumber())]])
 f.Value().SetVisible(False);f.Reference().SetLayer(K.F_Fab);f.Reference().SetTextSize(K.VECTOR2I(iu(.4),iu(.4)));f.Reference().SetTextThickness(iu(.06))
 b.Add(f);fs[ref]=f
fixed={'F101':(5,4),'U101':(12,4),'U102':(18,4),'U103':(23,4),'U104':(28,4)}
small=sorted(set(fs)-set(fixed))
for i,ref in enumerate(small):fixed[ref]=(2.5+(i%8)*3.7,9+(i//8)*4)
for ref,f in fs.items():f.SetPosition(K.VECTOR2I(*[iu(z) for z in fixed[ref]]))
for a,c in [((0,0),(32,0)),((32,0),(32,16)),((32,16),(0,16)),((0,16),(0,0))]:
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetLayer(K.Edge_Cuts);s.SetWidth(iu(.05));s.SetStart(K.VECTOR2I(*[iu(z) for z in a]));s.SetEnd(K.VECTOR2I(*[iu(z) for z in c]));b.Add(s)
b.GetDesignSettings().SetCopperLayerCount(2)
K.SaveBoard(str(P/'land-coupon.kicad_pcb'),b)
# Reopen the actual saved pads independently, including round6ball BGA.
saved=K.LoadBoard(str(P/'land-coupon.kicad_pcb'));ff={f.GetReference():f for f in saved.GetFootprints()};lands=json.loads((P/'land-sources.json').read_text());ledger=[];boxes=[];pads=0
for ref,f in ff.items():
 assert f.GetValue()==rows[ref]['value'];f.BuildCourtyardCaches();bb=f.GetCourtyard(K.F_CrtYd).BBox();z=[mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())]
 assert 0<z[0]<z[2]<32 and 0<z[1]<z[3]<16
 for other,a in boxes:assert min(a[2],z[2])<=max(a[0],z[0]) or min(a[3],z[3])<=max(a[1],z[1]),(ref,other)
 boxes.append((ref,z));nums=[]
 for pad in f.Pads():
  nums.append(pad.GetNumber());assert pad.GetNetname()==pn[(ref,pad.GetNumber())];pads+=1
 assert set(nums)=={no for rr,no in pn if rr==ref}
 fp=rows[ref]['footprint'];src=lands[fp]
 if ref=='U103':
  actual={p.GetNumber():[mm(p.GetPosition().x)-23,mm(p.GetPosition().y)-4,mm(p.GetSize().x),mm(p.GetSize().y)] for p in f.Pads()}
  expected={row+str(col):[x,y,.225,.225] for row,y in [('A',-.5),('B',0),('C',.5)] for col,x in [(1,-.25),(2,.25)]}
  assert all(all(abs(a-c)<1e-7 for a,c in zip(actual[k],expected[k])) for k in expected),actual
 if ref=='F101':
  assert sorted((p.GetNumber(),mm(p.GetSize().x),mm(p.GetSize().y)) for p in f.Pads())==[('1',1.96,3.15),('2',1.96,3.15)]
 ledger.append({'reference':ref,'scope':rows[ref]['kind'],'footprint':fp,'body_area_mm2':src['body_max_mm'][0]*src['body_max_mm'][1],'courtyard_mm2':(z[2]-z[0])*(z[3]-z[1]),'height_max_mm':src['height_max_mm'],'x':fixed[ref][0],'y':fixed[ref][1]})
assert len(ff)==21 and pads==61
added=[x for x in ledger if x['scope']=='added'];assert len(added)==14
with (P/'area-ledger.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(sorted(ledger,key=lambda x:x['reference']))
out={'status':'PASS21 actual saved footprints/padnets and nonoverlapping courtyards on32x16mm coupon; no sidecar fit/routing claim','physical_footprints':len(ff),'numbered_pads':pads,'added_protection_parts':len(added),'added_body_sum_mm2':sum(x['body_area_mm2'] for x in added),'added_courtyard_sum_mm2':sum(x['courtyard_mm2'] for x in added),'highest_added_part_mm':max(x['height_max_mm'] for x in added),'all_context_courtyard_sum_mm2':sum(x['courtyard_mm2'] for x in ledger),'coupon_outline_mm':[32,16],'all_on_F_Cu':True,'tracks':len(saved.GetTracks()),'external_ports':'No invented physical connector/cell lands. Actual cell/short-tab/fuse placement and integration owned by parent/Astra. Coupon remains unrouted.','main_board_fit':None,'manufacturing_release':False}
(P/'area-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
