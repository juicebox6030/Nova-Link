import FreeCAD as A,json
from pathlib import Path
P=Path(__file__).resolve().parent;d=A.openDocument(str(P.parent/'collar-source-integrated/integrated.FCStd'))
names=['USBPlugApproach','SRC_J1_maximum_body_allocation','StationaryCoreEnvelope','FixedStaticTail','IndexPin','IndexKnob']
out={}
for n in names:
 o=d.getObject(n);bb=o.Shape.BoundBox;out[n]={'bounds':[bb.XMin,bb.XMax,bb.YMin,bb.YMax,bb.ZMin,bb.ZMax],'volume':o.Shape.Volume}
(P/'comparison-source.json').write_text(json.dumps(out,indent=2));print(out)
