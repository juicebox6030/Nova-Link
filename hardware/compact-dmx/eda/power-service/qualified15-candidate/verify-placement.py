"""Independent check of saved board, actual pads, complete lands and reserves.
Does not import placement/generation code or trust their computed geometry.
Run using existing KiCad Python. No unconnected item is suppressed.
"""
from pathlib import Path
import pcbnew as K,xml.etree.ElementTree as E,json,math,csv
P=Path(__file__).resolve().parent;b=K.LoadBoard(str(P/'qualified15-placement.kicad_pcb'))
src=P.parents[1]/'service-footprints/gct-power-candidate/mechanical/tongue.kicad_pcb';old=K.LoadBoard(str(src))
mm=K.ToMM;f={x.GetReference():x for x in b.GetFootprints()};root=E.parse(P/'qualified15.net')
reviewed=K.LoadBoard(str(P/'history/pre-u40-fix-qualified15-placement.kicad_pcb'))
rf={x.GetReference():x for x in reviewed.GetFootprints()}
assert set(f)==set(rf)
net_changes=[]
for ref,x in f.items():
    y=rf[ref]
    assert (x.GetPosition(),x.GetOrientationDegrees(),x.GetLayer(),x.GetValue())==(y.GetPosition(),y.GetOrientationDegrees(),y.GetLayer(),y.GetValue()),ref
    xp=list(x.Pads());yp=list(y.Pads());assert len(xp)==len(yp)
    for a,c in zip(xp,yp):
        def geom(p):return (p.GetNumber(),p.GetPosition(),p.GetSize(),p.GetDrillSize(),p.GetShape(),p.GetAttribute(),p.GetOrientationDegrees(),p.GetLayerSet().FmtHex())
        assert geom(a)==geom(c),(ref,a.GetNumber())
        if a.GetNetname()!=c.GetNetname():net_changes.append([ref,a.GetNumber(),c.GetNetname(),a.GetNetname()])
assert net_changes==[['U40','5','GND_USB','AON_USB_LIMITED']],net_changes
assert next(p for p in f['U40'].Pads() if p.GetNumber()=='5').GetNetname()=='AON_USB_LIMITED'
rows={r['reference']:r for r in csv.DictReader((P/'component-ledger.csv').open())}
physical={r for r,v in rows.items() if v['kind'] in ['physical','pcb_feature']}
assert set(f)==physical|{'BASE_'+x.GetReference() if not x.GetReference().startswith('H') else x.GetReference() for x in old.GetFootprints() if x.GetReference() not in ['J_USB','U2']}
pn={(x.attrib['ref'],x.attrib['pin']):n.attrib['name'].rsplit('/',1)[-1] for n in root.findall('./nets/net') for x in n}
padchecks=0
def signature(x):return [(p.GetNumber(),p.GetPosition().x,p.GetPosition().y,p.GetNetname(),p.GetSize().x,p.GetSize().y,p.GetDrillSize().x,p.GetDrillSize().y,p.GetShape()) for p in x.Pads()]
for x in old.GetFootprints():
    r=x.GetReference()
    if r in ['J_USB','U2']:
        new=f['J1' if r=='J_USB' else 'U2'];assert signature(x)==signature(new),r
    else:
        new=f[r if r.startswith('H') else 'BASE_'+r]
        assert signature(x)==signature(new) and x.GetValue()==new.GetValue() and x.GetOrientationDegrees()==new.GetOrientationDegrees(),r
comps={c.attrib['ref']:c for c in root.findall('./components/comp')}
for r in physical:
    assert f[r].GetValue()==comps[r].findtext('value'),r
    nums=set()
    for p in f[r].Pads():
        if not p.GetNumber():continue
        nums.add(p.GetNumber());assert p.GetNetname()==pn[(r,p.GetNumber())],(r,p.GetNumber(),p.GetNetname());padchecks+=1
    assert nums=={no for rr,no in pn if rr==r},r
def bbox(x):
    x.BuildCourtyardCaches();v=x.GetCourtyard(K.F_CrtYd if x.GetLayer()==K.F_Cu else K.B_CrtYd).BBox()
    return [mm(v.GetLeft()),mm(v.GetTop()),mm(v.GetRight()),mm(v.GetBottom())]
def overlap(a,c):return min(a[2],c[2])>max(a[0],c[0])+1e-7 and min(a[3],c[3])>max(a[1],c[1])+1e-7
reserves={'cell':[26,23.5,61,37],'isolation':[4,23,26,42.5],'antenna':[83.4,23,94,51],'stop':[38,44.6,47.4,46.6],'pad':[38.3,46.6,47.1,47.2]}
extra={'radio_bottom':[59,23,83.4,46],'left_rail':[36.9,49,37.4,52.7],'right_rail':[48,49,48.5,52.7]}
boxes={r:bbox(f[r]) for r in physical};gaps=[];reserved_checks=0
for r,a in boxes.items():
    if r in ['J1','C23']:continue # Only real connector/cell lands occupy own reserves.
    assert 4.5<=a[0]<a[2]<=82.9 and 23.5<=a[1]<a[3]<=50.5,(r,a)
    rs=reserves|extra if f[r].GetLayer()==K.B_Cu else reserves
    for n,c in rs.items():assert not overlap(a,c),(r,n);reserved_checks+=1
    for s,y in f.items():
        if s==r:continue
        if not s.startswith('H') and y.GetLayer()!=f[r].GetLayer():continue
        if s.startswith('H'):
            x=mm(y.GetPosition().x);z=mm(y.GetPosition().y);c=[x-2.65,z-2.65,x+2.65,z+2.65]
        else:c=bbox(y)
        assert not overlap(a,c),(r,s)
        dx=max(a[0]-c[2],c[0]-a[2],0);dy=max(a[1]-c[3],c[1]-a[3],0);gaps.append(math.hypot(dx,dy))
area=lambda a:(a[2]-a[0])*(a[3]-a[1])
core=sum(area(a) for r,a in boxes.items() if r not in ['J1','C23'])
basearea=sum(area(bbox(x)) for x in old.GetFootprints() if x.GetReference() not in ['J_USB','U2'] and not x.GetReference().startswith('H'))
drc=json.loads((P/'drc.json').read_text());assert not drc['violations'],drc['violations']
assert len(b.GetTracks())==0
# KiCad inherited defaults ignore five categories. Record them, never claim
# allchecks enabled. Everycompletecourtyard is independentlyrequired here.
assert all(a[2]>a[0] and a[3]>a[1] for a in boxes.values())
assert core>150
# Physical outline from frozen approved tongue branch is unchanged in copy.
edges=lambda board:sorted((x.GetStart().x,x.GetStart().y,x.GetEnd().x,x.GetEnd().y) for x in board.GetDrawings() if x.GetLayer()==K.Edge_Cuts)
assert edges(b)==edges(old)
report={'status':'PASS actual saved-board pad/net/placement geometry;150mm2 reservation FAIL; routing not performed','candidate_footprints':len(physical),'actual_numbered_pad_checks':padchecks,'source_original37_plus4holes_unchanged':41,'GCT_and_NOR_exact_source_pad_geometry':True,'real_DRC_geometric_violations':len(drc['violations']),'real_DRC_unconnected_items':len(drc['unconnected_items']),'DRC_ignored_checks':drc['ignored_checks'],'reserve_checks':reserved_checks,'new_core_courtyard_sum_mm2':core,'core_courtyard_top_mm2':sum(area(a) for r,a in boxes.items() if r not in ['J1','C23'] and f[r].GetLayer()==K.F_Cu),'core_courtyard_bottom_mm2':sum(area(a) for r,a in boxes.items() if r not in ['J1','C23'] and f[r].GetLayer()==K.B_Cu),'original37_courtyard_sum_mm2':basearea,'combined_all_electrical_courtyard_sum_mm2':basearea+sum(map(area,boxes.values())),'minimum_new_to_any_same_side_courtyard_gap_mm':min(gaps),'board_main_area_mm2':2520,'tongue_area_mm2':12.4*2.3,'cell_projection_reserve_mm2':35*13.5,'antenna_projection_reserve_mm2':10.6*28,'new_core_excess_over150_mm2':core-150,'area_interpretation':'Courtyard sums are occupied areas on their own assemblyside, not a single rectangular floorplan. No overlap on a side; top/bottom projections can overlap. Reserve unions and routing channels are additional. Does not authorize reservation/case change.','manufacturing_release':False}
report['U40_correction']={'reviewed_board':'history/pre-u40-fix-qualified15-placement.kicad_pcb','all_footprint_positions_rotations_sides_values_preserved':len(f),'all_actual_pad_geometry_preserved':True,'only_pad_net_changes':net_changes,'repacked':False}
(P/'placement-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
