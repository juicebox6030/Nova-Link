from pathlib import Path
import pcbnew as K,json,hashlib,shutil,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent;EDA=P.parents[1];L=P/'Candidate.pretty';L.mkdir(exist_ok=True)
def rect(a,b,c,d,layer):return f'(fp_rect (start {a} {b}) (end {c} {d}) (stroke (width .05) (type default)) (fill none) (layer "{layer}"))'
s='(footprint "GCT_USB4125_GF_A" (version 20241229) (generator "nova_gct") (layer "F.Cu") (attr smd) (descr "GCT USB4125 A6 recommended copper; mask/paste nominal design defaults; SH proposed ground; default1mm stake")\n'
s+='(fp_text reference "J_USB" (at 0 -2) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))\n'
for pin,x,w in [('B12',-2.75,.8),('B9',-1.52,.76),('A5',-.5,.7),('B5',.5,.7),('A9',1.52,.76),('A12',2.75,.8)]:s+=f'(pad "{pin}" smd rect (at {x} -.08) (size {w} 1.2) (layers "F.Cu" "F.Mask" "F.Paste"))\n'
for x in [-4.32,4.32]:
 for y in [0,3.8]:s+=f'(pad "SH" thru_hole oval (at {x} {y}) (size 1.1 1.7) (drill oval .6 1.2) (layers "*.Cu" "*.Mask"))\n'
s+=rect(-4.47,-.4,4.47,6.4,'F.Fab')+rect(-5.12,-1.1,5.12,6.65,'F.CrtYd')+')\n';(L/'GCT_USB4125_GF_A.kicad_mod').write_text(s)
shutil.copyfile(P.parent/'Service.pretty/AT25SF161B_MHB_Derived.kicad_mod',L/'AT25SF161B_MHB_Derived.kicad_mod')
source=EDA/'placement-candidate/candidate.kicad_pcb';b=K.LoadBoard(str(source)); hashes={str(source):hashlib.sha256(source.read_bytes()).hexdigest()}
nets={n.GetNetname():n for n in b.GetNetInfo().NetsByNetcode().values()}
def net(name):
 if name not in nets:nets[name]=K.NETINFO_ITEM(b,name);b.Add(nets[name])
 return nets[name]
contracts={'J_USB':{'A5':'CC1','B5':'CC2','A9':'VBUS_RAW','B9':'VBUS_RAW','A12':'GND_USB','B12':'GND_USB','SH':'GND_USB'},'U2':{'1':'SPI_CS_N','2':'SPI_MISO','3':'FLASH_WP_N','4':'GND_USB','5':'SPI_MOSI','6':'SPI_SCK','7':'FLASH_HOLD_N','8':'SYS_3V3','9':'GND_USB'}}
for ref,name,xy in [('J_USB','GCT_USB4125_GF_A',(42.7,44.6)),('U2','AT25SF161B_MHB_Derived',(32,41.2))]:
 f=K.FootprintLoad(str(L),name);f.SetReference(ref);f.SetValue('USB4125-GF-A PROPOSED' if ref=='J_USB' else 'AT25SF161B-MHB-T DERIVED LANDS');f.SetPosition(K.VECTOR2I(K.FromMM(xy[0]),K.FromMM(xy[1])));b.Add(f)
 for p in f.Pads():
  if p.GetNumber():p.SetNet(net(contracts[ref][p.GetNumber()]))
# Preserve original reserve drawing but label authorized proposed occupancy, not a hidden exemption.
for d in b.GetDrawings():
 if isinstance(d,K.PCB_TEXT):
  if d.GetText()=='USB SLOT KEEP-OUT':d.SetText('GCT: SOLID PCB REQUIRED')
  elif '37 PARTS' in d.GetText():d.SetText(d.GetText().replace('37 PARTS','39 PARTS'))
  elif d.GetText()=='POWER / SPI NOR / USB / SERVICE UNPLACED':d.SetText('POWER / CC QUALIFICATION / SERVICE UNPLACED')
K.SaveBoard(str(P/'candidate.kicad_pcb'),b)
for path in [P.parent/'Service.pretty/AT25SF161B_MHB_Derived.kicad_mod',EDA/'power-service/power-service.net',EDA/'placement-candidate/inputs.json']:
 hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
(P/'inputs.json').write_text(json.dumps({'raw_sha256':hashes,'contracts':contracts,'USB_origin_mm':[42.7,44.6],'NOR_origin_mm':[32,41.2],'shell_ground':'PROPOSED ONLY in this copy; manufacturer SHELL GND; not active circuit binding','removed_slot':'Required proposal: restore solid PCB x36.5..48.9 y45.1..51; baseline PCB copy was already rectangular'},indent=2)+'\n')
print('39 electrical parts +4 existing mounting holes; proposed connector/NOR only')
