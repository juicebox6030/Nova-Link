"""Self-contained dimensioned SVG + PDF + DXF RFQ drawings, millimetres.
The PDFs and SVGs share the same vector primitives. Not vendor CAD or released tooling.
"""
from pathlib import Path
import math,html
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import ezdxf
P=Path(__file__).resolve().parents[1]/'exports';P.mkdir(exist_ok=True)
W,H=1000,710
pdf=canvas.Canvas(str(P/'manufacturer-drawings.pdf'),pagesize=(W,H))
class Sheet:
 def __init__(self,n,title):
  self.n=n;self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="1000" height="710"><rect width="1000" height="710" fill="white"/>'];pdf.setFillColor(HexColor('#ffffff'));pdf.rect(0,0,W,H,fill=1,stroke=0)
  self.text(30,35,title,21);self.text(30,57,'NOVA-LINK / B-RFQ / 2026-10-22 / mm / NOT RELEASED FOR MANUFACTURE',11,'#ad452b');self.line(30,73,970,73)
 def line(self,x,y,a,b,c='#283849',dash=False):
  self.s.append(f'<path d="M{x},{y} L{a},{b}" stroke="{c}" fill="none"'+(' stroke-dasharray="5 4"' if dash else '')+'/>');pdf.setStrokeColor(HexColor(c));pdf.setDash([5,4] if dash else []);pdf.line(x,H-y,a,H-b);pdf.setDash([])
 def rect(self,x,y,w,h,fill='#eef2f5',stroke='#283849'):
  self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>');pdf.setFillColor(HexColor(fill));pdf.setStrokeColor(HexColor(stroke));pdf.rect(x,H-y-h,w,h,fill=1,stroke=1)
 def circle(self,x,y,r,fill='#ffffff',stroke='#283849'):
  self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}"/>');pdf.setFillColor(HexColor(fill));pdf.setStrokeColor(HexColor(stroke));pdf.circle(x,H-y,r,fill=1,stroke=1)
 def text(self,x,y,s,size=12,c='#283849'):
  self.s.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{c}">{html.escape(s)}</text>');pdf.setFillColor(HexColor(c));pdf.setFont('Helvetica',size);pdf.drawString(x,H-y,s)
 def dim(self,x,y,a,b,s):
  self.line(x,y,a,b);self.line(x-4,y-4,x+4,y+4);self.line(a-4,b-4,a+4,b+4);self.text((x+a)/2-25,(y+b)/2-7,s,11)
 def poly(self,pts,c='#168d91'):
  for a,b in zip(pts,pts[1:]):self.line(*a,*b,c)
 def end(self):
  self.text(30,676,'Supplier components shown as envelopes. Verify actual footprints, latch approach, harness and fixture CAD before tooling.',10)
  self.text(30,694,'See canonical design for tolerances, assembly requirements, release gates and primary-source links.',10)
  self.s.append('</svg>');(P/(self.n+'.svg')).write_text('\n'.join(self.s));pdf.showPage()
s=Sheet('01-sidecar','01 / Right-angle sidecar: packing and reference fixture planes')
s.text(45,105,'TOP / toward fixture face / scale 3 px per mm',12)
# top view physical positions relative shell x0 y20
ox,oy,k=90,170,3
s.rect(ox,oy,98*k,34*k);s.rect(ox+4*k,oy+3*k,90*k,28*k,'#d6e8dd')
s.rect(ox+78*k,oy+2*k,18*k,30*k,'#d5f0f0');s.text(ox+79*k,oy+17*k,'RF',13)
s.rect(ox+8*k,oy+9*k,12.93*k,10.63*k,'#9aaebc');s.text(ox+7*k,oy+8*k,'U5',11)
s.rect(ox+26*k,oy+3.5*k,28.4*k,13.5*k,'#f5d9a8');s.text(ox+29*k,oy+12*k,'15 F',12)
s.rect(ox+62*k,oy+7*k,7*k,7*k,'#8da5b6');s.text(ox+60*k,oy+5*k,'TI',11)
s.rect(ox+52*k,oy+20*k,5.1*k,6.1*k,'#8da5b6');s.text(ox+51*k,oy+19*k,'SPI',10)
s.rect(ox+37*k,oy+25.65*k,11.4*k,8.35*k,'#b4c2ce');s.text(ox+36*k,oy+40*k,'USB-C power',11)
s.rect(ox-10.15*k,oy-30.15*k,72.9*k,20.3*k,'#c8d0d7');s.text(ox-9*k,oy-18*k,'Intact NC5FRX / boot retained',11)
s.dim(ox,oy+145,ox+98*k,oy+145,'98 +/-0.20');s.dim(ox+325,oy,ox+325,oy+34*k,'34')
s.text(490,110,'SIDE / fixture reference plane F = z0',12)
s.line(490,340,935,340,'#d66047');s.text(490,358,'F: actual recess / insertion / connector pitch UNKNOWN',11)
s.rect(510,340-41*4,20.3*4,41*4,'#c8d0d7');s.rect(620,340-29*4,98*2.8,24*4)
s.dim(595,340-41*4,595,340,'41 ref');s.dim(918,340-29*4,918,340,'29 ref')
s.text(620,210,'98 x 34 x 24 sidecar',13);s.text(620,228,'5 mm nominal stand-off from F',11)
s.text(45,395,'PACKING / x-y coordinates and full critical stack in canonical design',13)
for i,t in enumerate(['U5 max: 12.93 x 10.63 x 3.55; TI RGZ nominal: 7 x 7; SPI NOR DFN max: 5.10 x 6.10 x 0.60.', 'Cap max: diameter 13.5 x 28.4; PCB gap1.0 / lid gap1.5 nominal; cradle detailed design open.', 'USB: 11.4 x 8.35 x 3.66 envelope; footprint width reserve 12.3; shell aperture 14 x 6.', 'Cavity minimum width 29.5 minus PCB maximum 28.1 = 1.4 total lateral clearance.', 'Latch: retain 18 mm approach envelope; test finger action with power and DMX cables fitted.', 'Antenna keepout x78..96: no screws, capacitor or ground copper. External metal gap requires RF validation.', '98 mm retained: 25 x 6 power reservation does NOT prove complete EDA placement; routing/cradle remain open.']):s.text(45,425+i*25,t,12)
s.end()
s=Sheet('02-barrel','02 / Rotary USB barrel: fixed core, lock and independent stops')
s.text(40,107,'SIDE / x axis',12)
ox,oy,k=55,235,3.5
s.rect(ox,oy-24*k,142*k,48*k)
s.rect(ox+58*k,oy-42*k,26*k,84*k,'#d5f0f0');s.rect(ox+45*k,oy-10.75*k,45.7*k,21.5*k,'#f5d9a8')
s.text(ox+5,oy+6,'FIXED',13);s.text(ox+92*k,oy+6,'FIXED',13)
s.dim(ox,oy+180,ox+142*k,oy+180,'142');s.dim(ox+58*k,oy-150,ox+84*k,oy-150,'26')
s.text(55,448,'Core OD48 / collar OD84 / normal USB-C output 5 V, 1.5 A',13)
s.text(55,472,'L/N/PE and PSU do not rotate. Source / full assembly approval pending.',11)
# lock front
cx,cy=760,260;sc=2.7
s.circle(cx,cy,42*sc,'#d5f0f0');s.circle(cx,cy,24*sc,'#ffffff')
for d in range(-90,91,15):
 a=math.radians(d);s.circle(cx+29*sc*math.cos(a),cy-29*sc*math.sin(a),1.6*sc,'#6e8497')
s.text(633,405,'13 index holes / 15 degree spacing',12)
s.text(633,430,'R29; diameter 3.20 +0.05/0',12)
s.text(633,455,'Pin diameter 3.00 -0.02/0',12)
s.text(633,480,'Pull 4.2 mm to release; spring return',12)
for i,t in enumerate(['Independent R30 stop slot: width4.30; rounded R2.15 ends; diameter4 peg through diameter4.10 cheek bore.', 'Nominal stop travel180.57 degrees; acceptance180 +/-1. Lock release cannot bypass stop.', 'Lock guide B19: OD3.80 / ID3.20 x9; x58..67; divider/covers seal to sleeve; attachment still open.', 'USB window x65.5..78; wire-lane edge x64.8; board and receptacle lowered1 mm to clear guide.', 'Target: lock1 N m, stop2 N m, axial100 N, cable40 N. Retainers/endcaps/slider and qualification open.']):s.text(40,525+i*25,t,12)
s.end()
s=Sheet('03-wire-motion','03 / Secondary wire cassette: rolling-loop calculation and exploded order')
cx,cy,k=245,270,3.5
s.circle(cx,cy,42*k,'#eef2f5');s.circle(cx,cy,24*k,'#ffffff')
pts=[(cx+26*k*math.cos(t),cy-26*k*math.sin(t)) for t in [math.pi*i/80 for i in range(81)]]
pts += [(cx+(-33+7*math.cos(t))*k,cy+7*math.sin(t)*k) for t in [math.pi*i/40 for i in range(1,41)]]
pts += [(cx+40*k*math.cos(t),cy-40*k*math.sin(t)) for t in [math.pi*(1-i/80) for i in range(1,81)]]
s.poly(pts);s.text(125,450,'Neutral: two arcs + R7 reversing fold',12)
for i,t in enumerate(['Two independent axial wire lanes, no mains in cassette.', 'ri=26, ro=40; R=(40-26)/2=7 mm.', 'theta=-90..+90 degrees; phi=pi+40 theta/66.', 'Loop angle phi=125.45..234.55 degrees.', 'Lactive=pi(26+40+7)=229.34 mm.', 'Add 10 mm clamped tail each end:249.34 mm.', '24 AWG high-strand wire OD <=1.2 mm.', 'Supplier dynamic bend qualification <=7 mm required.', 'No twist in ideal routing; motion test still mandatory.', 'Slots1.6 / divider0.8; seal divider/covers at B19 sleeve.', 'B19-wire gap0.50 nominal /0.375 allocated worst case.', 'Termination/controller losses must be added.']):s.text(475,130+i*25,t,12)
s.text(40,500,'EXPLODED ASSEMBLY ORDER / corresponding STEP is spatially exploded',13)
labels=['inlet cap','fixed core','index ring','left bush','collar + loop','right bush','stop + retainer','outlet cap']
for i,l in enumerate(labels):
 x=42+i*116;s.rect(x,535,100,55,'#e4edf1');s.text(x+5,558,l,10)
 if i<7:s.line(x+100,562,x+116,562)
s.text(40,620,'Lock ring / pin remain independent of the mains path. Assemble at keyed neutral; verify both stops before closing.',11)
s.end()
pdf.save()
# DXF only exact board outline and lock ring; supplier footprints absent.
d=ezdxf.new('R2010');m=d.modelspace();m.add_lwpolyline([(0,0),(90,0),(90,28),(44.9,28),(44.9,22.1),(32.5,22.1),(32.5,28),(0,28)],close=True)
for x,y in [(3,3),(69,3),(3,25),(69,25)]:m.add_circle((x,y),1.1)
m.add_text('90x28 PCB OUTLINE ONLY - NO COPPER/DRC',dxfattribs={'height':2}).set_placement((0,32))
d.saveas(P/'sidecar-pcb-outline.dxf')
d=ezdxf.new('R2010');m=d.modelspace();m.add_circle((0,0),32);m.add_circle((0,0),24.05)
for deg in range(-90,91,15):a=math.radians(deg);m.add_circle((29*math.cos(a),29*math.sin(a)),1.6)
m.add_text('304 SS 2mm; B-RFQ; NOT RELEASED',dxfattribs={'height':2}).set_placement((-32,-38));d.saveas(P/'lock-ring.dxf')
print('Generated 3 SVG sheets, 3-page PDF, 2 DXFs')
