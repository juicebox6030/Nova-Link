"""Independent source drawing geometry checks on the ACTUAL saved board.
No generate.py/lands.py/place.py imports or expected-coordinate artifact reads.
"""
from pathlib import Path
import pcbnew as K,math,json
P=Path(__file__).resolve().parent;b=K.LoadBoard(str(P/'regulated-source.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()};mm=K.ToMM
checks=0
def local(f,p):
 dx=mm(p.GetPosition().x-f.GetPosition().x);dy=mm(p.GetPosition().y-f.GetPosition().y);ang=-math.radians(f.GetOrientationDegrees());return (dx*math.cos(ang)-dy*math.sin(ang),dx*math.sin(ang)+dy*math.cos(ang))
def compare(ref,no,x,y,w,h):
 global checks
 f=fs[ref];pp=[p for p in f.Pads() if p.GetNumber()==str(no)]
 assert any(all(abs(a-c)<1e-6 for a,c in zip((*local(f,p),mm(p.GetSize().x),mm(p.GetSize().y)),(x,y,w,h))) for p in pp),(ref,no,x,y,w,h)
 checks+=1
# TI RNM example: reference small pad center -1.15, pitch0.5;
# pins7/8 and12/13 share U copper because they are duplicated powers.
for n,y in [(1,-.75),(2,-.25),(3,.25),(4,.75)]:compare('U2',n,-1.15,y,.6,.25)
for n,x,y in [(5,-.725,1.4),(6,-.225,1.4),(14,-.225,-1.4),(15,-.725,-1.4),(7,.275,1.4),(8,.775,1.4),(13,.275,-1.4),(12,.775,-1.4)]:compare('U2',n,x,y,.25,.6)
for n,y,w,x in [(9,.5,1.35,.775),(10,0,1.7,.6),(11,-.5,1.35,.775)]:compare('U2',n,x,y,w,.25)
compare('U2',8,.525,1.225,.75,.25);compare('U2',12,.525,-1.225,.75,.25)
for n,y in [(1,-1.25),(2,-.75),(3,-.25),(4,.25),(5,.75),(6,1.25)]:compare('U3',n,-1.4,y,.6,.2)
for n,x in [(7,-.75),(8,-.25),(9,.25),(10,.75)]:compare('U3',n,x,1.9,.2,.6)
for n,y in [(11,1.25),(12,.75),(13,.25),(14,-.25),(15,-.75),(16,-1.25)]:compare('U3',n,1.4,y,.6,.2)
for n,x in [(17,.75),(18,.25),(19,-.25),(20,-.75)]:compare('U3',n,x,-1.9,.2,.6)
compare('U3',21,0,0,1.6,2.6)
for no,x,w in [('A1_B12',-3.2,.6),('A4_B9',-2.4,.6),('B8',-1.75,.3),('A5',-1.25,.3),('B7',-.75,.3),('A6',-.25,.3),('A7',.25,.3),('B6',.75,.3),('A8',1.25,.3),('B5',1.75,.3),('B4_A9',2.4,.6),('B1_A12',3.2,.6)]:compare('J1',no,x,-4.755,w,1.15)
f=fs['J1'];assert len(list(f.Pads()))==18 # 12sharedlands+4stakes+2NPTH, NOT16fictionalPCBsignals
for no,x,y,h,drillh in [('S1',-4.32,-4.18,2.1,1.7),('S2',4.32,-4.18,2.1,1.7),('S3',-4.32,-1.4,1.8,1.4),('S4',4.32,-1.4,1.8,1.4)]:
 compare('J1',no,x,y,1,h);p=next(p for p in f.Pads() if p.GetNumber()==no);assert abs(mm(p.GetDrillSize().x)-.6)<1e-8 and abs(mm(p.GetDrillSize().y)-drillh)<1e-8
holes=sorted((round(local(f,p)[0],6),round(local(f,p)[1],6),round(mm(p.GetDrillSize().x),6)) for p in f.Pads() if not p.GetNumber());assert holes==[(-2.89,-3.68,.65),(2.89,-3.68,.65)]
f=fs['L1'];p=sorted(f.Pads(),key=lambda p:local(f,p)[0]);assert abs(local(f,p[1])[0]-local(f,p[0])[0]-.98-2.37)<1e-8
assert all(abs(mm(pad.GetSize().x)-.98)<1e-8 and abs(mm(pad.GetSize().y)-3.4)<1e-8 for pad in p);checks+=3
assert next(p for p in fs['C8'].Pads() if p.GetNumber()=='1').GetNetname()=='REG_5V136'
result={'status':'PASS independent literal primary-land geometry on savedboard','coordinate_dimension_checks':checks,'USB_contacts':16,'USB_signal_solder_lands':12,'USB_shell_slots':4,'USB_NPTH':2,'inductor_inner_gap_mm':2.37,'RNM_stencil_and_mask_definition':'Prototype interpretation retained; not assemblyapproval','no_generator_import':True}
(P/'land-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
