from pathlib import Path
import FreeCAD as A,json
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};rows=[]
def contact(a,b,label):
 gap=S[a].distToShape(S[b])[0];vol=S[a].common(S[b]).Volume;rows.append({'a':a,'b':b,'gap':gap,'volume':vol,'role':label});assert gap<1e-6,(a,b,gap)
for pin,source in [('1','Pin_LVplus'),('2','Pin_LVminus')]:
 contact(source,'SourceWireCopper'+pin,'named unqualified source-pin electrical endpoint')
 for i in [0,1]:
  contact('SourceWireCopper'+pin,'J0_Solder'+pin+'_'+str(i),'proposed wire/fillet surface')
  contact('J0_Solder'+pin+'_'+str(i),'stationary_J0_Pad'+pin+'_'+str(int(pin)-1),'proposed fillet/actual J0 land')
 contact('stationary_J2_Pad'+pin+'_'+str(int(pin)-1),'J2_Solder'+pin,'actual protected/return pad to preform')
 contact('J2_Solder'+pin,'FixedFanoutCopper'+pin,'back-access exposed copper')
 contact('FixedFanoutCopper'+pin,'FixedTailCopper'+pin,'continuous developed static copper to fixed tail')
 contact('MovingTailCopper'+pin,'MovingFanoutCopper'+pin,'continuous moving tail to developed static copper')
 contact('MovingFanoutCopper'+pin,'J3_Solder'+pin,'exposed copper to preform')
 contact('J3_Solder'+pin,'rotating_J3_Pad'+pin+'_'+str(int(pin)-1),'actual rotating positive/return land')
(P/'contact-check.json').write_text(json.dumps({'status':'PASS local mechanical contacts only','rows':rows,'not_physical_edges':['J0 through U1 to J2: actual netlist, UNROUTED board','active1046mm copper lanes: invariant X lane contract on frozen winding, supplier circuit fabrication UNQUALIFIED'],'complete_electrical_assembly':False},indent=2)+'\n');print('CONTACTS',len(rows),'PASS',flush=True)
