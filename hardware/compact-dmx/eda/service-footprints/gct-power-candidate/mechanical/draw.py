"""Drawing-only layout; shared primitives keep SVG and PDF coordinates identical."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

P = Path(__file__).resolve().parent
W, H, SCALE = 1100, 800, 18
c = canvas.Canvas(str(P / 'section.pdf'), pagesize=(W, H), invariant=1)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>']

def text(x, y, s, size=12):
    c.setFillColor(HexColor('#172c3e'))
    c.setFont('Helvetica', size)
    c.drawString(x, H-y, s)
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" font-family="Helvetica, sans-serif" fill="#172c3e">{escape(s)}</text>')

def point(y, z):
    return 60+(y-43)*SCALE, 552-(z-5)*SCALE

def line(x1, y1, x2, y2):
    c.setStrokeColor(HexColor('#506475'))
    c.setLineWidth(.7)
    c.line(x1, H-y1, x2, H-y2)
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#506475" stroke-width="0.7"/>')

def box(y, z, w, h, color):
    x, bottom = point(y, z)
    top, ww, hh = bottom-h*SCALE, w*SCALE, h*SCALE
    assert top >= 120 and bottom <= 552
    c.setFillColor(HexColor(color))
    c.rect(x, H-bottom, ww, hh, fill=1, stroke=0)
    svg.append(f'<rect x="{x}" y="{top}" width="{ww}" height="{hh}" fill="{color}"/>')

def callout(y, z, row, label):
    x, sy = point(y, z)
    line(x, sy, 510, row-4)
    line(510, row-4, 535, row-4)
    text(545, row, label)

text(35, 30, 'GCT FLUSH PROTOTYPE - DIMENSIONED Y/Z SECTION', 19)
text(35, 52, 'Coordinates in mm. Equal Y/Z scale: 18 drawing points/mm; print scaling may vary.')
text(35, 73, 'Connector/stakes are envelopes, not supplier 3D. External plug screening only; no universal cable-fit claim.')
box(43, 5, 11, 2, '#adb7bf')
box(52, 15.5, 2, 11.5, '#adb7bf')
box(43, 27, 11, 2, '#adb7bf')
box(44.6, 16, 9.4, 3, '#6c8b9a')
box(44.6, 11.5, 2, 7.5, '#6c8b9a')
box(43, 10, 10.3, 1, '#3b9d79')
box(47.2, 11, 6.8, 3.16, '#e5af50')
# Full 12 mm engineering overmold length, matching the existing CAD envelope.
box(54.4, 9.5, 12, 6, '#b0c1eb')
callout(54, 28, 137, 'Lid z27..29; complete case z5..29 (24 high)')
callout(54, 22, 196, 'Front wall y52..54; outer mating plane y54')
callout(53.5, 18, 262, 'Bridge z16..19, x37.5..47.9; PA12 prototype')
callout(46.6, 12, 323, 'Rear stop ends y46.6; rigid gap 0.60 to shell')
callout(54, 14.16, 374, 'Shell y47.2..54, z11..14.16; face formerly y51')
callout(66.4, 12.5, 425, 'Engineering overmold: Y12 x Z6, y54.4..66.4')
callout(53.3, 10.5, 477, 'PCB z10..11; tongue ends y53.3')
callout(54, 6, 539, 'Base z5..7; external case 98 x 34 x 24')
text(60, 580, 'Y increases right; Z increases up. Section at connector centre X42.7.')
text(60, 600, 'Stakes and support rails lie out of this section; see PCB view and editable solids.')
text(35, 641, 'PLAN: main board x4..94 / y23..51. Tongue x36.5..48.9 / y51..53.3 (12.4 x 2.3).')
text(35, 664, 'USB origin (42.7,47.6); stakes x38.38/47.02 at y47.6/51.4; plated slots 0.6 x 1.2.')
text(35, 687, 'Rails: x36.9..37.4 and 48.0..48.5, y49..52.7; z7..9.6 + 0.4 foam. Stake screening bottom z9.75.')
text(35, 710, 'Bridge, rear stop and shell are projected envelopes; compliant rear pad omitted for clarity. No supplier internal model.')
text(35, 745, 'Gates: stake thickness, shim/pad compression, insertion-load/creep strength, exact plug and process tolerances.')
text(35, 768, 'Local prototype only; no routed-PCB, RF, power-placement, assembly-fit or manufacturing-release acceptance.')
svg.append('</svg>')
(P / 'section.svg').write_text('\n'.join(svg)+'\n')
c.save()
