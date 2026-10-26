from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
P=Path(__file__).resolve().parent;W,H=1190,842
c=canvas.Canvas(str(P/'comparison.pdf'),pagesize=(W,H));svg=[]
def begin(title,sub):
 global svg
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
 text(32,35,title,20);text(32,61,sub,11)
def text(x,y,s,size=10):
 c.setFillColor(HexColor('#183349'));c.setFont('Helvetica',size);c.drawString(x,H-y,s)
 svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#183349">{html.escape(s)}</text>')
def rect(x,y,w,h,color,stroke='#183349'):
 c.setFillColor(HexColor(color));c.setStrokeColor(HexColor(stroke));c.rect(x,H-y-h,w,h,fill=1,stroke=1)
 svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="{stroke}"/>')
def line(x,y,a,b):
 c.setStrokeColor(HexColor('#183349'));c.line(x,H-y,a,H-b);svg.append(f'<path d="M{x},{y} L{a},{b}" fill="none" stroke="#183349"/>')
def finish(n):
 (P/f'comparison-{n}.svg').write_text('\n'.join(svg+['</svg>'])+'\n');c.showPage()
s=2.7;ox=70
def top(y,old):
 # Xrelative-164; screengeometry mirrors savedallocation, source/housingcounted.
 def r(x,yy,w,h,col):rect(ox+(x+164)*s,y+(56-yy-h)*s,w*s,h*s,col)
 r(-140,-31,128,82,'#e7edf0');r(-164,8,24,48,'#d7dfe5')
 r(-116.5,-26.5,82,53,'#fff1c9');r(-101.95,-13.85,52.9,27.7,'#f3c875')
 r(-12,-17,12,34,'#d7dfe5');r(0,-24,142 if old else 82,48,'#e5f1f4')
 r(26.8 if old else 4,-33,77.37,66,'#aed5ca');r(142 if old else 82,-24,24,48,'#d7dfe5')
 if not old:r(-90,26.75,24,21,'#d8bbec')
 length=330 if old else 270
 line(ox,y+89*s+15,ox+length*s,y+89*s+15);text(ox,y+89*s+32,f'{length} mm overall allocation; width 89 mm',12)
begin('One compact in-line allocation - not product acceptance','Equal-scale top views: 2.7 drawing points/mm. All24mm connector blanks retained and unqualified. No12V board-fit claim.')
text(70,94,'REJECTED BASELINE: 330 x89 x72 mm /2.115 L bounding box',14);top(110,True)
text(70,430,'SHORTENED COMPARISON: 270 x89 x72 mm /1.730 L /18.18% reduction',14);top(446,False)
text(825,450,'Sourcepod unchanged128x82x62',11);text(825,470,'Core142 ->82; collarshift -22.8',11);text(825,490,'S12 stationaryboard+clamp inpurple',11)
text(825,515,'Carrier retention and terminal',11);text(825,532,'construction remain UNMET.',11)
text(70,790,'Gold: manufacturer-based insulation reservation / Green: intact oldcollar comparison / Grey: generic connector and housing allocations.',11)
finish(1)
begin('Two-arrangement screen and new source constraint','Offset rejected for transverse bulk, not falsely claimed to obstruct USB. S12 geometry has NOT been integrated into the collar.')
# equal scale offset dimensions relative exactminimumx-36,y-117
x0,y0=70,110
rect(x0+24*s,y0,128*s,82*s,'#e7edf0');rect(x0,y0+39*s,24*s,48*s,'#d7dfe5')
rect(x0+40*s,y0+84*s,77.37*s,66*s,'#aed5ca');rect(x0+118*s,y0+93*s,24*s,48*s,'#d7dfe5')
text(70,550,'Offset lower allocation: 152 x150 x72 mm /1.642 L',13);text(70,570,'Same2.7points/mm; excludes new transverse harness neck.',11)
text(70,592,'68.54% wider thaninline for5.12% smaller bounding volume.',11)
# Crosssection separately labeled4points/mm
cx,cy,sc=840,280,4
for rad,col in [(33,'#e4efef'),(24,'#ffffff')]:
 c.setFillColor(HexColor(col));c.circle(cx,H-cy,rad*sc,fill=1,stroke=1);svg.append(f'<circle cx="{cx}" cy="{cy}" r="{rad*sc}" fill="{col}" stroke="#183349"/>')
# crossview horizontalZ, verticalY
rect(cx-13*sc,cy-26.1*sc,26*sc,1*sc,'#7fa7d3')
rect(cx-18*sc,cy-28.1*sc,5*sc,2*sc,'#eea38b')
text(660,465,'S12 cross-section:4points/mm, not same viewscale.',11)
text(660,485,'Board32axial x26tangential x1mm.',11)
text(660,505,'Clamp outercornerR=sqrt(28.1^2+18^2)=33.371mm.',11)
text(660,525,'Bare clamp exceedsR33; wall/clearance additional.',11)
text(660,545,'1mm wall +.25assembly ->minimum screenOD69.24.',11)
text(660,565,'USB bodyends5mm fartheraxially, NOT matingplane.',11)
text(660,585,'275mm length is only revised dimension screen.',11)
text(70,665,'Lowerbound beforewalls/bends/tools:72.9 source-only +77.37 collar +48 connectors =198.27mm.',12)
text(70,690,'Conservative81mm whole-carrier reservation gives206.37mm; neither is an achievable or approved housing minimum.',11)
text(70,720,'Finite wires and residual intersections are recorded inchecks.json. No mains/thermal/fixture/endurance/manufacturing acceptance.',11)
text(70,745,'New32x26 rotor and24x16 stationaryboards remain unrouted; outputprotection/startup/thermal gates stayopen.',11)
text(70,775,'FAILED integration: primarybranch overlap; LVspool/clamp interference and0.581mm tail gap. NOT a complete assembly.',12)
finish(2);c.save()
