"""Candidate-only editable lands. Manufacturer example dimensions, not DFM release.
Coordinates in mm, top view, pin1 upper left. No library installation required.
"""
from pathlib import Path
import json,shutil,math
P=Path(__file__).resolve().parent;D=P/'Qualified.pretty';D.mkdir(exist_ok=True)
sources={};bounds={}
def footprint(name,body,pads,source,height,notes='',poly=None):
    # pads: number,x,y,w,h; same-number overlapping primitives form RPW L lands.
    x=max(body[0]/2,max(abs(p[1])+p[3]/2 for p in pads))+.25
    y=max(body[1]/2,max(abs(p[2])+p[4]/2 for p in pads))+.25
    b=[f'(footprint "{name}" (version 20241229) (generator "nova_q15_lands") (layer "F.Cu") (attr smd)',
       f'(descr "{source}; {notes}")',
       '(fp_text reference "REF**" (at 0 0) (layer "F.Fab") (effects (font (size .6 .6) (thickness .1))))',
       f'(fp_rect (start {-body[0]/2} {-body[1]/2}) (end {body[0]/2} {body[1]/2}) (stroke (width .05) (type default)) (fill none) (layer "F.Fab"))',
       f'(fp_rect (start {-x} {-y}) (end {x} {y}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))']
    for no,px,py,w,h in pads:
        b.append(f'(pad "{no}" smd roundrect (at {px} {py}) (size {w} {h}) (layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio {min(.25,.05/min(w,h))}) (solder_mask_margin .025))')
    for no,pts in poly or []:
        px=sum(a for a,c in pts)/len(pts);py=sum(c for a,c in pts)/len(pts)
        points=' '.join(f'(xy {a-px} {c-py})' for a,c in pts)
        b.append(f'(pad "{no}" smd custom (at {px} {py}) (size .001 .001) (layers "F.Cu" "F.Mask" "F.Paste") (solder_mask_margin .025) (options (clearance outline) (anchor rect)) (primitives (gr_poly (pts {points}) (width 0) (fill yes))))')
    b.append(')');(D/(name+'.kicad_mod')).write_text('\n'.join(b)+'\n')
    sources[name]={'source':source,'height_max_mm':height,'body_max_mm':body,'courtyard_mm':[2*x,2*y],'notes':notes}
def dual(n,pitch,span,w,h):
    m=n//2
    return [(i+1,-span/2,(i-(m-1)/2)*pitch,w,h) for i in range(m)]+[(n-i,span/2,(i-(m-1)/2)*pitch,w,h) for i in range(m)]
footprint('DCK6',(1.4,2.15),dual(6,.65,2.2,.9,.4),'TI DCK0006A example in SN74LVC1G11 appendix',1.1)
footprint('DCK5',(1.4,2.15),[p for p in dual(6,.65,2.2,.95,.4) if p[0]!=5], 'TI DCK0005A example in SN74LVC1G14 appendix',1.1,notes='Numbers corrected below: right top5/right bottom4')
# DCK5 numbering excludes the middle right lead; remaining top is5, bottom4.
f=D/'DCK5.kicad_mod';f.write_text(f.read_text().replace('(pad "6"','(pad "5"'))
footprint('DCU8',(2.1,2.4),dual(8,.5,3.1,.85,.3),'TI DCU0008A example in SN74LVC2G08 appendix',.9)
footprint('DRL8',(1.3,2.2),dual(8,.5,1.48,.67,.3),'TI DRL0008A example in TPS2116 appendix',.6)
footprint('DRL6',(1.3,1.7),dual(6,.5,1.48,.67,.3),'TI DRL0006A example in TPS61023 appendix',.6)
footprint('DDC6',(1.75,3.05),dual(6,.95,2.7,1.1,.6),'TI DDC0006A example in TPS3702-Q1 appendix; same package code TPS3700',1.1)
footprint('DBV6',(1.75,3.05),dual(6,.95,2.6,1.1,.6),'TI DBV0006A example in TPS3808 appendix',1.45)
footprint('DBV5',(1.75,3.05),[(1,-1.3,-.95,1.1,.6),(2,-1.3,0,1.1,.6),(3,-1.3,.95,1.1,.6),(4,1.3,.95,1.1,.6),(5,1.3,-.95,1.1,.6)],'TI DBV0005A example in TPS709 appendix',1.45)
footprint('DBZ3',(1.4,3.04),[(1,-1.05,-.95,1.3,.6),(2,-1.05,.95,1.3,.6),(3,1.05,0,1.3,.6)],'TI DBZ0003A example in TPS3839 appendix',1.12)
footprint('DSG8',(2.1,2.1),dual(8,.5,1.9,.5,.25)+[(9,0,0,.9,1.6)],'TI DSG0008A example in BQ25173 appendix',.8,notes='EP full paste in prototype; thermal vias and stencil windowing remain assembly/layout gate')
# RGT16: 1..4 left,5..8 bottom,9..12 right,13..16 top; EP17.
q=[]
for i in range(4):
    z=(i-1.5)*.5
    q.extend([(i+1,-1.4,z,.6,.24),(i+5,z,1.4,.24,.6),(12-i,1.4,z,.6,.24),(16-i,z,-1.4,.24,.6)])
footprint('RGT16',(3.1,3.1),q+[(17,0,0,1.68,1.68)],'TI RGT0016C example in TPS62130 appendix',1,notes='EP full paste in prototype; thermal vias/stencil windows are unresolved, not hidden pins')
q=[(1,-.65,-.2,.7,.2),(2,-.65,.2,.7,.2),(7,.65,.2,.7,.2),(8,.65,-.2,.7,.2)]
for i in range(4):
    z=(i-1.5)*.4
    # Outer top/bottom pad centres ±.65, inner ±.2, span1.3.
    xx=[-.6,-.2,.2,.6][i]
    q.extend([(3+i,xx,.75,.2,.5),(12-i,xx,-.75,.2,.5)])
footprint('RWB12',(1.7,1.7),q,'TI RWB0012A example in TUSB320LAI appendix',.4,notes='Side pads1/2/7/8 .7long; top/bottom8pads .5long, nonuniform corner pitch per drawing')
q=[(5,-.25,0,.30,2.40),(6,.25,0,.30,2.40),(2,-.9,-.225,.6,.25),(3,-.9,.225,.6,.25),(9,.9,-.225,.6,.25),(8,.9,.225,.6,.25)]
for no,sx,sy in [(1,-1,-1),(4,-1,1),(10,1,-1),(7,1,1)]:q.extend([(no,sx*.9,sy*.7,.6,.3),(no,sx*.725,sy*.875,.25,.65)])
footprint('RPW10',(2.1,2.1),q,'TI RPW0010A example, TPS25947 PDF p73,4225183/A',1,notes='Two same-pin primitives form each corner L. No fictional exposed pin. Full paste shown; exact RPW p74 stencil/assembly process must be reviewed')
# DQN exposed-metal geometry. Manufacturer example uses SMD, prototype NSMD
# uses these nominal exposed dimensions; explicit process approval still required.
polys=[]
for no,sx,sy in [(1,-1,-1),(2,-1,1),(3,1,1),(4,1,-1)]:
    pts=[(sx*x,sy*y) for x,y in [(.61,.43),(.25,.43),(.25,.40),(.43,.22),(.61,.22)]]
    polys.append((no,pts))
v=.48/math.sqrt(2);polys.append((5,[(v,0),(0,v),(-v,0),(0,-v)]))
footprint('DQN4',(1.05,1.05),[(5,0,0,.001,.001)],'TI DQN0004A exposed-metal dimensions, TPS3839 appendix drawing4215302/E',.4,notes='Diagonal EP .48square and clipped inner corners .22 clearance; prototype NSMD unlike source SMD, assembly approval gate',poly=polys)
for name,w,h,px,ww,hh,height,src in [('R0402',1.05,.55,.475,.55,.60,.4,'Vishay28950 IPC7351 reflow0402: .55x.60 lands gap.40'),('C0402',1.1,.6,.4,.4,.6,.6,'Murata GRM15 table2 reflow .4x.6 lands gap.4; selected from source ranges'),('R0805',2.1,1.4,.95,.9,1.45,.55,'Vishay28950 IPC7351 reflow0805:.9x1.45 lands gap1.0'),('R1206',3.3,1.75,1.45,1.15,1.8,.65,'Vishay28950 IPC7351 reflow1206:1.15x1.8 lands gap1.75')]:
    footprint(name,(w,h),[(1,-px,0,ww,hh),(2,px,0,ww,hh)],src,height)
footprint('L4020',(4.3,4.3),[(1,-1.675,0,.98,3.4),(2,1.675,0,.98,3.4)],'Coilcraft XGL4020 doc1529-3 and XFL4020 doc745-3: .98x3.4 lands with2.37 innergap',2.23,notes='Height2.1mounted+.13pre-mount maximum; pin1 short highdvdt start. Bodymax4.3, no shrink')
footprint('Contact2',(2.5,1),[(1,-.75,0,1,1),(2,.75,0,1,1)],'PCB service/reset contact, engineering geometry1mm pads1.5pitch',0,notes='No purchased switch or claimed tactile envelope')
footprint('Factory6',(4,2.5),[(i+1,(i%3-1)*1.5,(i//3-.5)*1.5,1,1) for i in range(6)],'PCB factory18/7/6 contract six accessible lands; engineering1mm/1.5pitch',0)
# Cell is horizontal inside fixed mechanical reserve. Only its two real leads
# enter this footprint; body reserve is checked separately, not a fake SMD body.
text='''(footprint "Cell_leads" (version 20241229) (generator "nova_q15_lands") (layer "F.Cu") (attr through_hole)
(descr "Eaton HV1325 0.60+/-.02 leads5+/-.5pitch; derived .9drill/1.6land, formed horizontal leads NOT supplier qualified")
(fp_rect (start -1.05 -3.55) (end 1.05 3.55) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
(pad "1" thru_hole circle (at 0 -2.5) (size 1.6 1.6) (drill .9) (layers "*.Cu" "*.Mask"))
(pad "2" thru_hole circle (at 0 2.5) (size 1.6 1.6) (drill .9) (layers "*.Cu" "*.Mask")))'''
(D/'Cell_leads.kicad_mod').write_text(text+'\n');sources['Cell_leads']={'source':'Eaton HV sheet4376 p3','height_max_mm':13.5,'body_max_mm':[28.4,13.5],'courtyard_mm':[2.1,7.1],'notes':'Full horizontal cell projection separately reserved x26..61/y23.5..37; leads forming and mounting remain gates'}
root=P.parents[1]
for src,name in [(root/'footprints/NOVA_HW.pretty/Murata_GRM21_Reflow.kicad_mod','C0805'),(root/'service-footprints/gct-power-candidate/Candidate.pretty/GCT_USB4125_GF_A.kicad_mod','USB_GCT'),(root/'service-footprints/gct-power-candidate/Candidate.pretty/AT25SF161B_MHB_Derived.kicad_mod','NOR8')]:
    shutil.copyfile(src,D/(name+'.kicad_mod'));sources[name]={'source':str(src.relative_to(P.parents[4])),'notes':'Exact read-only source footprint copied; file hash in manifest','height_max_mm':{'C0805':1.35,'USB_GCT':3.16,'NOR8':.9}[name]}
(P/'land-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
(P/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Q15") (type "KiCad") (uri "${KIPRJMOD}/Qualified.pretty") (options "") (descr "Candidate only, source dimensions + explicit derived lands")))\n')
print('lands',len(sources))
