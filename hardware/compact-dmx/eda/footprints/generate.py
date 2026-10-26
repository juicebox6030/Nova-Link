"""Dimensioned prototype lands. Manufacturer-backed dimensions; routing not supplied."""
from pathlib import Path
import json,re
P=Path(__file__).resolve().parent;L=P/'NOVA_HW.pretty';L.mkdir(exist_ok=True)
def rect(x,y,w,h,layer):return f'(fp_rect (start {x-w/2} {y-h/2}) (end {x+w/2} {y+h/2}) (stroke (width 0.05) (type default)) (fill none) (layer "{layer}"))'
def pad(n,x,y,w,h,angle=0,layers='"F.Cu" "F.Paste" "F.Mask"'):
 return f'(pad "{n}" smd rect (at {x} {y} {angle}) (size {w} {h}) (layers {layers}))'
def save(name,body,pads,note,extra=''):
 s=f'(footprint "{name}" (version 20241229) (generator "nova_source_dimensions") (layer "F.Cu") (attr smd) (descr "{note}")\n'
 s+=f'(fp_text reference "REF**" (at 0 {-body[1]/2-1.5}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
 court=(12.3,13.83) if name=='TI_DFM0020A' else ((4.1,2.3) if name=='Vishay_CRCW1206' else (body[0]+1,body[1]+1))
 s+=rect(0,0,*body,'F.Fab')+rect(0,0,*court,'F.CrtYd')+'\n'+'\n'.join(pads)+extra+'\n)\n';(L/(name+'.kicad_mod')).write_text(s)
# TI drawing4225640/A01/2020 example:20 pads2.1x0.6;row center span9.7;pitch1.27.
pads=[pad(i,-4.85,(i-5.5)*1.27,2.1,.6) for i in range(1,11)]+[pad(i,4.85,(15.5-i)*1.27,2.1,.6) for i in range(11,21)]
save('TI_DFM0020A',(7.5,12.83),pads,'TI SLLSF86D package DFM0020A land drawing4225640A; fab nominal body7.5x12.83;lead span9.97..10.63; isolation routing still required')
# TI RGZ0048A example:48pads0.6x0.24 centers +/-3.4;pitch0.5;EP5.15square.
pads=[]
for i in range(12):
 a=-2.75+i*.5
 pads +=[pad(i+1,-3.4,a,.6,.24),pad(i+13,a,3.4,.24,.6),pad(i+25,3.4,-a,.6,.24),pad(i+37,-a,-3.4,.24,.6)]
pads.append(pad(49,0,0,5.15,5.15,layers='"F.Cu" "F.Mask"'))
for x in (-1.89,-.63,.63,1.89):
 for y in (-1.89,-.63,.63,1.89):pads.append(pad("",x,y,1.06,1.06,layers='"F.Paste"'))
# TI4219044D stencil example:16 windows1.06square at1.26pitch;0.125mm stencil.
save('TI_RGZ0048A',(7,7),pads,'TI SWRS196I RGZ0048A example lands; EP49 local number; 16window TI stencil captured;21 thermal vias require board implementation')
# Rev3.1p3 expanded recommended land pattern1x1; centers3.5/1.8/3.5;rows2.6.
pads=[]
for i,x in enumerate([-4.4,-.9,.9,4.4]):pads +=[pad(i+1,x,1.3,1,1),pad(8-i,x,-1.3,1,1)]
keep='''(zone (net 0) (net_name "") (layers "*.Cu") (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (keepout (tracks allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints not_allowed)) (fill (thermal_gap 0.3) (thermal_bridge_width 0.3)) (polygon (pts (xy -14 -1.8) (xy 14 -1.8) (xy 14 8.2) (xy -14 8.2))))'''
save('Johanson_0900AD47_IsolatedLands',(10,3.2),pads,'Rev3.1p2p3 isolated NC lands2/3/5/6/7/8; local10x28 region proposal NOT exact reference board; only approved feed traces allowed',keep)
save('Vishay_CRCW1206',(3.2,1.6),[pad(1,-1.275,0,1.05,1.8),pad(2,1.275,0,1.05,1.8)],'Vishay20035 reflow G1.50 Y1.05 X1.80 Z3.60; courtyard added design margin')
# Official KiCad source transcription referencing manufacturer; pending visual recheck, explicitly not accepted manufacturer evidence.
s=(P.parent/'source-cache/pcm-kicad.kicad_mod').read_text();s=s[:s.index('  (model')]+')\n';s=s.replace('SW_SPDT_PCM12','PCM12_PENDING_MANUFACTURER_LAND_RECHECK');(L/'PCM12_PENDING_MANUFACTURER_LAND_RECHECK.kicad_mod').write_text(s)
for parent,uri in [(P.parent,'${KIPRJMOD}/footprints/NOVA_HW.pretty'),(P.parent/'mcu-radio','${KIPRJMOD}/../footprints/NOVA_HW.pretty')]:
 (parent/'fp-lib-table').write_text(f'(fp_lib_table (version 7) (lib (name "NOVA_HW") (type "KiCad") (uri "{uri}") (options "") (descr "Prototype source lands; see footprints/DESIGN.md gates")))\n')
print('Base5 footprint files regenerated; support generator adds12; switch datum gate remains')

import subprocess,sys
subprocess.run([sys.executable,str(P/"extract_ti_lands.py")],check=True)
subprocess.run([sys.executable,str(P/"generate_support.py")],check=True)
