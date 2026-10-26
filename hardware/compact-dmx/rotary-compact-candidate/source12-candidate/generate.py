"""One standalone hardware capture; all outputs stay beside this generator."""
from pathlib import Path
import json, uuid, csv
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v));uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-source12/'+v))
effect='(effects (font (size .8 .8)))';lib={};parts=[];meta={}
def symbol(name,pins):
 h=(len(pins)+1)*1.27
 lib[name]=([(str(no),pn,-15.24,h-(i+1)*2.54,t) for i,(no,pn,t) in enumerate(pins)],h)
symbol('TPS62135',[(1,'VIN','power_in'),(2,'SW','power_out'),(3,'GND_ACTUAL_POWER_BAR','power_in'),(4,'FB2_UNUSED','open_collector'),(5,'FB','input'),(6,'VOS_KELVIN_OUTPUT','input'),(7,'PG','open_collector'),(8,'EN','input'),(9,'SS_TR','input'),(10,'MODE_HIGH_FORCED_PWM','input'),(11,'VSEL_LOW','input')])
symbol('TPS259474',[(1,'EN_UVLO','input'),(2,'OVLO','input'),(3,'PG_UNUSED','open_collector'),(4,'PGTH_UNUSED','input'),(5,'IN','power_in'),(6,'OUT','power_out'),(7,'DVDT','input'),(8,'GND','power_in'),(9,'ILM','input'),(10,'ITIMER_OPEN_FASTEST','input')])
symbol('TPS25940',[(1,'DEVSLP_LOW','input'),(2,'PGOOD','open_collector'),(3,'PGTH','input')]+[(i,'OUT','power_out' if i==4 else 'passive') for i in range(4,9)]+[(i,'IN','power_in' if i==9 else 'passive') for i in range(9,14)]+[(14,'EN_UVLO','input'),(15,'OVP_BACKSTOP','input'),(16,'GND','power_in'),(17,'ILIM','input'),(18,'DVDT','input'),(19,'IMON_UNUSED','output'),(20,'FAULT_N','open_collector'),(21,'EP_GND','power_in')])
symbol('TPS3700_DDC',[(1,'OUTA_UV_ACTIVE_LOW','open_collector'),(2,'GND','power_in'),(3,'INA_PLUS','input'),(4,'INB_MINUS','input'),(5,'VDD_INDEPENDENT_12V','power_in'),(6,'OUTB_OV_ACTIVE_LOW','open_collector')])
symbol('TPS25810',[(1,'FAULT_N','open_collector'),(2,'IN1','power_in'),(3,'IN1','passive'),(4,'IN2','power_in'),(5,'AUX','power_in'),(6,'EN','input'),(7,'CHG_HIGH','input'),(8,'CHG_HI_LOW','input'),(9,'REF_RTN','passive'),(10,'REF','passive'),(11,'CC1','bidirectional'),(12,'GND','power_in'),(13,'CC2','bidirectional'),(14,'OUT','power_out'),(15,'OUT','passive'),(16,'DEBUG_N_UNUSED','open_collector'),(17,'AUDIO_N_UNUSED','open_collector'),(18,'POL_N_UNUSED','open_collector'),(19,'UFP_N_UNUSED','open_collector'),(20,'LD_DET_UNUSED','open_collector'),(21,'EP_GND','power_in')])
usbpins=[('A1_B12','GND_shared_land'),('A4_B9','VBUS_shared_land'),('B8','SBU2_NC'),('A5','CC1'),('B7','D_MINUS'),('A6','D_PLUS'),('A7','D_MINUS'),('B6','D_PLUS'),('A8','SBU1_NC'),('B5','CC2'),('B4_A9','VBUS_shared_land'),('B1_A12','GND_shared_land')]
symbol('USB4105',[(n,f,'passive') for n,f in usbpins]+[(f'S{i}','SHELL','passive') for i in range(1,5)])
for n in ['R','C','L','ESD']:symbol(n,[(1,'1','passive'),(2,'2','passive')])
symbol('TP',[(1,'DIAGNOSTIC_ONLY','passive')]);symbol('PAIR',[(1,'ISOLATED_PLUS','passive'),(2,'ISOLATED_RETURN','passive')])
lib['POWER_FLAG']=([('1','ACTUAL_POWER_SOURCE',0,0,'power_out')],0)
def add(name,ref,value,nets,footprint,role,zone='rotating'):
 i=len(parts);x=55.88+(i%8)*132.08;y=63.5+(i//8)*83.82
 parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y))
 meta[ref]={'kind':'flag' if ref.startswith('#') else 'land_only' if ref in ['J0','J2','J3','TP1','TP2'] else 'purchased','footprint':footprint,'role':role,'zone':zone}
g='GND_ISO';raw='MODULE12_UNPROTECTED';vin='FPC12_PROTECTED';v='BUCK5_18';safe='SAFE5_18';out='USB_VBUS'
add('TPS259474','U1','TPS259474LRPWR',{1:'SOURCE_UVLO',2:'SOURCE_OVLO',3:None,4:g,5:raw,6:vin,7:'SOURCE_DVDT',8:g,9:'SOURCE_ILM',10:None},'RPW10','Stationary: reverse-blocking latched breaker BEFORE flex; finite response, not instantaneous limiter','stationary')
add('TPS62135','U2','TPS62135RGXR',{1:vin,2:'SW',3:g,4:None,5:'REG_FB',6:v,7:'PORT_ENABLE',8:'REG_EN',9:'REG_SS',10:vin,11:g},'RGX11','4A buck, forcedPWM,5.18V; MODE high and VSEL low')
add('TPS25810','U3','TPS25810RVCR',{1:'PORT_FAULT_N',2:safe,3:safe,4:safe,5:safe,6:'PORT_ENABLE',7:safe,8:g,9:'REF_RTN',10:'REF',11:'USB_CC1',12:g,13:'USB_CC2',14:out,15:out,16:None,17:None,18:None,19:None,20:None,21:g},'RVC20','5V1.5A CC advertisement; no firmware, data or higherPD')
add('TPS25940','U4','TPS25940LRVCR',{1:g,2:'PORT_ENABLE',3:'SAFE_PGTH',**{i:safe for i in range(4,9)},**{i:v for i in range(9,14)},14:'BARRIER_EN',15:'BACKSTOP_OVP',16:g,17:'BARRIER_ILIM',18:'BARRIER_DVDT',19:None,20:'PROTECT_FAULT_N',21:g},'RVC20','Independent reverse-blocking output disconnector; thermal latch; OVP recovery is NOT latched')
add('TPS3700_DDC','U5','TPS3700DDCR',{1:'BARRIER_EN',2:g,3:'BUCK_UV_SENSE',4:'BUCK_OV_SENSE',5:vin,6:'BARRIER_EN'},'DDC6','Independent12V-powered4.8..5.4V window; wire-AND outputs control U4EN')
add('USB4105','J1','USB4105-GF-A',{n:(g if n.startswith('S') or n in ['A1_B12','B1_A12'] else out if n in ['A4_B9','B4_A9'] else 'USB_CC1' if n=='A5' else 'USB_CC2' if n=='B5' else 'USB_D_SHORT' if n in ['A6','A7','B6','B7'] else None) for n in [a for a,b in usbpins]+['S1','S2','S3','S4']},'USB4105','Actual16contacts/12signal lands plus4shellstakes')
add('PAIR','J0','FAB_SOURCE12_WIRE_LANDS',{1:raw,2:g},'Wire2','Stationary isolated module12V lead termination; primary/mains NOT present','stationary')
add('PAIR','J2','FAB_FPC20_STATIONARY',{1:vin,2:g},'FPC20','Stationary flex clamp/coverlay/strain relief external; no connector invented','stationary')
add('PAIR','J3','FAB_FPC20_ROTATING',{1:vin,2:g},'FPC20','Rotating end of SAME external finite-resistance20mm FPC')
def two(name,ref,value,a,b,fp,role,zone='rotating'):add(name,ref,value,{1:a,2:b},fp,role,zone)
two('L','L1','XAL4020-152MEC 1.5uH','SW',v,'XAL4020','TI supported1.5uH option; maxDCR23.6mohm25C, current/thermal derating gate')
two('ESD','D1','TPD1E10B06DPYR',out,g,'DPY2','ESD suppression only; NOT DC overvoltage clamp')
res=[('R1',68100,raw,'SOURCE_UVLO','stationary'),('R2',10000,'SOURCE_UVLO',g,'stationary'),('R3',100000,raw,'SOURCE_OVLO','stationary'),('R4',9090,'SOURCE_OVLO',g,'stationary'),('R5',2000,'SOURCE_ILM',g,'stationary'),('R6',100,'SOURCE_DVDT','SOURCE_DVDT_C','stationary'),('R7',64000,v,'REG_FB','rotating'),('R8',10000,'REG_FB',g,'rotating'),('R9',100000,vin,'REG_EN','rotating'),('R10',10000,'REG_EN',g,'rotating'),('R11',100000,v,'BUCK_UV_SENSE','rotating'),('R12',9090,'BUCK_UV_SENSE',g,'rotating'),('R13',100000,v,'BUCK_OV_SENSE','rotating'),('R14',8000,'BUCK_OV_SENSE',g,'rotating'),('R15',100000,v,'BARRIER_EN','rotating'),('R16',100000,'BARRIER_EN',g,'rotating'),('R17',100000,v,'BACKSTOP_OVP','rotating'),('R18',20000,'BACKSTOP_OVP',g,'rotating'),('R19',24900,'BARRIER_ILIM',g,'rotating'),('R20',37400,safe,'SAFE_PGTH','rotating'),('R21',10000,'SAFE_PGTH',g,'rotating'),('R22',100000,safe,'PORT_ENABLE','rotating'),('R23',100000,'PORT_ENABLE',g,'rotating'),('R24',100000,'REF','REF_RTN','rotating'),('R25',100000,safe,'PORT_FAULT_N','rotating'),('R26',100000,safe,'PROTECT_FAULT_N','rotating'),('R27',10000,safe,g,'rotating')]
codes={100:'100R',2000:'2K00',8000:'8K00',9090:'9K09',10000:'10K0',20000:'20K0',24900:'24K9',37400:'37K4',64000:'64K0',68100:'68K1',100000:'100K'}
for ref,ohm,a,b,zone in res:two('R',ref,'TNPW0402'+codes[ohm]+'BYED '+str(ohm)+'ohm',a,b,'R0402','0.1%10ppm; independent checker includes±0.2% allocation',zone)
caps=[('C1','MSAST21GBB5106MTNA01 10uF',raw,'C0805','stationary'),('C2','MSAST21GBB5106MTNA01 10uF',vin,'C0805','rotating'),('C3','MSAST21GBB5106MTNA01 10uF',vin,'C0805','rotating'),('C4','MSASE21GBB5226MTNA01 22uF',v,'C0805','rotating'),('C5','MSASE21GBB5226MTNA01 22uF',v,'C0805','rotating'),('C6','T520D157M010ATE055 150uF',safe,'T520D','rotating'),('C7','MSAST21GBB5106MTNA01 10uF',out,'C0805','rotating'),('C8','TMK105B7104MV-FR 100nF',safe,'C0402','rotating'),('C9','TMK105B7104MV-FR 100nF',vin,'C0402','rotating'),('C10','GRM155R71E103KA01D 10nF','REG_SS','C0402','rotating'),('C11','GRM155R71E103KA01D 10nF','SOURCE_DVDT_C','C0402','stationary'),('C12','GRM155R71E103KA01D 10nF','BARRIER_DVDT','C0402','rotating'),('C13','GRM155R71E103KA01D 10nF','BARRIER_DVDT','C0402','rotating'),('C14','TMK105B7104MV-FR 100nF',raw,'C0402','stationary'),('C15','TMK105B7104MV-FR 100nF',vin,'C0402','rotating'),('C16','TMK105B7104MV-FR 100nF',v,'C0402','rotating'),('C17','TMK105B7104MV-FR 100nF',safe,'C0402','rotating')]
for ref,value,a,fp,zone in caps:two('C',ref,value,a,g,fp,'Exact prototype MPN; bias/temperature/ESR/lifecycle gates in DESIGN',zone)
add('TP','TP1','FAB_PORT_FAULT_PROBE',{1:'PORT_FAULT_N'},'TP1','Diagnostic only; no MCU interface')
add('TP','TP2','FAB_PROTECT_FAULT_PROBE',{1:'PROTECT_FAULT_N'},'TP1','Diagnostic only; no qualified source-good signal')
for i,net in enumerate([raw,g,v],1):add('POWER_FLAG','#FLG'+str(i),'ACTUAL_POWER_SOURCE',{1:net},'','External source/return or real SW-L1 conversion path')

def definition(name):
 pins,h=lib[name]
 z=[f'(symbol {q(name)} (pin_names (offset .508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 {h+2.54} 0) {effect}) (property "Value" {q(name)} (at 0 {-h-2.54} 0) {effect})',f'(symbol {q(name+"_0_1")} (rectangle (start -12.7 {h}) (end 15.24 {-h}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol {q(name+"_1_1")}']
 for no,pn,x,y,typ in pins:z.append(f'(pin {typ} line (at {x} {y} 0) (length 2.54) (name {q(pn)} {effect}) (number {q(no)} {effect}))')
 return ''.join(z)+'))'
root=uid('root');lines=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A0") (title_block (title "NOVA 12V internal bus / independently protected 5V USB prototype") (rev "S12-R1")) (lib_symbols']
for name in lib:lines.append(definition(name).replace('(symbol '+q(name)+' ','(symbol '+q('S12:'+name)+' ',1))
lines.append(')')
for name,ref,value,nets,x,y in parts:
 pins,h=lib[name];m=meta[ref];physical=m['kind'] not in ['boundary','flag']
 lines.append(f'(symbol (lib_id "S12:{name}") (at {x} {y} 0) (unit 1) (in_bom {"yes" if physical else "no"}) (on_board {"yes" if physical else "no"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-3.81} 0) {effect}) (property "Value" {q(value)} (at {x} {y+h+3.81} 0) {effect}) (property "Role" {q(m["role"])} (at {x} {y} 0) (effects (font (size .7 .7)) hide)) (property "Scope" {q(m["kind"])} (at {x} {y} 0) (effects (font (size .7 .7)) hide))')
 if physical:lines.append(f'(property "Footprint" "S12:{m["footprint"]}" (at {x} {y} 0) (effects (font (size 1 1)) hide))')
 for no,_,_,_,_ in pins:lines.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
 lines.append(f'(instances (project "source12" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
 for no,pn,px,py,typ in pins:
  xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
  if net is None:lines.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
  end=round(xx-5.08,4)
  lines.append(f'(wire (pts (xy {xx} {yy}) (xy {end} {yy})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
  lines.append(f'(label {q(net)} (at {end} {yy} 0) {effect} (uuid "{uid(ref+no+"net")}"))')
notes=[
 'PROTOTYPE / NOT A RELEASE: only isolated12V is shown; no mains wiring. Stationary U1 protects the FPC before the rotary joint.',
 'Rotating U2 TPS62135:4A forcedPWM5.18V. U5 senses unprotected buck voltage; independent U4 disconnects and reverse-blocks before U3.',
 'U5 OUTA+OUTB are wired open-drain AND to U4 EN. No MCU/firmware/PG substitutes for independent voltage sensing.',
 'U4 internal OVP is a higher backstop, not the precision5.4V trip. Response/injected energy and power-ramp extremes remain UNMET.',
 'U3 CHG=SAFE5, CHG_HI=GND:1.5A only. Both CC orientations. Fullcontact GCT USB4105, fourD contacts passive short. No USBdata or higherPD.',
 'FPC ports J2/J3 are actual direct-solder lands on two boards plus an external20mm harness. Their finite resistance is independently budgeted.',
 'Input flag = isolated source atJ0; BUCK flag = actual U2.SW-L1 conversion path; GND flag = external isolated return. No other power flags.',
 'Proposed shell = isolatedGND, never rotatingPE. Mains/module/pod/PE/endcaps are external unqualified integration contracts.',
 'Unrouted placement allocation only. Connector3.46mm max height, clamp/flex reserves and routing/thermal/USB/safety gates remain open.'
]
for i,n in enumerate(notes):lines.append(f'(text {q(n)} (at 20.32 {755+i*5} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid("note"+str(i))}"))')
lines.append(')');(P/'source12.kicad_sch').write_text('\n'.join(lines)+'\n')
(P/'source12.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in lib)+'\n)\n')
(P/'source12.kicad_pro').write_text('{"meta":{"version":1}}\n')
for filename,kind in [('sym-lib-table','KiCad'),('fp-lib-table','KiCad')]:
 isfp=filename.startswith('fp');tag='fp_lib_table' if isfp else 'sym_lib_table';dest='Source12.pretty' if isfp else 'source12.kicad_sym'
 (P/filename).write_text(f'({tag} (version 7) (lib (name "S12") (type "{kind}") (uri "${{KIPRJMOD}}/{dest}") (options "") (descr "Source-based rotating prototype")))\n')
with (P/'component-ledger.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['reference','value','kind','footprint','role','zone'])
 for name,ref,value,nets,x,y in parts:w.writerow([ref,value,meta[ref]['kind'],meta[ref]['footprint'],meta[ref]['role'],meta[ref]['zone']])
print('Purchased',sum(x['kind']=='purchased' for x in meta.values()),'plus actualFPCfabricatedlands')
