from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());rows=[];tools={}
def tool(n,s,targets=()):tools[n]=(s,targets)
def cy(r,l,x,y,z,axis):return Part.makeCylinder(r,l,V(x,y,z),V(*axis))
# Core ends/endcap blanks are open during assembly; no in-service access claim.
for side,x,axis in [('Front',0,(1,0,0)),('Rear',47.5,(1,0,0))]:
 for z in [-9,9]:tool('CapDriver'+side+str(z),cy(.75,20.9 if side=='Front' else 39.5,x,14.1,z,axis),('StationaryCapScrew'+side+('m' if z<0 else 'p'),))
for pin,x in [('1',29.7),('2',38.7)]:
 shaft=cy(1.0,87-x,x,18,-5.8,(1,0,0));tip=cy(.45,3.335,x,14.665,-5.8,(0,1,0));tool('StationarySolder'+pin,shaft.fuse(tip),('FixedFanoutCopper'+pin,'J2_Solder'+pin,'stationary_J2_Pad'+pin+'_'+str(int(pin)-1)))
for pin,x in [('1',58.7),('2',67.7)]:
 shaft=cy(1,100-x,x,29,-10.5,(1,0,0));tip=cy(.45,2.665,x,26.335,-10.5,(0,1,0));tool('RotatingSolder'+pin,shaft.fuse(tip),('MovingFanoutCopper'+pin,'J3_Solder'+pin,'rotating_J3_Pad'+pin+'_'+str(int(pin)-1)))
for x in [51.7,74.7]:tool('MovingClampDriver'+str(x),cy(1,10,x,27.4,-15,(0,1,0)),('MovingClampScrew'+str(x).replace('.','_'),))
for z in [-17,17]:tool('EndGateDriver'+str(z),cy(.75,15,85.5,29,z,(1,0,0)),('SourceEndGateScrew'+str(z).replace('-','m'),))
for oldx,x in [('45_25',22.45),('68_9',46.1)]:
 for oldz,z in [('m29_5',-29.5),('29_5',29.5)]:tool('FrameDriver'+oldx+oldz,cy(.75,35,x,3.3,z,(0,1,0)),('COL_FrameBolt_'+oldx+'_'+oldz,))
exclude={'insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose90','screen'}
for n,(t,targets) in tools.items():
 for k,s in S.items():
  if k in targets or k.startswith('COL_Flex_') or G[k] in exclude or G[k].endswith('landing_reserve') or k in ['OutputEndcapBlank','InputEndcapBlank']:continue
  if not t.BoundBox.intersect(s.BoundBox):continue
  v=t.common(s).Volume
  if v>1e-7:rows.append({'tool':n,'part':k,'volume':v});print('TOOLFAIL',n,k,v,flush=True)
# Complete actual board/body insertion uses an enclosing axial prism for every part.
insertion=[]
for zone,frame,travel in [('rotating','RotorHalfPositiveY',35),('stationary','StationaryCoreWithSupports',65)]:
 for n,s in S.items():
  if not(n==zone+'_PCB' or (n.startswith(zone+'_') and (n.endswith('_Body') or n.endswith('_StakeReserve')))):continue
  if G[n].endswith('landing_reserve'):continue
  b=s.BoundBox;envelope=Part.makeBox(b.XLength+travel,b.YLength,b.ZLength,V(b.XMin,b.YMin,b.ZMin));v=envelope.common(S[frame]).Volume
  insertion.append({'part':n,'frame':frame,'volume':v,'axial_travel':travel,'basis':'complete axial AABB sweep; conservative relative to package allocation'})
  if v>1e-7:print('INSERTFAIL',n,v,flush=True)
# USB plug/relief/cable screening: actual181 transforms, finite engineering envelopes.
fixed=[n for n in S if G[n] in ['housing','module','carrier','trunk','joint','branch','stationary','stationary_wire','collar_stationary']];usb=[]
for a in range(-90,91):
 for n in ['USBPlugApproach','USBRelief','USBCable']:
  q=S[n].copy();q.rotate(V(),V(1,0,0),a)
  for k in fixed:
   t=S[k]
   if not q.BoundBox.intersect(t.BoundBox):continue
   v=q.common(t).Volume
   if v>1e-7:usb.append({'angle':a,'screen':n,'part':k,'volume':v})
 if a%30==0:print('USB',a,'bad',len(usb),flush=True)
(P/'access-check.json').write_text(json.dumps({'tool_count':len(tools),'tool_failures':rows,'board_insertion':insertion,'USB_positions':181,'USB_failures':usb,'status':'PASS' if not rows and not usb and not any(r['volume']>1e-7 for r in insertion) else 'FAIL','limitations':'Engineeringtool/plug envelopes; endcaps absent for assembly; exact cable/latch unknown; supplier package profiles and tool/process qualification open'},indent=2)+'\n')
td=A.newDocument('AssemblyToolScreens')
for n,(s,targets) in tools.items():o=td.addObject('PartDesign::Feature',n);o.Shape=s
for n in ['USBPlugApproach','USBRelief','USBCable']:o=td.addObject('PartDesign::Feature',n);o.Shape=S[n]
td.recompute();td.saveAs(str(P/'assembly-tool-screens.FCStd'));Part.export(td.Objects,str(P/'assembly-tool-screens.step'))
