"""Current power-only hardware capture; MCU/RF and isolated DMX are explicit interfaces.
No resident-loader implementation or hardware qualification is claimed.
"""
from pathlib import Path
import uuid,json
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v))
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-power-service/'+v))
e='(effects (font (size 1 1)))'
lib={};parts=[]
def ic(name,pins):
    # Actual pin numbers/types. Switching/analogue programming outputs remain outputs.
    n=len(pins);h=(n+1)*1.27
    geom=[(pn,str(no),-15.24,h-(i+1)*2.54,0,t) for i,(no,pn,t) in enumerate(pins)]
    lib[name]=(geom,15.24,h)
def part(name,ref,value,nets,x,y):parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y))
G='GND_USB'
ic('TPS2553DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'FAULT_N','open_collector'),(5,'ILIM','output'),(6,'OUT','power_out')])
ic('TPS61094DSS',[(1,'OSEL','input'),(2,'MODE','input'),(3,'EN','input'),(4,'VIN','power_in'),(5,'SW','power_out'),(6,'SUP','input'),(7,'PGND','power_in'),(8,'AGND','power_in'),(9,'VOUT','power_out'),(10,'VOUT','passive'),(11,'ICHG','input'),(12,'VCHG','input'),(13,'EP_GND','power_in')])
ic('TPS62132RGT',[(1,'SW','power_out'),(2,'SW','passive'),(3,'SW','passive'),(4,'PG','open_collector'),(5,'FB','input'),(6,'AGND','power_in'),(7,'FSW','input'),(8,'DEF','input'),(9,'SS_TR','input'),(10,'AVIN','power_in'),(11,'PVIN','power_in'),(12,'PVIN','power_in'),(13,'EN','input'),(14,'VOS','input'),(15,'PGND','power_in'),(16,'PGND','power_in'),(17,'EP_GND','power_in')])
ic('TPS7A0225DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'NC','no_connect'),(5,'OUT','power_out')])
ic('TLV3012BDCK',[(1,'OUT','output'),(2,'V_MINUS','power_in'),(3,'IN_PLUS','input'),(4,'IN_MINUS','input'),(5,'REF','output'),(6,'V_PLUS','power_in')])
ic('TPS3700DDC',[(1,'OUTA','open_collector'),(2,'GND','power_in'),(3,'INA_PLUS','input'),(4,'INB_MINUS','input'),(5,'VDD','power_in'),(6,'OUTB','open_collector')])
ic('TPS2116DRL',[(1,'GND','power_in'),(2,'VOUT','power_out'),(3,'VIN1','power_in'),(4,'PR1','input'),(5,'MODE','input'),(6,'VIN2','power_in'),(7,'VOUT','passive'),(8,'ST','open_collector')])
ic('TPS3839DBZ',[(1,'GND','power_in'),(2,'RESET_N','output'),(3,'VDD','power_in')])
ic('TPS3831DQN',[(1,'RESET_N','output'),(2,'MR_N','input'),(3,'GND','power_in'),(4,'VDD','power_in'),(5,'EP','passive')])
ic('SN74LVC1G74DCU',[(1,'CLK','input'),(2,'D','input'),(3,'Q_N','output'),(4,'GND','power_in'),(5,'Q','output'),(6,'CLR_N','input'),(7,'PRE_N','input'),(8,'VCC','power_in')])
for n in ['SN74LVC2G08DCU','SN74LVC2G32DCU']:ic(n,[(1,'1A','input'),(2,'1B','input'),(3,'2Y','output'),(4,'GND','power_in'),(5,'2A','input'),(6,'2B','input'),(7,'1Y','output'),(8,'VCC','power_in')])
ic('SN74LVC1G04DCK',[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')])
ic('AT25SF161B_MHB',[(1,'CS_N','input'),(2,'SO','tri_state'),(3,'WP_N','input'),(4,'GND','power_in'),(5,'SI','input'),(6,'SCK','input'),(7,'HOLD_N','input'),(8,'VCC','power_in'),(9,'EP_NOT_ELECTRICALLY_CONNECTED','passive')])
usb=[]
for side in ['A','B']:
 for i in range(1,13):
  name='GND' if i in (1,12) else 'VBUS' if i in (4,9) else 'CC'+('1' if side=='A' else '2') if i==5 else 'UNUSED_DATA'
  usb.append((side+str(i),name,'power_out' if side=='A' and i in (1,4) else 'passive'))
ic('USB_C_POWER_ONLY_BOUNDARY',usb)
mcunames=[('SYS_3V3','power_in'),(G,'power_in'),('MCU_DMX_TX','output'),('MCU_DMX_RX','input'),('MCU_DE_REQUEST','output'),('MCU_RE_N','output'),('MCU_ISO_REQUEST','output'),('SPI_CS_N','output'),('SPI_MOSI','output'),('SPI_SCK','output'),('SPI_MISO','input'),('VBUS_GOOD_3V3','input'),('SERVICE_N_DISTINCT_GPIO','input'),('ROM_BOOT_STRAP','input'),('RESET_OK','input'),('TMSC','bidirectional'),('TCKC','input'),('BUCK_PG','input')]
ic('CC1352_MCU_RF_BOUNDARY',[(i+1,n,t) for i,(n,t) in enumerate(mcunames)])
dmxnames=['SYS_3V3',G,'MCU_DMX_TX','DMX_DE_SAFE','MCU_RE_N','MCU_DMX_RX','DMX_POWER_EN']
ic('ISOW1412_SHEET_BOUNDARY',[(i+1,n,'power_in' if i<2 else 'output' if i==5 else 'input') for i,n in enumerate(dmxnames)])
ic('FACTORY_PADS',[(i+1,n,'passive') for i,n in enumerate(['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])])
for name in ['R','C','L','D','SW_NO']:
 lib[name]=([('K' if name=='D' else '1','1',0,5.08,270,'passive'),('A' if name=='D' else '2','2',0,-5.08,90,'passive')],1.27,2.54)
lib['DERIVED_POWER'] = ([('PWR','1',0,-5.08,90,'power_out')],2.54,2.54)
# Fixed IC coordinates. Actual named pins, not signal boxes masquerading as ICs.
part('USB_C_POWER_ONLY_BOUNDARY','J_USB','CX70M-24P1 electrical interface; shell/ESD integration open',{no:G if pn=='GND' else 'VBUS_RAW' if pn=='VBUS' else pn if pn.startswith('CC') else None for no,pn,t in usb},55.88,66.04)
part('TPS2553DBV','U6','TPS2553DBVR',{1:'VBUS_RAW',2:G,3:'VBUS_RAW',4:'INPUT_FAULT_N',5:'ILIM_SET',6:'LIMITED_5V'},157.48,66.04)
part('TPS61094DSS','U3','TPS61094DSSR',{1:'OSEL_SET',2:'AON_RAW',3:'RUN',4:'NORMAL_IN',5:'BOOST_SW',6:'CAP_POS',7:G,8:G,9:'BACKUP_RAW',10:'BACKUP_RAW',11:'ICHG_SET',12:'VCHG_SET',13:G},259.08,66.04)
part('TPS62132RGT','U4','TPS62132RGTR',{1:'BUCK_SW',2:'BUCK_SW',3:'BUCK_SW',4:'BUCK_PG',5:G,6:G,7:G,8:G,9:'BUCK_SS',10:'BACKUP_RAW',11:'BACKUP_RAW',12:'BACKUP_RAW',13:'RUN',14:'SYS_3V3',15:G,16:G,17:G},360.68,66.04)
part('TPS7A0225DBV','U7','TPS7A0225PDBVR',{1:'AON_RAW',2:G,3:'AON_RAW',4:None,5:'AON_2V5'},462.28,66.04)
part('TLV3012BDCK','U8','TLV3012BIDCKR',{1:'CAP_OK',2:G,3:'CAP_SENSE',4:'CAP_REF',5:'CAP_REF',6:'AON_2V5'},563.88,66.04)
part('TPS3839DBZ','U9','TPS3839G25DBZR',{1:G,2:'AON_OK',3:'AON_2V5'},665.48,66.04)
part('TPS3700DDC','U10','TPS3700DDCR',{1:'VBUS_OK',2:G,3:'VBUS_SENSE',4:G,5:'AON_2V5',6:None},55.88,165.1)
part('SN74LVC1G74DCU','U11','SN74LVC1G74DCUR',{1:G,2:G,3:None,4:G,5:'RUN_Q',6:'LATCH_CLEAR_N',7:'LATCH_PRE_N',8:'AON_2V5'},157.48,165.1)
part('SN74LVC2G08DCU','U12','SN74LVC2G08DCUR',{1:'VBUS_OK',2:'AON_OK',7:'REARM',5:'CAP_OR_VBUS',6:'AON_OK',3:'LATCH_CLEAR_N',4:G,8:'AON_2V5'},259.08,165.1)
part('SN74LVC2G32DCU','U13','SN74LVC2G32DCUR',{1:'CAP_OK',2:'VBUS_OK',7:'CAP_OR_VBUS',5:G,6:G,3:None,4:G,8:'AON_2V5'},360.68,165.1)
part('SN74LVC1G04DCK','U14','SN74LVC1G04DCKR',{1:None,2:'REARM',3:G,4:'LATCH_PRE_N',5:'AON_2V5'},462.28,165.1)
part('SN74LVC2G08DCU','U15','SN74LVC2G08DCUR',{1:'RUN_Q',2:'AON_OK',7:'RUN',5:G,6:G,3:None,4:G,8:'AON_2V5'},563.88,165.1)
part('TPS3831DQN','U16','TPS3831K33DQNR',{1:'RESET_OK',2:'MANUAL_RESET_N',3:G,4:'SYS_3V3',5:G},665.48,165.1)
part('SN74LVC2G08DCU','U17','SN74LVC2G08DCUR',{1:'RUN',2:'RESET_OK',7:'SYS_READY',5:'MCU_DE_REQUEST',6:'SYS_READY',3:'DMX_DE_SAFE',4:G,8:'SYS_3V3'},55.88,264.16)
part('SN74LVC2G08DCU','U18','SN74LVC2G08DCUR',{1:'MCU_ISO_REQUEST',2:'SYS_READY',7:'DMX_POWER_EN',5:'VBUS_OK',6:'SYS_READY',3:'VBUS_GOOD_3V3',4:G,8:'SYS_3V3'},157.48,264.16)
part('AT25SF161B_MHB','U2','AT25SF161B-MHB-T 16Mbit',{1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:G,5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:G},259.08,264.16)
part('CC1352_MCU_RF_BOUNDARY','X_MCU','MCU/RF NOT CAPTURED; proposed signals NO GPIO numbering',{i+1:n for i,(n,t) in enumerate(mcunames)},381,264.16)
part('ISOW1412_SHEET_BOUNDARY','X_DMX','MATCH dmx-interface.kicad_sch X1',{i+1:n for i,n in enumerate(dmxnames)},533.4,264.16)
part('FACTORY_PADS','J_FACTORY','VREF sense; cJTAG/RESET/ROM strap; no power injection',{i+1:n for i,n in enumerate(['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])},665.48,264.16)
part('TPS2116DRL','U19','TPS2116DRLR',{1:G,2:'NORMAL_IN',3:'LIMITED_5V',4:'LIMITED_5V',5:'LIMITED_5V',6:G,7:'NORMAL_IN',8:None},767.08,264.16)
passives=[]
def two(n,r,v,a,b):passives.append((n,r,v,a,b))
for r,v,a,b in [('R_CC1','5.1k 1%','CC1',G),('R_CC2','5.1k 1%','CC2',G),('R_ILIM','60.4k 0.1%','ILIM_SET',G),('R_OSEL','17.4k 1%','OSEL_SET',G),('R_ICHG','9.53k 1%','ICHG_SET',G),('R_VCHG','9.53k 1%','VCHG_SET',G),('R_CAP_TOP','20.0k 0.1%','CAP_POS','CAP_SENSE'),('R_CAP_BOTTOM','100k 0.1%','CAP_SENSE',G),('R_VBUS_TOP','93.1k 0.1%','NORMAL_IN','VBUS_SENSE'),('R_VBUS_BOTTOM','10k 0.1%','VBUS_SENSE',G),('R_VBUS_PU','10k','AON_2V5','VBUS_OK'),('R_INPUT_BLEED','47k','NORMAL_IN',G),('R_RUN_PD','100k','RUN',G),('R_INPUT_FAULT','100k','AON_2V5','INPUT_FAULT_N'),('R_BUCK_PG','100k','SYS_3V3','BUCK_PG'),('R_MR','10k','SYS_3V3','MANUAL_RESET_N'),('R_SERVICE','10k','SYS_3V3','SERVICE_N_DISTINCT_GPIO'),('R_ROM','10k','SYS_3V3','ROM_BOOT_STRAP'),('R_DE','100k','MCU_DE_REQUEST',G),('R_ISO','100k','MCU_ISO_REQUEST',G),('R_RE','10k','SYS_3V3','MCU_RE_N'),('R_CS','10k','SYS_3V3','SPI_CS_N'),('R_WP','10k','SYS_3V3','FLASH_WP_N'),('R_HOLD','10k','SYS_3V3','FLASH_HOLD_N'),('R_SCK','100k','SPI_SCK',G),('R_MOSI','100k','SPI_MOSI',G)]:two('R',r,v,a,b)
# Diode pin1=cathode, pin2=anode. Physical reverse barriers, not active slip/OR claims.
# U19 replaces D_MAIN: select VIN1 only; VIN2 is grounded, not a second source.
two('D','D_AON_USB','BAT54H,115','AON_RAW','LIMITED_5V')
two('D','D_AON_BUF','BAT54H,115','AON_RAW','BACKUP_RAW')
two('L','L_BOOST','XGL4020-222MEC 2.2uH','BOOST_SW','CAP_POS')
two('L','L_BUCK','XFL4020-222MEC 2.2uH','BUCK_SW','SYS_3V3')
two('C','C_BUF','HV1325-2R7156-R 15F 2.7V','CAP_POS',G)
for r,v,a in [('C_RAW','100n 16V','VBUS_RAW'),('C_LIMIT','1u effective 10V','LIMITED_5V'),('C_U19','100n 10V','LIMITED_5V'),('C_IN','10u effective 10V','NORMAL_IN'),('C_BACKUP','22u effective 10V','BACKUP_RAW'),('C_BUCK_IN','10u effective 10V','BACKUP_RAW'),('C_SYS','22u effective 10V','SYS_3V3'),('C_SS','3.3n','BUCK_SS'),('C_AON_IN','1u effective 10V','AON_RAW'),('C_AON_OUT','1u effective 10V','AON_2V5'),('C_REF','10n','CAP_REF'),('C_FLASH','100n 10V','SYS_3V3'),('C_FLASH_BULK','1u effective 10V','SYS_3V3')]:two('C',r,v,a,G)
for ref,rail in [('U8','AON_2V5'),('U9','AON_2V5'),('U10','AON_2V5'),('U11','AON_2V5'),('U12','AON_2V5'),('U13','AON_2V5'),('U14','AON_2V5'),('U15','AON_2V5'),('U16','SYS_3V3'),('U17','SYS_3V3'),('U18','SYS_3V3')]:two('C','C_'+ref,'100n 10V',rail,G)
two('SW_NO','S_SERVICE','RESIDENT LOADER SERVICE / NOT ROM','SERVICE_N_DISTINCT_GPIO',G)
two('SW_NO','S_RESET','RESET','MANUAL_RESET_N',G)
for i,(n,r,v,a,b) in enumerate(passives):part(n,r,v,{1:a,2:b},35.56+(i%13)*58.42,340.36+(i//13)*35.56)
for i,net in enumerate(['AON_RAW','CAP_POS','SYS_3V3']):part('DERIVED_POWER','#FLG'+str(i+1),'PASSIVE PATH POWER; VERIFIED SOURCE',{1:net},45.72+i*121.92,528.32)
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
root=uid('root');s=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A1") (title_block (title "NOVA power-only / buffer / RDM service hardware - PROTOTYPE") (rev "C-POWER-REVIEW-FIX")) (lib_symbols']
for n in lib:s.append(definition(n).replace('(symbol '+q(n)+' ','(symbol '+q('PWR:'+n)+' ',1))
s.append(')')
for name,ref,value,nets,x,y in parts:
    pins,w,h=lib[name];s.append(f'(symbol (lib_id "PWR:{name}") (at {x} {y} 0) (unit 1) (in_bom {"no" if ref.startswith("#") else "yes"}) (on_board {"no" if ref.startswith("#") else "yes"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-2.54} 0) {e}) (property "Value" {q(value)} (at {x} {y+h+2.54} 0) {e})')
    for pn,no,px,py,a,t in pins:s.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
    s.append(f'(instances (project "power-service" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
    for pn,no,px,py,a,t in pins:
        xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
        if net is None:s.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
        dx,dy={0:(-5.08,0),270:(0,-5.08),90:(0,5.08)}[a];ex,ey=round(xx+dx,4),round(yy+dy,4)
        s.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
        s.append(f'(label {q(net)} (at {ex} {ey} 0) {e} (uuid "{uid(ref+no+"l")}"))')
notes=['CURRENT POWER-ONLY DESIGN: USB data pins NC. <=500mA PSD design basis; COLD START NOT ACCEPTED (ISS max unknown).', 'Cap latch: PRE_N=!(VBUS_OK & AON_OK); CLR_N=AON_OK & (CAP_OK | VBUS_OK); RUN=Q & AON_OK.', 'MODE=AON_RAW independent of RUN. U19 low-loss reverse barrier; U10 senses actual NORMAL_IN (no slow input RC).', 'SERVICE is distinct from ROM strap; MCU pin allocation lives in mcu-radio/. Power boundary numbers are not package pins.', 'MCU/RF and existing ISOW1412 sheet are explicit boundaries; no resident RDM loader, security/update code or PCB routing claimed.', '15F at2.6V /25mA charge; runtime must subtract 100mV charge hysteresis. Stable source/PG still cannot promise future commit energy.']
for i,n in enumerate(notes):s.append(f'(text {q(n)} (at 20.32 {551+i*5.08} 0) (effects (font (size 1.0 1.0)) (justify left)) (uuid "{uid("note"+str(i))}"))')
s.append(')');(P/'power-service.kicad_sch').write_text('\n'.join(s)+'\n')
(P/'power-service.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in lib)+'\n)\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "PWR") (type "KiCad") (uri "${KIPRJMOD}/power-service.kicad_sym") (options "") (descr "Power/service source-backed typed symbols")))\n')
(P/'power-service.kicad_pro').write_text('{"meta":{"filename":"power-service.kicad_pro","version":1}}\n')
print(f'Generated {len(parts)} components; run verify.py for real export.')
