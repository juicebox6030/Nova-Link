#!/usr/bin/env python3
"""Fetch and checksum the manufacturer reference assets listed in the manifest."""

from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent / "source-cache"
ASSETS = {
    "etc-colorsource-v-3d-cad.zip": (
        "https://cdn.etcconnect.com/ColorSource%20V_3D%20CAD.zip",
        "e8bcf36cf7ea80b4726969d9288b3a66a883be3c1f0501b5521004f3770a9b95",
    ),
    "etc-colorsource-spot-v-installation-guide.pdf": (
        "https://www.etcconnect.com/WorkArea/DownloadAsset.aspx?id=10737516501",
        "31cb5981028b2e19583bf06197153417b91d2e145e5766832c09d13bef16b472",
    ),
    "etc-colorsource-fresnel-v-installation-guide.pdf": (
        "https://www.etcconnect.com/WorkArea/DownloadAsset.aspx?id=10737516500",
        "ca79970d0d4e41b9ebf1303edf24c22a075d54f730a2490ce3fdfa69aeaa2e5c",
    ),
    "chauvet-ovation-e-910fc-3d-cad.zip": (
        "https://chauvetprofessional.com/wp-content/uploads/2015/01/OVATION-E-910FC_3D_CAD.zip",
        "5032128181480201b3815f67699c6e264825188e3399b2341cf1f2d4c665051f",
    ),
    "chauvet-ovation-e-910fc-user-manual.pdf": (
        "https://www.chauvetprofessional.com/wp-content/uploads/2015/01/Ovation_E-910FC_UM_Rev18.pdf",
        "3939e7c928b2afaafe0568700bb8770f21a54909b29a5a018516b393ab0d75ad",
    ),
    "glp-impression-x5-cad.zip": (
        "https://glp.de/files/products/impression-x5-product-data/GLP_impression_X5_CAD_Rev20240202-1.zip",
        "94d87167d1a155785ec6de431817982aecd296ba1767d4882c8d617ef2e61da5",
    ),
    "glp-impression-x5-user-manual.pdf": (
        "https://glp.de/files/products/impression-x5-product-data/GLP_impression_X5_User_Manual_EN_Rev_20240207-01.pdf",
        "bc7a3cbf9950e89910e149fe87206b76ae20a920208f24f840bb1c764f0f3d66",
    ),
}


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in ASSETS.items():
        path = ROOT / name
        if not path.exists() or sha256(path.read_bytes()).hexdigest() != expected:
            request = Request(url, headers={"User-Agent": "NOVA-LINK-fixture-reference-fetch/1.0"})
            with urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise RuntimeError(f"{name}: HTTP {response.status}")
                path.write_bytes(response.read())
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"{name}: SHA-256 mismatch: {actual}")
        print(f"OK {name} bytes={path.stat().st_size} sha256={actual}")


if __name__ == "__main__":
    main()
