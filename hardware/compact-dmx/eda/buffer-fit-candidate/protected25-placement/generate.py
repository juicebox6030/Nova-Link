"""Execute frozen generator declarations locally, insert actual protection parts, then render KiCad."""
from pathlib import Path
P=Path(__file__).resolve().parent
source=(P/'qualified-generator-frozen.py').read_text()
cut=source.index('# Candidate structure, exact source/pin maps')
ns={'__file__':str(P/'generate.py')};exec(compile(source[:cut],str(P/'qualified-generator-frozen.py'),'exec'),ns)
cp=(P/'protection-generator-frozen.py').read_text();c={'__file__':str(P/'generate.py')};exec(compile(cp[:cp.index('def definition(name):')],str(P/'protection-generator-frozen.py'),'exec'),c)
parts=ns['parts'];meta=ns['meta'];roles={m['role']:r for r,m in meta.items()}
context={'U104':'U3','R201':roles['R_VCHG_TOP'],'R202':roles['R_VCHG_BOTTOM'],'R203':roles['R_ICHG'],'R204':roles['R_ICHG_FILTER'],'C201':next(r for r,m in meta.items() if r.startswith('C') and m['role']=='C_CHGIN'),'C203':next(r for r,m in meta.items() if r.startswith('C') and m['role']=='C_ICHG')}
# Replace roles only; preserve all other pins including control-sheet signals.
cp_by={p[1]:p for p in c['parts']}
for i,(name,ref,value,nets,x,y) in enumerate(parts):
 nets=dict(nets)
 if ref=='U3':nets['1']='CHARGER_IN_PROTECTED'
 if ref==context['C201']:nets['1']='CHARGER_IN_PROTECTED'
 if ref==roles['R_VCHG_TOP']:value=cp_by['R201'][2]
 if ref==roles['R_VCHG_BOTTOM']:value=cp_by['R202'][2]
 if ref=='C23':nets['1']='CELL_TAB_POS';value='HV1625-2R7256-R 25F 2.7V'
 parts[i]=(name,ref,value,nets,x,y)
for name,ref,value,nets,x,y in c['parts']:
 if c['meta'][ref]['kind']!='added':continue
 new='CP_'+name
 pins,h=c['lib'][name];ns['lib'][new]=([(pn,no,px,py,0,t) for no,pn,px,py,t in pins],15.24,h)
 parts.append((new,ref,value,nets,0,0));m=c['meta'][ref]
 meta[ref]={'role':m['role'],'sheet':'main','body_mm2':0,'package':m['footprint'],'kind':'physical','note':'Source cell-protection candidate; placement not protection qualification'}
import json
(P/'context-map.json').write_text(json.dumps(context,indent=2)+'\n')
# More A1 main rows for new parts: move lower passive rows to avoid notes/flags.
suffix=source[cut:].replace('365.76+(j//13)*30.48','365.76+(j//13)*25.4')
exec(compile(suffix,str(P/'qualified-generator-frozen.py'),'exec'),ns)
(P/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Q15") (type "KiCad") (uri "${KIPRJMOD}/Qualified.pretty") (options "") (descr "Frozen qualified lands plus protection")) (lib (name "CP") (type "KiCad") (uri "${KIPRJMOD}/CellProtection.pretty") (options "") (descr "Protection")) (lib (name "Buffer25") (type "KiCad") (uri "${KIPRJMOD}/Buffer25.pretty") (options "") (descr "Engineered cell")))\n')
import shutil
for p in (P/'CellProtection.pretty').glob('*'):shutil.copyfile(p,P/'Qualified.pretty'/p.name) if not (P/'Qualified.pretty'/p.name).exists() else None

# Preserve the actual engineered cell land assignment, not the superseded15F context land.
p=P/'qualified15.kicad_sch'
p.write_text(p.read_text().replace('"Q15:Cell_leads"','"Buffer25:HV1625_formed_ENGINEERING"'))
