"""Sequential local-only regeneration, reopened native checks and drawing export.
FreeCAD CLI can return0 after a Python exception: inspect diagnostics as well as rc.
"""
from pathlib import Path
import subprocess,os,json,time
P=Path(__file__).resolve().parent;R=P.parents[3];commands=[]
for name,cmd in [('build',['/home/juicebox/.local/bin/freecadcmd',str(P/'build.py')]),('project',['/home/juicebox/.local/bin/freecadcmd',str(P/'project.py')]),('verify',['/home/juicebox/.local/bin/freecadcmd',str(P/'verify.py')]),('draw',['python3',str(P/'draw.py')])]:
 start=time.monotonic()
 with (P/(name+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=R,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},stdout=f,stderr=subprocess.STDOUT)
 diagnostic=(P/(name+'.log')).read_text(errors='replace')
 assert r.returncode==0 and not any(x in diagnostic for x in ['Traceback (most recent call last)','Exception while processing file']),(name,r.returncode,'See '+str(P/(name+'.log')))
 commands.append({'command':cmd,'cwd':str(R),'QT_QPA_PLATFORM':'offscreen','exit_code':r.returncode,'seconds':round(time.monotonic()-start,3),'log':name+'.log','exception_diagnostic_screen':'PASS'})
 print(name,'PASS',flush=True)
for f in P.glob('*.FCBak'):f.unlink()
(P/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
assert json.loads((P/'checks.json').read_text())['unexpected_volume_intersections']==0
print('PASS bounded stationary integration checks; qualification gates remain UNMET')
