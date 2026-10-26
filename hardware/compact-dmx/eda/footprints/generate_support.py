"""Additional traceable lands; no pixel-scaled geometry."""
from pathlib import Path
import json,math
P=Path(__file__).resolve().parent;L=P/'NOVA_HW.pretty'
def rect(w,h,layer):return f'(fp_rect (start {-w/2} {-h/2}) (end {w/2} {h/2}) (stroke (width .05) (type default)) (fill none) (layer "{layer}"))'
def regular(pin,x,y,w,h):return f'(pad "{pin}" smd rect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Mask" "F.Paste"))'
def write(name,body,pads,extent,desc,extra=''):
 text=f'(footprint "{name}" (version 20241229) (generator "nova_source_lands") (layer "F.Cu") (attr smd) (descr "{desc}") (fp_text reference "REF**" (at 0 {-extent[1]/2-1}) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))'
 text+=rect(*body,'F.Fab')+rect(extent[0]+.5,extent[1]+.5,'F.CrtYd')+'\n'+'\n'.join(pads)+extra+'\n)\n';(L/(name+'.kicad_mod')).write_text(text)
def custom(pin,pad,layers):
 x,y=pad['at'];pts=' '.join(f'(xy {a} {b})' for a,b in pad['polygon'])
 return f'(pad "{pin}" smd custom (at {x} {y}) (size .01 .01) (layers {layers}) (options (clearance outline) (anchor rect)) (primitives (gr_poly (pts {pts}) (width 0) (fill yes))))'
j=json.loads((P/'ti-vector-lands.json').read_text())
for name,d in j['footprints'].items():
 pads=[];xs=[];ys=[]
 for a,b,c in zip(d['layers']['copper'],d['layers']['paste'],d['layers']['mask']):
  assert a['pin']==b['pin']==c['pin'] and a['polygon']==b['polygon'] and a['at']==b['at']==c['at']
  pads +=[custom(a['pin'],a,'"F.Cu" "F.Paste"'),custom('',c,'"F.Mask"')]
  xs += [a['at'][0]+x for x,y in a['polygon']];ys +=[a['at'][1]+y for x,y in a['polygon']]
 extent=[max(max(xs)-min(xs),d['body_nominal_mm'][0]),max(max(ys)-min(ys),d['body_nominal_mm'][1])]
 write(name,d['body_nominal_mm'],pads,extent,'TI SWRC3542018 exact Cu/paste/mask polygons; pin mapping and provenance ti-vector-lands.json; current source applicability must be qualified')
write('Epson_FC135_Manufacturer',(3.2,1.5),[regular(1,-1.25,0,1,1.8),regular(2,1.25,0,1,1.8)],(3.5,1.8),'Epson FC135 EVer2.0 p4;1x1.8 lands centers2.5; no circuit patterns under body; custom AG0 electrical suffix remains supplier gate')
write('NDK_NX2016SA_Manufacturer',(2,1.6),[regular(1,-.675,.525,.85,.75),regular(2,.675,.525,.85,.75),regular(3,.675,-.525,.85,.75),regular(4,-.675,-.525,.85,.75)],(2.2,1.8),'NDK current NX2016SA dimension drawing;1/3 crystal2/4 cover; custom EXS suffix electrical approval remains open')
write('Vishay_CRCW0402',(1,.5),[regular(1,-.525,0,.6,.6),regular(2,.525,0,.6,.6)],(1.65,.6),'Vishay20035 reflow G.45 Y.6 X.6 Z1.65')
write('Murata_GRM21_Reflow',(2,1.25),[regular(1,-.95,0,.7,1.3),regular(2,.95,0,.7,1.3)],(2.6,1.3),'GRM21BR71A106KE51-01 Notice Table2 reflow:gap1.2 padlengthchosen.7 from.6..8 widthchosen1.3 from1.2..1.4; assembly validation required')
print('10 additional footprints from TI vectors / manufacturer drawings')
# Current exact replacement families, manufacturer dimensioned land recommendations.
# Coilcraft526-1 p1: H=.66 width,I=.36 length,J=.51 inner gap; rotate drawing90deg.
write('Coilcraft_0402HP_Manufacturer',(1.09,.71),[regular(1,-.435,0,.36,.66),regular(2,.435,0,.36,.66)],(1.23,.71),'Coilcraft526-1 revised12/20/23 p1 H.66 I.36 J.51;0402HP not HPH;body max1.09x.71 height.61 before optional solder; prototype RF retune required')
# Murata exact GJM155 sheets p25: choose midrange a=.4 b=.4 c=.5.
write('Murata_GJM155_Manufacturer',(1.05,.55),[regular(1,-.4,0,.4,.5),regular(2,.4,0,.4,.5)],(1.2,.55),'Exact GJM1555C1H1R0BB01/GJM1555C1H8R2DB01 sheets Apr15/2026 p25; a.4 b.4 c.5 selected within manufacturer range; body max1.05x.55x.55; assembly and RF qualification open')
