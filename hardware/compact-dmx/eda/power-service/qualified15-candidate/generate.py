"""Separated-power prototype candidate; entirely separate from the active capture.
No resident-loader implementation or hardware qualification is claimed.
"""
from pathlib import Path
import uuid,json
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v))
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-qualified15/'+v))
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
  usb.append((side+str(i),name,'passive'))
ic('USB_C_POWER_ONLY_BOUNDARY',usb)
mcunames=[('SYS_3V3','power_in'),(G,'power_in'),('MCU_DMX_TX','output'),('MCU_DMX_RX','input'),('MCU_DE_REQUEST','output'),('MCU_RE_N','output'),('MCU_ISO_REQUEST','output'),('SPI_CS_N','output'),('SPI_MOSI','output'),('SPI_SCK','output'),('SPI_MISO','input'),('VBUS_GOOD_3V3','input'),('SERVICE_N_DISTINCT_GPIO','input'),('ROM_BOOT_STRAP','input'),('RESET_OK','input'),('TMSC','bidirectional'),('TCKC','input'),('BUCK_PG','input')]
ic('CC1352_MCU_RF_BOUNDARY',[(i+1,n,t) for i,(n,t) in enumerate(mcunames)])
dmxnames=['SYS_3V3',G,'MCU_DMX_TX','DMX_DE_SAFE','MCU_RE_N','MCU_DMX_RX','DMX_POWER_EN']
ic('ISOW1412_SHEET_BOUNDARY',[(i+1,n,'power_in' if i<2 else 'output' if i==5 else 'input') for i,n in enumerate(dmxnames)])
ic('FACTORY_PADS',[(i+1,n,'passive') for i,n in enumerate(['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])])
for name in ['R','C','L','D','SW_NO']:
 lib[name]=([('K' if name=='D' else '1','1',0,5.08,270,'passive'),('A' if name=='D' else '2','2',0,-5.08,90,'passive')],1.27,2.54)
lib['DERIVED_POWER'] = ([('PWR','1',0,-5.08,90,'power_out')],2.54,2.54)

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

# Qualified-source candidate. All writes below are confined to this directory.
import csv
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-qualified15/'+v))
parts=[];meta={};sheet='main';serial={'R':0,'C':0,'D':0,'L':0,'S':0}
def add(n,r,v,nets,area,pkg,role=None,kind='physical',note=''):
 part(n,r,v,nets,0,0);meta[r]={'role':role or r,'sheet':sheet,'body_mm2':area,'package':pkg,'kind':kind,'note':note}
def tw(n,role,v,a,b,area,pkg,kind='physical'):
 key='S' if n=='SW_NO' else n;serial[key]+=1;r=key+str(serial[key]);add(n,r,v,{1:a,2:b},area,pkg,key+'_'+role,kind);return r
def resistor(role,ohms,a,b,size='0402'):
 if size=='0402' and ohms>100000:size='0805'
 if ohms<1000:code=f'{ohms:g}R'
 else:
  k=ohms/1000;code=f'{k:g}K' if k>=100 else f'{k:.3g}'.replace('.','K')
  if 'K' not in code:code+='K'
  while len(code)<4:code+='0'
 mpn='TNPW'+size+code+'BE'+('ED' if size=='0402' else 'EA')
 return tw('R',role,f'{mpn} {ohms:g}ohm 0.1% 25ppm',a,b,{'0402':.5,'0603':1.28,'0805':2.5,'1206':5.12}[size],size)
def cap(role,t,a,b=G):
 spec={'100n':('GRM155R71E104KE14D 100nF 25V X7R',.5,'0402'),'1u':('GRM155R61C105KA12D 1uF 16V X5R',.5,'0402'),'10u':('GRM21BR71A106KE51L 10uF 10V X7R',2.5,'0805'),'10n':('GRM155R71H103KA88D 10nF 50V X7R',.5,'0402')}
 v,area,pkg=spec[t];return tw('C',role,v,a,b,area,pkg)
ic('TPS259474RPW',[(1,'EN_UVLO','input'),(2,'OVLO','input'),(3,'PG','open_collector'),(4,'PGTH','input'),(5,'IN','power_in'),(6,'OUT','power_out'),(7,'DVDT','output'),(8,'GND','power_in'),(9,'ILM','output'),(10,'ITIMER','output')])
ic('BQ25173DSG',[(1,'IN','power_in'),(2,'ISET','input'),(3,'CE_DISABLE_HIGH','input'),(4,'GND','power_in'),(5,'STAT','open_collector'),(6,'PG','open_collector'),(7,'FB','input'),(8,'OUT','power_out'),(9,'EP_GND','power_in')])
ic('TPS61023DRL',[(1,'FB','input'),(2,'EN','input'),(3,'VIN','power_in'),(4,'GND','power_in'),(5,'SW','power_out'),(6,'VOUT','power_out')])
ic('TPS709DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'NC','no_connect'),(5,'OUT','power_out')])
ic('TUSB320LAIRWB',[(1,'CC1','bidirectional'),(2,'CC2','bidirectional'),(3,'PORT_UFP','input'),(4,'VBUS_DET','input'),(5,'ADDR_GPIO_FLOAT','input'),(6,'OUT3_AUDIO','open_collector'),(7,'OUT1_CC_MODE','open_collector'),(8,'OUT2_CC_MODE','open_collector'),(9,'ID','open_collector'),(10,'GND','power_in'),(11,'EN_N','input'),(12,'VDD','power_in')])
ic('TPS3808DBV',[(1,'RESET_N','open_collector'),(2,'GND','power_in'),(3,'MR_N','input'),(4,'CT','input'),(5,'SENSE','input'),(6,'VDD','power_in')])
for n in ['SN74LVC1G0832DCK','SN74LVC1G3208DCK','SN74LVC1G11DCK']:ic(n,[(1,'A','input'),(2,'GND','power_in'),(3,'B','input'),(4,'Y','output'),(5,'VCC','power_in'),(6,'C','input')])
ic('SN74LVC1G08DCK',[(1,'A','input'),(2,'B','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')])
ic('SN74LVC1G14DCK',[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')])
for n in ['SN74LVC2G17DCK','SN74LVC2G14DCK']:ic(n,[(1,'1A','input'),(2,'GND','power_in'),(3,'2A','input'),(4,'2Y','output'),(5,'VCC','power_in'),(6,'1Y','output')])
ic('SN74LVC2G132DCU',[(1,'1A','input'),(2,'1B','input'),(3,'2Y','output'),(4,'GND','power_in'),(5,'2A','input'),(6,'2B','input'),(7,'1Y','output'),(8,'VCC','power_in')])
ic('GCT_USB4125',[(x,x,'passive') for x in ['A5','B5','A9','B9','A12','B12','SH']])
add('GCT_USB4125','J1','USB4125-GF-A',{ 'A5':'CC1','B5':'CC2','A9':'VBUS_RAW','B9':'VBUS_RAW','A12':G,'B12':G,'SH':G},60.792,'GCT',role='USB_POWER')
add('TPS259474RPW','U6','TPS259474LRPWR',{1:'CC_ALLOW',2:G,3:'SOURCE_SENSE_OD',4:'EFUSE_PGTH',5:'VBUS_RAW',6:'LIMITED_5V',7:'EFUSE_DVDT',8:G,9:'EFUSE_ILM',10:'EFUSE_TIMER'},4,'RPW10',note='Circuit-breaker/latch-off, NOT continuous current limiter; EN independent of PG/output')
add('BQ25173DSG','U3','BQ25173DSGR',{1:'LIMITED_5V',2:'ICHG_PIN',3:'CHARGE_DISABLE',4:G,5:None,6:None,7:'VCHG_FB',8:'CAP_POS',9:G},4,'DSG8')
add('TPS61023DRL','U5','TPS61023DRLR',{1:'BOOST_FB',2:'CAP_BOOST_EN',3:'CAP_POS',4:G,5:'BOOST_SW',6:'BOOST_3V9'},1.92,'DRL6')
add('TPS2116DRL','U19','TPS2116DRLR',{1:G,2:'BACKUP_RAW',3:'LIMITED_5V',4:'SOURCE_VALID',5:'AON_2V5',6:'BOOST_3V9',7:'BACKUP_RAW',8:None},1.92,'DRL8')
add('TPS62132RGT','U4','TPS62132RGTR',{1:'BUCK_SW',2:'BUCK_SW',3:'BUCK_SW',4:'BUCK_PG',5:G,6:G,7:G,8:G,9:'BUCK_SS',10:'BACKUP_RAW',11:'BACKUP_RAW',12:'BACKUP_RAW',13:'BUCK_EN',14:'SYS_3V3',15:G,16:G,17:G},9,'RGT16')
add('TPS7A0225DBV','U7','TPS7A0225PDBVR',{1:'AON_RAW',2:G,3:'AON_RAW',4:None,5:'AON_2V5'},4.64,'DBV5')
add('TPS3839DBZ','U9','TPS3839G25DBZR',{1:G,2:'AON_OK',3:'AON_2V5'},3.8,'DBZ3')
add('TPS709DBV','U24','TPS70933DBVR',{1:'CC_RAW',2:G,3:'CC_RAW',4:None,5:'CC_3V3'},4.64,'DBV5')
add('TUSB320LAIRWB','U25','TUSB320LAIRWBR',{1:'CC1',2:'CC2',3:G,4:'CC_VBUS_DET',5:None,6:None,7:'CC_OUT1',8:'CC_OUT2',9:None,10:G,11:G,12:'CC_3V3'},2.56,'RWB12')
add('TPS3808DBV','U26','TPS3808G33DBVR',{1:'CC_ALLOW',2:G,3:'CC_ADVERT_OK',4:None,5:'CC_3V3',6:'CC_3V3'},4.64,'DBV6',note='Direct supervisor open-drain eFuse enable; CC3V3 threshold and actual advertisement MR; CTopen12..28ms')
add('TPS3700DDC','U8','TPS3700DDCR',{1:'CAP_OK_OD',2:G,3:'CAP_SENSE',4:'CAP_START_SENSE',5:'AON_2V5',6:'CAP_START_N_OD'},4,'DDC6')
add('TPS3700DDC','U10','TPS3700DDCR',{1:'SOURCE_SENSE_OD',2:G,3:'USB_SENSE',4:'MAIN_SENSE',5:'AON_2V5',6:'MAIN_NOT_READY_OD'},4,'DDC6')
add('TPS3700DDC','U20','TPS3700DDCR',{1:'SOURCE_SENSE_OD',2:G,3:'RAW_SENSE',4:'BOOST_SENSE',5:'AON_2V5',6:'BOOST_NOT_READY_OD'},4,'DDC6')
add('TPS3808DBV','U27','TPS3808G01DBVR',{1:'VBUS_GOOD_3V3',2:G,3:'BUCK_PG_BUF',4:None,5:'SOURCE_VALID',6:'AON_2V5'},4.64,'DBV6',note='Actual source AND actual buckPG must persist: CT open12..28ms; immediate asynchronous assertion; no false blanking')
add('TPS3831DQN','U16','TPS3831K33DQNR',{1:'RESET_OK',2:'MANUAL_RESET_N',3:G,4:'SYS_3V3',5:G},1,'DQN4')
add('AT25SF161B_MHB','U2','AT25SF161B-MHB-T',{1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:G,5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:G},30,'MHB8')
add('CC1352_MCU_RF_BOUNDARY','J2','Existing MCU logical18 contact contract',{i+1:n for i,(n,t) in enumerate(mcunames)},0,'BOUNDARY',role='X_MCU',kind='external_interface')
add('ISOW1412_SHEET_BOUNDARY','J3','Existing DMX logical7 contact contract',{i+1:n for i,n in enumerate(dmxnames)},0,'BOUNDARY',role='X_DMX',kind='external_interface')
add('FACTORY_PADS','J4','Fabricated six-pad cJTAG/reset/ROM; VREF sense only',{i+1:n for i,n in enumerate(['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])},0,'FACTORY',role='FACTORY',kind='pcb_feature')
resistor('CC_FEED',150,'VBUS_RAW','CC_RAW',size='1206')
resistor('AON_FEED',330,'VBUS_RAW','AON_USB_LIMITED',size='0805')
add('TPS2116DRL','U40','TPS2116DRLR',{1:G,2:'AON_RAW',3:'AON_USB_LIMITED',4:'AON_PRIORITY',5:'AON_USB_LIMITED',6:'BOOST_3V9',7:'AON_RAW',8:None},1.92,'DRL8',note='Priority raw-first AON mux MODE=VIN1 per TPS2116 7.3.1; no external self-bias')
resistor('AON_PRIORITY_TOP',22100,'AON_USB_LIMITED','AON_PRIORITY');resistor('AON_PRIORITY_BOTTOM',10000,'AON_PRIORITY',G)
cap('AON_USB','1u','AON_USB_LIMITED')
resistor('CC_VBUS',909000,'VBUS_RAW','CC_VBUS_DET')
resistor('CC_OUT1_PU',10000,'CC_3V3','CC_OUT1');resistor('CC_OUT2_PU',10000,'CC_3V3','CC_OUT2')
resistor('CC_BLEED',10000,'CC_3V3',G)
resistor('CC_ALLOW_PD',249000,'CC_ALLOW',G)
resistor('CC_ALLOW_PU',115000,'CC_3V3','CC_ALLOW')
resistor('EFUSE_ILM',3320,'EFUSE_ILM',G)
resistor('EFUSE_PGTH_TOP',10000,'LIMITED_5V','EFUSE_PGTH');resistor('EFUSE_PGTH_BOTTOM',10000,'EFUSE_PGTH',G)
resistor('DVDT_SERIES',100,'EFUSE_DVDT','EFUSE_DVDT_C');cap('DVDT','10n','EFUSE_DVDT_C');cap('ITIMER','10n','EFUSE_TIMER')
resistor('RAW_BLEED',10000,'VBUS_RAW',G);resistor('USB_BLEED',100000,'LIMITED_5V',G);resistor('BOOST_BLEED',100000,'BOOST_3V9',G)
resistor('ICHG_FILTER',100,'ICHG_PIN','ICHG_FILTER');resistor('ICHG',11900,'ICHG_FILTER',G);cap('ICHG','100n','ICHG_FILTER')
for role,v,a,b in [('VCHG_TOP',22500,'CAP_POS','VCHG_FB'),('VCHG_BOTTOM',10000,'VCHG_FB',G),('BOOST_TOP',562000,'BOOST_3V9','BOOST_FB'),('BOOST_BOTTOM',100000,'BOOST_FB',G)]:resistor(role,v,a,b)
for pre,top,rail,sense in [('CAP',32400,'CAP_POS','CAP_SENSE'),('CAP_START',52300,'CAP_POS','CAP_START_SENSE'),('USB',89800,'LIMITED_5V','USB_SENSE'),('MAIN',80600,'BACKUP_RAW','MAIN_SENSE'),('RAW',89800,'VBUS_RAW','RAW_SENSE'),('BOOST_MON',80600,'BOOST_3V9','BOOST_SENSE')]:
 resistor(pre+'_TOP',top,rail,sense);resistor(pre+'_BOTTOM',10000,sense,G)
cap('RAW','100n','VBUS_RAW');cap('USB','10u','LIMITED_5V')
cap('CHGIN','1u','LIMITED_5V')
for pre,rail,n,t in [('BACKUP','BACKUP_RAW',2,'10u'),('SYS','SYS_3V3',2,'10u'),('BOOST_OUT','BOOST_3V9',2,'10u'),('BOOST_IN','CAP_POS',1,'10u'),('AON_IN','AON_RAW',2,'1u'),('AON_OUT','AON_2V5',2,'1u'),('CC_IN','CC_RAW',1,'10u'),('CC_OUT','CC_3V3',1,'10u'),('FLASH','SYS_3V3',1,'1u')]:
 for i in range(n):cap(pre+str(i+1),t,rail)
cap('SS','10n','BUCK_SS') # Headroom no longer needs500mA-specific100nF slow start.
tw('L','BOOST_L','XGL4020-222MEC 2.2uH 20%','BOOST_SW','CAP_POS',18.49,'XGL4020')
tw('L','BUCK_L','XFL4020-222MEC 2.2uH 20%','BUCK_SW','SYS_3V3',18.49,'XFL4020')
cell_ref=tw('C','CELL','HV1325-2R7156-R 15F 2.7V','CAP_POS',G,383.4,'CELL');meta[cell_ref]['note']='Maximum horizontalcell body projection28.4x13.5, NOT verticalcrosssection; mechanicalreserve35x13.5 separatelychecked'
for role,ohms,a,b in [('BUCK_PG',4700,'SYS_3V3','BUCK_PG'),('SOURCE_STATUS',10000,'SYS_3V3','VBUS_GOOD_3V3'),('MR',10000,'SYS_3V3','MANUAL_RESET_N'),('SERVICE',10000,'SYS_3V3','SERVICE_N_DISTINCT_GPIO'),('ROM',10000,'SYS_3V3','ROM_BOOT_STRAP'),('DE',100000,'MCU_DE_REQUEST',G),('ISO',100000,'MCU_ISO_REQUEST',G),('RE',10000,'SYS_3V3','MCU_RE_N'),('CS',10000,'SYS_3V3','SPI_CS_N'),('WP',10000,'SYS_3V3','FLASH_WP_N'),('HOLD',10000,'SYS_3V3','FLASH_HOLD_N'),('SCK',100000,'SPI_SCK',G),('MOSI',100000,'SPI_MOSI',G)]:resistor(role,ohms,a,b)
tw('SW_NO','SERVICE_CONTACT','PCB normally-open SERVICE contact','SERVICE_N_DISTINCT_GPIO',G,0,'CONTACT',kind='pcb_feature')
tw('SW_NO','RESET_CONTACT','PCB normally-open RESET contact','MANUAL_RESET_N',G,0,'CONTACT',kind='pcb_feature')
sheet='control'
add('SN74LVC1G14DCK','U28','SN74LVC1G14DCKR',{1:None,2:'CC_OUT1',3:G,4:'CC_ADVERT_OK',5:'CC_3V3'},2.5,'DCK5')
add('SN74LVC1G11DCK','U30','SN74LVC1G11DCKR',{1:'SOURCE_SENSE',2:G,3:'CC_ALLOW',4:'SOURCE_VALID',5:'AON_2V5',6:'AON_OK'},2.5,'DCK6')
add('SN74LVC1G0832DCK','U31','SN74LVC1G0832DCKR',{1:'MAIN_READY',2:G,3:'BOOST_READY',4:'CAP_SAFE_PATH',5:'AON_2V5',6:'SOURCE_VALID'},2.5,'DCK6')
add('SN74LVC1G11DCK','U32','SN74LVC1G11DCKR',{1:'CAP_OK',2:G,3:'AON_OK',4:'CAP_RESET_N',5:'AON_2V5',6:'CAP_SAFE_PATH'},2.5,'DCK6')
add('SN74LVC2G132DCU','U33','SN74LVC2G132DCUR',{1:'SOURCE_VALID',2:'CAP_START_OK',3:'CHARGE_DISABLE',4:G,5:'SOURCE_VALID',6:'BUCK_PG',7:'CAP_SET_N',8:'AON_2V5'},4.6,'DCU8')
add('SN74LVC2G132DCU','U34','SN74LVC2G132DCUR',{1:'CAP_SET_N',2:'CAP_BAR',3:'CAP_BAR',4:G,5:'CAP_RESET_N',6:'CAP_ARM',7:'CAP_ARM',8:'AON_2V5'},4.6,'DCU8',note='Actual cross-coupled NAND SR latch. Source/cap threshold ordering excludes simultaneous set/reset in DC.')
add('SN74LVC1G3208DCK','U35','SN74LVC1G3208DCKR',{1:'SOURCE_VALID',2:G,3:'CAP_ARM',4:'BUCK_EN',5:'AON_2V5',6:'MAIN_READY'},2.5,'DCK6')
add('SN74LVC2G17DCK','U36','SN74LVC2G17DCKR',{1:'SOURCE_SENSE_OD',2:G,3:'CAP_OK_OD',4:'CAP_OK',5:'AON_2V5',6:'SOURCE_SENSE'},2.5,'DCK6')
add('SN74LVC2G17DCK','U37','SN74LVC2G17DCKR',{1:'BUCK_PG',2:G,3:'CAP_ARM',4:'CAP_BOOST_EN',5:'AON_2V5',6:'BUCK_PG_BUF'},2.5,'DCK6')
add('SN74LVC2G14DCK','U38','SN74LVC2G14DCKR',{1:'CAP_START_N_OD',2:G,3:'MAIN_NOT_READY_OD',4:'MAIN_READY',5:'AON_2V5',6:'CAP_START_OK'},2.5,'DCK6')
add('SN74LVC2G14DCK','U39','SN74LVC2G14DCKR',{1:'BOOST_NOT_READY_OD',2:G,3:G,4:None,5:'AON_2V5',6:'BOOST_READY'},2.5,'DCK6')
add('SN74LVC2G08DCU','U17','SN74LVC2G08DCUR',{1:'BUCK_EN',2:'RESET_OK',3:'DMX_DE_SAFE',4:G,5:'MCU_DE_REQUEST',6:'SYS_READY',7:'SYS_READY',8:'SYS_3V3'},4.6,'DCU8')
add('SN74LVC2G08DCU','U18','SN74LVC2G08DCUR',{1:'MCU_ISO_REQUEST',2:'SYS_READY',3:None,4:G,5:G,6:G,7:'DMX_POWER_EN',8:'SYS_3V3'},4.6,'DCU8')
for n in ['SOURCE_SENSE_OD','CAP_OK_OD','CAP_START_N_OD','MAIN_NOT_READY_OD','BOOST_NOT_READY_OD']:resistor('PU_'+n,33000 if n=='SOURCE_SENSE_OD' else 47000,'AON_2V5',n)
for n in ['BUCK_EN','CAP_BOOST_EN']:resistor('PD_'+n,47000,n,G)
resistor('CE_DEFAULT',100000,'AON_2V5','CHARGE_DISABLE')
# Every actual IC is locally bypassed on its actual domain.
for n,r,v,ns,_,_ in list(parts):
 if not r.startswith('U'):continue
 if r in ['U6','U3','U5','U4','U7','U24','U19','U40']:continue # Selected power rail bulk above, explicit.
 rail='CC_3V3' if r in ['U25','U26','U28','U29'] else 'SYS_3V3' if r in ['U2','U16','U17','U18'] else 'AON_2V5'
 sheet=meta[r]['sheet'];cap('BYPASS_'+r,'100n',rail)
sheet='main'
for i,(net,why) in enumerate([('VBUS_RAW','external supply'),(G,'external return'),('AON_USB_LIMITED','actual330ohm raw-AON feed'),('SYS_3V3','actual buck inductor output'),('CC_RAW','actual150ohm raw-source feed')],1):add('DERIVED_POWER','#FLG'+str(i),why,{1:net},0,'FLAG',kind='power_flag')
def footprint_name(ref):
 m=meta[ref];pkg=m['package']
 if m['kind'] not in ['physical','pcb_feature']:return ''
 if pkg in ['0402','0805','1206']:return ('R' if ref.startswith('R') else 'C')+pkg
 return {'GCT':'USB_GCT','MHB8':'NOR8','CELL':'Cell_leads','CONTACT':'Contact2','FACTORY':'Factory6','XFL4020':'L4020','XGL4020':'L4020'}.get(pkg,pkg)
# Candidate structure, exact source/pin maps are separately transcribed in verify.py.
root=uid('root');child=uid('control-root');sheetid=uid('control-sheet')
assert len(set(p[1] for p in parts))==len(parts)
used={p[0] for p in parts}
netsets={s:{n for p in parts if meta[p[1]]['sheet']==s for n in p[3].values() if n is not None} for s in ['main','control']};cross=netsets['main']&netsets['control']
for sh in ['main','control']:
 ids=[i for i,p in enumerate(parts) if meta[p[1]]['sheet']==sh]
 big=[i for i in ids if parts[i][0] not in ['R','C','D','L','SW_NO','DERIVED_POWER']];small=[i for i in ids if i not in big and parts[i][0]!='DERIVED_POWER']
 for j,i in enumerate(big):
  n,r,v,ns,_,_=parts[i];parts[i]=(n,r,v,ns,55.88+(j%7)*111.76,66.04+(j//7)*93.98)
 for j,i in enumerate(small):
  n,r,v,ns,_,_=parts[i];parts[i]=(n,r,v,ns,30.48+(j%13)*60.96,365.76+(j//13)*30.48)
 for j,i in enumerate(i for i in ids if parts[i][0]=='DERIVED_POWER'):
  n,r,v,ns,_,_=parts[i];parts[i]=(n,r,v,ns,60.96+j*177.8,563.88)
for sh,filename,docuid in [('main','qualified15',root),('control','control',child)]:
 s=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{docuid}") (paper "A1") (title_block (title "NOVA qualified >=1.5A prototype - {sh}") (rev "Q15-PROTOTYPE-1")) (lib_symbols']
 for n in sorted(used):s.append(definition(n).replace('(symbol '+q(n)+' ','(symbol '+q('Q15:'+n)+' ',1))
 s.append(')')
 for name,ref,value,nets,x,y in parts:
  if meta[ref]['sheet']!=sh:continue
  pins,w,h=lib[name];sty='(effects (font (size .8 .8)))';role=meta[ref]['role'];boundary=meta[ref]['kind'] in ['external_interface','power_flag']
  s.append(f'(symbol (lib_id "Q15:{name}") (at {x} {y} 0) (unit 1) (in_bom {"no" if boundary else "yes"}) (on_board {"no" if boundary else "yes"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-2.54} 0) {sty}) (property "Value" {q(value)} (at {x} {y+h+2.54} 0) {sty}) (property "Role" {q(role)} (at {x} {y+h+3.81} 0) (effects (font (size .7 .7))))')
  if footprint_name(ref):s.append(f'(property "Footprint" {q("Q15:"+footprint_name(ref))} (at {x} {y} 0) (effects (font (size 1 1)) hide))')
  for pn,no,px,py,a,t in pins:s.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
  path='/'+root if sh=='main' else '/'+root+'/'+sheetid
  s.append(f'(instances (project "qualified15" (path "{path}" (reference {q(ref)}) (unit 1)))))')
  for pn,no,px,py,a,t in pins:
   xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
   if net is None:s.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
   dx,dy={0:(-5.08,0),270:(0,-5.08),90:(0,5.08)}[a];ex,ey=round(xx+dx,4),round(yy+dy,4)
   s.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
   label='global_label' if net in cross else 'label';shape=' (shape bidirectional)' if label=='global_label' else ''
   s.append(f'({label} {q(net)}{shape} (at {ex} {ey} 0) (effects (font (size .8 .8))) (uuid "{uid(ref+no+"label")}"))')
 if sh=='main':s.append(f'(sheet (at 680.72 294.64) (size 127 20.32) (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid "{sheetid}") (property "Sheetname" "Actual qualified control" (at 680.72 293.37 0) {e}) (property "Sheetfile" "control.kicad_sch" (at 680.72 316.23 0) {e}) (instances (project "qualified15" (path "/{root}" (page "2")))))')
 notes=['OWNER ACCEPTED:5V USB-C advertising1.5A or3A. UFP only; noUSBdata/noPD escalation. GCT six contacts, not old24pin map.',
 'RawCC/independentAON never fed by backup. TPS259474L is a circuit-breaker/latch-off; no guaranteed transient current ceiling.',
 'SOURCE_SENSE_OD is physical wired-AND rawUV +USBUV +eFusePG. Status adds actualbuckPG and12..28ms assertion delay.',
 'One cap-arm NAND latch: loadedUV or loss of both source and ready backup clears; rebound alone cannot rearm.',
 'SeparateBQ nominal25mA charger. Cap-onlyTPS61023; measured current/ESR/thermal/USB/mechanical/routing gates remain open.']
 for i,n in enumerate(notes):s.append(f'(text {q(n)} (at 20.32 {322.58+i*3.81} 0) (effects (font (size .8 .8)) (justify left)) (uuid "{uid(sh+str(i))}"))')
 s.append(')');(P/(filename+'.kicad_sch')).write_text('\n'.join(s)+'\n')
(P/'qualified15.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in sorted(used))+'\n)\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Q15") (type "KiCad") (uri "${KIPRJMOD}/qualified15.kicad_sym") (options "") (descr "Qualified power prototype")))\n')
(P/'qualified15.kicad_pro').write_text('{"meta":{"filename":"qualified15.kicad_pro","version":1}}\n')
with (P/'component-ledger.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['reference','role','value','sheet','kind','package','body_area_mm2','note'])
 for n,r,v,ns,x,y in sorted(parts,key=lambda p:p[1]):
  m=meta[r];w.writerow([r,m['role'],v,m['sheet'],m['kind'],m['package'],m['body_mm2'],m['note']])
print(json.dumps({'components':len(parts),'physical':sum(m['kind']=='physical' for m in meta.values()),'ICs':sum(r.startswith('U') for r in meta),'main':sum(m['sheet']=='main' for m in meta.values()),'control':sum(m['sheet']=='control' for m in meta.values())},indent=2))
