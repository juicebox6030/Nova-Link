from pathlib import Path
import urllib.request,hashlib,json,zipfile,subprocess
P=Path(__file__).resolve().parent;S=P/'sources';S.mkdir(exist_ok=True)
urls={
'pmp-page.html':'https://www.ti.com/tool/PMP11295',
'tida-page.html':'https://www.ti.com/tool/TIDA-01560',
'notice.html':'https://www.ti.com/legal/important-notice-and-disclaimer.html',
'pmp-report.pdf':'https://www.ti.com/lit/pdf/tidubh4',
'pmp-assembly.pdf':'https://www.ti.com/lit/pdf/tidrkg9',
'pmp-bom.pdf':'https://www.ti.com/lit/pdf/tidrkg8',
'pmp-schematic.pdf':'https://www.ti.com/lit/pdf/tidrkg7',
'pmp-gerber.zip':'https://www.ti.com/lit/zip/tidcbt5',
'tida-guide.pdf':'https://www.ti.com/lit/pdf/tiduds3',
'tida-assembly.pdf':'https://www.ti.com/lit/pdf/tidrvx1',
'tida-bom.pdf':'https://www.ti.com/lit/pdf/tidrvx0',
'tida-layout.pdf':'https://www.ti.com/lit/pdf/tidrvx2',
'tida-schematic.pdf':'https://www.ti.com/lit/pdf/tidrvw9',
'tida-cad.zip':'https://www.ti.com/lit/zip/tidrvx3',
'tida-gerber.zip':'https://www.ti.com/lit/zip/tidcek6'}
manifest={}
for n,u in urls.items():
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=40) as r:data=r.read();status=r.status;final=r.url;typ=r.headers.get('Content-Type')
  (S/n).write_bytes(data);valid=zipfile.is_zipfile(S/n) if n.endswith('.zip') else data.startswith(b'%PDF') if n.endswith('.pdf') else True
  manifest[n]={'url':u,'resolved_url':final,'http':status,'content_type':typ,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'expected_format_valid':valid}
  if valid and n.endswith('.pdf'):subprocess.run(['pdftotext','-layout',str(S/n),str(S/n.replace('.pdf','.txt'))],check=True)
  if valid and n.endswith('.zip'):
   z=zipfile.ZipFile(S/n);manifest[n]['members']=z.namelist()
   dest=S/n.replace('.zip','');dest.mkdir(exist_ok=True)
   for m in z.infolist():
    target=(dest/m.filename).resolve()
    if not target.is_relative_to(dest.resolve()):raise ValueError('unsafezip')
   z.extractall(dest)
  print(n,len(data),valid,flush=True)
 except Exception as e:manifest[n]={'url':u,'error':str(e)};print(n,str(e),flush=True)
 (P/'retrieval.json').write_text(json.dumps(manifest,indent=2)+'\n')
