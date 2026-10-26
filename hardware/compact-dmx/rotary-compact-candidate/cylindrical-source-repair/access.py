from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());old=A.openDocument(str(P.parent/'compact-interface-repair/interface-prototype.FCStd'));kept=set(json.loads((P/'preserved-names.json').read_text()))
new=[n for n in S if n not in kept and G[n] in ['newphysical','fastener','source','stationary_wire']]
def swept_box(s,dx=0,dz=0):
 b=s.BoundBox;return Part.makeBox(b.XLength+abs(dx),b.YLength,b.ZLength+abs(dz),V(b.XMin+min(0,dx),b.YMin,b.ZMin+min(0,dz)))
checks=[]
# Source module/pins placed before wires, upper lid absent. Body bbox and exact round pins swept vertically.
for n in ['IRM20_12_maxbody','Pin_L','Pin_N','Pin_LVplus','Pin_LVminus']:
 if n.startswith('Pin_'):
  b=S[n].BoundBox;sw=Part.makeCylinder(b.XLength/2,b.ZLength+60,V((b.XMin+b.XMax)/2,(b.YMin+b.YMax)/2,b.ZMin))
 else:sw=swept_box(S[n],dz=60)
 for other in ['LowerShellPosts','RetainedCarrier','SupportedFilm']:
  v=sw.common(S[other]).Volume;checks.append({'moving':n,'fixed':other,'sweep_volume_collision':v})
# Carrier lowering seats onto posts; upperhalf, screws, wires, film retained below are assembly-state explicit.
for other in ['LowerShellPosts','SupportedFilm']:
 sw=swept_box(S['RetainedCarrier'],dz=60);v=sw.common(S[other]).Volume;checks.append({'moving':'RetainedCarrier_AABB','fixed':other,'sweep_volume_collision':v})
# Driver access with upper shell removed; module and carrier in place. Exact screw shafts are nottools.
for n in [x for x in S if x.startswith('ClosureTool')]+['FuseServiceTool']:
 for other in ['IRM20_12_maxbody','RetainedCarrier','SupportedFilm']:
  v=S[n].common(S[other]).Volume;checks.append({'moving':n,'fixed':other,'sweep_volume_collision':v})
# Carrier-driver cylinders are real allocated paths above screwheads, upperlid absent.
for x in [-99.5,-42.5]:
 for y in [-20,20]:
  tool=Part.makeCylinder(2.25,50,V(x,y,-12))
  for other in ['IRM20_12_maxbody','RetainedCarrier']:
   v=tool.common(S[other]).Volume;checks.append({'moving':'CarrierDriver'+str((x,y)),'fixed':other,'sweep_volume_collision':v})
# Source boards remain in existing rails. New wires are installed after boards; named absence is assembly sequence.
boardchecks=[]
for n in S:
 if not n.startswith(('stationary_','rotating_')) or G[n].endswith('_landing_reserve'):continue
 sw=swept_box(S[n],dx=-35 if n.startswith('stationary_') else 35)
 for other in new:
  if other.startswith('SourceWire'):continue
  if not sw.BoundBox.intersect(S[other].BoundBox):continue
  v=sw.common(S[other]).Volume;boardchecks.append({'board_part':n,'new_part':other,'volume':v})
# Actual frozen USB engineering screens vs newparts: axial separation or exact containment envelopes.
usb=[]
for u in ['USBPlugApproach','USBRelief','USBCable']:
 ss=old.getObject(u).Shape;b=ss.BoundBox
 inner=Part.makeCylinder(24.25,b.XLength+.02,V(b.XMin-.01,0,0),V(1,0,0));assert ss.common(inner).Volume<1e-7
 for n in new:
  nn=S[n];bb=nn.BoundBox
  if bb.XMax<b.XMin or bb.XMin>b.XMax:proof='axial'
  else:
   clip=nn.common(Part.makeBox(b.XLength+.02,100,100,V(b.XMin-.01,-50,-50)))
   assert clip.cut(Part.makeCylinder(24,b.XLength+.02,V(b.XMin-.01,0,0),V(1,0,0))).Volume<1e-7,(u,n)
   proof='newpart R24; actualscreen outsideR24.25'
  usb.append({'screen':u,'part':n,'proof':proof,'valid_angles':[-90,90]})
fail=[r for r in checks if r['sweep_volume_collision']>1e-7];bf=[r for r in boardchecks if r['volume']>1e-7]
(P/'access-check.json').write_text(json.dumps({'source_tool_insertion_checks':checks,'source_failures':fail,'board_new_part_intersections':boardchecks,'board_failures':bf,'USB_certificates':usb,'sampled_angles':list(range(-90,91)),'USB_scope':'Frozen engineering plug/relief/cable only; no CI/CME installedmate inference','assembly_absences':['UpperShellRetention before sourceinsertion/toolaccess','all sourcewires before boardinsertion','carrier screws before carrierinsertion'],'neck_attachment_unbuilt':True},indent=2)+'\n');print('ACCESS',len(checks),'FAIL',fail,'BOARDFAIL',bf,'USB',len(usb),flush=True)
