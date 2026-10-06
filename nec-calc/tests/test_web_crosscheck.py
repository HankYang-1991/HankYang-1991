import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")


@unittest.skipUnless(shutil.which("node"), "needs Node.js")
class WebCrossCheck(unittest.TestCase):
    """The JavaScript port (web/necalc.js) must match the Python engine."""

    def test_js_matches_python(self):
        subprocess.run([sys.executable, os.path.join(WEB, "build_data.py")],
                       check=True, capture_output=True)
        subprocess.run([sys.executable, os.path.join(WEB, "crosscheck.py"),
                        "80"], check=True, capture_output=True)
        r = subprocess.run(["node", os.path.join(WEB, "crosscheck.js")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
