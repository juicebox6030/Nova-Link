"""Access to the shared test vectors in tests/vectors/ (generated from the C
core by tests/gen_vectors.c). Set NL_VECTORS_DIR to use another directory."""

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"
VECTOR_DIR = Path(os.environ.get("NL_VECTORS_DIR") or REPO_ROOT / "tests" / "vectors")

_cache = {}


def load(name):
    """Load tests/vectors/<name>.json (cached)."""
    if name not in _cache:
        with open(VECTOR_DIR / (name + ".json"), encoding="utf-8") as fh:
            _cache[name] = json.load(fh)
    return _cache[name]


def h(text):
    return bytes.fromhex(text)


class VectorMixin:
    """Mix into a unittest.TestCase: subclasses name their vector file and the
    sections they check, and a test fails if the generator grows a section
    nobody checks."""

    VECTOR_FILE = None
    SECTIONS = ()

    def vectors(self, section):
        data = load(self.VECTOR_FILE)
        self.assertIn(section, data, "%s.json has no section %r" % (self.VECTOR_FILE, section))
        self.assertTrue(data[section], "%s.json section %r is empty" % (self.VECTOR_FILE, section))
        return data[section]

    def test_every_section_is_checked(self):
        data = load(self.VECTOR_FILE)
        sections = set(data) - {"generator", "description"}
        self.assertEqual(sections, set(self.SECTIONS))
        self.assertEqual(data["generator"], "tests/gen_vectors.c")
