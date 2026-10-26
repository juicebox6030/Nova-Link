from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
P=Path(__file__).resolve().parent;data=json.loads((P/'section.json').read_text());patch=json.loads((P/'patch.json').read_text());W,H=1050,650;c=canvas.Canvas(str(P/'closure-section.pdf'),pagesize=(W,H));svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def text(x,y,t,size=12):
 c.setFillColorRGB(.08,.13,.17);c.setFont('Helvetica',size);c.drawString(x,H-y,t);svg.append(f'<text x="{x}" y="{y}" font-size="{size}" font-family="sans-serif" fill="#14212c">{html.escape(t)}</text>')
def line(pts,col='#285b78',dash=False,width=1):
 c.setStrokeColorRGB(int(col[1:3],16)/255,int(col[3:5],16)/255,int(col[5:7],16)/255);c.setLineWidth(width);c.setDash(3,2) if dash else c.setDash();p=c.beginPath();p.moveTo(pts[0][0],H-pts[0][1]);
 for x,y in pts[1:]:p.lineTo(x,H-y)
 c.drawPath(p);svg.append('<polyline points="'+' '.join(f'{x:.4f},{y:.4f}' for x,y in pts)+f'" fill="none" stroke="{col}" stroke-width="{width}"'+(' stroke-dasharray="3 2"' if dash else '')+'/>')
def pt(y,z):return (100+(y-24)*10,560-(z+6)*10)
text(30,32,'CAF-R2 | installed-lid driver clearance',21)
text(30,55,'Native-derived section X=-32, positive-Y screw. Dimensions mm;10 points/mm (PDF3.528:1).')
for name in ['OriginalUpperGhost','LowerShellPosts','UpperShellRetention','ClosureScrew_m32_32','ClosureTool_m32_32']:
 col={'OriginalUpperGhost':'#c2785b','LowerShellPosts':'#79878f','UpperShellRetention':'#245c7a','ClosureScrew_m32_32':'#212c35','ClosureTool_m32_32':'#287e52'}[name]
 for pts in data['curves'][name]:line([pt(y,z) for y,z in pts],col,name=='OriginalUpperGhost',.8)
# Complete proposed cut cylinder reference, including air above shell.
for yy in [29.25,34.75]:line([pt(yy,4.0),pt(yy,41.5)],'#6b9180',True,.6)
line([pt(29.25,42),pt(34.75,42)],'#287e52');text(130,65,'Ø5.5 passage',10)
text(400,95,'Four passages: X -110/-32; Y +/-32')
text(400,120,'Existing driver Ø5, Z4.5..40.5; cut Ø5.5, Z4.0..41.5')
text(400,145,'Nominal whole-tool gap0.25; cut starts0.5 below tip')
text(400,170,'Allocation: radius undersize0.10 + driver0.05 + axis0.05')
text(400,195,'Proposed tolerance budget only; no supplier qualification')
zi=data['centreline_inner_z'];zo=data['centreline_outer_z']
for z,label in [(zo,'Outer radius38.5: centreline exit Z21.4068'),(zi,'Inner radius35.5: centreline entry Z15.3704')]:
 line([pt(32,z),(380,pt(32,z)[1])],'#a97054',True,.6);text(400,pt(32,z)[1]+4,label)
text(400,385,'Original centreline blockage6.0363; red dashed = frozen original')
text(400,410,'Original four solid intersections127.758..127.838 mm³; repaired0')
line([pt(34,4.5),(380,pt(34,4.5)[1])],'#212c35',False,.6);text(400,459,'Head top/tool tip Z4.5: intentional face touch, no volume')
line([pt(34,3),(380,pt(34,3)[1])],'#212c35',False,.6);text(400,486,'Bearing seat Z3: Ø4 head / Ø2.4 hole; radial land0.8')
text(400,511,'All four8.04248 mm² bearing areas preserved; bosses remain connected')
text(400,536,'Through-open ports; caps/sealing/IP/strength decisions remain UNMET')
text(30,590,'Blue = repaired upper; gray = lower; black = screw; green = complete actual driver envelope.')
text(30,615,'Only UpperShellRetention changes. No other parts, screw positions, boards, envelope or rotary geometry change.')
c.save();svg.append('</svg>');(P/'closure-section.svg').write_text('\n'.join(svg)+'\n')
