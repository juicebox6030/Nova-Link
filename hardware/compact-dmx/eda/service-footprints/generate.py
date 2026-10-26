"""Source-dimensioned candidates; run existing Flatpak KiCad Python. No baseline edits."""
from pathlib import Path
import pcbnew as K,json,math
P=Path(__file__).resolve().parent;L=P/'Service.pretty'
def rect(x1,y1,x2,y2,layer):return f'(fp_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width .05) (type default)) (fill none) (layer "{layer}"))'
def smd(n,x,y,w,h,layers='"F.Cu" "F.Mask" "F.Paste"'):return f'(pad "{n}" smd rect (at {x} {y}) (size {w} {h}) (layers {layers}))'
def th(n,x,y,w,h,dx,dy):return f'(pad "{n}" thru_hole oval (at {x} {y}) (size {w} {h}) (drill oval {dx} {dy}) (layers "*.Cu" "*.Mask"))'
def save(name,desc,items):
 s=f'(footprint "{name}" (version 20241229) (generator "nova_service_source") (layer "F.Cu") (descr "{desc}") (fp_text reference "REF**" (at 0 -4) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))\n'+ '\n'.join(items)+'\n)\n';(L/(name+'.kicad_mod')).write_text(s)
# NOR terminal geometry from Renesas RevH p59; land/stencil allowances are explicit engineering choices.
a=[]
for i in range(4):a += [smd(i+1,-2.7,-1.905+1.27*i,1.2,.6),smd(8-i,2.7,-1.905+1.27*i,1.2,.6)]
a += [smd(9,0,0,3.4,4,'"F.Cu" "F.Mask"')]
for x in [-.8,.8]:
 for y in [-.95,.95]:a.append(smd('',x,y,1.4,1.7,'"F.Paste"'))
a += [rect(-3,-2.5,3,2.5,'F.Fab'),rect(-3.55,-2.8,3.55,2.8,'F.CrtYd')]
save('AT25SF161B_MHB_Derived','Renesas DS-AT25SF161B-188H p59 package; derived prototype lands NOT manufacturer land recommendation; EP9 ground recommended; paste70percent design choice',a)
# Hirose datum: midpoint of six signal TH holes; +y toward mating edge.
row=['B12','B11','B10']+['A'+str(i) for i in range(1,13)]+['B3','B2','B1'];a=[]
for i,n in enumerate(row):
 x=-3.4+.4*i;a.append(smd(n,x,-.925,.23,.85,'"F.Cu" "F.Mask"'));a.append(smd('',x,-.925,.23 if i in (0,17) else .25,.85,'"F.Paste"'))
for i,n in enumerate(['B9','B8','B7','B6','B5','B4']):
 x=-2+.8*i;a.append(th(n,x,0,.6,.6,.4,.4));a.append(f'(pad "" smd circle (at {x} 0) (size .6 .6) (layers "F.Paste"))')
# Six physical shell attachments share proposed identifier SH; no schematic binding is invented.
for x in [-3.915,3.915]:a.append(smd('SH',x,-.925,.46,.85))
for x in [-5.55,5.55]:
 a.append(th('SH',x,-.45,1.2,2.3,.6,1.7));a.append(smd('',x,-.45,1.2,2.3,'"F.Paste"'))
 # Lower shell copper includes inward rectangular extension (dimension9.7); outer oval gives R.6.
 a.append(th('SH',x,4.6,1.2,2.3,.6,1.7))
 inward=x+(.25 if x<0 else -.25)
 a.append(smd('SH',inward,4.6,.9,2.3,'"F.Cu" "B.Cu" "F.Mask" "B.Mask"'))
 a.append(smd('',x+(.05 if x<0 else -.05),4.6,1.3,2.3,'"F.Paste"'))
a +=[rect(-5.7,-1.15,5.7,7.2,'F.Fab'),rect(-6.4,-1.85,6.4,7.45,'F.CrtYd')]
# Dimensioned routed notch guide on drawings layer, not automatic Edge.Cuts insertion.
for x in [-4.67,4.67]:a.append(f'(fp_line (start {x} .85) (end {x} 7.2) (stroke (width .1) (type default)) (layer "Dwgs.User"))')
a.append('(fp_line (start -4.37 .55) (end 4.37 .55) (stroke (width .1) (type default)) (layer "Dwgs.User"))')
for sign in [-1,1]:
 x=sign*4.37;a.append(f'(fp_arc (start {sign*4.67} .85) (mid {x+sign*.212132} .637868) (end {x} .55) (stroke (width .1) (type default)) (layer "Dwgs.User"))')
save('CX70M_24P1_IntegrationCandidate','Hirose EDC3-61479 p1 / guide Rev2 pp5,11,12; datum six TH midpoint; nominal .8mm PCB only; shell SH absent from circuit; stencil corner simplification/process approval OPEN',a)
# Inspection board only, not the product placement.
b=K.BOARD()
for ref,name,x in [('U2','AT25SF161B_MHB_Derived',20),('J_USB','CX70M_24P1_IntegrationCandidate',45)]:
 f=K.FootprintLoad(str(L),name);f.SetReference(ref);f.SetPosition(K.VECTOR2I(K.FromMM(x),K.FromMM(20)));b.Add(f)
K.SaveBoard(str(P/'footprints.kicad_pcb'),b)
(P/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "NOVA_SERVICE") (type "KiCad") (uri "${KIPRJMOD}/Service.pretty") (options "") (descr "Unplaced source-derived service candidates")))\n')
print('2 editable candidates; USB shell unresolved; NOR land/process choices explicit')
