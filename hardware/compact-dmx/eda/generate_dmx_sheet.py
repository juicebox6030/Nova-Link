"""Generate self-contained modern KiCad PARTIAL DMX sheet; never writes a netlist.
Connectivity evidence must come from verify_kicad.py using the real KiCad CLI.
"""
from pathlib import Path
import uuid,csv,json
P=Path(__file__).resolve().parent
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-partial-dmx/'+s))
q=lambda s:'"'+str(s).replace('"','\\"')+'"'
effects='(effects (font (size 1.0 1.0)))'
pins=[('VIO',1,'SYS_3V3','power_in'),('D',2,'DMX_TX','input'),('DE',3,'DMX_DE_SAFE','input'),('R',4,'DMX_RX','output'),('RE_N',5,'DMX_RE_N','input'),('GNDIO',6,'GND_USB','power_in'),('OUT',7,None,'output'),('EN_FLT',8,'ISOW_EN_PIN','input'),('VDD',9,'SYS_3V3','power_in'),('GND1',10,'GND_USB','power_in'),('GND2',11,'GND_ISO','power_in'),('VISOOUT',12,'ISO_3V3','power_out'),('MODE',13,'GND_ISO','input'),('IN',14,'GND_ISO','input'),('GISOIN',15,'GND_ISO','power_in'),('VISOIN',16,'ISO_3V3','power_in'),('Y',17,'DMX_P','output'),('Z',18,'DMX_N','output'),('B',19,'DMX_N','input'),('A',20,'DMX_P','input')]
# Pin tuples: name, number, x, y in library coordinates, angle, electrical type.
ul=[]
for name,num,net,typ in pins:
 left=num<=10;i=(num-1) if left else (20-num)
 ul.append((name,str(num),-12.7 if left else 12.7,11.43-i*2.54,0 if left else 180,typ))
lib={}
def symbol(name,pins,width=10.16,height=13.97,ref='U',drawing=None):
 draw=drawing or f'(rectangle (start {-width} {height}) (end {width} {-height}) (stroke (width 0.254) (type default)) (fill (type background)))'
 lines=[f'(symbol {q(name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes)',f'(property "Reference" {q(ref)} (at 0 {height+2.54} 0) {effects})',f'(property "Value" {q(name)} (at 0 {-height-2.54} 0) {effects})',f'(symbol {q(name+"_0_1")} {draw})',f'(symbol {q(name+"_1_1")}']
 for pn,no,x,y,a,t in pins:lines.append(f'(pin {t} line (at {x} {y} {a}) (length 2.54) (name {q(pn)} {effects}) (number {q(no)} {effects}))')
 lines+=['))'];lib[name]=(''.join(lines),pins)
symbol('ISOW1412_ENABLE_MODE',ul)
pp=[('1','1',0,5.08,270,'passive'),('2','2',0,-5.08,90,'passive')]
symbol('PCM12SMTR',[(str(i),str(i),-7.62,5.08-(i-1)*5.08,0,'passive') for i in (1,2,3)],5.08,7.62,'S')
symbol('R',pp,1.016,2.54,'R')
symbol('C',pp,1.016,2.54,'C', '(polyline (pts (xy 0 2.54) (xy 0 0.508)) (stroke (width 0.254) (type default)) (fill (type none))) (polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.254) (type default)) (fill (type none))) (polyline (pts (xy -1.524 -0.508) (xy 1.524 -0.508)) (stroke (width 0.254) (type default)) (fill (type none))) (polyline (pts (xy 0 -0.508) (xy 0 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))')
bound=[('SYS_3V3','1','power_out'),('GND_USB','2','power_out'),('DMX_TX','3','output'),('DMX_DE_SAFE','4','output'),('DMX_RE_N','5','output'),('DMX_RX','6','input'),('DMX_POWER_EN','7','output')]
symbol('EXTERNAL_CONTROL_REQUIRED',[(n,no,17.78,7.62-i*2.54,180,t) for i,(n,no,t) in enumerate(bound)],15.24,10.16,'X')
symbol('DMX_BOUNDARY',[(n,str(i+1),-10.16,2.54-i*2.54,0,'passive') for i,n in enumerate(['GND_ISO','DMX_N','DMX_P'])],7.62,5.08,'J')
symbol('ISO_RETURN_REFERENCE',[('GND_ISO','1',0,-5.08,90,'power_out')],5.08,2.54,'#FLG')
root=uid('root');s=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A4") (title_block (title "NOVA partial isolated DMX interface - NOT RELEASED") (rev "C-TERM1")) (lib_symbols']
for name,(definition,_) in lib.items():s.append(definition.replace('(symbol '+q(name)+' ', '(symbol '+q('NOVA:'+name)+' ',1))
s.append(')')
def place(name,ref,value,x,y,nets,bom=True):
 assignment=json.loads((P/'footprints/assignments.json').read_text()).get('dmx.'+ref)
 if assignment:value=assignment['value']
 id=uid(ref);s.append(f'(symbol (lib_id "NOVA:{name}") (at {x} {y} 0) (unit 1) (in_bom {"yes" if bom else "no"}) (on_board {"yes" if bom else "no"}) (dnp no) (uuid "{id}")')
 s.append(f'(property "Reference" {q(ref)} (at {x+2.54} {y-17.78 if name.startswith("ISOW") else (y-15.24 if name=="EXTERNAL_CONTROL_REQUIRED" else (y-10.16 if name=="PCM12SMTR" else y-5.08))} 0) {effects})')
 s.append(f'(property "Value" {q(value)} (at {x+2.54} {y+17.78 if name.startswith("ISOW") else (y+15.24 if name=="EXTERNAL_CONTROL_REQUIRED" else (y+10.16 if name=="PCM12SMTR" else y+7.62))} 0) {effects})')
 fp=assignment['footprint'] if assignment else None
 if fp:s.append(f'(property "Footprint" "NOVA_HW:{fp}" (at {x} {y} 0) (effects (font (size 1 1)) hide))')
 for pn,no,px,py,a,t in lib[name][1]:s.append(f'(pin {q(no)} (uuid "{uid(ref+"pin"+no)}"))')
 s.append(f'(instances (project "dmx-interface" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
 for pn,no,px,py,a,t in lib[name][1]:
  xx,yy=round(x+px,4),round(y-py,4);net=nets.get(no)
  if net is None:s.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
  dx,dy={0:(-5.08,0),180:(5.08,0),270:(0,-5.08),90:(0,5.08)}[a]
  ex,ey=round(xx+dx,4),round(yy+dy,4)
  s.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"wire")}"))')
  s.append(f'(label {q(net)} (at {ex} {ey} 0) {effects} (uuid "{uid(ref+no+"label")}"))')
place('ISOW1412_ENABLE_MODE','U5','ISOW1412DFMR',139.7,76.2,{str(n):net for _,n,net,_ in pins})
place('EXTERNAL_CONTROL_REQUIRED','X1','OFF-SHEET CONTROL / POWER CONTRACT',50.8,76.2,{no:n for n,no,_ in bound},False)
place('DMX_BOUNDARY','J1','XLR1/2/3 boundary',231.14,76.2,{'1':'GND_ISO','2':'DMX_N','3':'DMX_P'},False)
place('ISO_RETURN_REFERENCE','#FLG01','ISOLATED RETURN REFERENCE',185.42,111.76,{'1':'GND_ISO'},False)
for name,ref,val,x,y,n1,n2 in [('R','R1','10k',40.64,121.92,'DMX_DE_SAFE','GND_USB'),('R','R2','10k',76.2,121.92,'SYS_3V3','DMX_RE_N'),('R','R3','10k',111.76,121.92,'DMX_POWER_EN','GND_USB'),('R','R4','1k 1%',152.4,121.92,'DMX_POWER_EN','ISOW_EN_PIN'),('C','C1','100n 16V X7R',40.64,147.32,'SYS_3V3','GND_USB'),('C','C2','10u 10V X7R',86.36,147.32,'SYS_3V3','GND_USB'),('C','C3','100n 16V X7R',175.26,147.32,'ISO_3V3','GND_ISO'),('C','C4','10u 10V X7R',220.98,147.32,'ISO_3V3','GND_ISO')]:place(name,ref,val,x,y,{'1':n1,'2':n2})
place('PCM12SMTR','S_TERM','PCM12SMTR OFF=1-2 / ON=2-3',231.14,106.68,{'1':None,'2':'DMX_P','3':'TERM_SW'})
place('R','R_TERM1','CRCW1206240RFKEA 240R 1% 0.25W',40.64,175.26,{'1':'TERM_SW','2':'DMX_N'})
place('R','R_TERM2','CRCW1206240RFKEA 240R 1% 0.25W',152.4,175.26,{'1':'TERM_SW','2':'DMX_N'})
notes=['PARTIAL SHEET ONLY. X1 is an explicit off-sheet electrical contract, NOT implemented gating circuitry.', 'X1 maps to power-service X_DMX: POR/cutoff gate DE and isolated-power enable; resident loader may enable RDM.', 'U5 pin8 ENABLE INPUT via R4=1k (TI SLLSF86D p5 permits series limiting). Brownout operation unverified.', 'GND_USB and GND_ISO must remain separate. ISO_RETURN_REFERENCE declares converter return only.', 'Termination: two240R in parallel via manual S_TERM; assemble OFF. No external TVS; on-chip ESD basis only.']
for i,n in enumerate(notes):s.append(f'(text {q(n)} (at 20.32 {20.32+i*5.08} 0) (effects (font (size 1.0 1.0)) (justify left)) (uuid "{uid("note"+str(i))}"))')
s.append(')');(P/'dmx-interface.kicad_sch').write_text('\n'.join(s)+'\n')
(P/'nova-dmx.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(d for d,_ in lib.values())+'\n)\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "NOVA") (type "KiCad") (uri "${KIPRJMOD}/nova-dmx.kicad_sym") (options "") (descr "Local partial DMX symbols")))\n')
with (P/'dmx-pin-net.csv').open('w') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['component','pin','pin_name','net','electrical_type'])
 for name,n,net,t in pins:w.writerow(['U5',n,name,net or 'NC',t])
print('Generated modern schematic and matching local library; netlist must be exported by KiCad.')

(P/"dmx-interface.kicad_pro").write_text('{"meta":{"filename":"dmx-interface.kicad_pro","version":1}}\n')
