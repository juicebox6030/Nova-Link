from pathlib import Path
import FreeCAD as A,json,math
P=Path(__file__).resolve().parent;d=A.openDocument(str(P.parent/'compact-interface-repair/interface-prototype.FCStd'));g=json.loads((P.parent/'compact-interface-repair/groups.json').read_text());s={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')}
rows={}
for n in s:
 if n.startswith(('rotating_','stationary_')) or n=='LockAccess':
  b=s[n].BoundBox;rows[n]={'bbox':[b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax],'valid':s[n].isValid(),'solid_count':len(s[n].Solids)}
rot=[s[n].BoundBox.XMin for n in s if g[n] in ['rotating','rotating_pad','rotating_stake','collar_rotor']]
# Cylinder ends before transition, which terminates at core X0. All turns leave X unchanged.
checks=[{'angle':a,'source_bay_to_rotor_axial_gap':min(rot)+21.33072900770154,'source_bay_to_USB_body_axial_gap':s['rotating_J1_Body'].BoundBox.XMin+21.33072900770154,'source_bay_to_lock_access_axial_gap':s['LockAccess'].BoundBox.XMin+21.33072900770154} for a in range(-90,91)]
out={'native_shapes':len(s),'source_board_and_lock_objects':rows,'motion_screen':checks,'scope':'Read-only axial separation of proposed source cylinder from frozen rotor/USB/lock; not new whole-assembly motion/stop/insertion acceptance','minimum_rotor_x':min(rot)}
(P/'native-screen.json').write_text(json.dumps(out,indent=2)+'\n');print('READ',len(s),'SHAPES',len(rows),'BOARD/LOCK OBJECTS;181 AXIAL SCREENS',flush=True)
A.closeDocument(d.Name)
