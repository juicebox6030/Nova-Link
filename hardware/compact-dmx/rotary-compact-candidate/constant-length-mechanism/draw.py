"""Same vector primitives render SVG/PDF. Dimensioned failure screen, not release."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import json,math,html
P=Path(__file__).resolve().parent;poses=json.loads((P/'poses.json').read_text());W,H=1100,950
c=canvas.Canvas(str(P/'sections.pdf'),pagesize=(W,H),invariant=1);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def text(x,y,s,size=11,color='#263746'):
 c.setFillColor(HexColor(color));c.setFont('Helvetica',size);c.drawString(x,H-y,s)
 svg.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}">{html.escape(s)}</text>')
def line(points,color='#30383e',width=.8):
 c.setStrokeColor(HexColor(color));c.setLineWidth(width);p=c.beginPath();p.moveTo(points[0][0],H-points[0][1])
 for x,y in points[1:]:p.lineTo(x,H-y)
 c.drawPath(p);svg.append('<polyline fill="none" stroke="'+color+'" stroke-width="'+str(width)+'" points="'+' '.join(f'{x:.4f},{y:.4f}' for x,y in points)+'"/>')
def rect(x,y,w,h,fill='#dddddd',stroke='#30383e'):
 c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke));c.setLineWidth(.6);c.rect(x,H-y-h,w,h,fill=1)
 svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width=".6"/>')
def circle(x,y,r,color):
 c.setStrokeColor(HexColor(color));c.setLineWidth(.6);c.circle(x,H-y,r,fill=0)
 svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{color}" stroke-width=".6"/>')
text(30,35,'CONSTANT-LENGTH ROTARY COLLAR / NON-ACCEPTED CANDIDATE',21)
text(30,61,'Stationary core Ø48 × 142 mm; trial shell Ø66 mm; ±90° geometric paths. No assembled mechanism acceptance.',12)
for i,a in enumerate([-90,0,90]):
 ox=190+360*i;oy=225;scale=3
 text(ox-110,105,f'{a:+d} degrees / active ribbon end view',12)
 for r,col in [(33,'#30383e'),(32,'#888888'),(31,'#448899'),(24.6,'#448899'),(24,'#30383e')]:circle(ox,oy,r*scale,col)
 for side in ['outer','inner']:line([(ox+p[0]*scale,oy-p[1]*scale) for p in poses[str(a)][side]],'#bb6c13',.45)
 text(ox-100,346,'Ø66 outer / Ø48 core; 3 drawing units/mm',10)
text(30,390,'AXIAL SECTION — X along core; radial section at USB. Board bay shifted +1.8 mm past fixed stop.',13)
def xy(x,r):return 50+(x-28)*11,600-(r-22)*11
def rb(x,r,l,h,color):u,v=xy(x,r+h);rect(u,v,l*11,h*11,color)
rb(28,22,85,2,'#c8cdd1');rb(42,32,56.8,1,'#b5c1cc');rb(47,25,20,5.5,'#e7c58f');rb(73.8,25.1,25,1,'#548959');rb(73.8,26.1,17.5,3.2,'#c2d6b5');rb(91.45,26.1,7.35,3.31,'#adb3ba')
line([xy(98.8,24.58),xy(110.8,24.58),xy(110.8,31.08),xy(98.8,31.08),xy(98.8,24.58)],'#9c3343')
line([xy(72.5,30.8),xy(73.5,30.8)],'#6f62a6',5);line([xy(34.5,28.5),xy(43.7,28.5)],'#6f62a6',4)
text(95,434,'Index / release -X');text(282,434,'20 mm active bay');text(570,434,'25 × 18 × 1 target PCB');text(850,454,'12 × 6.5 plug screen',10)
for x in [34.5,42,47,67,73.8,98.8,110.8]:u,v=xy(x,22);line([(u,v),(u,v+5)]);text(u-12,v+20,str(x),9)
text(45,643,'X / mm (11 drawing units/mm). Core continues X0..142; complete stationary connector endcaps not represented.',10)
text(30,687,'FIXED-TAIL CLAMP COMPLETION FAIL',14,'#9c3343')
# Enlarged true radial stack, no invented stiffener solid.
rect(35,715,45,100,'#dddddd');rect(80,715,90,100,'#adb3ba');rect(170.85143,715,24,100,'#e7c58f')
line([(133.3514,710),(170.8514,710)],'#c93344',4)
text(35,836,'R24');text(78,836,'24.3');text(155,854,'24.9');text(190,836,'25.066')
text(35,879,'150 drawing units/mm; proposed stiffener + gap shown in red.',9)
lines=['Only 0.005676 mm behind fixed tail; 0.20 mm stiffener + 0.05 gap needs another 0.244324 mm.',
'CAD also retains unfinished retention passages and a disconnected backing island.',
'Locked trial envelope: Ø66 × 64.3 mm. Released pin sweep: X30.3..98.8 (68.5 mm).',
'USB4105 body: 8.94 × 7.35 × 3.31 mm nominal; GF-A-060 stake option proposed.',
'Finite plug screen is engineering geometry, not universal cable acceptance.',
'No elastic equilibrium, clamp force, fatigue, thermal, mains or fixture validation.']
for i,s in enumerate(lines):text(330,717+i*26,s,10,'#9c3343' if i<2 else '#263746')
text(30,924,'Drawings are diagnostic. See cad-checks.json for every retained collision; not production surfaces or released assembly drawings.',11)
c.save();svg.append('</svg>');(P/'sections.svg').write_text('\n'.join(svg)+'\n')
