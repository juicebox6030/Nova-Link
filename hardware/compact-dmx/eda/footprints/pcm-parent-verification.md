# PCM12SMTR primary-source check — 2026-10-22

The live [manufacturer product page](https://www.littelfuse.com/products/switches/slide-switches/pcm/pcm12smtr)
lists **Product Status: Active** for PCM12SMTR. Parent read the rendered page in
the T3 collaborative browser; the [DOM/source receipt](pcm-official-status.json)
retains the status, exact URL and linked datasheet. This supersedes the earlier
unresolved lifecycle lookup; no EOL designation was established for this part.

The linked [official PDF](https://www.littelfuse.com/assetdocs/littelfuse-ck-slide-pcm-series-datasheet?assetguid=d2f6a96c-7a9a-4c4e-a5aa-4fe3075dffe5)
was retrieved by same-origin browser fetch, HTTP200, 498359 bytes, SHA-256
`6a758d151b7eee7f8cd59594bd92cfec4c9b1470e0743094f185f19e7ac2a868`.
Direct CLI requests returned403; browser retrieval recovered access without new
tools or authentication. Local cache: `.tools/references/pcm-official.pdf`.
Parent visually inspected printed page2, revision VL03/14/25, including its
PC Mounting detail. The source is not measured from raster pixels.

| Feature | Manufacturer drawing, mm | Current provisional footprint, mm |
|---|---|---|
| Signal-land width/length | 0.7 / (2.5−1.0)=1.5 | 0.7 / 1.5 |
| Signal1→2 / 2→3 spacing | 3.0 / 1.5 | 3.0 / 1.5 |
| Mounting-land width/height | 1.0 / 0.8 | 1.0 / 0.8 |
| Inner-edge gap between mounting-land rows | 1.13 | 1.41 |
| Locator-hole diameter / horizontal spacing | 0.9 / 3.0 | 0.9 / 3.0 |

The current mounting-land centres are y=−0.78 and+1.43, so their inner-edge gap
is `1.43−(−0.78)−0.8=1.41mm`: **0.28mm greater than the manufacturer's
dimensioned gap**. This prevents claiming the current candidate reproduces the
recommended mounting pattern. It does not establish a tested assembly failure.
Keep the footprint provisional until its complete coordinate/pin convention is
checked and corrected. In particular, do not infer the locator-centre-to-row
offset solely from the illustration's apparent symmetry. Preserve the known
manufacturer dimensions and mark any remaining datum interpretation explicitly.

No footprint library, schematic or CAD was changed by this parent check. The
ongoing placement task was informed of the mismatch and current Active status.
