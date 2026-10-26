"""Standalone prototype capture. No parent import or writes."""
from pathlib import Path
import json,uuid,csv
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v));uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-axial-routing/'+v))
effect='(effects (font (size .8 .8)))';lib={};parts=[];meta={}
def symbol(name,pins):
 h=(len(pins)+1)*1.27
 lib[name]=([(str(no),pn,-15.24,h-(i+1)*2.54,t) for i,(no,pn,t) in enumerate(pins)],h)
symbol('TPS63070',[(1,'PS_SYNC_LOW_FORCED_PWM','input'),(2,'PG','open_collector'),(3,'VAUX_NO_EXTERNAL_LOAD','power_out'),(4,'GND','power_in'),(5,'FB','input'),(6,'FB2_UNUSED','open_collector'),(7,'VOUT','power_out'),(8,'VOUT','passive'),(9,'L2','passive'),(10,'PGND','power_in'),(11,'L1','passive'),(12,'VIN','power_in'),(13,'VIN','passive'),(14,'EN','input'),(15,'VSEL_LOW','input')])
symbol('TPS259474',[(1,'EN_UVLO','input'),(2,'OVLO','input'),(3,'PG_UNUSED','open_collector'),(4,'PGTH_UNUSED','input'),(5,'IN','power_in'),(6,'OUT','power_out'),(7,'DVDT','input'),(8,'GND','power_in'),(9,'ILM','input'),(10,'ITIMER_OPEN_FASTEST','input')])
symbol('TPS25810',[(1,'FAULT_N','open_collector'),(2,'IN1','power_in'),(3,'IN1','passive'),(4,'IN2','power_in'),(5,'AUX','power_in'),(6,'EN','input'),(7,'CHG_HIGH','input'),(8,'CHG_HI_LOW','input'),(9,'REF_RTN','passive'),(10,'REF','passive'),(11,'CC1','bidirectional'),(12,'GND','power_in'),(13,'CC2','bidirectional'),(14,'OUT','power_out'),(15,'OUT','passive'),(16,'DEBUG_N_UNUSED','open_collector'),(17,'AUDIO_N_UNUSED','open_collector'),(18,'POL_N_UNUSED','open_collector'),(19,'UFP_N_UNUSED','open_collector'),(20,'LD_DET_UNUSED','open_collector'),(21,'EP_GND','power_in')])
usbpins=[('A1_B12','GND_shared_land'),('A4_B9','VBUS_shared_land'),('B8','SBU2_NC'),('A5','CC1'),('B7','D_MINUS'),('A6','D_PLUS'),('A7','D_MINUS'),('B6','D_PLUS'),('A8','SBU1_NC'),('B5','CC2'),('B4_A9','VBUS_shared_land'),('B1_A12','GND_shared_land')]
symbol('USB4105',[(n,f,'passive') for n,f in usbpins]+[(f'S{i}','SHELL','passive') for i in range(1,5)])
for n in ['R','C','L','ESD']:symbol(n,[(1,'1','passive'),(2,'2','passive')])
symbol('TP',[(1,'FAULT_PROBE','passive')])
symbol('FPC_LANDS',[(1,'STATIONARY_IRM20_PLUS_VIA_FPC','passive'),(2,'ISOLATED_RETURN_VIA_FPC','passive')])
lib['POWER_FLAG']=([('1','ACTUAL_EXTERNAL_SOURCE',0,0,'power_out')],0)
def add(name,ref,value,nets,footprint,role):
 i=len(parts);x=55.88+(i%6)*116.84;y=63.5+(i//6)*68.58
 parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y));meta[ref]={'kind':'flag' if ref.startswith('#') else 'land_only' if ref in ['J0','TP1'] else 'purchased','footprint':footprint,'role':role}
g='GND_ISO';raw='FPC_5V';vin='PROTECTED_IN';v='REG_5V136';out='USB_VBUS'
add('TPS259474','U1','TPS259474LRPWR',{1:'INPUT_UVLO',2:'INPUT_OVLO',3:None,4:g,5:raw,6:vin,7:'INPUT_DVDT',8:g,9:'INPUT_ILM',10:None},'RPW10','True reverse blocking, latched circuitbreaker; not instantaneous current limiter')
add('TPS63070','U2','TPS63070RNMR',{1:g,2:'REG_READY_OD',3:'REG_VAUX',4:g,5:'REG_FB',6:None,7:v,8:v,9:'SW_L2',10:g,11:'SW_L1',12:vin,13:vin,14:'REG_EN_SERIES',15:g},'RNM15','ForcedPWM5.136V; startup unloaded until PG enables U3')
add('TPS25810','U3','TPS25810RVCR',{1:'PORT_FAULT_OD',2:v,3:v,4:v,5:v,6:'REG_READY_OD',7:v,8:g,9:'REF_RTN',10:'REF',11:'USB_CC1',12:g,13:'USB_CC2',14:out,15:out,16:None,17:None,18:None,19:None,20:None,21:g},'RVC20','1.5A Rp/currentlimit, CC orientation, VCONN and detach discharge')
add('USB4105','J1','USB4105-GF-A',{n:(g if n.startswith('S') or n in ['A1_B12','B1_A12'] else out if n in ['A4_B9','B4_A9'] else 'USB_CC1' if n=='A5' else 'USB_CC2' if n=='B5' else 'USB_D_SHORT' if n in ['A6','A7','B6','B7'] else None) for n in [a for a,b in usbpins]+['S1','S2','S3','S4']},'USB4105','16 contacts /12 shared electrical lands +4 shellstakes, actual primaryB4 drawing')
add('FPC_LANDS','J0','FABRICATED_FPC20_SOLDER_LANDS',{1:raw,2:g},'FPC20','20mm ribbon direct solder lands, supplier/process unqualified, external clamp required')
def two(name,ref,value,a,b,fp,role):add(name,ref,value,{1:a,2:b},fp,role)
two('L','L1','XFL4020-152MEC 1.5uH','SW_L1','SW_L2','XFL4020','Exact TI typical application magnetics, NRND sourcing gate')
two('ESD','D1','TPD1E10B06DPYR',out,g,'DPY2','VBUS IEC transient suppressor; not DC overvoltage protection')
for ref,ohm,a,b,role in [('R1',24900,raw,'INPUT_UVLO','UVLO top'),('R2',10000,'INPUT_UVLO',g,'UVLO bottom'),('R3',37400,raw,'INPUT_OVLO','OVLO top'),('R4',10000,'INPUT_OVLO',g,'OVLO bottom'),('R5',1000,'INPUT_ILM',g,'3.334A nominal breaker, +/-10% plus resistor tolerance'),('R6',54200,v,'REG_FB','Reg top0.1%10ppm'),('R7',10000,'REG_FB',g,'Reg bottom0.1%10ppm'),('R8',100000,v,'REG_READY_OD','PG and U3 EN pullup'),('R9',100000,'REG_READY_OD',g,'U3 EN default pulldown'),('R10',100000,'REF','REF_RTN','Controller precision reference, return NOT ground')]:
 code={24900:'24K9',10000:'10K0',37400:'37K4',1000:'1K00',54200:'54K2',100000:'100K',1000000:'1M00'}[ohm]
 two('R',ref,'TNPW0402'+code+'BYED '+str(ohm)+'ohm',a,b,'R0402',role)
for ref,value,a,fp,role in [('C1','GRM21BC71E106ME11L 10uF',vin,'C0805','Reg input'),('C2','GRM21BC71E106ME11L 10uF',vin,'C0805','Reg input'),('C3','TMK107BBJ106MA-T 10uF',vin,'C0603','Reg close input'),('C4','GRM21BC81C226ME44L 22uF',v,'C0805','Reg output'),('C5','GRM21BC81C226ME44L 22uF',v,'C0805','Reg output'),('C6','GRM21BC81C226ME44L 22uF',v,'C0805','Reg output'),('C7','TMK107BBJ106MA-T 10uF',v,'C0603','Reg close output'),('C8','T520D157M010ATE055 150uF',v,'T520D','Positive pad1;120uF min25C bulk before cold-socket switch'),('C9','GRM21BC71E106ME11L 10uF',out,'C0805','Port output bypass'),('C10','TMK105B7104MV-FR 100nF',v,'C0402','U3 close bypass'),('C11','TMK105B7104MV-FR 100nF','REG_VAUX','C0402','Do not load VAUX'),('C12','GRM155R71E103KA01D 10nF','INPUT_DVDT_C','C0402','Efuse slew setting; max inrush still bounded by physical circuit tests'),('C13','TMK105B7104MV-FR 100nF',raw,'C0402','FPC local bypass')]:
 two('C',ref,value,a,g,fp,role)
two('R','R13','TNPW0402100RBYED 100ohm','INPUT_DVDT','INPUT_DVDT_C','R0402','TI TPS25947 section7.3.5.1 series100ohm forCdVdt>10nF; C12max11nF')
two('R','R12','TNPW040210K0BYED 10000ohm',vin,'REG_EN_SERIES','R0402','TI TPS63070 section11.1 requires10k series whenEN tiedVIN')
two('R','R11','TNPW0402100KBYED 100000ohm',v,'PORT_FAULT_OD','R0402','Fault OD pullup, diagnostic only')
add('TP','TP1','FAB_FAULT_PROBE',{1:'PORT_FAULT_OD'},'TP1','Bare1mm fault probe; no MCU/software dependency')
for i,net in enumerate([raw,g],1):
 add('POWER_FLAG','#FLG'+str(i),'ACTUAL_EXTERNAL_SOURCE',{1:net},'','Isolated module/FPC input and return')
def definition(name):
 pins,h=lib[name]
 z=[f'(symbol {q(name)} (pin_names (offset .508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 {h+2.54} 0) {effect}) (property "Value" {q(name)} (at 0 {-h-2.54} 0) {effect})',f'(symbol {q(name+"_0_1")} (rectangle (start -12.7 {h}) (end 15.24 {-h}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol {q(name+"_1_1")}']
 for no,pn,x,y,typ in pins:z.append(f'(pin {typ} line (at {x} {y} 0) (length 2.54) (name {q(pn)} {effect}) (number {q(no)} {effect}))')
 return ''.join(z)+'))'
root=uid('root');lines=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A1") (title_block (title "NOVA rotating regulated 5V 1.5A source prototype") (rev "AX-1")) (lib_symbols']
for name in lib:lines.append(definition(name).replace('(symbol '+q(name)+' ','(symbol '+q('RS:'+name)+' ',1))
lines.append(')')
for name,ref,value,nets,x,y in parts:
 pins,h=lib[name];m=meta[ref];physical=m['kind'] not in ['boundary','flag']
 lines.append(f'(symbol (lib_id "RS:{name}") (at {x} {y} 0) (unit 1) (in_bom {"yes" if physical else "no"}) (on_board {"yes" if physical else "no"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-3.81} 0) {effect}) (property "Value" {q(value)} (at {x} {y+h+3.81} 0) {effect}) (property "Role" {q(m["role"])} (at {x} {y} 0) (effects (font (size .7 .7)) hide)) (property "Scope" {q(m["kind"])} (at {x} {y} 0) (effects (font (size .7 .7)) hide))')
 if physical:lines.append(f'(property "Footprint" "RS:{m["footprint"]}" (at {x} {y} 0) (effects (font (size 1 1)) hide))')
 for no,_,_,_,_ in pins:lines.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
 lines.append(f'(instances (project "regulated-source" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
 for no,pn,px,py,typ in pins:
  xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
  if net is None:lines.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
  end=round(xx-5.08,4)
  lines.append(f'(wire (pts (xy {xx} {yy}) (xy {end} {yy})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
  lines.append(f'(label {q(net)} (at {end} {yy} 0) {effect} (uuid "{uid(ref+no+"net")}"))')
notes=['PROTOTYPE: stationaryIRM20-5/FPC input only. No mains/PE or module circuitry captured here. All physical source board parts shown.',
 'U1 reverse-blocking input, UVLO/OVLO and latched circuit-breaker. U2 forcedPWM5.136V, PG enables U3 after unloaded startup; no firmware.',
 'U3 CHG=REG5V, CHG_HI=GND:1.5A only. CC1/CC2 independent. No USBdata processing or PD voltage escalation.',
 'J1 has16 contacts but12 shared signal lands +4shell stakes, per originalGCTB4. D+ and D- tied by copper; no invented separate ground/VBUS pads.',
 'Bulk150uF+76uFceramic before cold socket switch. ESR/capacitance attemperature, startup/inrush/thermal/ripple/faults remain physical gates.',
 'Shell tiedisolatedGND proposal. No rotatingPE; accessiblemetal bonding/mainsendcap/harness/safety remain parent scope.',
 'R12=10k EN series perTI11.1; R13=100ohm DVDT series perTI7.3.5.1, C12max11nF. Connector maxheight3.46mm; no fit/release claim.']
for i,n in enumerate(notes):lines.append(f'(text {q(n)} (at 20.32 {490+i*5} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid("note"+str(i))}"))')
lines.append(')');(P/'regulated-source.kicad_sch').write_text('\n'.join(lines)+'\n')
(P/'regulated-source.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in lib)+'\n)\n')
(P/'regulated-source.kicad_pro').write_text('{"meta":{"version":1}}\n')
for filename,kind in [('sym-lib-table','KiCad'),('fp-lib-table','KiCad')]:
 isfp=filename.startswith('fp');tag='fp_lib_table' if isfp else 'sym_lib_table';dest='Regulated.pretty' if isfp else 'regulated-source.kicad_sym'
 (P/filename).write_text(f'({tag} (version 7) (lib (name "RS") (type "{kind}") (uri "${{KIPRJMOD}}/{dest}") (options "") (descr "Source-based rotating prototype")))\n')
with (P/'component-ledger.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['reference','value','kind','footprint','role'])
 for name,ref,value,nets,x,y in parts:w.writerow([ref,value,meta[ref]['kind'],meta[ref]['footprint'],meta[ref]['role']])
print('Purchased',sum(x['kind']=='purchased' for x in meta.values()),'plus actualFPCfabricatedlands')
