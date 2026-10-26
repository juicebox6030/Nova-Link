from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
P=Path(__file__).resolve().parent;s=json.loads((P/'screen.json').read_text());W,H=1000,600
c=canvas.Canvas(str(P/'screen.pdf'),pagesize=(W,H));svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def text(x,y,t,size=12):
 c.setFillColorRGB(.08,.12,.17);c.setFont('Helvetica',size);c.drawString(x,H-y,t);svg.append(f'<text x="{x}" y="{y}" font-size="{size}" font-family="sans-serif" fill="#14202b">{html.escape(t)}</text>')
def rect(x,y,w,h,col):
 c.setStrokeColorRGB(.2,.25,.3);c.setFillColorRGB(*col);c.rect(x,H-y-h,w,h,fill=1);color='#'+''.join(f'{int(v*255):02x}' for v in col);svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="#34404c"/>')
def circle(x,y,r,col):
 c.setStrokeColorRGB(.2,.25,.3);c.setFillColorRGB(*col);c.circle(x,H-y,r,fill=1);color='#'+''.join(f'{int(v*255):02x}' for v in col);svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="#34404c"/>')
text(30,32,'CYL-R1: one cylindrical allocation screen — HOLD',20)
text(30,55,'Not an assembly drawing; no retained carrier, qualified terminals, or final product envelope.')
k=2;cx,cy=155,175
circle(cx,cy,38.1*k,(.77,.82,.86));circle(cx,cy,35.1*k,(1,1,1));rect(cx-26.5*k,cy-22.5*k,53*k,45*k,(.94,.89,.73));rect(cx-13.85*k,cy-12*k,27.7*k,24.5*k,(.65,.8,.87))
for y in [-8,0,8]:circle(cx+y*k,cy+29*k,2.75*k,(.8,.6,.55))
text(265,115,'Cross-section: 2 drawing points/mm (PDF 0.706:1)')
text(265,140,'OD76.2 / ID70.2; proposed 3 mm wall, bore allowance -0.2 mm')
text(265,165,'81 x 52 x 44 inherited reservation +0.5 mm per face (tan)')
text(265,190,'Maximum module 52.9 x 27.7 x 24.5; pins 4.5 mm max')
text(265,215,'3 x OD5.5 trunk screens; wire family/bend qualification OPEN')
text(265,240,'0.1365 mm allocated corner clearance; support structure NOT included')
text(30,290,'Axial lower planning allocation: all rectangles at the same 2 points/mm scale')
x=30;y=315
for name,L,col in [('input rear',30.4,(.84,.84,.84)),('term/tool',20,(.95,.8,.7)),('source',88,(.7,.85,.9)),('bend',s['transition_axial_run'],(.9,.8,.65)),('CIR',87,(.75,.86,.73)),('term/tool',20,(.95,.8,.7)),('output rear',30.4,(.84,.84,.84))]:
 rect(x,y,L*k,55,col);text(x+2,y+74,f'{L:.2f}',9);text(x+2,y-10,name,9);x+=L*k
text(30,420,'Classic 297.13 x 76.2 x 76.2: 6.84% less box-volume but 22.13 mm longer than CIR275.')
text(30,445,'TRUE1 panel allocation300.33 mm. Flanged NEMA comparison325.23 mm is NOT molded-cord selection.')
text(30,470,'Rear depths are bare panel-shoulder dimensions. Front projections, mates, latch and hand envelopes excluded.')
text(30,495,'R12 continuous trunk transition: 21.3307 mm run; trial conical bore interference0.03948 mm.')
text(30,520,'Film corner fails -0.2 mm bore allowance by0.0258 mm; retention/branches/secondary connections OPEN.')
text(30,545,'No new CAD/STEP assembly issued. Frozen CIR/S12 are unchanged; this screen is not a manufacturing limit.')
c.save();svg.append('</svg>');(P/'screen.svg').write_text('\n'.join(svg)+'\n')
