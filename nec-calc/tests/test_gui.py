import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import tkinter as tk
    HAVE_TK = bool(os.environ.get("DISPLAY")) or sys.platform == "win32"
except ImportError:  # pragma: no cover
    HAVE_TK = False


@unittest.skipUnless(HAVE_TK, "needs tkinter and a display")
class GuiSmokeTest(unittest.TestCase):
    def test_all_tabs_both_languages(self):
        from necalc.gui import App
        root = tk.Tk()
        try:
            app = App(root)
            for lang in ("en", "zh"):
                app.v["lang"].set(lang)
                app.on_lang()
                app.calc_branch()
                app.calc_motor()
                app.calc_xfmr()
                app.calc_mv()
                app.calc_tray()
                app.calc_feeder()
                for key in ("br", "mo", "xf", "mv", "tr", "lc"):
                    self.assertIn(key, app.results, (lang, key))
                app.v["br.w.method"].set("busway")
                app.v["br.w.wiring"].set("3ph4w")
                app.v["br.w.voltage"].set("480")
                app.v["br.value"].set("1500")
                app.v["br.unit"].set("A")
                app.calc_branch()
                summ = app.results["br"][1].summary
                self.assertEqual(summ["method"], "busway")
                app.v["br.w.method"].set("cable")
                app.calc_capacity()
                self.assertIn("tr", app.results)
            app.v["edition"].set("2026")
            app.on_edition()
            d = app.project_dict()
            app.load_project_dict(d)
            self.assertEqual(app.v["edition"].get(), "2026")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
