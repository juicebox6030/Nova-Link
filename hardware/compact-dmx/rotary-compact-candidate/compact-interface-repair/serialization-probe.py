from pathlib import Path
import FreeCAD as A,difflib
P=Path(__file__).resolve().parent;a=A.openDocument(str(P/'before-head-clearance.FCStd'));b=A.openDocument(str(P/'interface-prototype.FCStd'))
for n in ['MovingFanoutDielectric0','COL_Flex_0']:
 x=a.getObject(n).Shape.cleaned().exportBrepToString();y=b.getObject(n).Shape.cleaned().exportBrepToString();print(n,'CLEAN EQUAL',x==y,flush=True)
 if x!=y:print('\n'.join(list(difflib.unified_diff(x.splitlines(),y.splitlines()))[:30]),flush=True)
