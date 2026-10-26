from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[3];B=P.parent
paths=[]
for folder in [B/'compact-interface-repair',B/'source12-candidate',R/'hardware/compact-dmx/connector-interface-candidate',R/'hardware/compact-dmx/connector-mating-envelope']:
 paths.extend(x for x in folder.rglob('*') if x.is_file())
paths += [R/'docs/hardware/DMX_Dongle_and_Power_Barrel.md',B/'stationary-source-pod/README.md',B/'stationary-irm20-integration/installation-gate/receipt.json',B/'constant-length-mechanism/motion.json']
sources={
 'regulated-source/sources/irm20.pdf':('https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF','2025-11-21, p3: nominal body52.4x27.2x24, general +/-.5; pin3.5+/-1'),
 'stationary-irm20-integration/sources/meanwell-pcb-installation.pdf':('https://www.meanwell.com/Upload/PDF/IRM-01/PCB.pdf','Installation(2), p1: 5mm bottom plusMylar;10mm around. Does not approve ourcarrier'),
 'regulated-source/sources/usb4105.pdf':('https://gct.co/files/drawings/USB4105.pdf','Frozen S12 connector geometry provenance; bodyedge is not matingdatum')}
for rel in sources: paths.append(B/rel)
manifest={str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(set(paths))}
(P/'protected-inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
(P/'sources.json').write_text(json.dumps({rel:{'url':u,'callout':c,'sha256':hashlib.sha256((B/rel).read_bytes()).hexdigest()} for rel,(u,c) in sources.items()},indent=2)+'\n')
print(len(manifest),'frozen files')
