"""Editable recovery-only candidate. Never fabricates CLI netlists/ERC.
Not the complete product power circuit: see ../POWER-DESIGN-OBJECTION.md.
"""
from pathlib import Path
import uuid,json
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v))
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-recovery-candidate/'+v))
e='(effects (font (size 1 1)))'
lib={};parts=[]
def ic(name,pins):
    # Actual pin numbers/types. Switching/analogue programming outputs remain outputs.
    n=len(pins);h=(n+1)*1.27
    geom=[(pn,str(no),-15.24,h-(i+1)*2.54,0,t) for i,(no,pn,t) in enumerate(pins)]
    lib[name]=(geom,15.24,h)
def part(name,ref,value,nets,x,y):parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y))
ic('TPS22950YBH',[('A1','ON','input'),('A2','FLT_N','open_collector'),('B1','VIN','power_in'),('B2','VOUT','power_out'),('C1','GND','power_in'),('C2','ILIM','output')])
ic('TPS2553DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'FAULT_N','open_collector'),(5,'ILIM','output'),(6,'OUT','power_out')])
ic('TPS70933DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'NC','no_connect'),(5,'OUT','power_out')])
ic('CP2102N_A02_GQFN20',[(1,'GPIO1','bidirectional'),(2,'GPIO0','bidirectional'),(3,'GND','power_in'),(4,'D+','bidirectional'),(5,'D-','bidirectional'),(6,'VDD_EXTERNAL_REG_MODE','power_in'),(7,'VREGIN','power_in'),(8,'VBUS','input'),(9,'RSTb','open_collector'),(10,'NC','no_connect'),(11,'SUSPENDb','output'),(12,'GND','power_in'),(13,'WAKEUP','input'),(14,'SUSPEND','output'),(15,'CTS','input'),(16,'RTS','output'),(17,'RXD','input'),(18,'TXD','output'),(19,'GPIO3','bidirectional'),(20,'GPIO2','bidirectional'),(21,'EP_GND','power_in')])
ic('SN74LVC2G08DCU',[(1,'1A','input'),(2,'1B','input'),(3,'2Y','output'),(4,'GND','power_in'),(5,'2A','input'),(6,'2B','input'),(7,'1Y','output'),(8,'VCC','power_in')])
ic('SN74LVC1G125DCK',[(1,'OE_N','input'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','tri_state'),(5,'VCC','power_in')])
ic('USB2_TEST_BOUNDARY',[(1,'VBUS_4V4_TO_5V5','power_out'),(2,'GND_USB','power_out'),(3,'D+','bidirectional'),(4,'D-','bidirectional')])
ic('MCU_BOUNDARY_NOT_POWER_MERGER',[(1,'REC_3V3_OUT','power_in'),(2,'GND_USB','power_in'),(3,'UART_TX_FROM_MCU','output'),(4,'UART_RX_TO_MCU','input'),(5,'ACTUAL_MCU_SUPPLY','power_out')])
for name in ['R','C','SW_NO']:
    lib[name]=([('1','1',0,5.08,270,'passive'),('2','2',0,-5.08,90,'passive')],1.27,2.54)
G='GND_USB'
part('USB2_TEST_BOUNDARY','J101','USB2 INPUT BOUNDARY / CC NOT CAPTURED',{1:'VBUS',2:G,3:'USB_DP',4:'USB_DM'},55.88,50.8)
part('TPS22950YBH','U101','TPS22950YBHR (NOT C/L)',{'A1':'VBUS','A2':None,'B1':'VBUS','B2':'BRIDGE_5V','C1':G,'C2':'BRIDGE_ILIM'},139.7,50.8)
part('TPS70933DBV','U102','TPS70933DBVR',{1:'BRIDGE_5V',2:G,3:'BRIDGE_5V',4:None,5:'BRIDGE_3V3'},228.6,50.8)
part('CP2102N_A02_GQFN20','U103','CP2102N-A02-GQFN20',dict(enumerate([None,None,G,'USB_DP','USB_DM','BRIDGE_3V3','BRIDGE_3V3','BRIDGE_3V3','BRIDGE_RST_N',None,'USB_ACTIVE',G,'BRIDGE_3V3',None,G,None,'BRIDGE_RX','BRIDGE_TX',None,None,G],1)),327.66,66.04)
part('TPS2553DBV','U104','TPS2553DBVR',{1:'VBUS',2:G,3:'REC_EN',4:None,5:'REC_ILIM',6:'REC_5V'},139.7,139.7)
part('TPS70933DBV','U105','TPS70933DBVR',{1:'REC_5V',2:G,3:'REC_EN',4:None,5:'REC_3V3'},228.6,139.7)
part('SN74LVC2G08DCU','U106','SN74LVC2G08DCUR',{1:'USB_ACTIVE',2:'REC_REQUEST',3:'REC_EN',4:G,5:'REC_INTENT',6:'CONFIG_VERIFIED',7:'REC_INTENT',8:'BRIDGE_3V3'},55.88,139.7)
part('SN74LVC1G125DCK','U107','SN74LVC1G125DCKR',{1:G,2:'MCU_TX',3:G,4:'BRIDGE_RX',5:'BRIDGE_3V3'},55.88,228.6)
part('SN74LVC1G125DCK','U108','SN74LVC1G125DCKR',{1:G,2:'BRIDGE_TX',3:G,4:'MCU_RX',5:'MCU_3V3'},139.7,228.6)
part('MCU_BOUNDARY_NOT_POWER_MERGER','J102','MCU DOMAIN CONTRACT / NO DIRECT RAIL JOIN',{1:'REC_3V3',2:G,3:'MCU_TX',4:'MCU_RX',5:'MCU_3V3'},228.6,228.6)
# Intentionally explicit user action. BOOT and RESET must be asserted by integration;
# this sheet does not falsely expose a manufactured GPIO assignment.
items=[('R','R101','19.2k 0.1%', 'BRIDGE_ILIM',G),('R','R102','88.7k 1%','REC_ILIM',G),('R','R103','10k','USB_ACTIVE',G),('R','R104','10k','REC_REQUEST',G),('R','R105','10k','REC_EN',G),('R','R106','1k','BRIDGE_3V3','BRIDGE_RST_N'),('R','R107','100k','MCU_TX',G),('R','R108','100k','BRIDGE_TX',G),('R','R109','100k','CONFIG_VERIFIED',G),('SW_NO','S102','FACTORY LINK OPEN / DNP','BRIDGE_3V3','CONFIG_VERIFIED'),('SW_NO','S101','RECOVERY REQUEST (HOLD)','BRIDGE_3V3','REC_REQUEST')]
for i,(name,ref,value,a,b) in enumerate(items):part(name,ref,value,{'1':a,'2':b},40.64+(i%5)*71.12,292.1+(i//5)*30.48)
cs=[('100n','VBUS'),('4.7u effective 10V','BRIDGE_5V'),('100n','BRIDGE_5V'),('4.7u effective 10V','BRIDGE_3V3'),('100n','BRIDGE_3V3'),('2.2u effective 10V','REC_5V'),('2.2u effective 10V','REC_3V3'),('100n','BRIDGE_3V3'),('100n','BRIDGE_3V3'),('100n','MCU_3V3')]
for i,(v,a) in enumerate(cs):part('C',f'C{101+i}',v,{1:a,2:G},40.64+(i%5)*71.12,396.24+(i//5)*30.48)
def definition(name):
    pins,w,h=lib[name]
    lines=[f'(symbol {q(name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 {h+2.54} 0) {e}) (property "Value" {q(name)} (at 0 {-h-2.54} 0) {e})',f'(symbol {q(name+"_0_1")} (rectangle (start {-w+2.54 if w>2 else -w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol {q(name+"_1_1")}']
    for pn,no,x,y,a,t in pins:lines.append(f'(pin {t} line (at {x} {y} {a}) (length 2.54) (name {q(pn)} {e}) (number {q(no)} {e}))')
    result=''.join(lines)+'))'
    if name in ('C','SW_NO'):
        # Replace only the graphic primitive, preserving the enclosing unit.
        old=f'(rectangle (start {-w+2.54 if w>2 else -w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background)))'
        segs=[((0,2.54),(0,.508)),((-1.524,.508),(1.524,.508)),((-1.524,-.508),(1.524,-.508)),((0,-.508),(0,-2.54))] if name=='C' else [((0,2.54),(0,1.27)),((0,1.27),(1.27,-1.27)),((0,-1.27),(0,-2.54))]
        draw=''.join(f'(polyline (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width .254) (type default)) (fill (type none)))' for a,b in segs)
        result=result.replace(old,draw)
    return result
root=uid('root');s=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A2" portrait) (title_block (title "NOVA USB recovery candidate - NOT integrated power circuit") (rev "B-EDA3-CANDIDATE")) (lib_symbols']
for n in lib:s.append(definition(n).replace('(symbol '+q(n)+' ','(symbol '+q('REC:'+n)+' ',1))
s.append(')')
for name,ref,value,nets,x,y in parts:
    pins,w,h=lib[name];s.append(f'(symbol (lib_id "REC:{name}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp {"yes" if ref=="S102" else "no"}) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-2.54} 0) {e}) (property "Value" {q(value)} (at {x} {y+h+2.54} 0) {e})')
    for pn,no,px,py,a,t in pins:s.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
    s.append(f'(instances (project "recovery-candidate" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
    for pn,no,px,py,a,t in pins:
        xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
        if net is None:s.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
        dx,dy={0:(-5.08,0),270:(0,-5.08),90:(0,5.08)}[a];ex,ey=round(xx+dx,4),round(yy+dy,4)
        s.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
        s.append(f'(label {q(net)} (at {ex} {ey} 0) {e} (uuid "{uid(ref+no+"l")}"))')
notes=['RECOVERY CANDIDATE ONLY: does NOT complete normal power, CC decode, cap charger, UVLO latch or rail merger.', 'U104 enable = request AND USB_ACTIVE AND CONFIG_VERIFIED. S102 ships OPEN/DNP pending qualification.', 'Required bridge descriptor: bus-powered, 500mA requested; programming/USB qualification NOT performed.', 'U107/U108 use receiving-domain supplies and Ioff. MCU_3V3 is actual MCU rail, NEVER assumed equal to REC_3V3.', 'Do not directly join REC_3V3 to buffered MCU power: reverse-blocking merger and BOOT/RESET sequencing remain open.', 'No RF/DMX/15F charging from this recovery branch. USB ESD, connector/CC and suspend maximum budget remain open.']
for i,n in enumerate(notes):s.append(f'(text {q(n)} (at 20.32 {474+i*7.62} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid("note"+str(i))}"))')
s.append(')');(P/'recovery-candidate.kicad_sch').write_text('\n'.join(s)+'\n')
(P/'recovery.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in lib)+'\n)\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "REC") (type "KiCad") (uri "${KIPRJMOD}/recovery.kicad_sym") (options "") (descr "Recovery candidate typed symbols")))\n')
(P/'recovery-candidate.kicad_pro').write_text('{"meta":{"filename":"recovery-candidate.kicad_pro","version":1}}\n')
print(f'Generated {len(parts)} components; run verify.py for real export.')
