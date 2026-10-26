from pathlib import Path
import FreeCAD as A,Part,json
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());exports=[]
exclude={'UNMET_INTERFACE','screen','collar_reserve','insulation','tolerance','trunk_tolerance','support','access'}
base=[n for n in S if G[n] not in exclude and not G[n].endswith('_pad') and not n.startswith('COL_Flex_')]
td=A.newDocument('Exploded');items=[]
for n in base+['COL_Flex_0']:
 s=S[n].copy();shift=V()
 if n=='RotorHalfPositiveY':shift=V(0,45,0)
 elif n=='RotorHalfNegativeY':shift=V(0,-45,0)
 elif n.startswith('rotating_'):shift=V(10,20,0)
 elif n.startswith('stationary_'):shift=V(-10,0,15)
 elif n.startswith('SourceEndGate'):shift=V(20,0,0)
 elif n.startswith('MovingFanout') or n.startswith('MovingClamp'):shift=V(0,0,-25)
 elif n.startswith('FixedFanout'):shift=V(0,0,-15)
 s.translate(shift);o=td.addObject('PartDesign::Feature',n);o.Shape=s;items.append(o)
Part.export(items,str(P/'assembly-exploded.step'));exports.append(P/'assembly-exploded.step');A.closeDocument(td.Name)
