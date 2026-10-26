from pathlib import Path
import json,math,html
import numpy as np
from scipy.special import betainc
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
P=Path(__file__).resolve().parent;W,H=420,297;c=canvas.Canvas(str(P/'interface-sections.pdf'),pagesize=(W*mm,H*mm));svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297"><rect width="420" height="297" fill="white"/>'];views=json.loads((P/'sections.json').read_text())
def line(points,color='#44515e',width=.15,dash=False):
 if len(points)<2:return
 pts=' '.join(f'{x:.4f},{y:.4f}' for x,y in points);svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="2 1"' if dash else '')+'/>');c.setStrokeColor(color);c.setLineWidth(width*mm);c.setDash([2*mm,mm] if dash else []);p=c.beginPath();p.moveTo(points[0][0]*mm,(H-points[0][1])*mm)
 for x,y in points[1:]:p.lineTo(x*mm,(H-y)*mm)
 c.drawPath(p)
def text(x,y,t,size=3,color='#152435'):
 svg.append(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{color}">{html.escape(t)}</text>');c.setFillColor(color);c.setFont('Helvetica',size*mm);c.drawString(x*mm,(H-y)*mm,t)
def dim(x0,x1,y,t):
 line([(x0,y-2),(x0,y+2)]);line([(x1,y-2),(x1,y+2)]);line([(x0,y),(x1,y)]);line([(x0+2,y-1),(x0,y),(x0+2,y+1)]);line([(x1-2,y-1),(x1,y),(x1-2,y+1)]);text((x0+x1)/2-len(t)*.65,y-2,t,2.8)
def col(n):
 if 'Copper' in n or 'Fanout' in n or 'Tail' in n:return '#b65c12'
 if n.startswith(('rotating_','stationary_')):return '#087e8b'
 if n.startswith('SourceWire'):return '#7d4b91'
 if 'Pin_' in n or 'Trunk' in n or 'Carrier' in n:return '#7b4051'
 return '#45515c'
text(12,15,'COMPACT INTERFACE REPAIR | S12 MECHANICAL PROTOTYPE',5)
text(12,23,'Equal scale 1:1 at A3. Dimensions mm. Sections of saved CAD, neutral collar. Not a manufacturing or electrical release.',3.1)
text(12,31,'Stationary mains/PE; only isolated LV rotates. Actual source boards unchanged. Body profiles are saved allocations; supplier detail remains open.',2.8)
origins={'XY':(189,120),'fixed':(80,235),'source':(210,235)}
for view,lines in views.items():
 ox,oy=origins[view]
 for r in lines:line([(ox+x,oy-y) for x,y in r['points']],col(r['part']),.12)
# Frozen neutral active path, independently labeled centerline, not a material/supplier claim.
m=json.loads((P.parent/'constant-length-mechanism/motion.json').read_text());row=next(x for x in m['rows'] if x['angle']==0);t=np.linspace(0,1,8193);N=6;k=row['k'];r=25+.3*N*t+(5.5-.3*N)*betainc(2+math.exp(k),2+math.exp(-k),t);ph=2*math.pi*N*t;line([(80+rr*math.cos(a),235-rr*math.sin(a)) for rr,a in zip(r,ph)],'#bd731e',.10)
line([(73,94),(154,94),(154,146),(73,146),(73,94)],'#87516f',.15,True)
text(74,91,'81 x 52 planning reservation',2.7,'#87516f')
line([(25,65),(355,65),(355,154),(25,154),(25,65)],'#9aa3aa',.15,True)
text(25,46,'LONGITUDINAL SECTION | Z0',3.5);text(318,53,'330 baseline',3,'#737e87');dim(25,300,57,'275 comparison with 24 mm blanks')
line([(308,64),(308,155)]);line([(306,64),(310,64)]);line([(306,155),(310,155)]);text(311,113,'91',3)
text(25,164,'24 mm input blank',2.8);text(77,174,'Sourcepod / carrier construction UNMET',3)
dim(189,276,168,'87 core allocation')
text(210,84,'24 x 16 S12',2.8);line([(222,86),(223,105)],'#087e8b')
text(245,77,'32 x 26 S12',2.8);line([(258,79),(258,94)],'#087e8b')
text(278,88,'USB body edge X86.37',2.8);text(278,92,'NOT a mating plane',2.8)
text(275,174,'24 mm output blank',2.8)
text(35,190,'A-A | X34.2 | FIXED INTERFACE',3.4);text(165,190,'B-B | X63.2 | SOURCE BAY',3.4)
dim(45,115,280,'70 trial OD');dim(175,245,280,'70 trial OD')
text(43,289,'Active centerline shown; 0.16 mm stack allocation',2.6);text(169,289,'New return bridge outside developed fanout',2.6)
notes=['Geometry comparison only: 275 x 91 x 74.', '330 x 89 x 72 baseline is also unaccepted.', 'Actual end assemblies add unknown space.', 'Bare rear-depth deltas: +12.8 classic,', '+16.0 TRUE1, +40.9 NEMA; before wires/tools.', 'NEMA flange diameter63.5 also changes fit.', 'No installed mating/latch/hand envelope.', '', 'Minco-compatible construction is a capability,', 'not approval of this stack or formed geometry.', 'S12 remains UNROUTED and unqualified.', 'Read receipt.json for actual check outcomes.', 'No torque, flex-life, thermal or safety rating.']
for i,t in enumerate(notes):text(269,204+5.7*i,t,2.8)
svg.append('</svg>');(P/'interface-sections.svg').write_text('\n'.join(svg)+'\n');c.showPage();c.save()
