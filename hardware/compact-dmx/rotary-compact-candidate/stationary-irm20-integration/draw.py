"""Dimensioned vector sheets from edges of the independently reopened saved CAD.
Existing reportlab only; no tool installation. SVG and PDF share primitives.
"""
from pathlib import Path
import json,html,math,textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
P=Path(__file__).resolve().parent;G=json.loads((P/'saved-projections.json').read_text());C=json.loads((P/'checks.json').read_text())
W,H=420,297;cv=canvas.Canvas(str(P/'stationary-integration.pdf'),pagesize=(W*mm,H*mm));cv.setTitle('STATIONARY-R1 - conditional IRM20 carrier / secondary leadout');svg=[]
def rgb(h):return tuple(int(h[i:i+2],16)/255 for i in [1,3,5])
def line(x1,y1,x2,y2,color='#334155',w=.25):
 cv.setStrokeColorRGB(*rgb(color));cv.setLineWidth(w*mm);cv.line(x1*mm,(H-y1)*mm,x2*mm,(H-y2)*mm);svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"/>')
def poly(pts,color='#334155',w=.18,fill='none'):
 if len(pts)<2:return
 path=cv.beginPath();path.moveTo(pts[0][0]*mm,(H-pts[0][1])*mm)
 for x,y in pts[1:]:path.lineTo(x*mm,(H-y)*mm)
 cv.setStrokeColorRGB(*rgb(color));cv.setLineWidth(w*mm)
 if fill!='none':cv.setFillColorRGB(*rgb(fill))
 cv.drawPath(path,stroke=1,fill=fill!='none');svg.append(f'<polyline points="'+ ' '.join(f'{x:.4f},{y:.4f}' for x,y in pts)+f'" fill="{fill}" stroke="{color}" stroke-width="{w}"/>')
def rect(x,y,w,h,color='#334155',fill='none',lw=.25):poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)],color,lw,fill)
def circle(x,y,r,color='#64748b',w=.25):
 pts=[(x+r*math.cos(a*math.pi/90),y+r*math.sin(a*math.pi/90)) for a in range(181)];poly(pts,color,w)
def text(x,y,s,size=3.2,color='#172033'):
 cv.setFont('Helvetica',size*mm);cv.setFillColorRGB(*rgb(color));cv.drawString(x*mm,(H-y)*mm,s);svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="{color}">{html.escape(s)}</text>')
def note(x,y,s,width=75,size=3.1):
 for i,t in enumerate(textwrap.wrap(s,width=width)):text(x,y+i*4.5,t,size)
def dim(x1,y1,x2,y2,label):
 line(x1,y1,x2,y2,'#64748b',.16)
 for x,y in [(x1,y1),(x2,y2)]:line(x-1,y-1,x+1,y+1,'#64748b',.16)
 text((x1+x2)/2-len(label)*.65,(y1+y2)/2-1.5,label,2.8)
def start(num,title):
 global svg;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297"><rect width="420" height="297" fill="white"/>']
 text(14,17,title,5);text(14,25,'STATIONARY-R1 | mm | 2026-10-23 | unchanged core / trunk / endcaps | CONDITIONAL PROTOTYPE',3.1)
 line(14,30,406,30)
 text(14,286,'NOT A MAINS FABRICATION RELEASE - insulation / solder process / assembly / retention / thermal / endcaps UNMET',3.1,'#b91c1c');text(391,286,f'{num}/3',3.1)
def finish(num):
 (P/f'sheet-{num}.svg').write_text('\n'.join(svg+['</svg>'])+'\n');cv.showPage()
def projection(names,axes,ox,oy,scale):
 for n in names:
  if n not in G:continue
  color='#64748b' if n.startswith('Protected') else '#334155'
  if 'Wire_PLUS' in n or 'PLUS' in n or 'V_PLUS' in n:color='#b91c1c'
  if 'Wire_MINUS' in n or 'MINUS' in n or 'V_MINUS' in n:color='#0f766e'
  if 'sled' in n or 'jaw' in n or 'Standoff' in n or 'shoe' in n:color='#7c3aed'
  if 'sleeve' in n or 'clamp' in n or 'liner' in n:color='#2563eb'
  for edge in G[n]['edges']:
   pts=[(ox+p[axes[0]]*scale,oy-p[axes[1]]*scale) for p in edge]
   poly(pts,color,.14)
start(1,'Stationary module, carrier and finite secondary leadout')
ox,oy,s=27,126,2.55
# True axial section of protected tube; internal geometry edges projected from saved native solids.
for z in [-24,21.5]:rect(ox+2*s,oy-(z+2.5)*s,138*s,2.5*s,'#94a3b8','#f1f5f9')
for x in [0,140]:rect(ox+x*s,oy-24*s,2*s,48*s,'#94a3b8','#f1f5f9')
rect(ox+6*s,oy+14.5*s,130*s,5*s,'#e11d48','#fff1f2')
projection([n for n in G if not n.startswith('Protected')],(0,2),ox,oy,s)
dim(ox,199,ox+142*s,199,'142 unchanged')
dim(ox+39*s,178,ox+100*s,178,'61 carrier')
dim(ox+45*s,65,ox+97.4*s,65,'52.4 nominal module')
line(ox+92*s,58,ox+92*s,76,'#2563eb');text(250,47,'Existing D4 feedthrough: X92 / Y0',3.2,'#2563eb')
text(27,55,'+Z',3);text(383,132,'+X',3)
text(42,170,'Fixed mains L/N/PE trunk: Z -19.5 .. -14.5',3.1,'#b91c1c')
text(284,90,'R9 stationary wire',3.1,'#2563eb')
text(281,102,'No moving mains/PE',3.1)
text(21,214,'Saved CAD: 54 individually valid solids; all-pair intersections independently enumerated.',3.3)
note(21,223,'Module nominal bottom/top -9.00 / +15.00; carrier bottom/top -11.00 / -9.40. Source pin length 2.5 .. 4.5, not a fixed 3.5. Min/max pins are separate editable source-lead-extremes.FCStd, never presented as a noncolliding nominal assembly.',116)
note(21,247,'No new hole or wall thinning. The port route ends at X91.5,Y +/-0.8,Z27.5, tangent +Z; collar FPC clamp remains an external contract. Wire loop outer X110.3. This section is a wireframe projection, not proof of assembly motion or sealed thermal performance.',116)
finish(1)
start(2,'Lead engagement, tolerance envelope and carrier lands')
# Cross section from actual saved source dimensions, worst-case bounding box visually distinct.
x0,y0,ss=93,127,2.2
circle(x0,y0,24*ss,'#64748b');circle(x0,y0,21.5*ss,'#64748b')
rect(x0-8*ss,y0+14.5*ss,16*ss,5*ss,'#e11d48','#fff1f2')
rect(x0-13.6*ss,y0-15*ss,27.2*ss,24*ss,'#334155')
rect(x0-14*ss,y0-15.7*ss,28*ss,24.9*ss,'#d97706')
rect(x0-16*ss,y0+9.4*ss,32*ss,1.6*ss,'#15803d','#f0fdf4')
rect(x0-14.5*ss,y0+13.9*ss,29*ss,.5*ss,'#7c3aed','#f5f3ff')
text(29,65,'Y/Z section bounds (not an all-X silhouette)',3)
dim(37,190,149,190,'OD48 / ID43')
text(26,205,'Orange: source + process body envelope',3,'#d97706')
text(26,213,f'Bore gap >= {C["bounded_body_to_nominal_bore_gap_mm"]:.3f} (nominal bore only)',3)
text(193,48,'Independent coupled vertical corners (32)',3.7)
rows=[('PCB bottom','-11.00 +/-0.05'),('PCB thickness','1.60 +/-0.10'),('Standoff','.40 +/-0.05'),('Body height','24.0 +/-0.5 source'),('Pin length','2.5 .. 4.5 source'),('Min projection below Cu','.280'),('Longest lead tip Z','-13.700'),('Worst deck top Z','-13.850'),('Lead / deck gap','.150'),('Film / nominal trunk gap','.075'),('Worst body top Z','+15.700')]
for i,(a,b) in enumerate(rows):text(193,58+i*7,a,3.2);text(307,58+i*7,b,3.2)
text(193,147,'Actual saved pin centres (X / Y), mm',3.7)
for i,(n,x,y) in enumerate([('AC_N',48.4,-10.4),('AC_L',48.4,10.4),('V_MINUS',93.4,-10.4),('V_PLUS',93.4,-2.4)]):text(193,157+i*8,f'{n:9s}       {x:.1f} / {y:+.1f}',3.3)
# Top view actual board/copper, no source body obscuring lands.
projection([n for n in G if n.startswith(('Carrier','Land_','Trace_','Pigtail_land','Pin_','Secondary_PLUS_via'))],(0,1),-35,250,1.9)
text(193,201,'Mechanical pin apertures include general drawing tolerances.',3.1)
note(193,210,'Nominal pins do NOT contact copper rings. Solder bridge / plated-aperture process UNMET. Primary branch wiring/fuse/connectors are not captured or released. The 2 x 28 slot is not a certified creepage barrier.',59)
note(193,239,'Deck material, 0.50 mm total tolerance allocation, core bore tolerance/ovality and source installation clearances remain open. Minimum lead projection is geometric engagement, not solder quality acceptance.',59)
finish(2)
start(3,'Secondary sleeve, retention and assembly limitations')
# Saved actual detail edges, no invented broad clearance circle.
projection([n for n in G if any(t in n for t in ['Wire_','sleeve','pigtail_clamp','liner','Clamp_M2'])],(0,2),-280,153,3.4)
line(39,153-20.2*3.4,171,153-20.2*3.4,'#94a3b8',.15)
text(17,48,'Finite max-OD wire / split sleeve',3.4)
text(31,211,'Tensility30-02075: OD1.5 +/-0.10, solid20AWG',3.1)
text(31,219,'Source minimum bend R9; each formed length54.462',3.1)
text(31,227,'plus2.600 bare tail. No ampacity / fault I2t grant.',3.1)
text(212,48,'Geometric screen is deliberately bounded',3.7)
items=[f'Wire / sleeve sampled minimum gap: {C["minimum_wire_to_sleeve_screen_mm"]:.4f} mm.', 'Sleeve tube OD3.90 / ID3.70; proposed IDmin3.65.', 'Forming R9..9.1 and common XY placement +/-0.02 are', 'fixture allocations, not wire/sleeve supplier guarantees.', 'Sleeve split, wall0.10, burr coverage and retention UNMET.', 'Maximum jackets touch each other; no wire/core contact.', 'Adjustable jaws and bore shoes: no core penetration.', 'Thread/torque/friction/creep and pull strength UNMET.']
for i,t in enumerate(items):text(212,59+i*7,t,3.05)
text(212,126,'Required assembly sequence - motion NOT proven',3.7)
for y,t in [(138,'1. Set board/module/jaws on sled outside tube.'),(147,'2. Insert sled before forming the secondary loop.'),(156,'3. Feed ends, form with end-access jig, fit split sleeve.'),(165,'4. Complete clamp, inspect terminations, pull/isolation test.'),(174,'5. Close parent-owned endcaps / primary harness design.')]:text(212,y,t,3.05)
note(212,188,'The verifier proves a preformed loop cannot slide axially into the intact core. Jig access, removal and forming loads are still UNMET; the completed CAD pose does not prove a buildable assembly sequence.',57)
note(31,242,'MEAN WELL generic PCB installation guide: 5 mm bottom insulation distance plus film, 10 mm around unit. These are not qualified by this tight layout. Module/body source approval is not barrel safety approval. Thermal/line derating in the sealed barrel, primary wiring, PE policy, variants and endcap clearances remain parent integration gates.',111)
text(31,271,'See DESIGN.md, checks.json, pair-checks.json and receipt.json for explicit assumptions and acceptance limits.',3.1)
finish(3);cv.save();print('DRAWN 3 dimensioned PDF/SVG sheets from saved geometry')
