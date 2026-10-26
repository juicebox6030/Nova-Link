"""Explicit primary-based copper. No parent writes; assembly/stencil approval open."""
from pathlib import Path
import shutil,json
P=Path(__file__).resolve().parent;D=P/'Regulated.pretty';D.mkdir(exist_ok=True)
Q=P.parents[1]/'eda/power-service/qualified15-candidate';records={}
for n in ['RPW10','R0402','C0402','C0805']:
 shutil.copyfile(Q/'Qualified.pretty'/f'{n}.kicad_mod',D/f'{n}.kicad_mod');r=json.loads((Q/'land-sources.json').read_text())[n];records[n]=r|{'read_only_origin':str(Q/'Qualified.pretty'/f'{n}.kicad_mod')}
records['C0805'].update({'body_max_mm':[2.1,1.35],'courtyard_mm':[3.1,1.8]})
def create(n,pads,body,height,court,source,extra=None):
 z=[f'(footprint "{n}" (version 20241229) (generator "nova_rotary_lands") (layer "F.Cu") (attr smd)',f'(descr "{source}")',f'(fp_rect (start {-court[0]/2} {-court[1]/2}) (end {court[0]/2} {court[1]/2}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))',f'(fp_rect (start {-body[0]/2} {-body[1]/2}) (end {body[0]/2} {body[1]/2}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))']
 for no,x,y,w,h,*mask in pads:
  z.append(f'(pad "{no}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio .1) (solder_mask_margin {mask[0] if mask else .025}))')
 if extra:z+=extra
 z.append(')');(D/f'{n}.kicad_mod').write_text('\n'.join(z)+'\n');records[n]={'source':source,'body_max_mm':body,'height_max_mm':height,'courtyard_mm':court,'assembly_gate':'Prototype lands/stencil/thermal vias require assembly approval. No paste reduction or thermal routing claim.'}
# RNM0015A irregular power pads. Same-net bridge joins duplicate VIN/OUT balls.
a=[(i,-1.15,-.75+(i-1)*.5,.6,.25) for i in range(1,5)]
a += [(5,-.725,1.4,.25,.6),(6,-.225,1.4,.25,.6),(14,-.225,-1.4,.25,.6),(15,-.725,-1.4,.25,.6)]
a += [(9,.775,.5,1.35,.25,-.05),(10,.6,0,1.7,.25,-.05),(11,.775,-.5,1.35,.25,-.05)]
for top,coords in [(True,[(13,.275),(12,.775)]),(False,[(7,.275),(8,.775)])]:
 for no,x in coords:a.append((no,x,-1.4 if top else 1.4,.25,.6,-.05))
 a.append((12 if top else 8,.525,-1.225 if top else 1.225,.75,.25,-.05))
create('RNM15',a,[2.6,3.1],1,[3.5,4.0],'TI RNM0015A4222000B:15 actual pins,0.5pitch; irregular U pads; mask-definedpowerlands per example p40. Bridge assigned duplicate same net.')
a=[(i,-1.4,-1.25+(i-1)*.5,.6,.2) for i in range(1,7)]
a += [(7+i,-.75+i*.5,1.9,.2,.6) for i in range(4)]
a += [(11+i,1.4,1.25-i*.5,.6,.2) for i in range(6)]
a += [(17+i,.75-i*.5,-1.9,.2,.6) for i in range(4)]+[(21,0,0,1.6,2.6)]
create('RVC20',a,[3.1,4.1],.8,[3.9,4.9],'TI RVC0020A4219150B p37:20 peripheral pads +actualEP21; no invented disconnected thermal pad')
create('DPY2',[(1,-.35,0,.3,.5),(2,.35,0,.3,.5)],[1.05,.65],.45,[1.6,1.1],'TI DPY0002A example p28:0.7pitch0.3x0.5 lands; symmetric bidirectional ESD')
create('XFL4020',[(1,-1.675,0,.98,3.4),(2,1.675,0,.98,3.4)],[4.3,4.3],2.23,[4.83,4.8],'Coilcraft745-3 land0.98x3.4 INNERgap2.37,centerpitch3.35;body4.0+/-.3 height2.1mounted+0.13premountallocation')
create('T520D',[(1,-2.85,0,2.0,3.0),(2,2.85,0,2.0,3.0)],[7.6,4.6],3.1,[8.2,5.1],'DERIVED conservative reflowlands fromKEMETDcase7.3+/-.3x4.3+/-.3; terminalsS1.3+/-.3,F2.4+/-.1; not manufacturer-recommendedlandpattern. Positivepad1.')
create('C0603',[(1,-.8,0,.85,.95),(2,.8,0,.85,.95)],[1.7,.9],.9,[2.95,1.45],'DERIVED0603 assembly allocation for TI specifiedTMK107BBJ106MA-T;1.6x0.8nominal,0.1body allowance; land/process gate')
# USB drawing viewed from component side, mate points toward+y. Origin at recommended PCBedge.
# 16 CONTACTS share12 solder lands, exactly as manufacturer drawing (no fictional physical pads).
a=[]
for no,x in [('A1_B12',-3.2),('A4_B9',-2.4),('B8',-1.75),('A5',-1.25),('B7',-.75),('A6',-.25),('A7',.25),('B6',.75),('A8',1.25),('B5',1.75),('B4_A9',2.4),('B1_A12',3.2)]:a.append((no,x,-4.755,.6 if '_' in no else .3,1.15))
extra=[]
for no,x,y,w,h,slot in [('S1',-4.32,-4.18,1,2.1,1.7),('S2',4.32,-4.18,1,2.1,1.7),('S3',-4.32,-1.4,1,1.8,1.4),('S4',4.32,-1.4,1,1.8,1.4)]:extra.append(f'(pad "{no}" thru_hole oval (at {x} {y}) (size {w} {h}) (drill oval .6 {slot}) (layers "*.Cu" "*.Mask"))')
for x in [-2.89,2.89]:extra.append(f'(pad "" np_thru_hole circle (at {x} -3.68) (size .65 .65) (drill .65) (layers "*.Cu" "*.Mask"))')
create('USB4105',a,[9.09,7.65],3.46,[10.14,8.65],'GCTUSB4105B4 18Dec2023:16contacts/12solderlands, four0.6wideplatedslots,2x0.65NPTH;0.95+/-.15stake. Boardedgeorigin;mate+y.',extra)
f=D/'USB4105.kicad_mod';s=f.read_text().replace('(start -5.07 -4.325) (end 5.07 4.325)','(start -5.07 -5.83) (end 5.07 2.82)').replace('(start -4.545 -3.825) (end 4.545 3.825)','(start -4.545 -5.48) (end 4.545 2.17)');f.write_text(s)
records['USB4105']['body_local_bounds_mm']=[-4.545,-5.48,4.545,2.17];records['USB4105']['edge_overhang_max_mm']=2.17
create('FPC20',[(1,-4.5,0,8,2),(2,4.5,0,8,2)],[20,2],.3,[20.5,3.0],'DERIVED bareboard/directsolderland8mm each,1mmgap;20mmribbon. No connectorMPN/stackqualification. External clamp/coverlay/strainrelief required.')
create('TP1',[(1,0,0,1,1)],[1,1],0,[1.5,1.5],'DERIVED1mm exposed fault testpad; no purchased component')
(P/'land-sources.json').write_text(json.dumps(records,indent=2)+'\n');print('Complete lands',len(records))
