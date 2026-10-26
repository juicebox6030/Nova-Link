"""Extract exact vector pad polygons from SWRC354 Gerbers, not raster measurement.
PnP supplies location/rotation. IPC numbering independently follows Johanson top view.
"""
from pathlib import Path
import re,math,json,hashlib
P=Path(__file__).resolve().parent;S=P.parent/'source-cache/swrc354'
def read(name):
 s=(S/'gerber'/name).read_text();assert '%FSLAX25Y25*MOMM*%' in s
 aps=dict(re.findall(r'%ADD(\d+)(.*?)\*%',s,re.S));mac=dict(re.findall(r'%AM([^*]+)\*(.*?)%',s,re.S));x=y=0;ap='';out=[]
 for c in re.sub(r'%.*?%','',s,flags=re.S).split('*'):
  c=c.strip();m=re.fullmatch(r'(?:G54)?D(\d+)',c)
  if m:ap=m[1];continue
  # Positions must advance on draws/moves too, not just flashes.
  for axis in ('X','Y'):
   m=re.search(axis+r'(-?\d+)',c)
   if m:
    if axis=='X':x=int(m[1])/1e5
    else:y=int(m[1])/1e5
  if 'D03' not in c or not aps.get(ap,'').startswith('MACRO'):continue
  z=mac[aps[ap]].strip().split('*')[0].replace('\n','').split(',');assert z[0]=='4' and z[1]=='1'
  n=int(z[2]);v=list(map(float,z[3:3+2*(n+1)]));assert float(z[-1])==0
  pts=list(zip(v[::2],v[1::2]));out.append({'xy':[x,y],'aperture':ap,'polygon':pts})
 return out
pnp={}
for line in (S/'docs/Pick n Place.txt').read_text().splitlines():
 a=[x.strip() for x in line.split('!')]
 if len(a)>=6 and a[0] in ['TR1','C131','C331','C41','FL1','L331']:
  assert not a[4];pnp[a[0]]={'xy':[float(a[1]),float(a[2])],'rotation':float(a[3]),'package':a[5]}
config={'TR1':('TI_IPC1352_Vector',1.3,10,[2,1.25]),'C131':('TI_CAPC1005_Vector',.7,2,[1,.5]),'C331':('TI_CAPC1608_Vector',.85,2,[1.6,.8]),'C41':('TI_CAPC0603_Vector',.5,2,[.6,.3]),'FL1':('TI_BLM18_Vector',1,2,[1.6,.8]),'L331':('TI_MLZ2012_Vector',1.2,2,[2,1.25])}
files={'copper':'Top.art','paste':'paste_top.art','mask':'soldmask_top.art'};data={k:read(f) for k,f in files.items()};result={}
def transform(x,y,angle):
 c=math.cos(math.radians(angle));s=math.sin(math.radians(angle));return [round(c*x+s*y,6),round(s*x-c*y,6)]
for ref,(name,radius,count,body) in config.items():
 pos=pnp[ref];cx,cy=pos['xy'];angle=pos['rotation'];layers={}
 for layer,flashes in data.items():
  picks=[p for p in flashes if math.hypot(p['xy'][0]-cx,p['xy'][1]-cy)<radius];assert len(picks)==count,(ref,layer,len(picks))
  normalized=[]
  for f in picks:
   xy=transform(f['xy'][0]-cx,f['xy'][1]-cy,angle)
   normalized.append({'at':xy,'polygon':[transform(x,y,angle) for x,y in f['polygon']],'gerber_flash_xy':f['xy'],'aperture':f['aperture']})
  if ref=='TR1':
   for pad in normalized:
    x,y=pad['at']
    if abs(y)<.01:pin=10 if x>0 else 5
    elif y<0:pin={.75:1,.25:2,-.25:3,-.75:4}[round(x,2)]
    else:pin={-.75:6,-.25:7,.25:8,.75:9}[round(x,2)]
    pad['pin']=str(pin)
  else:
   normalized.sort(key=lambda p:p['at'][0]);assert abs(normalized[0]['at'][1])<.001 and abs(normalized[1]['at'][1])<.001
   for i,pad in enumerate(normalized):pad['pin']=str(i+1) # unpolarized2terminal convention
  layers[layer]=sorted(normalized,key=lambda p:int(p['pin']))
 result[name]={'reference':ref,'source_pnp':pos,'body_nominal_mm':body,'layers':layers}
files2=[S/'gerber'/f for f in files.values()]+[S/'docs/Pick n Place.txt',S/'cadence/pstchip.dat',S/'cadence/pstxnet.dat']
out={'source':'TI SWRC354 CC1352EM-IPC Rev1.1.0 2018-03-15','pin_mapping':'TR1 manufacturer Rev2.0 top view;2terminal nonpolar local1left2right','source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files2},'footprints':result}
(P/'ti-vector-lands.json').write_text(json.dumps(out,indent=2)+'\n')
for n,d in result.items():
 print(n,[(p['pin'],p['at'],[round(max(z[i] for z in p['polygon'])-min(z[i] for z in p['polygon']),6) for i in (0,1)]) for p in d['layers']['copper']])
