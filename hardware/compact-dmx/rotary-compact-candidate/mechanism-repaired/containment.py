"""Final assembly within the181-position swept envelope + keyed retention/assembly tests."""
import FreeCAD as A,Part,json,os,hashlib
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']);V=A.Vector
old=A.openDocument(str(P/'sweep-envelope.FCStd'));oldsh={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')};A.closeDocument(old.Name)
D=A.openDocument(str(P/'mechanism.FCStd'));sh={o.Name:o.Shape.copy() for o in D.Objects if hasattr(o,'Shape')}
G=json.loads((P/'groups.json').read_text());OG=json.loads((P/'sweep-groups.json').read_text())
def cmp(sh,g,k):return Part.makeCompound([sh[n] for n,v in g.items() if v==k])
om=cmp(oldsh,OG,'rotor');nm=cmp(sh,G,'rotor')
assert nm.cut(om).Volume<1e-6
of=cmp(oldsh,OG,'stationary');nf=cmp(sh,G,'stationary')
extra=nf.cut(of)
# New anti-rotation key is entirely before the rotating assembly; transfer of the
# travel stop from housing to cap stays in old envelope. No hidden new swept collision.
assert extra.Volume<1e-6 or extra.BoundBox.XMax<41.40001
assert nm.BoundBox.XMin>=41.99999
op=oldsh['IndexPin'];np=sh['IndexPin'].fuse(sh['IndexKnob']);assert np.cut(op).Volume<1e-6
# Pin tip is unchanged in the index engagement region, so prior locked tests apply.
region=Part.makeBox(3,70,70,V(42,-35,-35))
assert op.common(region).cut(np).Volume<1e-6 and np.common(region).cut(op).Volume<1e-6
pin=sh['IndexPin'];spool=sh['StationarySpool'];cap=sh['IndexRearCap'];retainer=spool.fuse(cap)
stops=[]
for dx in [0,-4.2,.05,-4.25]:
 s=pin.copy();s.translate(V(dx,0,0));vol=s.common(retainer).Volume
 assert (vol<1e-6 if dx in [0,-4.2] else vol>.01),(dx,vol)
 stops.append({'pin_displacement_mm':dx,'intersection_mm3':vol,'allowed':dx in [0,-4.2]})
keys=[]
for ang in [-45,45]:
 s=pin.copy();s.rotate(V(0,28.5,0),V(1,0,0),ang);vol=s.common(spool).Volume
 assert vol>.01;keys.append({'stem_rotation_deg':ang,'key_interference_mm3':vol})
# Cap and knob removed: flange must actually pass through rear housing for assembly.
assembly=[]
for dx in range(0,-13,-1):
 s=pin.copy();s.translate(V(dx,0,0));vol=s.common(spool).Volume
 assert vol<1e-6,(dx,vol);assembly.append({'pin_displacement_mm':dx,'housing_intersection_mm3':vol})
r={'status':'PASS final mechanism conservatively covered by swept input','sweep_input_sha256':hashlib.sha256((P/'sweep-envelope.FCStd').read_bytes()).hexdigest(),'moving_outside_swept_input_mm3':nm.cut(om).Volume,'stationary_added_key_volume_mm3':extra.Volume,'added_key_XMax_mm':extra.BoundBox.XMax if extra.Volume>1e-6 else None,'rotor_XMin_mm':nm.BoundBox.XMin,'pin_union_outside_original_mm3':np.cut(op).Volume,'tip_geometry_equal':True,'axial_stop_checks':stops,'stem_key_checks':keys,'rear_insertion_checks':assembly,'interpretation':'Same181rigid pose proof applies; added fixed key has>=0.6mm axial separation from all rotating parts. Active flex proof unchanged.'}
(P/'containment.json').write_text(json.dumps(r,indent=2)+'\n');print('CONTAINMENT / RETENTION / INSERTION PASS',flush=True)
A.closeDocument(D.Name)
