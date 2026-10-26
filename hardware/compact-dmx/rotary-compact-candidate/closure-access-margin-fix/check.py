from pathlib import Path
import json,hashlib,zipfile,xml.etree.ElementTree as E,traceback,os,math
import FreeCAD as A,Part
P=Path(__file__).resolve().parent;B=P.parent;R=P.parents[3]
S=B/'closure-access-fix';O=P
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
try:
    old=zipfile.ZipFile(S/'prototype.FCStd');new=zipfile.ZipFile(P/'prototype.FCStd')
    names=[n for n in old.namelist() if n.endswith('.Shape.brp')]
    assert len(names)==356 and set(names)=={n for n in new.namelist() if n.endswith('.Shape.brp')}
    unchanged=[];byte_identical=0
    for n in names:
        if n=='UpperShellRetention.Shape.brp':continue
        a,b=old.read(n),new.read(n)
        if a==b:byte_identical+=1
        else:
            # Saved OCC BRep check-state flags can differ after Boolean use.
            # Compare the actual cleaned, validated shapes as the native API does.
            aa=Part.Shape();aa.importBrepFromString(a.decode())
            bb=Part.Shape();bb.importBrepFromString(b.decode())
            assert aa.isValid() and bb.isValid(),n
            x,y=aa.cleaned().exportBrepToString().split(),bb.cleaned().exportBrepToString().split()
            assert len(x)==len(y),n
            for u,v in zip(x,y):
                if u!=v:assert abs(float(u)-float(v))<1e-12,(n,u,v)
        unchanged.append(n)
    def placements(z):
        root=E.fromstring(z.read('Document.xml'))
        return {o.attrib['name']:o.find("./Properties/Property[@name='Placement']/PropertyPlacement").attrib for o in root.findall('./ObjectData/Object') if o.find("./Properties/Property[@name='Shape']") is not None}
    pa,pb=placements(old),placements(new)
    assert pa.keys()==pb.keys()
    for n in pa:
        assert pa[n].keys()==pb[n].keys()
        assert all(abs(float(pa[n][k])-float(pb[n][k]))<1e-12 for k in pa[n]),n
    def shape(z,n):
        s=Part.Shape();s.importBrepFromString(z.read(n+'.Shape.brp').decode());return s
    a,b=shape(old,'UpperShellRetention'),shape(new,'UpperShellRetention')
    assert b.isValid() and b.isClosed() and len(b.Solids)==1
    assert b.cut(a).Volume<1e-7
    seat=Part.makeBox(100,100,4.0,A.Vector(-120,-50,0))
    assert a.common(seat).cut(b).Volume<1e-7
    rows=[]
    for name in sorted(n[:-10] for n in names if n.startswith('ClosureTool_')):
        tool=shape(new,name);before=tool.common(a).Volume;after=tool.common(b).Volume
        distance=tool.distToShape(b)[0]
        assert before<1e-7 and after<1e-7 and distance>.249999,(name,before,after,distance)
        rows.append({'tool':name,'CAF_R1_overlap_mm3':before,'CAF_R2_overlap_mm3':after,'minimum_tool_to_upper_distance_mm':distance})
    assert len(rows)==4
    bearings=[]
    for x in(-110,-32):
        for y in(-32,32):
            disk=Part.makeCylinder(2,.01,A.Vector(x,y,2.99))
            before=a.common(disk).Volume/.01;after=b.common(disk).Volume/.01
            assert abs(before-after)<1e-6 and abs(after-math.pi*(4-1.2**2))<1e-5
            bearings.append({'xy':[x,y],'before_area_mm2':before,'after_area_mm2':after})
    out={'status':'PASS targeted parent saved-BRep checks','source_native_sha256':sha(S/'prototype.FCStd'),'native_sha256':sha(P/'prototype.FCStd'),'unchanged_other_BReps':len(unchanged),'byte_identical_other_BReps':byte_identical,'all_placements_preserved_numeric_1e12':True,'changed_upper_valid_connected_closed':True,'changed_upper_added_volume_mm3':b.cut(a).Volume,'removed_upper_volume_mm3':a.Volume-b.Volume,'four_driver_checks':rows,'four_bearing_checks':bearings,'limits':['BReps imported directly from actual saved FCStd zip; no whole-native UI or STEP import repeated','Author full tool/lid/screw insertion pair receipts retained via hashes, not independently repeated','No strength, sealing, source-construction or electrical acceptance']}
    (O/'check.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out),flush=True)
except BaseException:
    traceback.print_exc();os._exit(1)
os._exit(0)
