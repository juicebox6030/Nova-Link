from pathlib import Path
import pcbnew as K,json,xml.etree.ElementTree as E,csv,math,shutil
P=Path(__file__).resolve().parent;mm=K.ToMM;iu=K.FromMM
b=K.LoadBoard(str(P.parent/'integrated25/integrated25.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
r=E.parse(P/'protected25.net');pn={};values={c.attrib['ref']:c.findtext('value') for c in r.findall('./components/comp')}
for n in r.findall('./nets/net'):
 name=n.attrib['name'].rsplit('/',1)[-1]
 for p in n:pn[(p.attrib['ref'],p.attrib['pin'])]=name
nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
def net(name):
 if name not in nets:nets[name]=K.NETINFO_ITEM(b,name);b.Add(nets[name])
 return nets[name]
# Exact targeted changes; all unrelated pad nets remain byte-equivalent in meaning.
for ref,pin in [('C23','1'),('U3','1'),('C7','1')]:next(p for p in fs[ref].Pads() if p.GetNumber()==pin).SetNet(net(pn[(ref,pin)]))
for ref in ['R20','R21']:fs[ref].SetValue(values[ref])
rows={x['reference']:x for x in csv.DictReader((P.parents[1]/'cell-protection-candidate/component-ledger.csv').open())};lands=json.loads((P.parents[1]/'cell-protection-candidate/land-sources.json').read_text())
def bbox(f):
 f.BuildCourtyardCaches();bb=f.GetCourtyard(K.B_CrtYd if f.IsFlipped() else K.F_CrtYd).BBox();return [mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())]
def overlap(a,c,g=.15):return min(a[2],c[2])+g>max(a[0],c[0]) and min(a[3],c[3])+g>max(a[1],c[1])
occupied=[('B' if f.IsFlipped() else 'F',bbox(f),f.GetReference()) for f in fs.values()]
# Conservative protected regions; no use of cap/RF/isolated allocation or mounting axes.
reserves=[[4,23,26,42.5],[26,23.5,61,37],[59,23,83.4,43],[83.4,23,94,51],[36.5,45.1,48.9,54]]
reserves += [[x-2.6,y-2.6,x+2.6,y+2.6] for x,y in [(7,26),(73,26),(7,48),(73,48)]]
added=[r for r in rows if rows[r]['kind']=='added'];order=['F101','U101','U102','U103']+[r for r in added if r not in ['F101','U101','U102','U103']]
placed=[];fail=[]
for ref in order:
 print('START',ref,flush=True)
 row=rows[ref];f=K.FootprintLoad(str(P/'CellProtection.pretty'),row['footprint']);f.SetReference(ref);f.SetValue(values[ref]);f.SetFPID(K.LIB_ID('CP',row['footprint']))
 b.Add(f)
 for p in f.Pads():p.SetNet(net(pn[(ref,p.GetNumber())]))
 # One deterministic first-fit attempt, nearest cell for fuse, nearest charger for controls.
 target=(57.9,26.9) if ref=='F101' else (53.75,39.1) if ref=='R101' else (28,45.75)
 candidates=[]
 for side in (['F'] if ref=='F101' else ['B','F']):
  for angle in [0,90]:
   if f.IsFlipped()!=(side=='B'):f.Flip(f.GetPosition(),False)
   f.SetOrientationDegrees(angle);f.SetPosition(K.VECTOR2I(0,0));local=bbox(f)
   for xi in range(22,333):
    x=xi*.25
    for yi in range(150,198):
     y=yi*.25;a=[local[0]+x,local[1]+y,local[2]+x,local[3]+y]
     if a[0]<4.4 or a[1]<23.4 or a[2]>93.6 or a[3]>50.6:continue
     if any(overlap(a,z,.15) for z in reserves):continue
     if any(side==s and overlap(a,z,.15) for s,z,_ in occupied):continue
     score=(x-target[0])**2+(y-target[1])**2+(0 if side=='B' else 5)
     candidates.append((score,side,angle,x,y,a))
 if not candidates:
  assert ref=='F101','Unexpected extra fit failure'
  fail.append(ref)
  # Retain a concrete bottom-side limiting attempt; not accepted height/DFM.
  side,angle,x,y='B',270,56.5,41.0
  if not f.IsFlipped():f.Flip(f.GetPosition(),False)
  f.SetOrientationDegrees(angle);f.SetPosition(K.VECTOR2I(iu(x),iu(y)));a=bbox(f)
  candidates=[(0,side,angle,x,y,a)]
 _,side,angle,x,y,a=min(candidates)
 if f.IsFlipped()!=(side=='B'):f.Flip(f.GetPosition(),False)
 f.SetOrientationDegrees(angle);f.SetPosition(K.VECTOR2I(iu(x),iu(y)));f.Value().SetVisible(False);f.Reference().SetLayer(K.F_Fab if side=='F' else K.B_Fab)
 occupied.append((side,a,ref));placed.append({'ref':ref,'side':side,'x':x,'y':y,'angle':angle,'bounds':a,'body':lands[row['footprint']]['body_max_mm'],'height':lands[row['footprint']]['height_max_mm']})
K.SaveBoard(str(P/'protected25.kicad_pcb'),b);shutil.copyfile(P.parent/'integrated25/integrated25.kicad_pro',P/'protected25.kicad_pro')
(P/'placement.json').write_text(json.dumps({'added':placed,'failed':fail,'reserved_regions':reserves,'tracks':len(b.GetTracks()),'footprints':len(b.GetFootprints()),'existing_moved':[]},indent=2)+'\n');print('PLACED',len(placed),'FAILED',fail);print(placed)
