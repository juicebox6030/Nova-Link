#!/usr/bin/env python3
"""Run with existing Flatpak KiCad Python. Imports actual exported nets and library lands."""
import pcbnew as K, pathlib, json, xml.etree.ElementTree as E, hashlib
D=pathlib.Path(__file__).resolve().parent; EDA=D.parent
assign=json.loads((EDA/'footprints/assignments.json').read_text())
P={'U5':(18,36,90),'S_TERM':(18,26.6,180),'R_TERM1':(6.5,32.2,90),'R_TERM2':(9.2,32.2,90), 'C3':(25,28,90),'C4':(11.8,26.4,90),'C1':(18,44,0),'C2':(22,44.5,0),'R1':(12,44,90),'R2':(15,44,90),'R3':(27,43,90),'R4':(25,46,90),
'U1':(67,33,180),'TR101':(73,34.5,-90),'A101':(91.6,37,-90),
'Y101':(74,30,90),'Y102':(65,26,0),'FL101':(60,42,0),'L101':(66,41,0),
'C101':(60,45,0),'C102':(66,44,0),'C103':(71,40,90),
'C104':(70,38.3,0),'C105':(62,37.5,90),'C106':(65,28,0),'C107':(62,30,90),'C108':(67.5,27.6,0),'C109':(69.8,27.6,0),
'C110':(76,29,90),'C111':(76,32,90),'C112':(77,37,0),'C113':(75,38,90),
'L102':(82,32.6,0),'C115':(82.6,30.5,90),'L104':(82,41.4,0),'L103':(79,39,90),'C116':(81,39,90)}
assert len(P)==37
b=K.BOARD(); b.GetDesignSettings().SetBoardThickness(K.FromMM(1))
def pos(x,y): return K.VECTOR2I(K.FromMM(x),K.FromMM(y))
def line(x1,y1,x2,y2,layer=K.Dwgs_User):
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetStart(pos(x1,y1));s.SetEnd(pos(x2,y2));s.SetLayer(layer);s.SetWidth(K.FromMM(.1));b.Add(s)
def rect(x1,y1,x2,y2,layer=K.Dwgs_User):
 for a,c in [((x1,y1),(x2,y1)),((x2,y1),(x2,y2)),((x2,y2),(x1,y2)),((x1,y2),(x1,y1))]:line(*a,*c,layer)
def label(t,x,y):
 s=K.PCB_TEXT(b);s.SetText(t);s.SetPosition(pos(x,y));s.SetTextSize(pos(.8,.8));s.SetTextThickness(K.FromMM(.12));s.SetLayer(K.Dwgs_User);b.Add(s)
rect(4,23,94,51,K.Edge_Cuts)
rect(36.5,45.1,48.9,51);label('USB SLOT KEEP-OUT',42.7,48)
rect(26,23.5,61,37);label('CAP / LEADS: HEIGHT UNVERIFIED',43,30)
rect(4,34.8,26,37.2);label('ISOLATION ROUTING CORRIDOR',16,36)
label('90 x 28 x 1 mm | 37 PARTS | UNROUTED PARTIAL',49,54)
label('POWER / SPI NOR / USB / SERVICE UNPLACED',49,56)
line(4,59,94,59);line(4,58,4,60);line(94,58,94,60);label('90.00 mm',49,59)
line(98,23,98,51);line(97,23,99,23);line(97,51,99,51);label('28.00 mm',103,37)
for i,(x,y) in enumerate([(7,26),(73,26),(7,48),(73,48)],1):
 f=K.FOOTPRINT(b);f.SetReference('H'+str(i));f.SetValue('Mechanical NPTH 2.2');f.SetPosition(pos(x,y));p=K.PAD(f);p.SetAttribute(K.PAD_ATTRIB_NPTH);p.SetShape(K.PAD_SHAPE_CIRCLE);p.SetSize(pos(2.2,2.2));p.SetDrillSize(pos(2.2,2.2));p.SetLayerSet(K.LSET.AllCuMask());p.SetPosition(pos(x,y));f.Add(p);b.Add(f)
alias={'DMX_TX':'MCU_DMX_TX','DMX_RX':'MCU_DMX_RX','DMX_RE_N':'MCU_RE_N'}
nets={}; expected={}; hashes={}; omitted={}; stable_exports={}
def stable_xml(data):
 root=E.fromstring(data)
 date=root.find('./design/date')
 if date is not None:date.text=None
 return hashlib.sha256(E.tostring(root,encoding='utf-8')).hexdigest()

for sheet,path in [('dmx',EDA/'dmx-interface.net'),('mcu-radio',EDA/'mcu-radio/mcu-radio.net')]:
 rel=str(path.relative_to(EDA)); hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
 stable_exports[rel]=stable_xml(path.read_bytes())
 sch=path.with_suffix('.kicad_sch');hashes[str(sch.relative_to(EDA))]=hashlib.sha256(sch.read_bytes()).hexdigest()
 root=E.parse(path).getroot(); pinmap={}
 for n in root.findall('./nets/net'):
  raw=n.attrib['name'].lstrip('/'); name=alias.get(raw,raw)
  if name.startswith('unconnected-'):name=sheet+'_'+name
  for node in n.findall('node'):pinmap[(node.attrib['ref'],node.attrib['pin'])]=name
 omitted[sheet]=[]
 for c in root.findall('./components/comp'):
  ref=c.attrib['ref'];key=sheet+'.'+ref
  if key not in assign:omitted[sheet].append(ref);continue
  a=assign[key]; fpfile=EDA/'footprints/NOVA_HW.pretty'/ (a['footprint']+'.kicad_mod'); hashes[str(fpfile.relative_to(EDA))]=hashlib.sha256(fpfile.read_bytes()).hexdigest()
  f=K.FootprintLoad(str(fpfile.parent),a['footprint']);f.SetReference(ref);f.SetValue(a['value']);f.SetPosition(pos(*P[ref][:2]));f.SetOrientationDegrees(P[ref][2]);f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Add(f)
  expected[ref]={}
  for p in f.Pads():
   num=p.GetNumber()
   if not num:continue
   name=pinmap.get((ref,num));assert name,(ref,num)
   if name not in nets:
    net=K.NETINFO_ITEM(b,name);b.Add(net);nets[name]=net
   p.SetNet(nets[name]);expected[ref][num]=name
  label(ref,*P[ref][:2])
K.SaveBoard(str(D/'candidate.kicad_pcb'),b)
(D/'inputs.json').write_text(json.dumps({'sha256':hashes,'stable_export_sha256':stable_exports,'stable_export_rule':'XML parse/serialize; blank ONLY top-level design/date text; every other parsed field retained','assignments':assign,'positions_mm':P,'expected_pad_nets':expected,'omitted_boundary_refs':omitted,'aliases':alias},indent=2)+'\n')
print('Generated',len(expected),'physical components,',len(nets),'nets; 4 mechanical NPTHs')
