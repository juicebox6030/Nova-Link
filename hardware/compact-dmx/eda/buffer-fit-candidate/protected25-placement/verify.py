from pathlib import Path
import pcbnew as K,json,hashlib,xml.etree.ElementTree as E,math
P=Path(__file__).resolve().parent;root=P.parents[4];mm=K.ToMM
frozen=json.loads((P/'frozen-inputs.json').read_text())
for path,h in frozen.items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h,path
src=K.LoadBoard(str(P.parent/'integrated25/integrated25.kicad_pcb'));b=K.LoadBoard(str(P/'protected25.kicad_pcb'));fa={f.GetReference():f for f in src.GetFootprints()};fb={f.GetReference():f for f in b.GetFootprints()}
changes={('C23','1'):'CELL_TAB_POS',('U3','1'):'CHARGER_IN_PROTECTED',('C7','1'):'CHARGER_IN_PROTECTED'}
def signature(p):return (p.GetPosition().x,p.GetPosition().y,p.GetSize().x,p.GetSize().y,p.GetDrillSize().x,p.GetDrillSize().y,p.GetLayerSet().FmtHex(),str(p.GetShape()))
originalpads=0
for ref,a in fa.items():
 c=fb[ref];assert a.GetPosition()==c.GetPosition() and a.GetOrientationDegrees()==c.GetOrientationDegrees() and a.IsFlipped()==c.IsFlipped(),ref
 assert a.GetFPID()==c.GetFPID(),ref
 assert ref in ['R20','R21'] or a.GetValue()==c.GetValue(),ref
 assert sorted((p.GetNumber(),signature(p)) for p in a.Pads())==sorted((p.GetNumber(),signature(p)) for p in c.Pads()),ref
 originalpads+=len(list(a.Pads()))
 aa={p.GetNumber():p for p in a.Pads()};cc={p.GetNumber():p for p in c.Pads()};assert aa.keys()==cc.keys()
 for no,p in aa.items():
  assert signature(p)==signature(cc[no]),(ref,no)
  assert cc[no].GetNetname()==changes.get((ref,no),p.GetNetname()),(ref,no)

r=E.parse(P/'protected25.net');pn={};values={c.attrib['ref']:c.findtext('value') for c in r.findall('./components/comp')}
for n in r.findall('./nets/net'):
 name=n.attrib['name'].rsplit('/',1)[-1]
 for p in n:pn[(p.attrib['ref'],p.attrib['pin'])]=name
mismatches=[];checked=0
for (ref,no),name in pn.items():
 if ref not in fb:continue
 pad=next((p for p in fb[ref].Pads() if p.GetNumber()==no),None)
 if pad is None:mismatches.append([ref,no,'missing']);continue
 if name.startswith('unconnected-'):continue
 if pad.GetNetname()!=name:mismatches.append([ref,no,name,pad.GetNetname()])
 checked+=1
assert not mismatches,mismatches
for ref in ['R20','R21']+list(set(fb)-set(fa)):assert fb[ref].GetValue()==values[ref],ref
# Independent critical physical-pin truth, not inferred from label similarity.
expected={('F101','1'):'CELL_TAB_POS',('F101','2'):'CAP_POS',('C23','1'):'CELL_TAB_POS',('R101','1'):'CELL_TAB_POS',('U103','A2'):'LIMITED_5V',('U103','B2'):'LIMITED_5V',('U103','A1'):'CHARGER_IN_PROTECTED',('U103','B1'):'CHARGER_IN_PROTECTED',('U3','1'):'CHARGER_IN_PROTECTED',('U3','8'):'CAP_POS',('U3','3'):'CHARGE_DISABLE',('U101','4'):'CELL_OV_SENSE',('U101','6'):'CHARGER_PERMIT_OD',('U102','1'):'CHARGER_PERMIT_OD',('U103','C2'):'CHARGER_SWITCH_ON',('C202','1'):'CAP_POS',('R20','1'):'CAP_POS',('R20','2'):'VCHG_FB',('R21','1'):'VCHG_FB',('R21','2'):'GND_USB'}
for (ref,no),name in expected.items():assert next(p for p in fb[ref].Pads() if p.GetNumber()==no).GetNetname()==name
assert set((f.GetReference(),p.GetNumber()) for f in fb.values() for p in f.Pads() if p.GetNetname()=='CELL_TAB_POS')=={('C23','1'),('F101','1'),('R101','1')}
def edge(s):return(s.GetShape(),s.GetStart().x,s.GetStart().y,s.GetEnd().x,s.GetEnd().y,s.GetArcMid().x if s.GetShape()==K.SHAPE_T_ARC else 0,s.GetArcMid().y if s.GetShape()==K.SHAPE_T_ARC else 0)
assert sorted(edge(s) for s in src.GetDrawings() if s.GetLayer()==K.Edge_Cuts)==sorted(edge(s) for s in b.GetDrawings() if s.GetLayer()==K.Edge_Cuts)
placement=json.loads((P/'placement.json').read_text());assert len(placement['added'])==14
# Independently test real saved courtyards and declared protected regions.
boxes=[]
for ref,f in fb.items():
 f.BuildCourtyardCaches();bb=f.GetCourtyard(K.B_CrtYd if f.IsFlipped() else K.F_CrtYd).BBox();boxes.append((ref,f.IsFlipped(),[mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())]))
def overlap(a,c):return min(a[2],c[2])>max(a[0],c[0])+1e-6 and min(a[3],c[3])>max(a[1],c[1])+1e-6
added=set(fb)-set(fa);spatial=0
for ref,side,a in boxes:
 if ref not in added:continue
 for other,side2,c in boxes:
  if ref!=other and side==side2:assert not overlap(a,c),(ref,other);spatial+=1
 for c in placement['reserved_regions']:assert not overlap(a,c),(ref,c)
assert len(b.GetTracks())==0
j=json.loads((P/'drc.json').read_text());assert not j['violations'];erc=json.loads((P/'erc.json').read_text());assert sum(len(s['violations']) for s in erc['sheets'])==0
f=fb['F101'];p1=next(p for p in f.Pads() if p.GetNumber()=='1');tab=next(p for p in fb['C23'].Pads() if p.GetNumber()=='1');distance=math.hypot(mm(p1.GetPosition().x-tab.GetPosition().x),mm(p1.GetPosition().y-tab.GetPosition().y))
mechanics=json.loads((P/'mechanics-check.json').read_text());reopen=json.loads((P/'reopen.json').read_text())
assert not mechanics['nominal_intersections'] and not mechanics['existing_component_collisions']
assert mechanics['allocated_XY_0_25_down_0_20_base_overlap']<1e-7
assert reopen['unexpected_intersections']==0 and reopen['STEP_closed_solids']==40 and all(reopen['valid'].values())
result={'saved_board_total_pads':sum(len(list(f.Pads())) for f in fb.values()),'status':'Electrical mapping and nominal 2D checks PASS; conditional placement with proposed local base relief; unprotected route/access/protection qualification OPEN','frozen_hashes':len(frozen),'baseline_footprints_unchanged_position':len(fa),'baseline_pad_geometry_checks':originalpads,'explicit_changed_padnets':len(changes),'added_parts':len(added),'board_footprints':len(fb),'actual_export_connected_pin_comparisons':checked,'critical_pin_assertions':len(expected),'spatial_pairs':spatial,'ERC_violations':0,'DRC_violations':len(j['violations']),'unconnected':len(j['unconnected_items']),'tracks':0,'cell_tab_to_fuse_land_straight_distance_mm':distance,'routing_length_is_not_this_distance':True,'schematic_scope':'Complete qualified power + cell protection; existing MCU/RF/DMX are retained board context, not newly captured whole product'}
(P/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
