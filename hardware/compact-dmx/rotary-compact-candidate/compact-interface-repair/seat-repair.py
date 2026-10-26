from pathlib import Path
import FreeCAD as A,Part,json,hashlib,shutil
P=Path(__file__).resolve().parent;V=A.Vector
# Pure subtractive repair, also executed by generator before save.
def repair(O):
 core=O['StationaryCoreWithSupports'].Shape
 cap=O['StationaryCornerCapFrontp'].Shape
 core=core.cut(cap)
 s=O['RotorHalfPositiveY'].Shape
 s=s.cut(Part.makeBox(24.2,.8,2.2,V(51.1,26.35,-16.1)))
 for x in [51.7,74.7]:
  s=s.cut(Part.makeCylinder(.38,.84,V(x,25.4,-15),V(0,1,0)))
  s=s.cut(Part.makeCylinder(.55,.86,V(x,26.24,-15),V(0,1,0)))
  s=s.cut(Part.makeCylinder(1.05,10,V(x,27.1,-15),V(0,1,0)))
 s=s.cut(Part.makeBox(10,100,100,V(84.2,-50,-50)))
 for z in [-17,17]:s=s.cut(Part.makeCylinder(.38,2.2,V(82.1,29,z),V(1,0,0)))
 for n,new in [('StationaryCoreWithSupports',core),('RotorHalfPositiveY',s)]:
  old=O[n].Shape;assert new.isValid() and len(new.Solids)==1,(n,len(new.Solids));assert new.cut(old).Volume<1e-7;O[n].Shape=new
if globals().get('APPLY_TO_GENERATOR',False):
 repair(O)
else:
 src=P/'interface-prototype.FCStd';backup=P/'before-seat-repair.FCStd';assert not backup.exists();shutil.copyfile(src,backup);d=A.openDocument(str(src));O={o.Name:o for o in d.Objects if hasattr(o,'Shape')};repair(O);d.recompute();d.saveAs(str(src));print('SUBTRACTIVE SEATS PASS',flush=True)
