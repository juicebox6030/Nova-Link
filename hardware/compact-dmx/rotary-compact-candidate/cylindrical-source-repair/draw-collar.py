from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
P=Path(__file__).resolve().parent;d=json.loads((P/'sections.json').read_text());W,H=1000,650;c=canvas.Canvas(str(P/'collar-section.pdf'),pagesize=(W,H));svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def text(x,y,t,size=13):
 c.setFont('Helvetica',size);c.setFillColorRGB(.08,.12,.17);c.drawString(x,H-y,t);svg.append(f'<text x="{x}" y="{y}" font-size="{size}" font-family="sans-serif">{html.escape(t)}</text>')
text(30,35,'CYL-R2: actual retained CIR collar and S12 sections',21);text(30,60,'Same native coordinates and geometry. Neutral pose only. 4 points/mm (PDF1.411:1), both views equal scale.')
for key,ox in [('collar34.2',250),('collar65',720)]:
 for row in d[key]:
  pts=[(ox+4*x,260-4*y) for x,y in row['points']];col='#ad6533' if 'Flex' in row['part'] else '#2d596b';c.setStrokeColorRGB(int(col[1:3],16)/255,int(col[3:5],16)/255,int(col[5:7],16)/255);c.setLineWidth(.35);path=c.beginPath();path.moveTo(pts[0][0],H-pts[0][1]);
  for x,y in pts[1:]:path.lineTo(x,H-y)
  c.drawPath(path);svg.append('<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" fill="none" stroke="{col}" stroke-width=".35"/>')
text(90,440,'D-D X34.2: active winding + stationary sourceboard')
text(555,440,'E-E X65: rotating sourceboard / frame / core')
text(30,485,'317 preserved objects match CIR saved BRep topology and coordinates to1e-12 serialization tolerance.')
text(30,510,'Active1046.167655992167 mm winding family,13 index positions and independent stops remain unchanged.')
text(30,535,'Both S12 boards and189 numbered pad features remain frozen. These sections do not establish routing or thermal fit.')
text(30,560,'New source parts clear rotation by axial separation or exact R24 containment; USB screens use the frozen engineering envelope.')
text(30,585,'No dynamic equilibrium, cable endurance, legal RF, USB, electrical protection, fixture fit or manufacture acceptance.')
c.save();svg.append('</svg>');(P/'collar-section.svg').write_text('\n'.join(svg)+'\n')
