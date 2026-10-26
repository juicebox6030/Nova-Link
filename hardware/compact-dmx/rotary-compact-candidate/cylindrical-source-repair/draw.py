from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
P=Path(__file__).resolve().parent;data=json.loads((P/'sections.json').read_text());W,H=1190,842;c=canvas.Canvas(str(P/'sections.pdf'),pagesize=(W,H));svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def text(x,y,t,size=12):
 c.setFillColorRGB(.08,.14,.18);c.setFont('Helvetica',size);c.drawString(x,H-y,t);svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#14242e">{html.escape(t)}</text>')
def poly(pts,color='#345568',width=.7):
 c.setStrokeColorRGB(int(color[1:3],16)/255,int(color[3:5],16)/255,int(color[5:7],16)/255);c.setLineWidth(width);p=c.beginPath();p.moveTo(pts[0][0],H-pts[0][1]);
 for x,y in pts[1:]:p.lineTo(x,H-y)
 c.drawPath(p);svg.append(f'<polyline points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="{width}"/>')
def section(key,ox,oy,scale=2.5):
 for row in data[key]:
  col='#bd6432' if 'Trunk' in row['part'] or 'Branch' in row['part'] else '#2e657a'
  poly([(ox+scale*x,oy-scale*y) for x,y in row['points']],col)
text(30,32,'CYL-R2 | constructed partial assembly — qualification HOLD',21)
text(30,55,'CAD-derived sections; all at 2.5 drawing points/mm (PDF 0.882:1). All dimensions mm. No finished variant envelope.')
section('mid_source',160,190);section('post_source',460,190)
text(50,310,'A-A source centre X=-71: OD77 / ID71')
text(350,310,'B-B carrier post X=-99.5: real post/ear/screw')
text(650,105,'Source bay: X -115..-27 (88 long); neck -27..0 (27 long)')
text(650,130,'81x52x44 reservation +0.5/face; source translated +4.5X/-2Z')
text(650,155,'Film nominal clearance0.574; with bore allowance0.374')
text(650,180,'Four carrier posts/ears; M2 pilot engagement4.4')
text(650,205,'Four shell M2 closures; pilot engagement4.0')
text(650,230,'Module side/top play0.25; no clamp-load or creep rating')
text(650,255,'Posts/ribs/screws cross insulation reservation: UNQUALIFIED')
text(30,355,'C-C longitudinal Y=0; constructed source/neck and continuous trunk (CIR centre region is referenced, not sectioned here)')
section('longitudinal',390,475)
# Same-scale referencecore/rotor extent, clearly diagrammatic.
poly([(390,475-24*2.5),(390+87*2.5,475-24*2.5),(390+87*2.5,475+24*2.5),(390,475+24*2.5)],'#9aa4a9')
text(400,565,'CIR core0..87 / frozen S12 boards and active mechanism')
text(30,595,'Classic matched planning: CIR327.8 x91 x74; CYL302.8 x77 x77 (nominal; not approved housing dimensions).')
text(30,620,'Both include60.8 rear +40 terminal/tool. 25 mm shorter /18.669% less box-volume, conditional on same access accounting.')
text(30,645,'Exact OD5.5 corridor BReps fit bore reduced0.2; R12 double bend +5.669 straight. Source/neck wall nominal3.')
text(30,670,'Lock-access relief leaves0.970 nominal local wall (0.670 allocated); strength and neck attachment remain OPEN.')
text(30,695,'Primary fuse has an explicit4 mm unconnected endpoint interface; no selected fuse/terminal or released mains construction.')
text(30,720,'Sourceboard circuits unchanged/unrouted. Neck/core joint, connector ends/mates, molded NEMA cord interfaces UNBUILT.')
text(30,745,'Film/lead passages and source mounting are drawn but not approved insulation construction. No thermal/endurance/USB claim.')
text(30,775,'Prototype.FCStd and STEP contain actual solids; supplier body profiles, tolerances, material allowables and physical assembly require qualification.')
c.save();svg.append('</svg>');(P/'sections.svg').write_text('\n'.join(svg)+'\n')
