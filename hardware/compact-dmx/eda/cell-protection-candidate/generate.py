"""One independent hardware prototype; no parent generator import or writes."""
from pathlib import Path
import json,uuid,csv
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v))
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-cell-protection/'+v))
effect='(effects (font (size .8 .8)))'
lib={};parts=[];meta={}
def symbol(name,pins):
 h=(len(pins)+1)*1.27
 lib[name]=([(str(no),pn,-15.24,h-(i+1)*2.54,t) for i,(no,pn,t) in enumerate(pins)],h)
symbol('TPS3700',[(1,'OUTA','open_collector'),(2,'GND','power_in'),(3,'INA_PLUS','input'),(4,'INB_MINUS','input'),(5,'VDD','power_in'),(6,'OUTB','open_collector')])
symbol('TPS3808',[(1,'RESET_N','open_collector'),(2,'GND','power_in'),(3,'MR_N','input'),(4,'CT','input'),(5,'SENSE','input'),(6,'VDD','power_in')])
symbol('TPS22963C',[('A1','VOUT','power_out'),('B1','VOUT','passive'),('A2','VIN','power_in'),('B2','VIN','passive'),('C1','GND','power_in'),('C2','ON','input')])
symbol('BQ25173',[(1,'IN','power_in'),(2,'ISET','input'),(3,'CE_DISABLE','input'),(4,'GND','power_in'),(5,'STAT_N','open_collector'),(6,'PG_N','open_collector'),(7,'FB','input'),(8,'OUT','power_out'),(9,'EP_GND','power_in')])
for name in ['R','C','F']:symbol(name,[(1,'1','passive'),(2,'2','passive')])
symbol('SOURCE_BOUNDARY',[(1,'LIMITED_5V_FROM_EXISTING_EFUSE','passive'),(2,'GND_USB','passive'),(3,'CHARGE_DISABLE_FROM_EXISTING_LOGIC','output')])
symbol('CELL_BOUNDARY',[(1,'25F_CELL_POSITIVE_TAB','passive'),(2,'25F_CELL_NEGATIVE_TAB','passive')])
symbol('BOOST_BOUNDARY',[(1,'EXISTING_CAP_POS_BOOST_AND_SENSE','passive'),(2,'GND_USB','passive')])
lib['POWER_FLAG']=([('1','ACTUAL_SOURCE',0,0,'power_out')],0)
def add(name,ref,value,nets,footprint,x,y,kind='added',role=''):
 parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y))
 meta[ref]={'kind':kind,'footprint':footprint,'role':role}
g='GND_USB';v='LIMITED_5V';cp='CAP_POS';tab='CELL_TAB_POS'
add('TPS3700','U101','TPS3700DDCR',{1:None,2:g,3:g,4:'CELL_OV_SENSE',5:v,6:'CHARGER_PERMIT_OD'},'DDC6',60.96,48.26,role='Independent cell overvoltage')
add('TPS3808','U102','TPS3808G33DBVR',{1:'CHARGER_PERMIT_OD',2:g,3:v,4:None,5:v,6:v},'DBV6',167.64,48.26,role='Independent monitor-startup inhibit, CT open12..28ms')
add('TPS22963C','U103','TPS22963CYZPR',{'A1':'CHARGER_IN_PROTECTED','B1':'CHARGER_IN_PROTECTED','A2':v,'B2':v,'C1':g,'C2':'CHARGER_SWITCH_ON'},'YZP6',274.32,48.26,role='Charger input disconnect; no quick output discharge')
add('BQ25173','U104','BQ25173DSGR',{1:'CHARGER_IN_PROTECTED',2:'ICHG_PIN',3:'CHARGE_DISABLE',4:g,5:None,6:None,7:'VCHG_FB',8:cp,9:g},'DSG8',60.96,134.62,'existing_context','Existing charger, no main path change')
def two(name,ref,value,a,b,fp,x,y,kind='added',role=''):
 add(name,ref,value,{1:a,2:b},fp,x,y,kind,role)
two('F','F101','045101.5MRL 1.5A non-resettable',tab,cp,'Fuse451',167.64,134.62,role='FIRST cell positive element before charger/boost branch split')
def res(ref,ohm,a,b,x,y,kind='added',role='',tcr='Y'):
 code=(str(ohm)+'R') if ohm<1000 else f'{ohm/1000:.2f}'.rstrip('0').rstrip('.').replace('.','K')
 if ohm>=1000 and 'K' not in code:code+='K0'
 two('R',ref,'TNPW0402'+code+'B'+tcr+'ED '+str(ohm)+'ohm',a,b,'R0402',x,y,kind,role)
res('R101',56500,tab,'CELL_OV_SENSE',40.64,198.12,role='OV top0.1%10ppm')
res('R102',10000,'CELL_OV_SENSE',g,96.52,198.12,role='OV bottom0.1%10ppm')
res('R103',82000,v,'CHARGER_PERMIT_OD',152.4,198.12,role='Hardware permit pullup')
res('R104',10000,'CHARGER_PERMIT_OD','CHARGER_SWITCH_ON',208.28,198.12,role='ON low-state attenuation')
res('R105',56000,'CHARGER_SWITCH_ON',g,264.16,198.12,role='ON default pulldown')
res('R201',22200,cp,'VCHG_FB',40.64,233.68,'tuned_existing','BQ feedback top changes22.5k to22.2k,0.1%10ppm')
res('R202',10000,'VCHG_FB',g,96.52,233.68,'tuned_existing','BQ feedback bottom remains10k, tighten10ppm')
res('R203',11900,'ICHG_FILTER',g,152.4,233.68,'existing_context','Existing25mA nominal charge',tcr='E')
res('R204',100,'ICHG_PIN','ICHG_FILTER',208.28,233.68,'existing_context','Existing ISET filter',tcr='E')
for ref,value,rail,x,y,kind,role in [
 ('C101','GRM155R71E104KE14D 100nF',v,40.64,266.7,'added','U101 local bypass'),
 ('C102','GRM155R71E104KE14D 100nF',v,96.52,266.7,'added','U102 local bypass'),
 ('C103','GRM155R61C105KA12D 1uF',v,152.4,266.7,'added','U103 local input'),
 ('C104','GRM155R61C105KA12D 1uF','CHARGER_IN_PROTECTED',208.28,266.7,'added','U103 local output'),
 ('C201','GRM155R61C105KA12D 1uF','CHARGER_IN_PROTECTED',264.16,266.7,'existing_context','BQ input bypass'),
 ('C202','GRM155R61C105KA12D 1uF',cp,320.04,266.7,'added','BQ local1uF output filter; fuse separates cell and adds lead inductance'),
 ('C203','GRM155R71E104KE14D 100nF','ICHG_FILTER',320.04,233.68,'existing_context','Existing ISET filter')]:two('C',ref,value,rail,g,'C0402',x,y,kind,role)
add('SOURCE_BOUNDARY','X1','EXISTING source/control boundary, no purchased connector',{1:v,2:g,3:'CHARGE_DISABLE'},'',274.32,129.54,'boundary')
add('CELL_BOUNDARY','X2','Eaton HV1625-2R7256-R 25F, actual cell assembly owned by Astra',{1:tab,2:g},'',365.76,48.26,'boundary')
add('BOOST_BOUNDARY','X3','Existing cap-only boost/UVLO/arm boundary',{1:cp,2:g},'',365.76,129.54,'boundary')
for i,net in enumerate([v,g,tab]):add('POWER_FLAG','#FLG'+str(i+1),'Actual external source/return',{'1':net},'',40.64+i*71.12,294.64,'flag')
def definition(name):
 pins,h=lib[name]
 z=[f'(symbol {q(name)} (pin_names (offset .508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 {h+2.54} 0) {effect}) (property "Value" {q(name)} (at 0 {-h-2.54} 0) {effect})',f'(symbol {q(name+"_0_1")} (rectangle (start -12.7 {h}) (end 15.24 {-h}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol {q(name+"_1_1")}']
 for no,pn,x,y,typ in pins:z.append(f'(pin {typ} line (at {x} {y} 0) (length 2.54) (name {q(pn)} {effect}) (number {q(no)} {effect}))')
 return ''.join(z)+'))'
root=uid('root');lines=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A2") (title_block (title "NOVA 25F cell OVP + cell-local fuse prototype") (rev "CP-1")) (lib_symbols']
for name in lib:lines.append(definition(name).replace('(symbol '+q(name)+' ','(symbol '+q('CP:'+name)+' ',1))
lines.append(')')
for name,ref,value,nets,x,y in parts:
 pins,h=lib[name];m=meta[ref];physical=m['kind'] not in ['boundary','flag']
 lines.append(f'(symbol (lib_id "CP:{name}") (at {x} {y} 0) (unit 1) (in_bom {"yes" if physical else "no"}) (on_board {"yes" if physical else "no"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-3.81} 0) {effect}) (property "Value" {q(value)} (at {x} {y+h+3.81} 0) {effect}) (property "Role" {q(m["role"])} (at {x} {y} 0) (effects (font (size .7 .7)) hide)) (property "Scope" {q(m["kind"])} (at {x} {y} 0) (effects (font (size .7 .7)) hide))')
 if physical:lines.append(f'(property "Footprint" "CP:{m["footprint"]}" (at {x} {y} 0) (effects (font (size 1 1)) hide))')
 for no,_,_,_,_ in pins:lines.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
 lines.append(f'(instances (project "cell-protection" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
 for no,pn,px,py,typ in pins:
  xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
  if net is None:lines.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
  end=round(xx-5.08,4)
  lines.append(f'(wire (pts (xy {xx} {yy}) (xy {end} {yy})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
  lines.append(f'(label {q(net)} (at {end} {yy} 0) {effect} (uuid "{uid(ref+no+"net")}"))')
notes=['PROTOTYPE ONLY: added F101,U101..103,R101..105,C101..104,C202. Existing charger shown completely; parent integration pending.',
 'F101 first at cell positive tab BEFORE ALL charger/boost branches. Cell tab-to-fuse conductor must be short, insulated and mechanically restrained.',
 'U103 interrupts BQ input, including BQ IN-OUT short; not a cell-discharge switch. U101 senses actual cell tab independently of BQ feedback.',
 'U102 holds ON low during monitor startup/brownout. OV fault opens U103; hysteretic retry, not a latched OVP. No firmware dependency.',
 'PROPOSED charger tuning2.576V, same25mA: top22.2k/bottom10k both0.1%10ppm. No sibling edits. Healthy overshoot5mV allocation requires bench proof.',
 'Fault-turnoff max absent; fuse I2t/resistance nominal only. Decaying fault clearing/temperature/voltage overshoot UNMET. Not all-single-fault safe.',
 'Boundaries are external circuits/cell assembly, not invented physical connector pads. No layout fit or manufacturing-release claim.']
for i,n in enumerate(notes):lines.append(f'(text {q(n)} (at 20.32 {320.04+i*4.5} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid("note"+str(i))}"))')
lines.append(')');(P/'cell-protection.kicad_sch').write_text('\n'.join(lines)+'\n')
(P/'cell-protection.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in lib)+'\n)\n')
(P/'cell-protection.kicad_pro').write_text('{"meta":{"version":1}}\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "CP") (type "KiCad") (uri "${KIPRJMOD}/cell-protection.kicad_sym") (options "") (descr "Independent cell protection prototype")))\n')
(P/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "CP") (type "KiCad") (uri "${KIPRJMOD}/CellProtection.pretty") (options "") (descr "Source-based prototype lands")))\n')
with (P/'component-ledger.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['reference','value','kind','footprint','role'])
 for name,ref,value,nets,x,y in parts:w.writerow([ref,value,meta[ref]['kind'],meta[ref]['footprint'],meta[ref]['role']])
print('Captured',sum(m['kind']=='added' for m in meta.values()),'added protection parts,2 tuned existing resistors, complete BQ context; no physical boundary pads')
