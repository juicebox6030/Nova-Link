"""Complete source-based lands; no shrinking. No parent footprint writes."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;D=P/'CellProtection.pretty';D.mkdir(exist_ok=True)
Q=P.parent/'power-service/qualified15-candidate'
records={}
# Copy existing exact, independently checked manufacturer-derived lands.
for name in ['DDC6','DBV6','DSG8','R0402','C0402']:
 src=Q/'Qualified.pretty'/(name+'.kicad_mod');shutil.copyfile(src,D/(name+'.kicad_mod'))
 r=json.loads((Q/'land-sources.json').read_text())[name]
 records[name]=r|{'read_only_origin':str(src)}
def create(name,pads,body,height,court,source):
 x,y=court[0]/2,court[1]/2
 z=[f'(footprint "{name}" (version 20241229) (generator "nova_cell_lands") (layer "F.Cu") (attr smd)',f'(descr "{source}")',f'(fp_rect (start {-x} {-y}) (end {x} {y}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))',f'(fp_rect (start {-body[0]/2} {-body[1]/2}) (end {body[0]/2} {body[1]/2}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))']
 for no,px,py,w,h in pads:z.append(f'(pad "{no}" smd {"circle" if w==h else "rect"} (at {px} {py}) (size {w} {h}) (layers "F.Cu" "F.Mask" "F.Paste") (solder_mask_margin .025))')
 z.append(')');(D/(name+'.kicad_mod')).write_text('\n'.join(z)+'\n')
 records[name]={'source':source,'body_max_mm':body,'height_max_mm':height,'courtyard_mm':court,'prototype_process':'NSMD +25um radial mask; full pad paste, reflow/stencil approval required'}
# TI PDF package outline is TOP ball-A1 corner at rowA/column1. Land pattern
# is footprint top view, NOT the package's bump-view pin-function illustration.
create('YZP6',[(row+str(col),x,y,.225,.225) for row,y in [('A',-.5),('B',0),('C',.5)] for col,x in [(1,-.25),(2,.25)]],[.972,1.472],.5,[1.472,1.972],'TI TPS22963C YZP0006 outline4219524-A and land example:0.5pitch,0.225round land; maxdie0.972x1.472')
# Littelfuse recommended total land span6.86, lands1.96x3.15; package
# length6.10+/-.20,width/height2.69+/-.25. No pixel-derived dimensions.
create('Fuse451',[(1,-2.45,0,1.96,3.15),(2,2.45,0,1.96,3.15)],[6.3,2.94],2.94,[7.36,3.65],'Littelfuse451-453 dimensions/padlayout:span6.86,land1.96x3.15; maxbody6.30x2.94x2.94')
(P/'land-sources.json').write_text(json.dumps(records,indent=2)+'\n')
print('Complete source/derived footprints',len(records))
