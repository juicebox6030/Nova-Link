from pathlib import Path
import html,math,json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
P=Path(__file__).resolve().parent;W,H=1200,900
c=canvas.Canvas(str(P/'allocation-sections.pdf'),pagesize=(W,H),invariant=1);svg=[]
def page():
 global svg;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
def txt(x,y,t,size=12):
 c.setFillColor(HexColor('#17364b'));c.setFont('Helvetica',size);c.drawString(x,H-y,t);svg.append(f'<text x="{x}" y="{y}" fill="#17364b" font-family="sans-serif" font-size="{size}">{html.escape(t)}</text>')
def rect(x,y,w,h,col,stroke='#49616d'):
 c.setFillColor(HexColor(col));c.setStrokeColor(HexColor(stroke));c.setLineWidth(.7);c.rect(x,H-y-h,w,h,fill=1,stroke=1);svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}" stroke="{stroke}" stroke-width=".7"/>')
def circ(x,y,r,col):
 c.setFillColor(HexColor(col));c.setStrokeColor(HexColor('#49616d'));c.circle(x,H-y,r,fill=1,stroke=1);svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" stroke="#49616d"/>')
def line(x1,y1,x2,y2,col='#17364b'):
 c.setStrokeColor(HexColor(col));c.setLineWidth(.8);c.line(x1,H-y1,x2,H-y2);svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width=".8"/>')
def save(n):
 svg.append('</svg>');(P/f'allocation-{n}.svg').write_text('\n'.join(svg)+'\n');c.showPage()
page();txt(30,32,'STATIONARY12V SOURCE POD / ONE ALLOCATION',23)
txt(30,58,'Not a manufactured minimum housing. Old5V collar is comparison only; new12V rotor board is not integrated.')
txt(30,85,'TOP X/Y projection - equal scale2.7 drawing points/mm. All stated dimensions inmm.',13)
s=2.7;xx=lambda x:35+(x+164)*s;yy=lambda y:125+(56-y)*s
for x0,x1,y0,y1 in [(-140,-12,-31,51),(-164,-140,8,56),(-12,0,-17,17),(0,142,-24,24),(142,166,-24,24)]:rect(xx(x0),yy(y1),(x1-x0)*s,(y1-y0)*s,'#d2dde4')
rect(xx(-116),yy(26),81*s,52*s,'#f9e6b7');rect(xx(-101.95),yy(13.85),52.9*s,27.7*s,'#d6b26a')
rect(xx(26.8),yy(33),77.37*s,66*s,'#96cbb9')
rect(xx(104.17),yy(31.08),12*s,6.5*s,'#e6ad7b');rect(xx(116.17),yy(31.08),18*s,6.5*s,'#f2d0a9');rect(xx(134.17),yy(30.83),80*s,6*s,'#ecdcc8')
line(xx(-164),403,xx(166),403);line(xx(-164),397,xx(-164),409);line(xx(166),397,xx(166),409)
txt(350,425,'330 overall product allocation / X-164..166',14)
txt(55,465,'Pod shell128 x82 x62; input blank offsetY32,Z-15, Ø48 x24.',13)
txt(55,489,'Whole product including collar/endcap blanks:330L x89W x72H.',13)
txt(55,513,'Bounds X-164..166 / Y-33..56 / Z-39..33. No universal connector/fixture-fit claim.',13)
txt(55,545,'Collar comparisonØ66; released sweep startsX26.8. Sourcepod/neck endsX0:26.8 axial gap.',13)
txt(55,569,'Only isolatedLV rotates.13 detents at15degrees; ±90degree range inherited unchanged.',13)
txt(55,601,'Actual frozen USB body allocation endsX104.17; this is NOT its exact mating plane.',13)
txt(55,625,'Engineering approach:12mm plug +18mm relief +80mm cable; far endX214.17.',13)
txt(55,649,'Product plus finite cable screen spans378.17mm. No cable supplier profile or bend approval.',13)
txt(55,681,'−X pod placement clears the USB approach throughout181 angles; output blank remains a gate.',13)
txt(55,713,'Carrier supports, terminal transitions and final fixed-clamp radial exit are visible unimplemented',13)
txt(55,737,'interfaces. Neither wire continuity nor mains construction approval follows from this layout.',13)
txt(55,785,'Solid/spacing/motion evidence:checks.json. Exact allocations and scope labels:editableFCStd +STEP.',12)
save(1)
page();txt(30,32,'SOURCE POD / Y-Z SECTION AT X-75',22)
txt(30,58,'Equal scale7 drawing points/mm; hidden pin projection is a bounding reservation, not actual leads.',12)
s=7;xx=lambda y:70+(y+31)*s;zz=lambda z:110+(29-z)*s
rect(xx(-31),zz(29),82*s,62*s,'#b5c4ce');rect(xx(-28),zz(26),76*s,56*s,'#ffffff')
rect(xx(-26),zz(24),52*s,44*s,'#fff0cc');rect(xx(-13.85),zz(14),27.7*s,24.5*s,'#d5b16a')
rect(xx(-13.85),zz(-10.5),27.7*s,4.5*s,'#eadcca');rect(xx(-16),zz(-11.5),32*s,1.6*s,'#72b29a')
rect(xx(-26.5),zz(-20.5),53*s,.25*s,'#9b6daf')
for y in [32,38,44]:circ(xx(y),zz(-25),2.75*s,'#e0e8ed');circ(xx(y),zz(-25),2.25*s,'#93a8b8')
for i,t in enumerate(['SOURCE REQUIREMENTS / CACHED PRIMARY','10mm around general unit;5mm bottom +Mylar.','Planning whole-carrier box81 x52 x44.','Maximum module52.9 x27.7 x24.5.','Maximum pin projection4.5 below body.','Actual pins/carrier/solder/retention NOT released.','','ENGINEERING ALLOCATIONS','+/-0.5 envelope beyond planning box.','Film0.25; chosen grade/retention unqualified.','Shell3mm nominal; material/thermal gates.','TrunkØ4.5, centrelineR12; +0.5 radial space.','Trunk below reservation, not through it.','Primarybranch R8 bend-space only; no fuseMPN.']):txt(690,120+i*26,t,12)
txt(60,600,'Bottom reservation surfaceZ-20; maximum pin tipZ-15 ->5mm. Film topZ-20.5 adds0.5 allocation.',12)
txt(60,626,'Maximum body topZ14 -> reserved topZ24:10mm. CarrierY±16 -> reservationY±26:10mm.',12)
txt(60,652,'L/N/PE axes atY32/38/44,Z-25 in pod; nominal upper wire surfaceZ-22.75 lies below reservation.',12)
txt(60,684,'Support zones are outside the reservation. Their bridge/attachment to the carrier is NOT designed.',12)
txt(60,710,'Primary interface stopsX-116.5 versus carrier edge-106:10.5mm construction gap explicitly open.',12)
txt(60,736,'Secondary interface startsX-34.5 versus carrier edge-45:10.5mm construction gap explicitly open.',12)
txt(60,762,'The terminal transitions cannot be treated as permission to fill the insulation space with trunk/joints.',12)
txt(60,804,'Thermal, ventilation, adjacent fixture heat, film/safety construction and variant endcaps remain unqualified.',12)
save(2);c.save()
