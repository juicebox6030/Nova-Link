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
text(30,35,'REPAIRED CONSTANT-LENGTH ROTARY COLLAR / GEOMETRIC PROTOTYPE',20)
text(30,61,'Ø48 × 142 stationary core; Ø66 collar. Supplier, strength, cycle life and source-board integration remain open.',12)
for i,a in enumerate([-90,0,90]):
 ox=190+360*i;oy=225;scale=3
 text(ox-100,105,f'{a:+d} degrees / active ribbon',12)
 for r,col in [(33,'#30383e'),(32,'#888888'),(31,'#448899'),(24.6,'#448899'),(24,'#30383e')]:circle(ox,oy,r*scale,col)
 for side in ['outer','inner']:line([(ox+p[0]*scale,oy-p[1]*scale) for p in poses[str(a)][side]],'#bb6c13',.45)
 text(ox-100,346,'Ø66 / Ø48; 3 drawing units per mm',10)
text(30,390,'AXIAL ENVELOPE — lock X31..44.3; active flex X47..67; target board X73.8..98.8',13)
def xy(x,r):return 50+(x-26)*10.5,600-(r-22)*11
def rb(x,r,l,h,color):u,v=xy(x,r+h);rect(u,v,l*10.5,h*11,color)
rb(26,22,85,2,'#c8cdd1');rb(42,32,56.8,1,'#b5c1cc');rb(47,25,20,5.5,'#e7c58f');rb(73.8,25.1,25,1,'#548959');rb(73.8,26.1,17.2,3.61,'#c2d6b5');rb(91.15,26.1,7.65,3.46,'#adb3ba')
line([xy(98.8,24.58),xy(110.8,24.58),xy(110.8,31.08),xy(98.8,31.08),xy(98.8,24.58)],'#9c3343')
line([xy(72.5,30.8),xy(73.5,30.8)],'#6f62a6',5);line([xy(31,28.5),xy(44.3,28.5)],'#6f62a6',4)
text(60,434,'Captive spring-return lock');text(300,434,'20 mm active bay');text(590,434,'25 × 18 × 1 PLACEHOLDER');text(865,454,'Finite plug screen',10)
for x in [26.8,31,47,67,73.8,98.8,110.8]:u,v=xy(x,22);line([(u,v),(u,v+5)]);text(u-12,v+20,str(x),9)
text(30,649,'Locked length67.8 mm; release sweep72.0 mm. Axial/radial drawing scales10.5 /11 units per mm; see dimensions.json.',10)
text(30,687,'REPAIRED FIXED CLAMP / ENLARGED RADIAL STACK',14)
# 200 drawing units/mm: core to24; backing24.1..24.6; fitted pad to24.6557; stiffener+.20; adhesive+.05; flex+.16.
base=35;scale=200
for r,w,col in [(24,.1,'#eeeeee'),(24.1,.5,'#adb3ba'),(24.6,.055676,'#b6d9bd'),(24.655676,.2,'#d7b5de'),(24.855676,.05,'#f2c35b'),(24.905676,.16,'#e7c58f')]:rect(base+(r-24)*scale,715,w*scale,100,col)
for r,y in [(24,836),(24.1,854),(24.6,836),(24.6557,872),(24.9057,854),(25.0657,836)]:text(base+(r-24)*scale-10,y,str(r),9)
lines=['Backing outerR24.6; stiffener0.20 + adhesive0.05; minimum unpadded gap0.055676 mm.',
'Contoured compliant ear pads fill that gap outside the active20 mm width.',
'Stiffener/adhesive taper to zero over0.08 rad (~2.0 /2.44 mm), fixed/moving tails.',
'Both rotor halves and stationary spool are connected single closed solids.',
'Four frame head counterbores; radial ear-driver passages; captive service cap.',
'Power reserve3.46 max height +0.15 assembly allowance; no actual source-PCB fit claim.']
for i,s in enumerate(lines):text(330,717+i*26,s,10)
text(30,924,'Engineering geometry only. Taper process, bond/preload, spring sourcing, flex equilibrium/endurance, thermal and fixture fit require qualification.',10)
c.save();svg.append('</svg>');(P/'sections.svg').write_text('\n'.join(svg)+'\n')
# Dedicated dimensioned plunger section. All cylindrical features are shown through their axis.
c=canvas.Canvas(str(P/'lock-section.pdf'),pagesize=(W,H),invariant=1);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
text(30,35,'CAPTIVE INDEX LOCK / LOCKED AND RELEASED SECTIONS',20)
text(30,62,'Plunger axis at barrel radius28.5 mm; all dimensions mm; section scale32 drawing units/mm.',12)
for released,oy,title in [(False,255,'LOCKED: 1.3 engagement; flange on front shoulder'),(True,610,'RELEASED: 4.2 stroke; flange on rear stop')]:
 text(30,oy-130,title,14)
 def b(x,r,l,h,col):rect(45+(x-26)*32,oy-(r+h)*32,l*32,h*32,col)
 # carrier walls and nose
 for sign in [-1,1]:
  def ann(x,ri,ro,l,col):b(x,ri if sign>0 else -ro,l,ro-ri,col)
  ann(34,2.4,3,1,'#adb3ba');ann(35,2.2,3,6.4,'#adb3ba');ann(41.4,1.1,3,.7,'#adb3ba');ann(42.1,1.1,2.3,.7,'#adb3ba')
  ann(35,1.7,2.15,1.6,'#8d9bab');ann(33.4,1.1,3.2,.6,'#8d9bab');ann(34,1.1,2.6,1,'#8d9bab')
  ann(35,1.4,1.6,1.6 if released else 5.8,'#cf8b2b');ann(43,1.1,3.3,1.7,'#6fa58c')
 dx=-4.2 if released else 0
 b(32.5+dx,-1,11.8,2,'#6682a6');b(31+dx,-2,1.5,4,'#6682a6');b(40.8+dx,-1.8,.6,3.3,'#6682a6')
 b(36.6,1.65,4.8,.65,'#adb3ba')
 # Draw centreline after solids.
 line([(45,oy),(675,oy)],'#888888',.4)
 for x in [31+dx,33.4,35,36.6,40.8,41.4,42.8,44.3+dx]:
  u=45+(x-26)*32;line([(u,oy+110),(u,oy+116)]);text(u-8,oy+134,f'{x:g}',8)
 text(720,oy-95,'Carrier OD6 / nose OD4.6',11)
 text(720,oy-70,'Pin Ø2 / flange Ø3.6',11)
 text(720,oy-45,'Hole Ø2.2; 13 ×15° detents',11)
 text(720,oy-20,'Spring: free7; working5.8 /1.6',11)
 text(720,oy+5,'Solid1.4; target k0.114 N/mm',11)
 text(720,oy+30,'Return preload0.137 N nominal',11)
 text(720,oy+55,'No hold-open latch / no bypass',11)
 text(720,oy+80,'Cap includes removable rear stop',11)
text(30,824,'Orange: spring engineering envelope (not a solid spring). Proposed wire0.20 / mean coilØ3 /5 active +2 end coils.',11)
text(30,850,'Front and rear flange stops retain the pin. Release clearance to index:2.9 mm. Spring solid-height nominal margin0.2 mm.',11)
text(30,876,'Spring sourcing, return friction <0.08 N target, fatigue, thread locking and lock strength remain physical qualification gates.',11)
text(30,910,'Removable threaded knob: M1.2 envelope,0.8 engagement,0.6 wide face slot. D-flat flange/key restrains stem during service.',11)
c.save();svg.append('</svg>');(P/'lock-section.svg').write_text('\n'.join(svg)+'\n')
