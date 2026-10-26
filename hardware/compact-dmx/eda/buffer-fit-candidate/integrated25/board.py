from pathlib import Path
import pcbnew as K,hashlib,json,shutil
P=Path(__file__).resolve().parent
src=P.parents[1]/'power-service/qualified15-candidate/qualified15-placement.kicad_pcb'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='fc0785cdaaf874002b2362835070f29f00b187e4054dd3ab093c43e177ea035f'
b=K.LoadBoard(str(src));cell=next(f for f in b.GetFootprints() if f.GetReference()=='C23');nets={p.GetNumber():p.GetNet() for p in cell.Pads()};print({k:v.GetNetname() for k,v in nets.items()})
mod='''(footprint "HV1625_formed_ENGINEERING" (version 20241229) (generator "buffer25") (layer "F.Cu")
(descr "Engineering proposed formed leads; not Eaton recommended land pattern. Slots accommodate pitch; supplier forming gate.")
(attr through_hole)
(property "Reference" "C23" (at 0 -5.5) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
(property "Value" "HV1625-2R7256-R 25F 2.7V" (at 0 5.5) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
(pad "1" thru_hole oval (at 0 -3.75) (size 1.7 2.7) (drill oval 1.1 2.1) (layers "*.Cu" "*.Mask"))
(pad "2" thru_hole oval (at 0 3.75) (size 1.7 2.7) (drill oval 1.1 2.1) (layers "*.Cu" "*.Mask"))
(fp_rect (start -1 -5.25) (end 1 5.25) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
(fp_text user "+" (at -1.5 -3.75) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
)'''
(P/'Buffer25.pretty/HV1625_formed_ENGINEERING.kicad_mod').write_text(mod)
f=K.FootprintLoad(str(P/'Buffer25.pretty'),'HV1625_formed_ENGINEERING');f.SetReference('C23');f.SetValue('HV1625-2R7256-R 25F 2.7V');f.SetPosition(K.VECTOR2I(K.FromMM(57.9),K.FromMM(30.65)));b.Remove(cell);b.Add(f)
for p in f.Pads():p.SetNet(nets[p.GetNumber()])
def v(x,y):return K.VECTOR2I(K.FromMM(x),K.FromMM(y))
def line(a,z):
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_SEGMENT);s.SetStart(v(*a));s.SetEnd(v(*z));s.SetLayer(K.Edge_Cuts);s.SetWidth(K.FromMM(.05));b.Add(s)
def arc(a,m,z):
 s=K.PCB_SHAPE();s.SetShape(K.SHAPE_T_ARC);s.SetArcGeometry(v(*a),v(*m),v(*z));s.SetLayer(K.Edge_Cuts);s.SetWidth(K.FromMM(.05));b.Add(s)
x0,x1,y0,y1,r=26.5,55.9,25.5,35.8,.5;q=r*(1-2**-.5)
line((x0+r,y0),(x1-r,y0));arc((x1-r,y0),(x1-q,y0+q),(x1,y0+r));line((x1,y0+r),(x1,y1-r));arc((x1,y1-r),(x1-q,y1-q),(x1-r,y1));line((x1-r,y1),(x0+r,y1));arc((x0+r,y1),(x0+q,y1-q),(x0,y1-r));line((x0,y1-r),(x0,y0+r));arc((x0,y0+r),(x0+q,y0+q),(x0+r,y0))
K.SaveBoard(str(P/'integrated25.kicad_pcb'),b)
shutil.copyfile(src.with_suffix('.kicad_pro'),P/'integrated25.kicad_pro')
(P/'board-input.json').write_text(json.dumps({'path':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'C23_nets':{k:v.GetNetname() for k,v in nets.items()},'aperture':[x0,y0,x1,y1,r],'source_footprints':len(b.GetFootprints()),'tracks':len(b.GetTracks())},indent=2)+'\n')
