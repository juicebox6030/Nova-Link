from pathlib import Path
import json,math
P=Path(__file__).resolve().parent
raw=json.loads((P/'local-pairs.json').read_text());fix=json.loads((P/'repaired-pairs.json').read_text());changed=set(fix['changed']);rows=[r for r in raw['positive'] if not ({r['a'],r['b']}&changed)]+fix['positive'];rows=list({tuple(sorted((r['a'],r['b']))):r for r in rows}.values())
wire=json.loads((P/'wire-radius-check.json').read_text());wn=set(wire['changed']);rows=[r for r in rows if not ({r['a'],r['b']}&wn)]+wire['positive']
parts=json.loads((P/'actual-boards.json').read_text());pads={}
for board,d in parts.items():
 for c in d['components']:
  for i,p in enumerate(c['pads']):pads[f"{board}_{c['ref']}_Pad{p['number']}_{i}"]=(p,c['ref'],board)
allowed={}
def add(a,b,bound,basis):allowed[tuple(sorted((a,b)))]=(bound,basis)
for i in [0,1]:
 add('COL_StationarySpool','COL_FixedScrew'+str(i),.20,'Frozen M1 pilot thread engagement')
 add('RotorHalfPositiveY','COL_MovingScrew'+str(i),.20,'Frozen moving clamp M1 pilot thread engagement')
add('COL_StationarySpool','COL_IndexRearCap',3.2,'Frozen captive cap thread envelope')
for x in ['45_25','68_9']:
 for z in ['m29_5','29_5']:add('RotorHalfNegativeY','COL_FrameBolt_'+x+'_'+z,1.05,'Frozen bounded frame-screw pilot engagement')
for side in ['Front','Rear']:
 for sg in ['m','p']:add('StationaryCoreWithSupports','StationaryCapScrew'+side+sg,math.pi*(.5**2-.38**2)*1+1e-6,'1mm M1 pilot engagement; screw/material/strength unqualified')
for x in ['51_7','74_7']:add('RotorHalfPositiveY','MovingClampScrew'+x,math.pi*(.5**2-.38**2)*.74+1e-6,'0.74mm M1 pilot engagement; no head interference allowed')
for z in ['m17','17']:add('RotorHalfPositiveY','SourceEndGateScrew'+z,math.pi*(.5**2-.38**2)*2+1e-6,'2mm M1 pilot engagement; no head interference allowed')
for a,b,v in [('Trunk_L','L_TrunkToFuse',15),('Trunk_N','N_TrunkToCarrier',15.1),('Pin_N','N_TrunkToCarrier',.181),('Pin_L','L_FuseToCarrier',.261),('Pin_LVplus','SourceWireCopper1',.089),('Pin_LVminus','SourceWireCopper2',.089)]:add(a,b,v,'Named electrical endpoint envelope intersection; actual termination/insulation remains UNMET')
classified=[];bad=[]
for r in rows:
 a,b=r['a'],r['b'];key=tuple(sorted((a,b)));rule=allowed.get(key)
 for body,pad in [(a,b),(b,a)]:
  if body.endswith('_Body') and pad in pads and pad.startswith(body[:-5]+'_Pad'):
   pd,ref,board=pads[pad];rule=(pd['size'][0]*pd['size'][1]*.035+1e-7,'Specific own-component body allocation intersects its physical copper land; supplier package profile unresolved')
 if a in pads and b in pads:
  pa,ra,ba=pads[a];pb,rb,bb=pads[b]
  if (ba,ra,pa['number'],pa['net'])==(bb,rb,pb['number'],pb['net']):rule=(min(pa['size'][0]*pa['size'][1],pb['size'][0]*pb['size'][1])*.035+1e-7,'Source-defined duplicate same-number same-net land features, union copper not a short')
 if rule and r['volume']<=rule[0]:classified.append(dict(r,bound_mm3=rule[0],basis=rule[1]))
 else:bad.append(dict(r,rule=rule))
out={'status':'PASS' if not bad else 'FAIL','baseline_pairs':raw['pairs'],'fresh_repaired_pairs':fix['pairs'],'fresh_wire_pairs':wire['pairs'],'unchanged_parts':len(fix['unchanged_BRep_structure_numeric_tolerance_1e12']),'classified_contacts':classified,'unintended':bad,'basis':'Fresh two-part checks replace old pairs; all other BRep topology/tokens unchanged to1e-12 numerical save normalization. Frozen-frozen mechanism evidence retained. Relative rigid contacts remain invariant at all poses; cross-domain motion separately checked.'}
(P/'pair-classification.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(classified),'named contacts',len(bad),'UNINTENDED');print(json.dumps(bad,indent=2));assert not bad
