"""One deterministic complete-footprint placement pass, no routing/fit release.
Uses frozen GCT tongue branch and unchanged original37 footprints. No CAD writes.
Run with existing KiCad flatpak Python (pcbnew).
"""
from pathlib import Path
import pcbnew as K,xml.etree.ElementTree as E,json,csv,math,hashlib
P=Path(__file__).resolve().parent;EDA=P.parents[1]
src=EDA/'service-footprints/gct-power-candidate/mechanical/tongue.kicad_pcb'
old=K.LoadBoard(str(src));mm=K.ToMM;iu=K.FromMM
def xy(v):return [mm(v.x),mm(v.y)]
def box(f):
    f.BuildCourtyardCaches();v=f.GetCourtyard(K.F_CrtYd if f.GetLayer()==K.F_Cu else K.B_CrtYd).BBox()
    return [mm(v.GetLeft()),mm(v.GetTop()),mm(v.GetRight()),mm(v.GetBottom())]
def overlap(a,c,gap=0):return a[0]<c[2]+gap-1e-7 and a[2]>c[0]-gap+1e-7 and a[1]<c[3]+gap-1e-7 and a[3]>c[1]-gap+1e-7
def sig(f):return [(p.GetNumber(),*xy(p.GetPosition()),p.GetNetname()) for p in f.Pads()]
original={f.GetReference():{'value':f.GetValue(),'pads':sig(f),'xy':xy(f.GetPosition()),'rotation':f.GetOrientationDegrees()} for f in old.GetFootprints() if f.GetReference() not in ['J_USB','U2']}
# Remove the two service footprints in the editable copy before loading: this
# avoids KiCad10 SWIG Remove ownership/type corruption, not a circuit change.
text=src.read_text();blocks=[];start=0
while True:
    start=text.find('(footprint ',start)
    if start<0:break
    depth=0;quoted=False;escape=False
    for end in range(start,len(text)):
        c=text[end]
        if quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:break
    block=text[start:end+1]
    import re
    ref=re.search(r'\(property "Reference" "([^"]+)"',block)[1]
    if ref in ['J_USB','U2']:replacement=''
    elif ref.startswith('H'):replacement=block
    else:replacement=block.replace('(property "Reference" "'+ref+'"','(property "Reference" "BASE_'+ref+'"',1)
    blocks.append((start,end+1,replacement));start=end+1
for a,z,v in reversed(blocks):text=text[:a]+v+text[z:]
(P/'placement-context.kicad_pcb').write_text(text)
b=K.LoadBoard(str(P/'placement-context.kicad_pcb'))
# Net names already match current MCU/DMX contract. No hidden physical boundary pads.
netobjs={pad.GetNetname():pad.GetNet() for f in b.GetFootprints() for pad in f.Pads() if pad.GetNetname()}
root=E.parse(P/'qualified15.net');components={c.attrib['ref']:c for c in root.findall('./components/comp')}
pn={}
for n in root.findall('./nets/net'):
    name=n.attrib['name'].rsplit('/',1)[-1]
    if name not in netobjs:
        o=K.NETINFO_ITEM(b,name);b.Add(o);netobjs[name]=o
    for p in n:pn[(p.attrib['ref'],p.attrib['pin'])]=name
rows={r['reference']:r for r in csv.DictReader((P/'component-ledger.csv').open())}
fs={}
for r,c in components.items():
    if rows[r]['kind'] not in ['physical','pcb_feature']:continue
    fn=c.findtext('footprint');assert fn and fn.startswith('Q15:'),(r,fn)
    f=K.FootprintLoad(str(P/'Qualified.pretty'),fn.split(':')[1]);assert f,fn
    f.SetReference(r);f.SetValue(c.findtext('value'));f.SetFPID(K.LIB_ID('Q15',fn.split(':')[1]))
    for pad in f.Pads():
        if pad.GetNumber():pad.SetNet(netobjs[pn[(r,pad.GetNumber())]])
    f.Reference().SetVisible(True);f.Reference().SetLayer(K.F_Fab);f.Reference().SetTextSize(K.VECTOR2I(iu(.4),iu(.4)));f.Reference().SetTextThickness(iu(.06));f.Value().SetVisible(False);b.Add(f);fs[r]=f
    # Every real numbered pad including shell, EP and duplicate power lands.
    actual={p.GetNumber() for p in f.Pads() if p.GetNumber()}
    expected={no for (ref,no) in pn if ref==r}
    assert actual==expected,(r,actual,expected)
assert len(fs)==sum(v['kind'] in ['physical','pcb_feature'] for v in rows.values())
reserves=[('CELL_TOP_AND_CONSERVATIVE_BOTTOM',[26,23.5,61,37]),('ISOLATION_AND_ISOLATED_HALF',[4,23,26,42.5]),('ANTENNA',[83.4,23,94,51]),('REAR_STOP',[38,44.6,47.4,46.6]),('BACKED_PAD',[38.3,46.6,47.1,47.2])]
bottom_extra=[('MCU_RF_BOTTOM_ROUTING_RESERVE',[59,23,83.4,46]),('RAIL_LEFT',[36.9,49,37.4,52.7]),('RAIL_RIGHT',[48,49,48.5,52.7])]
occupied={'F':[],'B':[]}
for f in b.GetFootprints():
    if f.GetReference() in fs:continue
    bb=box(f)
    # Screw boss diameter4.8 projects below, keepnew top also2.65radius.
    if f.GetReference().startswith('H'):
        x,y=xy(f.GetPosition());bb=[x-2.65,y-2.65,x+2.65,y+2.65]
        occupied['B'].append((f.GetReference(),bb))
    occupied['F'].append((f.GetReference(),bb))
placements={};failed=[]
def put(r,x,y,a=0,side='F'):
    f=fs[r]
    if (f.GetLayer()==K.F_Cu)!=(side=='F'):f.Flip(f.GetPosition(),False)
    f.SetOrientationDegrees(a);f.SetPosition(K.VECTOR2I(iu(x),iu(y)))
    bb=box(f);occupied[side].append((r,bb));placements[r]={'x':x,'y':y,'rotation':a,'side':side,'courtyard':bb}
put('J1',42.7,47.6);put('U2',32,41.2);put('C23',27.5,30.25)
# Shell slots and cell leads physically traverse the board; they are obstacles
# on both sides even though the owning component is top-mounted.
for ref in ['J1','C23']:
 for pad in fs[ref].Pads():
  if pad.GetAttribute()==K.PAD_ATTRIB_PTH:
   v=pad.GetBoundingBox();occupied['B'].append((ref+'_PTH_'+pad.GetNumber(),[mm(v.GetLeft())-.25,mm(v.GetTop())-.25,mm(v.GetRight())+.25,mm(v.GetBottom())+.25]))
def allowed(bb,side):
    if bb[0]<4.5 or bb[2]>82.9 or bb[1]<23.5 or bb[3]>50.5:return False
    for n,r in reserves+(bottom_extra if side=='B' else []):
        if overlap(bb,r,.15):return False
    return not any(overlap(bb,r,.20) for n,r in occupied[side])
# Power stages first with their magnetic and rail caps; this is placement only.
# No claimed optimal escape/thermal/EMI routing. All otherparts use one gridpass.
preferred={'U4':(52.5,41),'L2':(56.5,41),'U5':(52.5,47),'L1':(56.5,47),'U6':(49.5,44),'U3':(28,38.5),'U19':(49.5,41),'U40':(49.5,48),'U24':(36,40),'U25':(36,42.5),'U7':(28,46.5),'U8':(29,49),'U10':(62,48.5),'U20':(67,48.5),'U26':(34,46.5),'U27':(78,48.5),'J4':(10.5,48),'S1':(16,48.5),'S2':(20,48.5)}
byrole={v['role']:r for r,v in rows.items()}
order=['U4','L2','U5','L1','U6','U19','U40','U3','U25','U24','U7','U8','U10','U20','U26','U27','U9','U16','J4','S1','S2']
order += sorted([r for r in fs if r.startswith('U') and r not in order and r not in placements],key=lambda r:-math.prod([box(fs[r])[2]-box(fs[r])[0],box(fs[r])[3]-box(fs[r])[1]]))
# Reserve no imaginary zero-area bypasses: place each immediately after IC.
expanded=[]
for r in order:
    expanded.append(r)
    c=byrole.get('C_BYPASS_'+r)
    if c:expanded.append(c)
order=[byrole['C_BYPASS_U2']]+expanded+sorted([r for r in fs if r not in placements and r not in expanded and r!=byrole['C_BYPASS_U2']],key=lambda r:-math.prod([box(fs[r])[2]-box(fs[r])[0],box(fs[r])[3]-box(fs[r])[1]]))
grid=[(x/4,y/4) for y in range(96,201) for x in range(20,332)]
for step,r in enumerate(order):
    f=fs[r];role=rows[r]['role'];target=preferred.get(r,(33,46.5))
    if role.startswith('C_BYPASS_'):
        host=role.removeprefix('C_BYPASS_');v=placements[host];target=(v['x'],v['y'])
    elif r.startswith('C'):
        v=f.GetValue()
        # Logical rail target, not fictional netless placement.
        n=pn[(r,'1')];host={'SYS_3V3':'U4','BACKUP_RAW':'U19','BOOST_3V9':'U5','CAP_POS':'U5','LIMITED_5V':'U6','CC_RAW':'U24','CC_3V3':'U25','AON_RAW':'U7','AON_2V5':'U7'}.get(n)
        if host in placements:target=(placements[host]['x'],placements[host]['y'])
    points=sorted(grid,key=lambda p:(p[0]-target[0])**2+(p[1]-target[1])**2)
    # Logic/passives may use bottom. Magnetics, eFuse, converters and contacts top.
    sides=['F'] if r in ['L1','L2','U4','U5','U6','U3','J4','S1','S2'] else ['F','B']
    if role.startswith('C_BYPASS_'):sides=[placements[host]['side']] # true localdomain bypass on same side.
    selected=None
    for side in sides:
        if (f.GetLayer()==K.F_Cu)!=(side=='F'):f.Flip(f.GetPosition(),False)
        # Cache actual local courtyard at each rotation; translate the measured
        # rectangle in Python rather than rebuilding KiCad caches per gridpoint.
        local={}
        for a in [0,90]:
            f.SetOrientationDegrees(a);f.SetPosition(K.VECTOR2I(0,0));local[a]=box(f)
        for x,y in points:
            for a in [0,90]:
                z=local[a];bb=[z[0]+x,z[1]+y,z[2]+x,z[3]+y]
                if allowed(bb,side):selected=(x,y,a,side);break
            if selected:break
        if selected:break
    if selected:put(r,*selected)
    else:
        # Offboard failures are visible, counted and not called fitting.
        put(r,101+len(failed)%10*6,26+len(failed)//10*6);failed.append(r)
    if step%20==0:print('placed',step+1,r,flush=True)
# Original37 electrical footprints and4holes remain literally unchanged in copy.
for orig,v in original.items():
    ref=orig if orig.startswith('H') else 'BASE_'+orig
    f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
    assert f.GetValue()==v['value'] and sig(f)==v['pads'] and xy(f.GetPosition())==v['xy'] and f.GetOrientationDegrees()==v['rotation'],orig
# Replace only stale contextdrawing labels; no sourcepad/net/value edits.
for drawing in b.GetDrawings():
    if hasattr(drawing,'GetText') and ('UNPLACED' in drawing.GetText() or 'PARTS |' in drawing.GetText()):drawing.SetText('')
for footprint in b.GetFootprints():footprint.Value().SetVisible(False)
# Reserve rectangles shown on Dwgs.User, not excluded-rule pseudo-courtyards.
for name,bb in reserves+bottom_extra:
    s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_RECT);s.SetLayer(K.Dwgs_User);s.SetWidth(iu(.08));s.SetStart(K.VECTOR2I(iu(bb[0]),iu(bb[1])));s.SetEnd(K.VECTOR2I(iu(bb[2]),iu(bb[3])));b.Add(s)
K.SaveBoard(str(P/'qualified15-placement.kicad_pcb'),b)
area=lambda z:(z[2]-z[0])*(z[3]-z[1])
landarea={r:area(p['courtyard']) for r,p in placements.items()}
core=sum(v for r,v in landarea.items() if r not in ['J1','C23'])
gaps=[]
for side in ['F','B']:
    vv=[(r,p['courtyard']) for r,p in placements.items() if p['side']==side and r not in ['J1','C23']]
    for i,(r,a) in enumerate(vv):
        for s,c in vv[i+1:]:
            dx=max(a[0]-c[2],c[0]-a[2],0);dy=max(a[1]-c[3],c[1]-a[3],0)
            gaps.append((math.hypot(dx,dy),r,s))
gaps.sort()
bypass={}
for role,r in byrole.items():
    if role.startswith('C_BYPASS_'):
        host=role.removeprefix('C_BYPASS_');c=placements[r];h=placements[host]
        bypass[r]={'IC':host,'centre_distance_mm':math.hypot(c['x']-h['x'],c['y']-h['y']),'same_side':c['side']==h['side']}
report={'status':'COMPLETE PLACEMENT PASS; UNROUTED and physical release gates open' if not failed else 'DOES NOT FIT IN THIS PASS','source_board':str(src.relative_to(P.parents[4])),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'original37_plus4holes_preserved':len(original),'base_reference_prefix':'BASE_ only in localcopy, no net/position/value/pad changes','candidate_complete_footprints':len(fs),'unplaced':failed,'placements':placements,'reserves':dict(reserves+bottom_extra),'top_parts':sum(p['side']=='F' for p in placements.values()),'bottom_parts':sum(p['side']=='B' for p in placements.values()),'power_courtyard_sum_excluding_cell_USB_mm2':core,'power_courtyard_sum_including_USB_excluding_cell_mm2':core+landarea['J1'],'cell_lead_courtyard_mm2':landarea['C23'],'USB_courtyard_mm2':landarea['J1'],'reservation150_excess_mm2':core-150,'minimum_new_pair_courtyard_gap_mm':gaps[0][0],'closest_pairs':gaps[:10],'courtyard_area_by_ref_mm2':landarea,'bypass_distances':bypass,'board':'main90x28 + proposed12.4x2.3 tongue; no case enlargement, x4..94,y23..51','component_height':'New bottomparts <=1.45mm: boardbottomz10, casefloorz7 gives>=1.55mm nominal floor gap. Topnewparts clearstop/pad. Bridgeundersidez16 leaves5mm top height, magneticsmax2.23mm. Cell horizontalbody reserve separate; tolerance/thermal/routing not qualified.','tracks':len(b.GetTracks()),'fit_claim':'Footprints and conservative AABB court-yard/reserve packing only. Routing, returnpaths, thermal vias, DFM and assembly tolerance remain open.150mm2 constraint FAIL even if fullboard placement completes.','manufacturing_release':False}
(P/'placement.json').write_text(json.dumps(report,indent=2)+'\n')
with (P/'placement-ledger.csv').open('w') as out:
    w=csv.writer(out);w.writerow(['reference','value','land','side','x_mm','y_mm','rotation','courtyard_mm2'])
    for r,p in placements.items():w.writerow([r,components[r].findtext('value'),components[r].findtext('footprint'),p['side'],p['x'],p['y'],p['rotation'],landarea[r]])
print(json.dumps({k:v for k,v in report.items() if k not in ['placements','reserves','bypass_distances','courtyard_area_by_ref_mm2']},indent=2))
