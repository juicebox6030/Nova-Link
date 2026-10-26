"""Local geometry-aware prototype router; real KiCad DRC is the acceptance authority.
Outer power necks follow pad pitch; power buses .9mm on B.Cu, full In1 ground.
No footprint edits, exclusions or clearance-rule reduction.
"""
from pathlib import Path
import pcbnew as K,numpy as np,math,heapq,json,time
P=Path(__file__).resolve().parent;b=K.LoadBoard(str(P/'source-axial.kicad_pcb'));iu=K.FromMM;mm=K.ToMM;fs={f.GetReference():f for f in b.GetFootprints()};nets={str(n.GetNetname()):n for n in b.GetNetInfo().NetsByNetcode().values()};assert len(list(b.GetTracks()))==0 and len(list(b.Zones()))==0,'Run build.py before route.py; never accumulate old copper'
layers=[K.F_Cu,K.B_Cu,K.In2_Cu];step=.025;W,H=27,20;nx,ny=int(W/step)+1,int(H/step)+1
pads=[];shapes=[];holes=[];vias=[];traces=[];report=[]
def coord(p):return (mm(p.x),mm(p.y))
def pad(ref,no):return next(p for p in fs[ref].Pads() if p.GetNumber()==str(no))
def point(ref,no):return coord(pad(ref,no).GetPosition())
for ref,f in fs.items():
 for p in f.Pads():
  box=p.GetBoundingBox();x0,y0=mm(box.GetLeft()),mm(box.GetTop());w,h=mm(box.GetWidth()),mm(box.GetHeight());net=p.GetNetname();ls=[0] if p.GetAttribute()==K.PAD_ATTRIB_SMD else [0,1,2]
  if p.GetNumber():
   item={'kind':'rect','net':net,'xy':(x0+w/2,y0+h/2),'size':(w,h),'ls':ls,'ref':ref,'no':p.GetNumber(),'p':p};shapes.append(item);pads.append(item)
  if p.GetDrillSize().x:
   # Slots are represented conservatively by axis-aligned rectangles plus rounded endpoints.
   dw,dh=mm(p.GetDrillSize().x),mm(p.GetDrillSize().y)
   if round(f.GetOrientationDegrees())%180:dw,dh=dh,dw
   holes.append({'kind':'hole','net':net,'xy':coord(p.GetPosition()),'size':(dw,dh)})
def segment(net,a,c,width=.2,layer=0):
 if math.dist(a,c)<1e-7:return
 s=K.PCB_TRACK(b);s.SetStart(K.VECTOR2I(iu(a[0]),iu(a[1])));s.SetEnd(K.VECTOR2I(iu(c[0]),iu(c[1])));s.SetWidth(iu(width));s.SetLayer(layers[layer]);s.SetNet(nets[net]);b.Add(s)
 shapes.append({'kind':'line','net':net,'a':a,'c':c,'width':width,'ls':[layer]});traces.append({'net':net,'a':a,'c':c,'width_mm':width,'layer':K.BOARD.GetStandardLayerName(layers[layer])})
def chain(net,pts,width=.2,layer=0):
 for a,c in zip(pts,pts[1:]):segment(net,a,c,width,layer)
def via(net,xy,diam=.6,drill=.3):
 if any(v['net']==net and math.dist(v['xy'],xy)<.01 for v in vias):return
 v=K.PCB_VIA(b);v.SetPosition(K.VECTOR2I(iu(xy[0]),iu(xy[1])));v.SetWidth(iu(diam));v.SetDrill(iu(drill));v.SetViaType(K.VIATYPE_THROUGH);v.SetLayerPair(K.F_Cu,K.B_Cu);v.SetNet(nets[net]);b.Add(v)
 shapes.append({'kind':'circle','net':net,'xy':xy,'radius':diam/2,'ls':[0,1,2]});holes.append({'kind':'hole','net':net,'xy':xy,'size':(drill,drill)});vias.append({'net':net,'xy':xy,'diam_mm':diam,'drill_mm':drill})
# Keep the switching loop on top; each narrow section is an unavoidable package neck.
for n,x,lc in [('SW_L1',8.,'1'),('SW_L2',9.,'2')]:
 p=point('U2',11 if n=='SW_L1' else 9);side=-1 if n=='SW_L1' else 1
 chain(n,[p,(x,5.4),(x+side*.4,4.9)],.22)
 chain(n,[(x+side*.4,4.9),point('L1',lc)],.8)
# Pre-escape actual high-current IC pads into paired vias; all remain on their real net.
anchors={}
def anchor(net,xy):via(net,xy);anchors.setdefault(net,[]).append(xy)
for name,no,xx,yy in [('PROTECTED_IN',12,6.2,5.95),('PROTECTED_IN',13,6.2,6.65),('REG_5V136',7,10.7,6.7),('REG_5V136',8,10.7,6.0)]:
 p=point('U2',no);xy=(xx,yy);chain(name,[p,(xx,p[1]),xy],.22);anchor(name,xy)
for xx in [2.7,3.3]:
 p=point('U1',5);xy=(xx,10.15);chain('FPC_5V',[p,(p[0],10.6),xy],.22);via('FPC_5V',xy)
 if xx==2.7:anchors.setdefault('FPC_5V',[]).append(xy)
 else:segment('FPC_5V',xy,(2.7,10.15),.5,1)
for xy in [(4.3,10.25),(4.8,9.8)]:
 p=point('U1',6);chain('PROTECTED_IN',[p,(p[0],10.6 if xy[1]<12 else 13.6),xy],.22);anchor('PROTECTED_IN',xy)
for name,nums,xx in [('REG_5V136',[2,3,4,5],16.65),('USB_VBUS',[14,15],20.8)]:
 for no in nums:
  p=point('U3',no);yy=(12.0 if no in [2,3] else 13.0) if name=='REG_5V136' else (11.4 if no==14 else 10.7);xy=(xx,yy);chain(name,[p,(xx,p[1]),xy],.22);anchor(name,xy)
# Large capacitor and connector pads carry vias; no tiny pad is given an unjustified 3A trace.
power_refs={'FPC_5V':[('J0',1)],'PROTECTED_IN':[(x,1) for x in ['C1','C2','C3']], 'REG_5V136':[(x,1) for x in ['C4','C5','C6','C7','C8']], 'USB_VBUS':[('C9',1),('J1','A4_B9'),('J1','B4_A9')]}
for net,rr in power_refs.items():
 for ref,no in rr:
  p=point(ref,no)
  if ref in ['C8','J0']:
   for dx,dy in [(-.3,-.3),(-.3,.3),(.3,-.3),(.3,.3)]:anchor(net,(p[0]+dx,p[1]+dy))
  elif ref=='J1':
   via(net,p);xy=(21.1,p[1]);segment(net,p,xy,.5,1);anchors.setdefault(net,[]).append(xy)
  else:anchor(net,p)
# Quiet control returns are wired locally on top, then join the plane only at the IC star.
quiet={'U2':[('U2',1),('U2',4),('U2',15),('R7',2),('C11',2)],'U1':[('U1',4),('U1',8),('R2',2),('R4',2),('R5',2),('C12',2)]}
quietkeys={(ref,str(no)) for rows in quiet.values() for ref,no in rows}
# Dedicated U3 EP thermal vias: six .30mm finished drills on .6/.8mm pitch; filled/capped process gate.
for dx in [-.3,.3]:
 for dy in [-.8,0,.8]:via('GND_ISO',(18.5+dx,12.5+dy))
# Return and bulk thermal/current spreading arrays, kept inside their existing large lands.
for ref,no in [('J0',2),('C8',2)]:
 p=point(ref,no)
 for dx,dy in [(-.3,-.3),(-.3,.3),(.3,-.3),(.3,.3)]:via('GND_ISO',(p[0]+dx,p[1]+dy))
for no in ['A1_B12','B1_A12']:
 p=point('J1',no)
 for dx in [-.325,.25]:via('GND_ISO',(p[0]+dx,p[1]))
# Regulator PGND central stripe exits along its own axis, away from both SW necks.
pg=point('U2',10);chain('GND_ISO',[pg,(8.5,4.8)],.25);chain('GND_ISO',[(8.5,4.8),(8.5,3.7)],.5);via('GND_ISO',(8.5,4.6));via('GND_ISO',(8.5,3.7))
via('GND_ISO',point('C13',2))
chain('FPC_5V',[point('C13',1),(3.3,10.15)],.2) # actual close input bypass
for xy in [(2.,13.5),point('R2',2),point('R4',2),point('R5',2),point('C12',2),(3.4,14.6),(9.35,8.7),(6.2,8.1),point('C11',2),point('R7',2)]:via('GND_ISO',xy)
chain('GND_ISO',[point('U1',8),(5.6,12.325),(6.575,11.35),point('R5',2)],.2)
via('FPC_5V',point('R1',1))
via('FPC_5V',point('R3',1)) # explicit raw-sense escape, before quiet-return topology
chain('REG_READY_OD',[point('U2',2),(8.25,8.65),(7.1,8.65),(6.75,8.8),(6.4,8.8),(6.2,8.95),(5.8,9.2)],.2);via('REG_READY_OD',(5.8,9.2))
# Raster collision model, conservative rectangles/clearance; independent DRC checks actual roundrects later.
def patch(shape,inflate):
 if shape['kind']=='line':
  a,c=shape['a'],shape['c'];rad=shape['width']/2+inflate;bounds=(min(a[0],c[0])-rad,min(a[1],c[1])-rad,max(a[0],c[0])+rad,max(a[1],c[1])+rad)
 else:
  x,y=shape['xy'];w,h=(shape['radius']*2,)*2 if shape['kind']=='circle' else shape['size'];bounds=(x-w/2-inflate,y-h/2-inflate,x+w/2+inflate,y+h/2+inflate)
 x0=max(0,int(math.floor(bounds[0]/step)));x1=min(nx-1,int(math.ceil(bounds[2]/step)));y0=max(0,int(math.floor(bounds[1]/step)));y1=min(ny-1,int(math.ceil(bounds[3]/step)))
 if x1<x0 or y1<y0:return None
 xx=np.arange(x0,x1+1)[None,:]*step;yy=np.arange(y0,y1+1)[:,None]*step
 if shape['kind']=='line':
  a,c=shape['a'],shape['c'];dx,dy=c[0]-a[0],c[1]-a[1];t=np.clip(((xx-a[0])*dx+(yy-a[1])*dy)/(dx*dx+dy*dy),0,1);dist=(xx-a[0]-t*dx)**2+(yy-a[1]-t*dy)**2;mask=dist<rad*rad
 elif shape['kind']=='circle':mask=(xx-x)**2+(yy-y)**2<(shape['radius']+inflate)**2
 else:
  dx=np.maximum(abs(xx-x)-w/2,0);dy=np.maximum(abs(yy-y)-h/2,0);mask=dx*dx+dy*dy<inflate*inflate+1e-12
 return slice(y0,y1+1),slice(x0,x1+1),mask

def obstacles(net,width):
 block=np.zeros((3,ny,nx),dtype=bool);vb=np.zeros((ny,nx),dtype=bool)
 edge=.55+width/2
 block[:,:,:int(math.ceil(edge/step))]=True;block[:,:,-int(math.ceil(edge/step)):]=True;block[:,:int(math.ceil(edge/step)),:]=True;block[:,-int(math.ceil(edge/step)):,:]=True
 e=int(math.ceil(.85/step));vb[:e,:]=True;vb[-e:,:]=True;vb[:,:e]=True;vb[:,-e:]=True
 for sh in shapes:
  if sh['net']==net:continue
  z=patch(sh,.215+width/2)
  if z:
   ys,xs,mask=z
   for layer in sh['ls']:block[layer,ys,xs]|=mask
  z=patch(sh,.215+.3)
  if z:
   ys,xs,mask=z;vb[ys,xs]|=mask
 for sh in holes:
  z=patch(sh,.25+width/2) if sh['net']!=net else None
  if z:
   ys,xs,mask=z;block[:,ys,xs]|=mask
  z=patch(sh,.25+.15)
  if z:
   ys,xs,mask=z;vb[ys,xs]|=mask
 # No signal copper under the inductor or inside the top switching loop corridor.
 if net not in ['GND_ISO','SW_L1','SW_L2']:
  for layer in [0,1,2]:block[layer,int(1/step):int(5.0/step),int(6/step):int(11/step)]=True
 return block,vb

def search(net,a,c,width=.2,startlayer=0,goallayer=0,allowed=(0,1,2),ground=False):
 block,vb=obstacles(net,width)
 def snap(pt,ll):
  cx,cy=[int(math.floor(v/step+.5)) for v in pt];options=[]
  for yy in range(max(0,cy-2),min(ny,cy+3)):
   for xx in range(max(0,cx-2),min(nx,cx+3)):
    if not block[ll,yy,xx]:options.append((math.dist(pt,(xx*step,yy*step)),xx,yy))
  if not options:raise RuntimeError(('BLOCKED_ENDPOINT',net,pt,ll,width))
  _,xx,yy=min(options);return xx,yy
 sx,sy=snap(a,startlayer);tx,ty=snap(c,goallayer) if not ground else (sx,sy)
 for layer in set(range(3))-set(allowed):block[layer]=True
 ownvias={int(round(v['xy'][1]/step))*nx+int(round(v['xy'][0]/step)) for v in vias if v['net']==net}
 N=nx*ny;s=startlayer*N+sy*nx+sx;t=goallayer*N+ty*nx+tx
 dist=np.full(3*N,np.inf);parent=np.full(3*N,-1,dtype=np.int32);dist[s]=0;heap=[(0,0,s)];bf=block.ravel();vbf=vb.ravel();exp=0
 def heuristic(x,y,z):
  if ground:return 0
  dx,dy=abs(x-tx),abs(y-ty);return max(dx,dy)+.41421356237*min(dx,dy)+(0 if z==goallayer else 16)
 found=None
 while heap:
  _,g,idx=heapq.heappop(heap)
  if g!=dist[idx]:continue
  layer=idx//N;xy=idx%N;y,x=divmod(xy,nx);exp+=1
  if (not ground and idx==t) or (ground and not vbf[xy] and not bf[N+xy] and x>6 and x<nx-6 and y>6 and y<ny-6):found=idx;break
  for dx,dy,dd in [(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.41421356237),(1,-1,1.41421356237),(-1,1,1.41421356237),(-1,-1,1.41421356237)]:
   xx,yy=x+dx,y+dy
   if not 0<=xx<nx or not 0<=yy<ny:continue
   j=layer*N+yy*nx+xx
   if bf[j]:continue
   ng=g+dd
   if ng<dist[j]:dist[j]=ng;parent[j]=idx;heapq.heappush(heap,(ng+1.08*heuristic(xx,yy,layer),ng,j))
  if not vbf[xy] or xy in ownvias:
   for ll in allowed:
    j=ll*N+xy
    if ll==layer or bf[j]:continue
    ng=g+16
    if ng<dist[j]:dist[j]=ng;parent[j]=idx;heapq.heappush(heap,(ng+1.08*heuristic(x,y,ll),ng,j))
 if found is None:raise RuntimeError(('NO_ROUTE',net,a,c,width,exp))
 path=[];j=found
 while j!=-1:
  ll=j//N;yy,xx=divmod(j%N,nx);path.append((ll,(round(xx*step,5),round(yy*step,5))));j=int(parent[j])
 path=path[::-1]
 # Retain exact original pad center at endpoints, not merely the raster approximation.
 path.insert(0,(startlayer,a))
 if not ground:path.append((goallayer,c))
 else:via(net,path[-1][1])
 start=path[0];last=start;direction=None
 for node in path[1:]:
  if node[0]!=last[0]:
   segment(net,start[1],last[1],width,start[0]);via(net,node[1]);start=node;last=node;direction=None;continue
  delta=(round(node[1][0]-last[1][0],5),round(node[1][1]-last[1][1],5));mag=max(abs(delta[0]),abs(delta[1]));nd=tuple(round(v/mag,4) for v in delta) if mag else direction
  if direction is not None and nd!=direction:segment(net,start[1],last[1],width,start[0]);start=last
  direction=nd;last=node
 segment(net,start[1],last[1],width,start[0]);report.append({'net':net,'start':a,'end':path[-1][1],'width':width,'expanded':exp,'ground_via':ground});print('routed',net,a,'->',path[-1][1],width,exp,flush=True)
 return path[-1][1]
# Reserve the deliberate single power join of U1 quiet ground before the power buses.
search('GND_ISO',(2.,13.5),(3.4,14.6),.2,1,1,(1,))
# High-current tree on B.Cu; paired vias and original F necks already exist.
for net,points in anchors.items():
 points=list(dict.fromkeys(points));connected=[points.pop(0)]
 while points:
  _,i,t=min((math.dist(a,c),i,c) for i,a in enumerate(points) for c in connected);a=points.pop(i);search(net,a,t,.9,1,1,(1,));connected.append(a)
# Reserve the sensitive control copper before building its separate local return tree.
search('REG_VAUX',point('U2',3),point('C11',1),.2,0,0,(0,))
search('REG_FB',point('U2',5),point('R6',2),.2,0,0,(0,))
search('REG_FB',point('R7',1),point('R6',2),.2,0,0,(0,))
search('REG_5V136',point('R6',1),point('C7',1),.2,0,0,(0,)) # dedicated Kelvin sense to output ceramic
# Independent quiet returns route on F to IC-control star before any other GND plane connections.
# Dedicated control return: an In1 copper void prevents its three vias joining
# the power plane before the actual IC-local star. In2 carries this quiet tree.
star=(9.35,8.7);via('GND_ISO',star)
search('GND_ISO',point('U2',4),star,.2,0,0,(0,))
digital=(6.2,8.1);via('GND_ISO',digital)
for no in [1,15]:search('GND_ISO',point('U2',no),digital,.2,0,0,(0,))
for xy in [digital,point('C11',2),point('R7',2)]:
 via('GND_ISO',xy);search('GND_ISO',xy,star,.2,2,2,(2,))
# U1 quiet island likewise returns on In2 to only the left GND terminal star.
star=(2.,13.5);search('GND_ISO',point('U1',4),star,.2,0,0,(0,))
for xy in [point('R2',2),point('R4',2),point('R5',2),point('C12',2)]:search('GND_ISO',xy,star,.2,2,2,(2,))
# All other pad nets, including ground and low-current power taps.
by={}
for p in pads:
 if p['net'].startswith('unconnected-'):continue
 by.setdefault(p['net'],[]).append(p)
# Short sensitive nets before the remaining low-current taps.
order=['REF','REF_RTN','REG_EN_SERIES','INPUT_ILM','INPUT_DVDT','INPUT_DVDT_C','INPUT_UVLO','INPUT_OVLO','USB_D_SHORT','USB_CC2','USB_CC1','REG_READY_OD','PORT_FAULT_OD','FPC_5V','PROTECTED_IN','REG_5V136','USB_VBUS','GND_ISO']
for net in order:
 pp=by.get(net,[])
 if net=='GND_ISO':
  for p in pp:
   ref,no=p['ref'],p['no']
   if ref in ['J0','C8','C13'] or ref=='J1' and no in ['A1_B12','B1_A12'] or (ref,no) in quietkeys or (ref,no)==('U2','10') or ref=='U3' and no=='21':continue
   if p['p'].GetAttribute()!=K.PAD_ATTRIB_SMD:continue # platedshells touch internalplane directly
   search(net,p['xy'],p['xy'],.2,ground=True)
  continue
 if net in anchors:
  # All power pins/caps that were deliberately pre-escaped are connected; taps use narrow traces only.
  skip=set(power_refs[net]);skip|={('C13',1)} if net=='FPC_5V' else set();skip|={('R6',1)} if net=='REG_5V136' else set();skip|={('U2',str(n)) for n in ([12,13] if net=='PROTECTED_IN' else [7,8] if net=='REG_5V136' else [])}
  skip|={('U1',str(5 if net=='FPC_5V' else 6))} if net in ['FPC_5V','PROTECTED_IN'] else set()
  skip|={('U3',str(n)) for n in ([2,3,4,5] if net=='REG_5V136' else [14,15] if net=='USB_VBUS' else [])}
  skip={(a,str(c)) for a,c in skip}
  connected=[(a,1) for a in anchors[net]];pending=[p for p in pp if (p['ref'],p['no']) not in skip]
 elif net=='REG_READY_OD':
  connected=[((5.8,9.2),2)];pending=[p for p in pp if (p['ref'],p['no'])!=('U2','2')]
 else:
  if not pp:continue
  first=pp[0];connected=[(first['xy'],0)];pending=pp[1:]
 while pending:
  _,i,t,tl=min((math.dist(p['xy'],t),i,t,tl) for i,p in enumerate(pending) for t,tl in connected);p=pending.pop(i);search(net,p['xy'],t,.2,0,tl);connected.append((p['xy'],0))
# Ground plane all In1, solid pad connection; filled by real KiCad after saving.
z=K.ZONE(b);z.SetLayer(K.In1_Cu);z.SetNet(nets['GND_ISO']);z.SetLocalClearance(iu(.2));z.SetThermalReliefGap(iu(.25));z.SetThermalReliefSpokeWidth(iu(.3));z.SetPadConnection(K.ZONE_CONNECTION_FULL);out=z.Outline();out.NewOutline()
for x,y in [(.25,.25),(W-.25,.25),(W-.25,H-.25),(.25,H-.25)]:out.Append(iu(x),iu(y))
out.NewHole()
for x,y in [(.6,7.5),(3.1,7.5),(3.1,8.95),(3.9,8.95),(3.9,7.5),(5.7,7.5),(5.7,7.),(8.8,7.),(8.8,9.3),(9.7,9.3),(9.7,7.),(12.5,7.),(12.5,11.3),(6.6,11.3),(6.6,16.2),(3.85,16.2),(3.85,14.2),(2.95,14.2),(2.95,16.2),(.6,16.2),(.6,13.9),(2.4,13.9),(2.4,13.1),(.6,13.1)]:out.Append(iu(x),iu(y),0,0)
b.Add(z);K.SaveBoard(str(P/'source-axial.kicad_pcb'),b)
# Proposed supplier-qualified stack, not a measured laminate/material guarantee.
f=P/'source-axial.kicad_pcb';text=f.read_text();assert '(stackup' not in text;text=text.replace('(setup', '(setup\n'+'(stackup\n (layer "F.SilkS" (type "Top Silk Screen"))\n (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))\n (layer "F.Cu" (type "copper") (thickness 0.07))\n (layer "dielectric 1" (type "prepreg") (thickness 0.10) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))\n (layer "In1.Cu" (type "copper") (thickness 0.035))\n (layer "dielectric 2" (type "core") (thickness 0.57) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))\n (layer "In2.Cu" (type "copper") (thickness 0.035))\n (layer "dielectric 3" (type "prepreg") (thickness 0.10) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))\n (layer "B.Cu" (type "copper") (thickness 0.07))\n (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))\n (layer "B.SilkS" (type "Bottom Silk Screen"))\n (copper_finish "None") (dielectric_constraints no))',1);f.write_text(text)
(P/'route-ledger.json').write_text(json.dumps({'segments':traces,'vias':vias,'paths':report,'router_grid_mm':step,'conservative_router_clearance_mm':.215,'ground_layer':'In1.Cu','power_bus_width_mm':.9,'layout_functional_acceptance':False},indent=2)+'\n')
print('SAVED',len(traces),'segments',len(vias),'vias')
