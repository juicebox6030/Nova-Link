from pathlib import Path
import json,math
P=Path(__file__).resolve().parent;d=json.loads((P/'cad-check.json').read_text());allow={}
def pair(a,b,limit,kind):allow[frozenset((a,b))]=(limit,kind)
for x in ['m110','m32']:
 for y in ['m32','32']:pair('ClosureScrew_'+x+'_'+y,'LowerShellPosts',math.pi*(1-.8**2)*4+1e-6,'M2 shaft / diameter1.6 pilot,4mm engagement; unqualified thread')
for i in range(4):pair('CarrierScrew'+str(i),'LowerShellPosts',math.pi*(1-.8**2)*4.4+1e-6,'M2 shaft / diameter1.6 pilot,4.4mm engagement; unqualified thread')
for a,b,v in [('Pin_L','FuseToLinePin',.6),('Pin_N','NeutralBranch',.3),('Pin_LVplus','SourceWireCopper1',.11),('Pin_LVminus','SourceWireCopper2',.11),('TrunkL','LineToFuse',16),('TrunkN','NeutralBranch',16)]:pair(a,b,v,'Named electrical endpoint envelope overlap; solder/splice process UNQUALIFIED')
rows=[];bad=[]
for r in d['positive_pairs']:
 lim,kind=allow.get(frozenset((r['a'],r['b'])),(0,'UNINTENDED'));row={**r,'limit_mm3':lim,'classification':kind};rows.append(row)
 if r['volume']>lim:bad.append(row)
o={'new_physical_pairs':d['new_vs_physical_pairs'],'classified_positive_pairs':rows,'unintended':bad,'reservation_crossings_not_waived':d['unqualified_reservation_crossings'],'bounded_geometry_status':'PASS' if not bad and not d['lock_access_collisions'] else'FAIL','whole_product_status':'HOLD: unbuilt joints, electrical and insulation qualification'}
(P/'classified.json').write_text(json.dumps(o,indent=2)+'\n');print(o['bounded_geometry_status'],len(rows),'NAMEDCONTACTS',len(bad),'UNINTENDED');assert not bad
