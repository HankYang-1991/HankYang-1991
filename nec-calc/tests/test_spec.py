"""The development specification (docs/SPEC.md) must follow the code.

Every change to the program updates the spec in the same commit: the
version, a revision-history row and the sections it affects.  These checks
catch the parts that can be verified mechanically.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from necalc import __version__                 # noqa: E402
from necalc.i18n import tr                     # noqa: E402

SPEC = os.path.join(ROOT, "docs", "SPEC.md")
TABS = ("tab_branch", "tab_motor", "tab_xfmr", "tab_mv", "tab_tray",
        "tab_load", "tab_sc", "tab_harm", "tab_ref")


class SpecSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SPEC, encoding="utf-8") as fh:
            cls.spec = fh.read()

    def test_version(self):
        m = re.search(r"\| 對應程式版本 \| ([0-9.]+) \|", self.spec)
        self.assertIsNotNone(m, "version row missing in docs/SPEC.md")
        self.assertEqual(m.group(1), __version__,
                         "update docs/SPEC.md for the new version")
        self.assertRegex(self.spec, rf"\n\| {re.escape(__version__)} \| "
                         r"\d{4}-\d{2}-\d{2} \|",
                         "add a revision-history row for this version")

    def test_modules_documented(self):
        for name in sorted(os.listdir(os.path.join(ROOT, "necalc"))):
            if name.endswith(".py") and name != "__init__.py":
                self.assertIn(name, self.spec, f"necalc/{name} not in spec")

    def test_tabs_documented(self):
        for key in TABS:
            self.assertIn(tr(key, "zh").split(" ")[0], self.spec, key)

    def test_tests_documented(self):
        for name in sorted(os.listdir(HERE)):
            if name.startswith("test_") and name.endswith(".py"):
                self.assertIn(f"tests/{name}", self.spec, name)

    def test_project_format_version(self):
        with open(os.path.join(ROOT, "necalc", "gui.py"),
                  encoding="utf-8") as fh:
            m = re.search(r'"format": "necalc-project", "version": (\d+)',
                          fh.read())
        self.assertIsNotNone(m)
        self.assertIn(f"version {m.group(1)}", self.spec)


if __name__ == "__main__":
    unittest.main()
