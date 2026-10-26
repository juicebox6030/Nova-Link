"""Same vector primitives render SVG/PDF. Dimensioned failure screen, not release."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import json,math,html
P=Path(__file__).resolve().parent;W,H=1100,1000
c=canvas.Canvas(str(P/'integration.pdf'),pagesize=(W,H),invariant=1);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
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

import csv
text(30,35,'AXIAL-R1 SOURCE / REPAIRED ROTARY COLLAR INTEGRATION',20)
text(30,60,'Dimensions mm. Source board bytes preserved. Mechanical prototype; electrical and physical qualification remain open.',11)
text(30,95,'AXIAL ENVELOPE / X scale 10; radial scale 13 drawing units per mm',13)
def xy(x,y):return 50+(x-26)*10,290-(y-22)*13
def rb(x,y,l,h,col):u,v=xy(x,y+h);rect(u,v,l*10,h*13,col)
rb(26,22,91,2,'#c8cdd1');rb(42,32,60,1,'#9caebb');rb(47,25,20,5.5,'#e7c58f');rb(75,25.1,27,1,'#578f67');rb(75,26.1,21.52,3.71,'#c8dfbf');rb(96.52,26.1,7.65,3.46,'#9ca5b1')
line([xy(104.17,24.58),xy(116.17,24.58),xy(116.17,31.08),xy(104.17,31.08)],'#b54e56')
for x in [26.8,31,47,67,75,102,104.17,116.17]:
 u,v=xy(x,22);line([(u,v),(u,v+5)]);text(u-10,v+20,str(x),9)
text(30,340,'OD66. Locked X31..104.17 =73.17; released X26.8..104.17 =77.37. Core Ø48 x142 unchanged.',11)
text(30,363,'Connector front is a conservative body allocation, NOT a sourced mating plane. 12 x6.5 x12 plug screen is engineering-only.',10)
text(30,405,'ACTUAL SOURCE PLAN / local PCB27 x20; 18 drawing units per mm',13)
ox,oy,sc=70,450,18
rect(ox,oy,27*sc,20*sc,'#d6ead5')
for yy in [0,19.8]:rect(ox,oy+yy*sc,27*sc,.2*sc,'#a6b3c7')
lands=json.loads((P.parent/'source-axial-routing/land-sources.json').read_text())
for row in csv.DictReader((P.parent/'source-axial-routing/placement-ledger.csv').open()):
 w,h=lands[row['footprint']]['body_max_mm'];x,y,a=[float(row[k]) for k in ['x','y','degrees']]
 if row['ref']=='J1':x-=1.655
 if round(a)%180:w,h=h,w
 rect(ox+(x-w/2)*sc,oy+(y-h/2)*sc,w*sc,h*sc,'#abb6c6' if row['ref']=='J1' else '#e5ca9e')
 text(ox+(x-w/2)*sc+1,oy+y*sc+3,row['ref'],7)
rect(ox+.5*sc,oy+22*sc,20*sc,2*sc,'#d1a058')
text(ox,oy+26*sc,'External clamp / shaped flex tongue; screws outside routed board',10)
notes=['Proper rotation: local +Z -> global +Y; local +Y -> global -Z.',
'Global=(75+x, 26.1+z, 10-y); determinant +1.',
'PCB X75..102 / Y25.1..26.1 / Z-10..10.',
'98 actual holes and four swept stake allocations retained.',
'Edge capture0.20; copper gap >=0.3005 from actual saved copper.',
'No new PCB holes. End retainer uses two external M1 screws.',
'Board1.0 +/-0.1; top lip clearance0.24 nominal.',
'Bottom reserve -1.35; top reserve +3.71 from PCB top.',
'R2.5 formed static bend; saddle ends before PCB edge.',
'Clamp shoe0.94 high; two M1 screws, preload unqualified.',
'Solder access slot20.8 x2.8; enclosure sealing/guard gate.',
'No insulating pad over ICs; no rated heat path asserted.',
'Four inherited GCT NPTH process errors remain unresolved.']
for i,t in enumerate(notes):text(610,455+i*24,t,10)
text(30,970,'Static flex, solder, spring, wear, thermal/current, source faults, USB profile and mains safety remain qualification gates.',10)
c.save();svg.append('</svg>');(P/'integration.svg').write_text('\n'.join(svg)+'\n')
c=canvas.Canvas(str(P/'fanout-section.pdf'),pagesize=(W,H),invariant=1);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
text(30,35,'STATIC FANOUT / SECTION AND TERMINATION CONTRACT',20)
text(30,62,'Projection through axial width: features at different X are overlaid. Generalized-cylinder surface, not a twisted ribbon.',11)
a=json.loads((P/'fanout-path.json').read_text())['samples'];ox,oy,scale=340,390,7.5
for r,col in [(33,'#2a343d'),(32,'#8b969e'),(31.6,'#ba8c4d'),(24,'#2a343d')]:circle(ox,oy,r*scale,col)
line([(ox+v[1]*scale,oy-v[2]*scale) for v in a],'#b66d21',2)
rect(ox+25.1*scale,oy-10*scale,scale,20*scale,'#548d64')
rect(ox+26.1*scale,oy-10*scale,3.71*scale,20*scale,'#c8dfbf')
text(45,680,'Core R24 / shell ID32 / OD33; projection scale7.5 units/mm. RouteR31.6; bendR2.5.',11)
text(45,706,'Axial trim center shifts X57 ->85.5; width20. All ruling lines remain parallel to X.',11)
text(650,160,'STATIC DEVELOPED PATTERN',13)
proof=json.loads((P/'fanout-proof.json').read_text());text(650,193,f"Centerline {proof['static_centerline_length_mm']:.3f} mm; active1046.168 unchanged.",10)
for i,t in enumerate(['Single-layer RA70um / total0.16 proposed stack.', 'Two8mm traces /1mm gap; Minco material-class basis.', 'No plated features in active bend; static pad coverlay window.', 'J0.1 /FPC_5V: local(6,18.4), globalX81.', 'J0.2 /GND_ISO: local(15,18.4), globalX90.', 'Pads8 x2, cornerR0.2; unchanged actual KiCad lands.', 'Exposed flex conductor ends overlap Z-9.4..-7.4.', 'J0 saved0.3mm land/joint allocation retained.', 'Joint thickness/fillet/process are engineering gates.', 'No conductive solder bridge across1mm trace gap.', 'Clamp Z-14..-12; shoe Y26.56..27.5.', 'Saddle stops atZ-10.3, before boardedgeZ-10.', 'Bottom/top flex Y26.4/26.56 at termination.', 'Bare-copper orientation and polarity require assembly check.']):text(650,225+i*24,t,10)
text(30,760,'TERMINAL STRAIGHT SECTION / horizontal32 and vertical55 drawing units per mm',13)
def b(z,y,dz,dy,col):rect(80+(z+17)*32,940-(y+dy-25)*55,dz*32,dy*55,col)
b(-10,25.1,2.6,1,'#548d64');b(-14,25.8,2,.6,'#a9b6c4');b(-14,26.56,2,.94,'#a9b6c4');b(-16.8,26.4,9.4,.16,'#cd9348');b(-9.4,26.1,2,.3,'#d9b29d')
text(450,815,'PCB1.0 +/-0.1; source land/joint envelope0.3.',11)
text(450,840,'Clamp contacts the full-width covered flex, outside solder lands.',11)
text(450,865,'Preload, solder wetting, peel strength and flex profile unqualified.',11)
text(450,890,f"Incremental hot loop {proof['additional_loop_R85_ohm']*1000:.2f} mOhm / {proof['additional_drop_at_2p987A_V']*1000:.1f} mV at2.987A.",11)
text(450,915,'Source power budget must include this static extension.',11)
text(30,980,'Finite source/package and solder-allocation envelopes; not supplier connector CAD, approved flex fabrication artwork or manufacturing release.',10)
c.save();svg.append('</svg>');(P/'fanout-section.svg').write_text('\n'.join(svg)+'\n')
