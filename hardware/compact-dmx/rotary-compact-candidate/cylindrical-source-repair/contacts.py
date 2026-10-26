from pathlib import Path
import FreeCAD as A,json
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};rows=[]
def check(a,b,maxgap=1e-7):
 gap=S[a].distToShape(S[b])[0];r={'a':a,'b':b,'gap':gap,'max_gap':maxgap};rows.append(r);assert gap<=maxgap,r
for i,pin in [('1','Pin_LVplus'),('2','Pin_LVminus')]:
 check('SourceWireCopper'+i,pin)
 choices=['J0_Solder'+i+'_'+str(j) for j in range(2)];wire='SourceWireCopper'+i;pad='stationary_J0_Pad'+i+'_'+str(int(i)-1)
 for solder in choices:check(wire,solder);check(solder,pad)
check('IRM20_12_maxbody','RetainedCarrier');check('RetainedCarrier','LowerShellPosts');check('SupportedFilm','LowerShellPosts')
topgap=S['IRM20_12_maxbody'].distToShape(S['UpperShellRetention'])[0];assert abs(topgap-.25)<1e-6
fusegap=S['LineToFuse'].distToShape(S['FuseToLinePin'])[0]
(P/'contact-check.json').write_text(json.dumps({'contacts':rows,'module_top_retention_gap':topgap,'fuse_conductor_envelope_gap':fusegap,'fuse_centerline_endpoint_gap':4,'fuse_unconnected':True,'S12_through_board_electrical_path':'UNROUTED / no physical continuity claim','sourcepin_wire_and_J0_solder_contact':'Geometry only; solder/splice process unqualified'},indent=2)+'\n');print('CONTACTS',len(rows),'TOPGAP',topgap,'FUSEGAP',fusegap,flush=True)
