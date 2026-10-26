"""Bounded LibreDWG conversion + body-preservation check. No source cache writes.
python3 hardware/fixture-fit/measurements/check_chauvet.py
Temporary DWG/DXF are removed; metadata and actual converter diagnostics remain.
"""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from tempfile import TemporaryDirectory
from collections import Counter
import json,subprocess
import ezdxf
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'chauvet-e910fc'
OUT.mkdir(exist_ok=True)
archive=ROOT/'hardware/fixture-fit/source-cache/chauvet-ovation-e-910fc-3d-cad.zip'
archive_hash=sha256(archive.read_bytes()).hexdigest()
assert archive_hash=='5032128181480201b3815f67699c6e264825188e3399b2341cf1f2d4c665051f'
member='OVATION E-910FC_3D.dwg'
with ZipFile(archive) as z: data=z.read(member)
receipt={'archive':str(archive.relative_to(ROOT)),'archive_sha256':archive_hash,'member':member,'member_bytes':len(data),'member_sha256':sha256(data).hexdigest(),'dwg_header':data[:6].decode(),'converter':'LibreDWG 0.14 (.tools/libredwg-0.14/bin/dwg2dxf)','timeout_seconds':180}
with TemporaryDirectory(prefix='conversion-',dir=OUT) as work:
    src=Path(work)/'source.dwg';dst=Path(work)/'converted.dxf';src.write_bytes(data)
    cmd=[str(ROOT/'.tools/libredwg-0.14/bin/dwg2dxf'),'-o',str(dst),str(src)]
    with (OUT/'conversion.log').open('w') as log:
        try: status=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
        except subprocess.TimeoutExpired: status=124
    receipt['conversion_exit']=status
    if dst.exists() and status==0:
        receipt['dxf_bytes']=dst.stat().st_size
        receipt['dxf_sha256']=sha256(dst.read_bytes()).hexdigest()
        d=ezdxf.readfile(dst)
        receipt['dxf_version']=d.dxfversion;receipt['declared_INSUNITS']=d.units
        receipt['modelspace_counts']=dict(Counter(e.dxftype() for e in d.modelspace()))
        solids=list(d.modelspace().query('3DSOLID'))
        receipt['solid_payloads']=[{'handle':e.dxf.handle,'sat_lines':len(e.sat),'sab_bytes':len(e.sab)} for e in solids]
        receipt['ACDSDATA_entity_count']=len(d.acdsdata.entities)
        receipt['usable_body_payloads']=sum(bool(e.sat or e.sab) for e in solids)
        receipt['fit_use']='Rejected: empty converted solid bodies; no preserved measurable 3D geometry.'
    else: receipt['fit_use']='Rejected: bounded conversion did not complete successfully.'
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='solid_payloads'},indent=2))
