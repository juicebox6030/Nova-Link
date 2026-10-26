from pathlib import Path
import FreeCAD as A,json,math,hashlib
P=Path(__file__).resolve().parent;root=P.parents[3];d=A.openDocument(str(P/'interface-prototype.FCStd'));boards=json.loads((P/'actual-boards.json').read_text());names=json.loads((P/'pad-objects.json').read_text());rows=[]
def area(w,h,r):return w*h-(4-math.pi)*r*r
for zone,board in boards.items():
 ox,oy,oz=(22.2,14.5,8) if zone=='stationary' else(52.2,26.1,13)
 for comp in board['components']:
  for i,p in enumerate(comp['pads']):
   if not p['number']:continue
   n=names['|'.join([zone,comp['ref'],p['number']])]
   # Shared padnumber bars require the exact index, not a dictionary's last match.
   n=zone+'_'+comp['ref']+'_Pad'+p['number']+'_'+str(i);o=d.getObject(n);assert o,n
   w,h=p['size'];r=min(w,h)/2 if p['shape']==2 else p['round_radius'];ar=area(w,h,r);dw,dh=p['drill']
   if dw:ar-=area(dw,dh,min(dw,dh)/2)
   c=o.Shape.Solids[0].CenterOfMass;target=[ox+p['x'],oy+.0175,oz-p['y']];err=max(abs(a-b) for a,b in zip([c.x,c.y,c.z],target));ve=abs(o.Shape.Volume-ar*.035)
   assert err<1e-6 and ve<1e-6,(n,err,ve)
   assert o.Basis.split(';')[0]==p['net'],n
   rows.append({'pad':n,'centroid_error':err,'volume_error':ve,'net':p['net']})
for zone in boards:
 src=P.parent/'source12-candidate'/('source12-'+zone+'.kicad_pcb');copy=P/'electrical-frozen'/src.name
 assert src.read_bytes()==copy.read_bytes();assert hashlib.sha256(src.read_bytes()).hexdigest()==boards[zone]['sha256']
(P/'pad-cad-check.json').write_text(json.dumps({'count':len(rows),'status':'PASS','rows':rows},indent=2)+'\n');print('PAD/CAD',len(rows),'PASS',flush=True)
