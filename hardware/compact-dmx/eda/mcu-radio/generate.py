"""CC1352R1 support and dual-band frontend; antenna/final match remains incomplete.
Does not execute or mutate the power-service generator.
"""
from pathlib import Path
import json
import uuid,json,csv
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v))
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-mcu-radio/'+v))
e='(effects (font (size 1 1)))'
lib={};parts=[]
def ic(name,pins):
 h=(len(pins)+1)*1.27
 lib[name]=([(pn,str(no),-15.24,h-(i+1)*2.54,0,t) for i,(no,pn,t) in enumerate(pins)],15.24,h)
def part(name,ref,value,nets,x,y):parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y))
# SWRS196I Table7-1 pp9-10; EGP mapped to local footprint pad49.
names={1:'RF_P_2_4GHZ',2:'RF_N_2_4GHZ',3:'RF_P_SUB_1GHZ',4:'RF_N_SUB_1GHZ',5:'RX_TX',6:'X32K_Q1',7:'X32K_Q2',13:'VDDS2',22:'VDDS3',23:'DCOUPL',24:'JTAG_TMSC',25:'JTAG_TCKC',33:'DCDC_SW',34:'VDDS_DCDC',35:'RESET_N',44:'VDDS',45:'VDDR',46:'X48M_N',47:'X48M_P',48:'VDDR_RF',49:'EGP'}
for dio,pin in [(3,8),(4,9),(5,10),(6,11),(7,12),(8,14),(9,15),(10,16),(11,17),(12,18),(13,19),(14,20),(15,21),(16,26),(17,27),(18,28),(19,29),(20,30),(21,31),(22,32),(23,36),(24,37),(25,38),(26,39),(27,40),(28,41),(29,42),(30,43)]:names[pin]='DIO_'+str(dio)
assigned={8:'ROM_BOOT_STRAP',9:'SERVICE_N_DISTINCT_GPIO',10:'MCU_DE_REQUEST',11:'MCU_ISO_REQUEST',12:'MCU_RE_N',14:'SPI_MISO',15:'SPI_MOSI',16:'SPI_SCK',17:'SPI_CS_N',18:'MCU_DMX_RX',19:'MCU_DMX_TX',20:'VBUS_GOOD_3V3',21:'BUCK_PG',24:'TMSC',25:'TCKC',35:'RESET_OK'}
inputs={8,9,14,18,20,21,25,35};outputs={10,11,12,15,16,17,19}
power={13,22,34,44,45,48,49}
types={p:('input' if p in inputs else 'output' if p in outputs else 'power_in' if p in power else 'power_out' if p in (23,33) else 'bidirectional' if names[p].startswith('DIO') or p==24 else 'passive') for p in names}
nets={p:assigned.get(p) for p in names}
for p in [13,22,34,44]:nets[p]='MCU_VDDS'
nets[43]=None # RF switch removed in direct dual-feed prototype
nets[49]='GND_USB';nets[45]=nets[48]='MCU_VDDR'
for p in [1,2,3,4,5,6,7,23,33,46,47]:nets[p]=names[p]
ic('CC1352R1F3RGZ',[(p,names[p],types[p]) for p in sorted(names)])
part('CC1352R1F3RGZ','U1','CC1352R1F3RGZR',nets,210.82,109.22)
contract=[('SYS_3V3','power_out'),('GND_USB','power_out')]+[(assigned[p],'output' if types[p]=='input' else 'input' if types[p]=='output' else 'bidirectional') for p in assigned]
ic('POWER_SERVICE_CONTRACT',[(i+1,n,t) for i,(n,t) in enumerate(contract)])
part('POWER_SERVICE_CONTRACT','X101','EXISTING power-service X_MCU / net contract',{i+1:n for i,(n,t) in enumerate(contract)},55.88,109.22)
# SWRC354 CC1352EM-IPC Rev1.1.0 March15 2018 support; current IPC manufacturer pin map.
G='GND_USB'
for name in ['R','C','L','FB']:
 lib[name]=([('1','1',0,5.08,270,'passive'),('2','2',0,-5.08,90,'passive')],1.27,2.54)
ic('XTAL2',[(1,'X1','passive'),(2,'X2','passive')])
ic('XTAL4',[(1,'X1','passive'),(2,'GND','passive'),(3,'X2','passive'),(4,'GND','passive')])
ic('JTI0900PC15A0036001E',[(1,'UNBAL_2G4','passive'),(2,'GND','passive'),(3,'GND','passive'),(4,'UNBAL_SUB1','passive'),(5,'RX_TX','passive'),(6,'RF_N_SUB1','passive'),(7,'RF_P_SUB1','passive'),(8,'RF_N_2G4','passive'),(9,'RF_P_2G4','passive'),(10,'GND','passive')])
ic('JTI0900AD47',[(i,'FEED_2G4' if i==1 else 'FEED_915' if i==4 else 'NC_LAND_MUST_SOLDER','passive') for i in range(1,9)])
lib['DERIVED_POWER']=([('PWR','1',0,-5.08,90,'power_out')],2.54,2.54)
part('JTI0900PC15A0036001E','TR101','0900PC15A0036001E',{1:'RF_2G4_50',2:G,3:G,4:'RF_915_UNBLOCKED',5:'RX_TX',6:'RF_N_SUB_1GHZ',7:'RF_P_SUB_1GHZ',8:'RF_N_2_4GHZ',9:'RF_P_2_4GHZ',10:G},335.28,88.9)
part('JTI0900AD47','A101','0900AD47A2450001E PROTOTYPE TUNING REQUIRED',{i:'ANT_2G4' if i==1 else 'ANT_915' if i==4 else None for i in range(1,9)},480.06,88.9)
part('XTAL2','Y101','FC-135 32.7680KA-AG0',{1:'X32K_Q1',2:'X32K_Q2'},335.28,165.1)
part('XTAL4','Y102','NX2016SA 48MHz EXS00A-CS05517',{1:'X48M_P',2:G,3:'X48M_N',4:G},335.28,215.9)
passives=[
 ('FB','FL101','BLM18HE152SN1D','MCU_VDDS','SYS_3V3'),
 ('L','L101','MLZ2012N6R8LT000 6.8uH','DCDC_SW','MCU_VDDR'),
 ('C','C101','GRM188R60J226MEA0D 22uF','MCU_VDDS',G),
 ('C','C102','GRM188R60J226MEA0D 22uF','MCU_VDDR',G),
 ('C','C103','GRM155R61C105KA12D 1uF','DCOUPL',G),
 ('C','C104','GRM155R71E104KE14D 100nF','MCU_VDDS',G),
 ('C','C105','GRM155R71E104KE14D 100nF','MCU_VDDS',G),
 ('C','C106','GRM155R71E104KE14D 100nF','MCU_VDDS',G),
 ('C','C107','GRM155R71E104KE14D 100nF','MCU_VDDS',G),
 ('C','C108','GRM155R71E104KE14D 100nF','MCU_VDDR',G),
 ('C','C109','GRM155R71E104KE14D 100nF','MCU_VDDR',G),
 ('C','C110','GRM1555C1H120JA01D 12pF','X32K_Q1',G),
 ('C','C111','GRM1555C1H120JA01D 12pF','X32K_Q2',G),
 ('C','C112','GRM0335C1H101GA01D 100pF','RF_915_UNBLOCKED','RF_915_50'),
 ('C','C113','GRM0335C1H101GA01D 100pF','RX_TX',G),
 ('L','L102','0402HP-2N7XGRW 2.7nH TUNE','RF_2G4_50','ANT_2G4'),
 ('C','C115','GJM1555C1H1R0BB01D 1.0pF TUNE','ANT_2G4',G),
 ('L','L103','0402HP-5N1XGRW 5.1nH TUNE','RF_915_50',G),
 ('C','C116','GJM1555C1H8R2DB01D 8.2pF TUNE','RF_915_50',G),
 ('L','L104','0402HP-12NXGRW 12nH TUNE','RF_915_50','ANT_915')]
for i,(n,r,v,a,b) in enumerate(passives):part(n,r,v,{1:a,2:b},40.64+(i%6)*88.9,254+(i//6)*30.48)
# Source declarations after actual passive power paths, not missing control implementations.
for i,net in enumerate(['MCU_VDDS','MCU_VDDR']):part('DERIVED_POWER','#FLG'+str(101+i),'ACTUAL FB / DCDC INDUCTOR PATH',{1:net},406.4+i*76.2,218.44)
mcu_nets=nets.copy()
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
root=uid('root');s=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A2") (title_block (title "NOVA R1 dual-feed antenna prototype") (rev "C-MCU-RF2")) (lib_symbols']
for n in lib:s.append(definition(n).replace('(symbol '+q(n)+' ','(symbol '+q('MCU:'+n)+' ',1))
s.append(')')
for name,ref,value,nets,x,y in parts:
    pins,w,h=lib[name];s.append(f'(symbol (lib_id "MCU:{name}") (at {x} {y} 0) (unit 1) (in_bom {"no" if ref.startswith("#") else "yes"}) (on_board {"no" if ref.startswith("#") else "yes"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-2.54} 0) {e}) (property "Value" {q(value)} (at {x} {y+h+2.54} 0) {e})')
    assignment=json.loads((P.parent/'footprints/assignments.json').read_text()).get('mcu-radio.'+ref)
    fp=assignment['footprint'] if assignment else None
    if fp:s.append(f'(property "Footprint" "NOVA_HW:{fp}" (at {x} {y} 0) (effects (font (size 1 1)) hide))')
    for pn,no,px,py,a,t in pins:s.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
    s.append(f'(instances (project "mcu-radio" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
    for pn,no,px,py,a,t in pins:
        xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
        if net is None:s.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
        dx,dy={0:(-5.08,0),270:(0,-5.08),90:(0,5.08)}[a];ex,ey=round(xx+dx,4),round(yy+dy,4)
        s.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
        s.append(f'(label {q(net)} (at {ex} {ey} 0) {e} (uuid "{uid(ref+no+"l")}"))')
notes=['OWNER BAND: 2.4GHz + US915MHz. One shared radio; no simultaneous independent radios or PHY/legal-power claim.',
'SWRC354 support + JTI IPC Rev2.0 + dual-feed antenna Rev3.1. External LNA bias BOTH bands; RF qualification OPEN.',
'SERVICE DIO4/pin9 != ROM DIO3/pin8. DIO30/pin43 now NC; no RF switch. One time-shared radio.',
'A101 NC pins2/3/5/6/7/8 must solder to isolated lands. Matching values are EVAL-BOARD STARTS, NOT qualified for28mm PCB.',
'Factory reset operates supervisor MR; MCU RESET_N takes RESET_OK. DIO18/pin28 fault reserve remains NC.']
for i,n in enumerate(notes):s.append(f'(text {q(n)} (at 20.32 {378+i*5.08} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid("note"+str(i))}"))')
s.append(')');(P/'mcu-radio.kicad_sch').write_text('\n'.join(s)+'\n')
(P/'mcu-radio.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in lib)+'\n)\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "MCU") (type "KiCad") (uri "${KIPRJMOD}/mcu-radio.kicad_sym") (options "") (descr "MCU support and dual-band frontend and antenna prototype; qualification open")))\n')
(P/'mcu-radio.kicad_pro').write_text('{"meta":{"filename":"mcu-radio.kicad_pro","version":1}}\n')
with (P/'pin-allocation.csv').open('w') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['package_pin','TI_pin_name','net','electrical_type','status'])
 for p in sorted(names):w.writerow([p,names[p],mcu_nets[p] or 'NC',types[p],'PROPOSED routing; source-verified physical pin'])
print('Generated support and dual-band frontend; antenna prototype captured; PCB/tuning/qualification remain incomplete')
