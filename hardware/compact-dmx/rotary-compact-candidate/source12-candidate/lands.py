"""Source-dimensioned IC/magnetic lands plus explicitly derived passive/process lands."""
from pathlib import Path
import json, shutil
P=Path(__file__).resolve().parent;L=P/'Source12.pretty';L.mkdir(exist_ok=True)
old=P.parent/'source-axial-routing';root=P.parents[3]
sources={}
for name in ['RPW10','RVC20','USB4105','FPC20','R0402','C0402','C0805','T520D','DPY2','TP1']:
 src=old/'Regulated.pretty'/f'{name}.kicad_mod';shutil.copyfile(src,L/f'{name}.kicad_mod');sources[name]={'copied_readonly_from':str(src.relative_to(root))}
src=root/'hardware/compact-dmx/eda/cell-protection-candidate/CellProtection.pretty/DDC6.kicad_mod';shutil.copyfile(src,L/'DDC6.kicad_mod');sources['DDC6']={'copied_readonly_from':str(src.relative_to(root))}
def fp(name,body,court,descr):
 return [f'(footprint "{name}" (version 20241229) (generator "nova_source12") (layer "F.Cu") (attr smd) (descr "{descr}")',
 '(fp_text reference "REF**" (at 0 0) (layer "F.Fab") (effects (font (size .5 .5) (thickness .07))))',
 f'(fp_rect (start {-body[0]/2} {-body[1]/2}) (end {body[0]/2} {body[1]/2}) (stroke (width .05) (type default)) (fill none) (layer "F.Fab"))',
 f'(fp_rect (start {-court[0]/2} {-court[1]/2}) (end {court[0]/2} {court[1]/2}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))']
def pad(no,x,y,w,h,mask=.025,paste=True):
 return f'(pad "{no}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Mask"'+(' "F.Paste"' if paste else '')+f') (roundrect_rratio .1) (solder_mask_margin {mask}))'
a=fp('RGX11',[2.1,3.1],[3.2,4.0],'TI RGX0011A4221908A10/2015 p45: real11pads,3 power bars; NO invented EP12')
for no,y in [(1,-.5),(2,0),(3,.5)]:
 a.append(pad(no,0,y,2.4,.25,-.025,False))
 for x in [-.86,0,.86]:a.append(f'(fp_rect (start {x-.33} {y-.125}) (end {x+.33} {y+.125}) (stroke (width 0) (type default)) (fill solid) (layer "F.Paste"))')
for no,x in [(11,-.75),(10,-.25),(9,.25),(8,.75)]:a.append(pad(no,x,-1.4,.25,.6))
for no,x in [(4,-.75),(5,-.25),(6,.25),(7,.75)]:a.append(pad(no,x,1.4,.25,.6))
(L/'RGX11.kicad_mod').write_text('\n'.join(a+[')'])+'\n')
a=fp('XAL4020',[4.3,4.3],[4.9,4.9],'Coilcraft806-4 Rev02/25/26: lands0.98x3.4, gap2.37; maxbody4.3x4.3x2.1')
for no,x in [(1,-1.675),(2,1.675)]:a.append(pad(no,x,0,.98,3.4))
(L/'XAL4020.kicad_mod').write_text('\n'.join(a+[')'])+'\n')
a=fp('Wire2',[7,4.5],[8,5.5],'DERIVED isolated-source solder lands2.5x3 at4mm pitch. Wire/solder/strain relief process NOT qualified.')
for no,x in [(1,-2),(2,2)]:a.append(pad(no,x,0,2.5,3))
(L/'Wire2.kicad_mod').write_text('\n'.join(a+[')'])+'\n')
# Retain the old0.7x1.3 lands with1.2gap. For different Taiyo MPNs these
# are explicitly DERIVED0805 reflow lands, not a supplier-approved pattern.
a=fp('C0805',[2.2,1.45],[3.1,2.0],'DERIVED0805 lands0.7x1.3 gap1.2, Taiyo current MSAST21GBB5106MTNA01/MSASE21GBB5226MTNA01 vendor maxbody2.2x1.45x1.45; derived land/stencil/bias gate')
for no,x in [(1,-.95),(2,.95)]:a.append(pad(no,x,0,.7,1.3))
(L/'C0805.kicad_mod').write_text('\n'.join(a+[')'])+'\n')
spec={
 'RPW10':([2.1,2.1],.8,[3.1,2.6],'TI RPW0010A; copied lands'),
 'RVC20':([3.1,4.1],1.0,[3.9,4.9],'TI RVC0020A common TPS25810/TPS25940; realEP21 ground'),
 'RGX11':([2.1,3.1],1.0,[3.2,4.0],'TI RGX0011A source-dimensioned; GND is actualpad3, not extraEP'),
 'DDC6':([1.75,3.05],1.1,[4.3,3.55],'TI DDC0006A; body allocation includes terminal span separately in courtyard'),
 'USB4105':([9.09,7.65],3.46,[10.14,8.65],'GCT B4 unchanged16contacts/12signal lands+4shell+2NPTH'),
 'XAL4020':([4.3,4.3],2.1,[4.9,4.9],'Coilcraft806-4 dimensions and lands'),
 'T520D':([7.6,4.6],3.1,[8.2,5.1],'KEMET Dcase source drawing;120uF minimum only at tolerance reference'),
 'R0402':([1.1,.6],.45,[1.8,1.0],'Vishay28758/derived assembly courtyard'),
 'C0402':([1.1,.6],.6,[1.8,1.0],'Derived0402 envelope and lands; exact vendor height/bias/stencil gate'),
 'C0805':([2.2,1.45],1.45,[3.1,2.0],'Taiyo official preferred-current HTML maxbody2.2x1.45x1.45; DERIVED lands/stencil/bias gate'),
 'DPY2':([1.05,.65],.5,[1.65,1.3],'TI DPY0002A source lands'),
 'FPC20':([20,2],.3,[20.5,3.0],'Derived actual20mm ribbon solder lands; external clamp volume additional'),
 'Wire2':([7,4.5],2.5,[8,5.5],'Derived source-wire/solder allowance; exact harness OD/process gate'),
 'TP1':([1,1],0,[1.5,1.5],'Fabricated probe land')}
for name,(body,height,court,source) in spec.items():
 sources.setdefault(name,{});sources[name].update({'body_allocation_mm':body,'height_allocation_mm':height,'courtyard_mm':court,'source':source,'manufacturing_land_height_thermal_acceptance':False})
(P/'land-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
print('Generated14 footprint types; supplier and derived allocations explicitly distinguished')
