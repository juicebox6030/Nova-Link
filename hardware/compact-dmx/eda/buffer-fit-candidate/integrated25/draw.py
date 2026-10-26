from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
P=Path(__file__).resolve().parent;c=canvas.Canvas(str(P/'assembly-sections.pdf'),pagesize=(1000,760),invariant=1)
def text(x,y,t,n=12):c.setFillColor(HexColor('#17384b'));c.setFont('Helvetica',n);c.drawString(x,760-y,t)
def rect(x,y,w,h,color):c.setFillColor(HexColor(color));c.rect(x,760-y-h,w,h,fill=1,stroke=0)
text(30,30,'25 F INTEGRATED PROTOTYPE / ASSEMBLY SECTIONS',20)
text(30,55,'Engineering geometry; not supplier forming approval. All physical dimensions mm; each view scale stated.')
# X/Z projection, scale10. cell length and height max source.
text(35,92,'X/Z projection: 10 drawing points/mm. Retainers shown schematically at true bounds.')
def bx(x,z,w,h,col):rect(40+(x-25)*10,410-(z+h-7)*10,w*10,h*10,col)
bx(25,5,38,2,'#bdc9ce');bx(27,9.85,28.4,16.5,'#e6b561');bx(25,27,38,2,'#bdc9ce')
for x in [28,50]:bx(x,7,3,5.5,'#80979f');bx(x,26.35,3,.35,'#65bda5');bx(x,26.7,3,.3,'#80979f')
bx(26.3,24.5,.3,2.5,'#80979f');bx(55.8,24.5,.3,2.5,'#80979f');bx(26.6,24.5,.4,1.7,'#65bda5');bx(55.4,24.5,.4,1.7,'#65bda5')
bx(55.9,10,7.1,1,'#469d81')
# Formed lead centreline; PDF cubic approximation only, CAD has exact circle.
x=lambda a:40+(a-25)*10;z=lambda a:410-(a-7)*10
c.setStrokeColor(HexColor('#b85e30'));c.setLineWidth(8.2);p=c.beginPath();p.moveTo(x(55.4),760-z(18.1));p.lineTo(x(56.7),760-z(18.1));p.curveTo(x(57.362742),760-z(18.1),x(57.9),760-z(17.562742),x(57.9),760-z(16.9));p.lineTo(x(57.9),760-z(9));c.drawPath(p)
for i,t in enumerate(['Max can x27..55.4; z9.85..26.35','Body Ø16.5 x 28.4; nominal cell centre z18.1','Axial stop rigid gaps .4 each, with compliant pads','Integral lower saddles; .35 radial silicone liners','Lid bosses + top liners prevent upward escape','Four flush M2x22 screws retain lid to original bosses','Thread/creep/torque and silicone compression unqualified','Lead reference plane x55.4 is max-body face, not','a manufacturer-dimensioned internal seal datum.']):text(475,145+24*i,t)
text(35,450,'Lead form: straight1.3 from body face; centreline R1.2; max wire diameter.82; vertical x57.9, trimz9.')
text(35,475,'These forming dimensions are engineering proposals. Preform with a supported seal-side clamp; no load on seal.')
text(35,500,'C23 pin1 positive: y26.9 / CAP_POS. Pin2 negative: y34.4 / GND_USB. Nominal pitch7.5; supplier tolerance +/-0.5.')
text(35,525,'Lands: oval copper1.7 x 2.7, plated slots1.1 x 2.1; slot long axisY. No paste; explicit hand-solder process gate.')
text(35,550,'Routed aperture x26.5..55.9 / y25.5..35.8, cornerR0.5. Allocated 3D clearance0.178 (was0.231 square).')
text(35,575,'Actual PCB pad-to-aperture conservative minimum1.15. Copper endsx58.75; courtyardx58.90, beforeRFx59.')
text(35,610,'Vent: axial end restraints occupy only upper peripheral regionz24.5..26.2; central endface radius6.4 open.')
text(35,635,'This opening is geometric, not Eaton vent approval. No encapsulation; verify actual vent location and escape path.')
text(35,670,'Case98 x 34 x 24 retained; no routed board or manufacturing release. Source data/commands/checks: README.md.')
c.save()
