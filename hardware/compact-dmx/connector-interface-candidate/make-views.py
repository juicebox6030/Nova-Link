#!/usr/bin/env python3
"""Source-dimensioned allocation views, never substituted for vendor geometry."""
from pathlib import Path
import json,html
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
ROOT=Path(__file__).resolve().parent
c=json.loads((ROOT/'contracts.json').read_text());cad=json.loads((ROOT/'cad-inspection.json').read_text())
saved=json.loads((ROOT/'saved-cad-check.json').read_text())
W,H=1060,720
s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="1060" height="720" fill="white"/>','<style>text{font-family:Arial,sans-serif;fill:#172b3c}.small{font-size:13px}.part{font-size:17px;font-weight:bold}</style>', '<text x="28" y="34" font-size="24">CI-R1 — nominal bare rear depth versus 24 mm allocation</text>','<text x="28" y="59" class="small">Source-dimensioned allocation diagram only. Not CAD, not installed plug depth, not an assembly release.</text>']
for i,x in enumerate(c['interfaces']):
 y=92+i*88;v=x['drawing_rear_depth_mm'];scale=10
 s += [f'<text x="28" y="{y+18}" class="part">{x["part"]}</text>',f'<text x="28" y="{y+39}" class="small">{html.escape(x["gender"])}</text>',f'<rect x="235" y="{y}" width="240" height="29" fill="#dae8f1"/>',f'<rect x="235" y="{y+6}" width="{scale*v}" height="17" fill="#d78632"/>',f'<line x1="475" y1="{y-5}" x2="475" y2="{y+35}" stroke="#205c85" stroke-width="2"/>',f'<text x="710" y="{y+18}" class="part">{v:.1f} mm rear; +{v-24:.1f} mm</text>']
 flange=f'Ø{x["flange_diameter_mm"]:.1f}' if 'flange_diameter_mm' in x else ' × '.join(str(a) for a in x['flange_mm'])
 s += [f'<text x="710" y="{y+40}" class="small">Flange {flange} mm; wires / terminals / tools additional</text>']
s += ['<text x="28" y="651" class="small">Blue line = 24 mm allocation. Drawing depths start at the rear flange/panel shoulder.</text>','<text x="28" y="677" class="small">All six fail a standalone 24 mm rear allocation. NEMA flanges additionally exceed Ø48 by 15.5 mm.</text>','<text x="28" y="702" class="small">Original STEP and independent orthographic CAD projections are separate files; no mated assembly datum was invented.</text>','</svg>']
(ROOT/'views/contract-summary.svg').write_text('\n'.join(s))
p=canvas.Canvas(str(ROOT/'views/contract-summary.pdf'),pagesize=landscape(A4));pw,ph=landscape(A4)
p.setTitle('CI-R1 manufacturer connector interface contracts')
def text(x,y,t,size=10):p.setFont('Helvetica',size);p.drawString(x,y,t)
text(28,ph-30,'CI-R1 - six stationary interfaces / source geometry contract',18)
text(28,ph-50,'Nominal rear depths from the drawn rear flange shoulder. Termination and assembly access are additional.',10)
for i,x in enumerate(c['interfaces']):
 y=ph-90-i*65;v=x['drawing_rear_depth_mm'];scale=6
 text(28,y+2,x['part'],12)
 p.setFillColorRGB(.86,.92,.96);p.rect(175,y-5,24*scale,20,fill=1,stroke=0)
 p.setFillColorRGB(.83,.49,.15);p.rect(175,y,scale*v,10,fill=1,stroke=0)
 p.setStrokeColorRGB(.1,.3,.5);p.line(175+24*scale,y-8,175+24*scale,y+22)
 p.setFillColorRGB(.08,.14,.2)
 text(490,y+2,f'{v:.1f} mm; {v-24:+.1f} mm beyond 24',11)
 flange=f'Dia {x["flange_diameter_mm"]:.1f}' if 'flange_diameter_mm' in x else ' x '.join(str(a) for a in x['flange_mm'])
 text(490,y-15,'Flange '+flange+' mm; no wire/tool allowance',9)
text(28,64,'All 24 mm rear allocations fail before termination allowance. NEMA flange Dia63.5 exceeds Dia48.',12)
text(28,45,'Source drawing depths are not installed plug projection. Mounting planes do not establish contact mating planes.',9)
text(28,28,'No production approval, electrical test, custom-contact design, or baseline change.',9)
p.showPage()
text(28,ph-30,'Mating map and actual CAD inspection limits',18)
lines=[
'Classic: input NAC3MPXXA <- NAC3FXXA-W-S (A / blue).',
'Output NAC3MPXXB -> NAC3FXXB-W-S -- cord -- NAC3FXXA-W-S -> fixture blue A inlet.',
'B is not A. FXX + legacy inlet has no CBC; do not transfer XX/FXX load-break permission.',
'TRUE1: input NAC3MPX-TOP <- female NAC3FX-W-TOP.',
'Output female NAC3FPX-TOP -> male NAC3MX-W-TOP -- cord -- female NAC3FX-W-TOP -> male fixture inlet.',
'NEMA: input male 5278-C <- female 5269-C. Output female 5279-C -> male 5266-C cord / fixture plug.',
'Optional source-to-fixture extension has 5266-C at source, 5269-C at fixture. No default positive mains lock.',
'Flanged NEMA comparison does not qualify baseline molded pigtails or a cord connector as a custom panel insert.',
]
y=ph-60
for t in lines:text(28,y,t,10);y-=19
text(28,y-15,'Saved original-model inspection (0.03 mm mesh samples are not maximum tolerance envelopes):',11);y-=38
for k,v in cad['items'].items():
 ax=v['projection_axis_index'];b=v['sampled_mesh_bbox_mm'];length=b[ax+3]-b[ax]
 text(28,y,f'{v["part"]:21s}  sampled axial span {length:8.3f} mm; valid={v["valid"]}; solids={v["solids"]}',9);y-=16
text(28,81,'Invalid TRUE1 chassis and open/surface models retained unchanged. CAD face IDs are import-version specific.',9)
text(28,65,'No installed mate/hand/cable bend plane, rear terminal sleeve/tool sweep, wall/seal/boss fit, or assembly is qualified.',9)
text(28,49,'Source URLs, hashes, model headers, panel face coordinates, static checks: source-manifest / contracts / cad-inspection JSON.',9)
text(28,33,'Original STEP + editable import library are private source-cache evaluation artifacts; no redistribution licence asserted.',9)
p.save()
sources={Path(x['file']).stem:x['url'] for x in json.loads((ROOT/'source-manifest.json').read_text())}
rows=''.join(f'<tr><td>{html.escape(x["variant"])}</td><td><a href="{html.escape(sources[x["id"]+"-drawing"],quote=True)}">{x["part"]}</a></td><td>{x["drawing_rear_depth_mm"]:.1f} mm</td><td>+{x["drawing_depth_excess_over_24_mm"]:.1f} mm</td></tr>' for x in c['interfaces'])
h='''<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:var(--font-sans,Arial);color:var(--foreground,#172b3c);margin:0}p{line-height:1.5}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:9px 4px;border-bottom:1px solid var(--border,#ddd)}th{color:var(--muted-foreground,#555)}.note{font-size:13px;color:var(--muted-foreground,#555)}@media(max-width:500px){th,td{padding:8px 2px;font-size:11px}}</style></head><body><p><strong>Official CAD retrieved for all six interfaces.</strong> None establishes a complete Ø48 ×24 mm connector end.</p><table><thead><tr><th>Variant</th><th>Chassis</th><th>Bare rear depth</th><th>Beyond 24 mm</th></tr></thead><tbody>'''+rows+'''</tbody></table><p>NEMA flanges are Ø63.5 mm. Classic powerCON requires a gray-B-to-blue-A fixture jumper; <a href="https://www.neutrik.us/en-us/news/neu-powercon-xx-iec-60320-1-konform">legacy mating combinations have no breaking capacity</a>. TRUE1 uses its separate male/female pair.</p><p class="note">Drawing nominal dimensions only; terminals, insulation, cable bends and access are additional. Twelve original STEP models inspected including the specified external mates. Some models are invalid or open surfaces. No installed assembly fit or manufacturing release.</p></body></html>'''
(ROOT/'views/contract-summary.html').write_text(h)
print('Generated SVG, two-page PDF and self-contained HTML allocation views')
