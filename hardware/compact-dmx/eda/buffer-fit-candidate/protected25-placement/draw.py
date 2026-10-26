from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
P=Path(__file__).resolve().parent;W,H=1100,850
c=canvas.Canvas(str(P/'placement-sections.pdf'),pagesize=(W,H),invariant=1);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def txt(x,y,t,size=12):
 c.setFillColor(HexColor('#183447'));c.setFont('Helvetica',size);c.drawString(x,H-y,t);svg.append(f'<text x="{x}" y="{y}" fill="#183447" font-family="sans-serif" font-size="{size}">{html.escape(t)}</text>')
def rect(x,y,w,h,col,stroke='#334155'):
 c.setFillColor(HexColor(col));c.setStrokeColor(HexColor(stroke));c.setLineWidth(.5);c.rect(x,H-y-h,w,h,fill=1,stroke=1);svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}" stroke="{stroke}" stroke-width=".5"/>')
txt(30,32,'PROTECTED25 / ONE PLACEMENT ATTEMPT',22);txt(30,55,'192 footprints; no routing. Local base relief is a proposal, not approved tooling or protection performance.')
txt(30,72,'Teal:13 added controls / orange:fuse / gray:unchanged courtyards. Exact references and pads:actual-board SVGs.',10)
base=json.loads((P/'baseline-board.json').read_text());new=json.loads((P/'placement.json').read_text())['added']
for side,oy in [('F',95),('B',335)]:
 txt(30,oy-10,('TOP' if side=='F' else 'BOTTOM (viewed through board; same X/Y datum)')+' - courtyard allocation view')
 bx=lambda x:40+(x-4)*10;by=lambda y:oy+(y-23)*6
 # anisotropic plan labeled explicitly to avoid physical scale interpretation.
 txt(710,oy-10,'Plan scales X10 / Y6 points per mm',11)
 rect(bx(4),by(23),900,168,'#eff6f3');rect(bx(26.5),by(25.5),294,61.8,'#ffffff');rect(bx(83.4),by(23),106,168,'#fae1ca')
 for q in base:
  if q['side']!=side:continue
  x,y,x2,y2=q['bounds']
  if x2<=x or y2<=y:continue
  rect(bx(x),by(y),(x2-x)*10,(y2-y)*6,'#d9e1e6')
 for q in new:
  if q['side']!=side:continue
  x,y,x2,y2=q['bounds'];rect(bx(x),by(y),(x2-x)*10,(y2-y)*6,'#f1b765' if q['ref']=='F101' else '#79c6b2')
  if q['ref']=='F101':txt(bx(x),by(y)-2,q['ref'],8)
 txt(40,oy+215,'PCB main: X4..94, Y23..51, Z10..11; USB tongue retained. Internal aperture29.4 x10.3, R0.5.',11)
txt(30,570,'FUSE SECTION AT X56.5 - scale X20 / Z35 drawing points per mm',13)
# section Y horizontal, Z vertical; full5..11 appears below title.
xx=lambda y:55+(y-36)*20;zz=lambda z:790-(z-5)*35
rect(xx(36),zz(7),200,70,'#aebdc5');rect(xx(37.4),zz(7),7.2*20,.4*35,'#ffffff')
rect(xx(36),zz(11),200,35,'#6da890');rect(xx(37.85),zz(10),6.3*20,2.94*35,'#f1b765')
for i,t in enumerate(['F101 max body6.30 x2.94 x2.94; bottom Z7.06.', 'Original base Z7: gap0.06; NOT sufficient allocated margin.', 'Proposed relief: X54.6..58.4 / Y37.4..44.6 / floor Z6.6.', 'Vertical gap0.46; shortest3D gap0.434; .20 down clears.', 'Remaining floor1.60; strength/creep/process approval OPEN.', 'Cell tab to fuse: no route yet; unfused conductor must be', 'restrained/insulated and protection placement approved.', 'No fuse clearing, turnoff maximum or healthy10s acceptance.']):txt(310,600+i*23,t,12)
c.save();svg.append('</svg>');(P/'placement-sections.svg').write_text('\n'.join(svg)+'\n')
