"""Real KiCad CLI export/ERC and exhaustive partial-sheet connectivity assertions.
No synthesized netlist, ERC exclusions, or whole-product completion claims.
"""
from pathlib import Path
import subprocess,xml.etree.ElementTree as E,json,hashlib
P=Path(__file__).resolve().parent
cli=['flatpak','run','--command=kicad-cli','org.kicad.KiCad']
def run(*args):return subprocess.run(cli+list(args),check=True,text=True,capture_output=True).stdout.strip()
version=run('version');sch=P/'dmx-interface.kicad_sch'
run('sch','export','netlist','--format','kicadxml','-o',str(P/'dmx-interface.net'),str(sch))
run('sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(P/'dmx-erc.json'),str(sch))
run('sch','export','svg','-o',str(P/'rendered'),str(sch))
run('sch','export','pdf','-o',str(P/'dmx-interface.pdf'),str(sch))
r=E.parse(P/'dmx-interface.net');components={c.attrib['ref'] for c in r.findall('./components/comp')}
assert components=={'U5','R1','R2','R3','C1','C2','C3','C4','R4','X1','J1','S_TERM','R_TERM1','R_TERM2'},components
nets={n.attrib['name'].removeprefix('/'):{(x.attrib['ref'],x.attrib['pin']):x.attrib['pintype'] for x in n} for n in r.findall('./nets/net')}
expected={
 'SYS_3V3':{'U5.1','U5.9','R2.1','C1.1','C2.1','X1.1'},
 'GND_USB':{'U5.6','U5.10','R1.2','R3.2','C1.2','C2.2','X1.2'},
 'DMX_TX':{'U5.2','X1.3'},'DMX_DE_SAFE':{'U5.3','R1.1','X1.4'},
 'DMX_RX':{'U5.4','X1.6'},'DMX_RE_N':{'U5.5','R2.2','X1.5'},
 'DMX_POWER_EN':{'R4.1','R3.1','X1.7'},'ISOW_EN_PIN':{'R4.2','U5.8'},
 'GND_ISO':{'U5.11','U5.13','U5.14','U5.15','C3.2','C4.2','J1.1'},
 'ISO_3V3':{'U5.12','U5.16','C3.1','C4.1'},
 'DMX_P':{'U5.17','U5.20','J1.3','S_TERM.2'},'DMX_N':{'U5.18','U5.19','J1.2','R_TERM1.2','R_TERM2.2'},
 'TERM_SW':{'S_TERM.3','R_TERM1.1','R_TERM2.1'},
 'unconnected-(S_TERM-Pad1)':{'S_TERM.1'},
 'unconnected-(U5-OUT-Pad7)':{'U5.7'}}
assert r.find("./components/comp[@ref='R4']/value").text=='CRCW04021K00FKED 1k 1%'
for ref in ('R_TERM1','R_TERM2'):assert r.find(f"./components/comp[@ref='{ref}']/value").text=='CRCW1206240RFKEA 240R 1% 0.25W'
assert r.find("./components/comp[@ref='S_TERM']/value").text=='PCM12SMTR OFF=1-2 / ON=2-3'
assert set(nets)==set(expected),set(nets)
for name,pins in expected.items():assert {'.'.join(node) for node in nets[name]}==pins,(name,nets[name])
types={1:'power_in',2:'input',3:'input',4:'output',5:'input',6:'power_in',7:'output+no_connect',8:'input',9:'power_in',10:'power_in',11:'power_in',12:'power_out',13:'input',14:'input',15:'power_in',16:'power_in',17:'output',18:'output',19:'input',20:'input'}
for n,t in types.items():assert [typ for nodes in nets.values() for (ref,pin),typ in nodes.items() if ref=='U5' and pin==str(n)]==[t],n
assert not set(nets['GND_USB']) & set(nets['GND_ISO'])
erc=json.loads((P/'dmx-erc.json').read_text());violations=[v for sh in erc['sheets'] for v in sh['violations']];assert not violations,violations
report={'status':'PASS','kicad_version':version,'exported_components':14,'intended_circuit_components':12,'explicit_boundary_components':['X1','J1'],'nets_total':15,'connected_nets':13,'intentional_nc_nets':2,'erc_errors':0,'erc_warnings':0,'erc_exclusions':0,'all_U5_pins_and_passive_nodes_verified':True,'scope':'PARTIAL isolated DMX sheet only. X1 specifies external power/control obligations; no full-product/ERC/PCB/hardware qualification.'}
report['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [sch,P/'nova-dmx.kicad_sym',P/'dmx-interface.kicad_pro',P/'dmx-interface.net',P/'dmx-erc.json']}
(P/'kicad-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
