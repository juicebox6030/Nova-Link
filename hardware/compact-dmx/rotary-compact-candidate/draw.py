from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import json
P=Path(__file__).resolve().parent;r=json.loads((P/'screen.json').read_text());c=canvas.Canvas(str(P/'phase0-summary.pdf'),pagesize=(1000,750),invariant=1)
def text(x,y,t,n=12):c.setFillColor(HexColor('#17384b'));c.setFont('Helvetica',n);c.drawString(x,750-y,t)
text(30,35,'COMPACT ROTARY COLLAR / PHASE 0 LIMITS',22)
text(30,65,'Unchanged 5 V source path fails. No reduced assembly CAD or motion PASS is claimed.',15)
text(30,105,'Receptacle DC voltage at 1.5 A: module4.875 V; controller55 mOhm; termination20 mOhm')
text(30,128,'FPC: two8 mm traces, width-0.2 mm/copper-10%; hot copper80 C. Supplier qualification remains open.')
text(40,165,'Length / copper',13);text(250,165,'20 C port',13);text(410,165,'80 C port',13);text(600,165,'Required receptacle minimum',13)
for i,(L,t) in enumerate([(L,t) for L in [.8,1,1.1] for t in [35,70]]):
 rows=[x for x in r['electrical_rows'] if x['length_m']==L and x['copper_nom_um']==t]
 y=195+i*27;text(40,y,f'{L:.1f} m / {t} um');text(250,y,f'{rows[0]["port_DC_V"]:.4f} V');text(410,y,f'{rows[1]["port_DC_V"]:.4f} V');text(600,y,'4.7500 V - FAIL')
text(30,385,'Even optimistic1m/70um with zero terminations and25 C controller maximum gives4.72575 V.')
text(30,420,'181-angle spiral diagnostic: fixed radii25..30.5,6turns at neutral,0.16 allocated strip thickness.',14)
text(30,445,'Neutral length1046.165 mm; fixed-end winding changes length by +/-43.589 mm at +/-90 degrees.')
text(30,470,'Holding length instead forces outer radius32.912 mm at-90 degrees, outside the30.5 mm cavity.')
text(30,495,'This is a falsified simple model, not a proof that every clockspring is impossible. Tangent clamps remain unsolved.')
text(30,540,'One compensation direction: rotating local5.10 V +/-1% regulator BEFORE TPS25810.',14)
text(30,565,'Conditional minimum4.9365 V after switch/paths; about8.517 W input at90% assumed efficiency.')
text(30,590,'Requires an actual selected power stage, thermal/startup qualification and packing. No source architecture changed.')
text(30,630,'GCT six-contact source also lacks D+/D- required by USB-C R2.4 charger compatibility provision.')
text(30,655,'End-face nominal connector suggests near64 mm, but maximum dimensions + allowances screen64.51 mm.')
text(30,680,'Mains/PE remain stationary. No hardware tests, fixture/cable-fit claim, cycle rating or manufacturing release.')
c.save()
