#!/usr/bin/env python3
from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
ROOT=Path(__file__).resolve().parent
cs=json.loads((ROOT/'contracts.json').read_text());contours=json.loads((ROOT/'sources/meridian-contours.json').read_text())
# Vendor-derived contours stay private/ignored. Every view has identical 4 px/mm scale,
# raw axial zero and no partner placement. Screen units are not a certified print scale.
items=[]
for key,sections in contours.items():
 for section,data in sections.items():
  paths=[]
  for line in data['polylines']:
   if len(line)>1:paths.append('M'+' L'.join(f'{(x+40)*4:.4f},{115-y*4:.4f}' for x,y in line))
  title=key+' / '+section+' — UNPLACED source section'
  svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="230" viewBox="0 0 520 230"><rect width="520" height="230" fill="white"/><text x="10" y="18" font-size="12">{html.escape(title)}</text><text x="10" y="34" font-size="10">4 px/mm; bodyward axis sign only; orange = raw source axial zero</text><path d="M160,40V205" stroke="#b35c00"/><path d="M20,115H505" stroke="#ddd"/><g fill="none" stroke="#244963" stroke-width=".5">{''.join('<path d="'+p+'"/>' for p in paths)}</g><path d="M30,210H110M30,206V214M110,206V214" stroke="black"/><text x="43" y="225" font-size="10">20 mm reference</text></svg>'''
  fn=f'{key}-{section}.svg';(ROOT/'sources'/fn).write_text(svg);items.append(fn)
(ROOT/'sources/reference-atlas.html').write_text('<!doctype html><meta charset="utf-8"><title>Unplaced source sections</title><style>body{font:14px sans-serif} img{display:block;border:1px solid #ccc;margin:8px}</style><h1>UNPLACED manufacturer reference sections</h1><p>Neutrik source geometry. No assembly placement, fitted stop or locked pose. Same scale for every view. Source hashes and copyright retained in original private STEP/PDF files.</p>'+''.join('<img src="'+f+'">' for f in items))
# Own-authored public decision table; no vendor geometry reproduced.
rows=[]
for c in cs['pairs']:
 axis='XYZ'[c['expected_chassis_mating_axis']['source_axis_index']]
 length=c['standalone_mate_drawing_nominal']['length_range_mm']
 rows.append(f'<tr><td>{c["chassis_part"]}<br><small>{c["mate_part"]}</small></td><td>+{axis}<br>{c["panel_shoulder"]["source_face"]} @ 0</td><td>{c["bare_chassis_rear_depth_drawing_mm"]:.1f} mm</td><td>{length[0]}–{length[1]} mm</td><td class="hold">HOLD</td></tr>')
page='''<!doctype html><html><head><meta charset="utf-8"><title>CME-R1 mating contracts</title><style>*{box-sizing:border-box}body{margin:0;padding:0;background:transparent;color:var(--foreground,#172533);font:15px/1.45 system-ui,sans-serif}main{max-width:1000px;margin:auto}h1{font-size:25px;margin:0 0 8px}p{margin:10px 0}table{border-collapse:collapse;width:100%;background:var(--card,#fff);margin:20px 0;font-size:13px}th,td{text-align:left;padding:13px 10px;border-bottom:1px solid var(--border,#d9e0e7)}th{background:var(--secondary,#e5ebf1)}small{color:var(--muted-foreground,#496078)}.hold{font-weight:750;color:var(--warning-foreground,#8b4700)}.callout{padding:16px;background:var(--warning-surface,#fff3df);border-radius:var(--radius,6px);border-left:4px solid #aa6208}.foot{font-size:13px;color:var(--muted-foreground,#44586a)}</style></head><body><main><h1>CME-R1 · Four installed-mating holds</h1><p>The source pass confirms mating types, reference axes and bare chassis depths. It does not establish final seating depth, locked clocking or release-latch travel.</p><table><thead><tr><th>Chassis / specified mate</th><th>Raw panel reference</th><th>Bare rear<br>drawing nominal</th><th>Mate standalone<br>length</th><th>Installed<br>envelope</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table><p class="callout"><b>All four bare rear depths exceed 24 mm.</b> Insulated rear terminals, wire bends and assembly access require additional unqualified space. Standalone mate length is not installed projection.</p><p>No mated transform or continuous insertion/rotation path is accepted. Eight saved, unplaced references preserve the source geometry; two TRUE1 chassis shapes are invalid and both TRUE1 cable models are open surface references.</p><p><b>Next data:</b> a labeled installed datum or sectioned paired assembly identifying the real axial stop, key/contact engagement, fully locked latch state and tolerances; then the operated-latch and exact insulated-terminal/access envelopes.</p><p class="foot">28 reused primary sources + 4 exact mate drawings · 233 directly protected files unchanged · reference-data contract only; no product-fit or mains assembly release. Full evidence: contracts.json, saved-reference-check.json, receipt.json.</p></main></body></html>'''
(ROOT/'views/contracts.html').write_text(page)
# Summary PDF, authored dimensions/table only, no source CAD redistribution.
pdf=canvas.Canvas(str(ROOT/'views/contract-summary.pdf'),pagesize=landscape(A4));W,H=landscape(A4)
pdf.setTitle('CME-R1 - installed mating envelope HOLD');pdf.setAuthor('NOVA-LINK engineering reference pass')
def line(text,y,size=11):pdf.setFont('Helvetica',size);pdf.drawString(35,y,text)
line('CME-R1: installed mating envelopes remain HOLD',H-40,19)
line('No defended rigid transform / installed length / latch motion envelope for any selected pair.',H-64)
y=H-103
for c in cs['pairs']:
 line(c['chassis_part']+' + '+c['mate_part'],y,13)
 ax='XYZ'[c['expected_chassis_mating_axis']['source_axis_index']];length=c['standalone_mate_drawing_nominal']['length_range_mm']
 line(f'Panel: +{ax}, {c["panel_shoulder"]["source_face"]} at 0; bare rear {c["bare_chassis_rear_depth_drawing_mm"]} mm; standalone mate {length[0]}..{length[1]} mm.',y-19)
 line('Installed panel-to-mate extent, locked transverse envelope, terminal assembly depth: UNKNOWN.',y-35,10)
 y-=76
line('All four bare rear dimensions exceed the 24 mm blank; terminals, wiring and access are additional.',y-3,11)
line('Panel shoulders are mounting references, not contact mating planes. Dimensions retain drawing tolerances.',y-23,10)
line('Source hashes, model identities, exact URLs and face constraints: source-links.json / new-source-manifest.json.',y-43,10)
line('Private editable reference: sources/unplaced-references.FCStd. No mated STEP issued.',y-63,10)
line('No product fit, electrical engagement, energized assembly or manufacturing release.',y-83,10)
pdf.showPage();line('CME-R1: geometric probes and missing datums',H-40,19)
y=H-75
for t in ['Axial body cylinders identify axes but leave axial translation and circumferential rotation unresolved.',
'Classic A: Face466 / mate Face247, analytical tZ=-1.65 mm: zero isolated planar overlap.',
'Classic A: Face337 / mate Face2435, tZ=-2.15 mm: 50.69984 mm2 overlap.',
'Classic A: Face560 / mate Face2435, tZ=+20.35 mm: 95.57412 mm2 overlap.',
'Positive plane overlap is not a valid assembly pose, electrical engagement or lock/stop proof.',
'Eight independent saved-reference probes are recorded; no whole-assembly Boolean or motion PASS.',
'Two TRUE1 chassis whole-shapes are invalid. Both TRUE1 cable models have zero closed solids.',
'No source shape was healed; all models remain in their original coordinates and configuration.',
'',
'Required next: actual axial stop + panel datum; insertion and final locked key angles; contact overlap;',
'latch state/travel/tolerances; exact insulated rear terminal/sleeve profile and finite tool/cable bend space.',
'No defensible finite insertion-depth interval or arbitrary hand/bend/tool allowance is supplied.',
'',
'New exact mate drawing versions: 20003815 / 20003817 (2022-06-21);',
'ST-NAC3FX-W-TOP / ST-NAC3MX-W-TOP (2018-05-03). Manufacturer: Neutrik.',
'Private equal-scale unplaced sections: sources/reference-atlas.html and sixteen SVGs.',
'The four exact drawing PDFs retain original maker title blocks/copyright in the ignored cache.']:
 line(t,y,11);y-=23
pdf.save()
# Own-authored SVG, editable dimension-status view.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360"><rect width="1000" height="360" fill="white"/><g font-family="sans-serif" fill="#172533"><text x="25" y="35" font-size="23">CME-R1 - installed mating envelopes unresolved</text>']
for i,c in enumerate(cs['pairs']):
 y=80+i*56;svg.append(f'<text x="25" y="{y}" font-size="16">{c["chassis_part"]} + {c["mate_part"]}</text><text x="470" y="{y}" font-size="16">bare rear {c["bare_chassis_rear_depth_drawing_mm"]:.1f} mm</text><text x="720" y="{y}" font-size="16" fill="#8b4700">installed extent HOLD</text>')
svg.append('<text x="25" y="320" font-size="15">All bare rear depths exceed 24 mm; terminal, cable bend, latch and hand access are additional unknowns.</text><text x="25" y="343" font-size="13">Author-created status diagram, not vendor CAD or a fitted assembly. See receipt and private source atlas.</text></g></svg>')
(ROOT/'views/contracts.svg').write_text(''.join(svg));print('Created 16 private equal-scale sections, private atlas, public contract HTML/SVG and two-page summary PDF.')
