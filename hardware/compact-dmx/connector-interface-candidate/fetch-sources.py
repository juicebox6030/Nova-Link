#!/usr/bin/env python3
"""Cache only explicit official URLs; no catalog crawling or model substitution."""
from pathlib import Path
import urllib.request,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parent
manifest=ROOT/'source-manifest.json'
rows=json.loads(manifest.read_text()) if manifest.exists() else []
for spec in sys.argv[1:]:
 name,url=spec.split('=',1)
 path=ROOT/'sources'/name
 if path.exists(): continue
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r: data=r.read(); final=r.url; headers=dict(r.headers)
  path.write_bytes(data)
  row={'file':'sources/'+name,'url':url,'retrieved_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'final_url':final,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'content_type':headers.get('Content-Type'),'last_modified':headers.get('Last-Modified'),'status':'fetched'}
 except Exception as e: row={'file':'sources/'+name,'url':url,'status':'failed','error':str(e)}
 rows.append(row)
 manifest.write_text(json.dumps(rows,indent=2)+'\n')
 print(name,row['status'],row.get('bytes',row.get('error')))
