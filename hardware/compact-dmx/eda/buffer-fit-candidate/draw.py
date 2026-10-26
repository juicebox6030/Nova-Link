from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from xml.sax.saxutils import escape
P=Path(__file__).resolve().parent;W,H=1000,650;c=canvas.Canvas(str(P/'fit-section.pdf'),pagesize=(W,H),invariant=1);s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><rect width="100%" height="100%" fill="white"/>']
def text(x,y,t,size=12):
 c.setFillColor(HexColor('#163449'));c.setFont('Helvetica',size);c.drawString(x,H-y,t);s.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#163449">{escape(t)}</text>')
def rect(x,y,w,h,col):
 c.setFillColor(HexColor(col));c.rect(x,H-y-h,w,h,fill=1,stroke=0);s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}"/>')
def box(y,z,w,h,col):rect(50+(y-20)*14,460-(z+h-5)*14,w*14,h*14,col)
text(30,30,'25 F BUFFER / LOCAL PCB CUTOUT PROPOSAL',20)
text(30,53,'Y/Z section through cell; equal axis scale 14 points/mm. Existing case 98 x 34 x 24 mm.')
box(20,5,34,2,'#bcc8ce');box(20,7,2,20,'#bcc8ce');box(52,7,2,20,'#bcc8ce');box(20,27,34,2,'#bcc8ce')
box(23,10,2.5,1,'#449b82');box(35.8,10,15.2,1,'#449b82')
x=50+(30.65-20)*14;y=460-(18.1-5)*14;r=8.25*14
c.setFillColor(HexColor('#e3b158'));c.circle(x,H-y,r,fill=1,stroke=0);s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#e3b158"/>')
for i,t in enumerate(['Eaton HV1625-2R7256-R, 25 F / 2.7 V','Maximum can: diameter16.5 x length28.4','Axis X; x27..55.4, cy30.65, cz18.1','Can bottom9.85 / top26.35','PCB z10..11; new aperture:','x26.5..55.9 / y25.5..35.8 (29.4 x 10.3)','Nominal gaps: wall0.40 / lid0.65','Allocated screen: PCB0.231 / wall0.25 / lid0.50','Further case/lid process allowance0.10 remains.','Two cradle saddles x28..31 and50..53','Saddle radius8.60, .35 compliant liner TBD','Lead forming + retainer/vent path remain open.']):text(550,140+i*24,t)
text(30,505,'Can penetrates PCB plane: this is not a drop-in substitution. Original USB tongue, supports, NOR and case are retained.')
text(30,530,'Screened 173 finite courtyard volumes: zero overlap at allocated heights; no supplier-exact full assembly model.')
text(30,555,'Cradles are present in FCStd/STEP, omitted here for clarity. Liner, retention, formed leads and PCB routing are NOT released.')
text(30,590,'16.34 s conditional aged screen at 1.11 W, 80% electronics efficiency, 54 mOhm ESR; not measured or cold-qualified.')
text(30,615,'No active PCB/CAD/BOM change; all dimensions mm. Supplier lead/temperature and protection qualification required.')
s.append('</svg>');(P/'fit-section.svg').write_text('\n'.join(s)+'\n');c.save()
