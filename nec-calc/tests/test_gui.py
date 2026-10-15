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
                app.calc_sc()
                app.calc_harm()
                for key in ("br", "mo", "xf", "mv", "tr", "lc", "sc", "hm"):
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
                app.v["xf.pri_v"].set("480")
                app.v["xf.sec_v"].set("208")
                app.v["xf.kva"].set("1000")
                app.v["xf.pri_method"].set("busway")
                app.calc_xfmr()
                prim = app.results["xf"][1].children["primary"].summary
                self.assertEqual(prim["bw_rating"], 1600)
                app.v["xf.pri_v"].set("24900")
                app.v["xf.sec_v"].set("480")
                app.v["xf.kva"].set("1500")
                app.v["xf.pri_method"].set("cable")
                app.calc_capacity()
                self.assertIn("tr", app.results)
            app.v["edition"].set("2026")
            app.on_edition()
            d = app.project_dict()
            app.load_project_dict(d)
            self.assertEqual(app.v["edition"].get(), "2026")
        finally:
            root.destroy()

    def test_panels_excel(self):
        import shutil
        import tempfile
        from unittest import mock
        from necalc import panel_io as PIO
        from necalc.gui import App
        d = tempfile.mkdtemp()
        root = tk.Tk()
        try:
            app = App(root)
            with mock.patch("necalc.gui.messagebox.showinfo"), \
                    mock.patch("necalc.gui.messagebox.askyesno",
                               return_value=True):
                tpl = os.path.join(d, "tpl.xlsx")
                app.export_template(tpl)
                app.import_excel(tpl, replace=True)
                self.assertEqual([p.name for p in app.panels],
                                 ["LP-1", "DP-1"])
                self.assertIn("lc", app.results)
                self.assertEqual(app.v["lc.name"].get(), "LP-1")
                app.panel_select(1)
                self.assertEqual(app.v["lc.system"].get(), "480Y/277")
                self.assertEqual(app.v["lc.flen"].get(), "150")
                app.calc_feeder()
                self.assertEqual(
                    app.results["lc"][1].__name__, "draw")
                app.panel_new()
                self.assertEqual(len(app.panels), 3)
                app.v["lc.name"].set("LP-NEW")
                self.assertEqual(app.panels[2].name, "LP-NEW")
                app.load_example()
                app.calc_all()
                out = os.path.join(d, "out.xlsx")
                app.export_excel(out)
                panels, notes = PIO.read_panels(out)
                self.assertEqual([p.name for p in panels],
                                 ["LP-1", "DP-1", "LP-NEW"])
                app.panel_delete()
                self.assertEqual(len(app.panels), 2)
                # merge: same names are replaced, new names added
                app.import_excel(out, replace=False)
                self.assertEqual([p.name for p in app.panels],
                                 ["LP-1", "DP-1", "LP-NEW"])
                for lang in ("zh", "en"):
                    app.v["lang"].set(lang)
                    app.on_lang()
                    self.assertIn("lc", app.results)
                app.on_edition()
                pd = app.project_dict()
                app.load_project_dict(pd)
                self.assertEqual(len(app.panels), 3)
                # version-1 project files hold one panel in the vars
                pd1 = {"vars": pd["vars"], "panel_loads": pd["panel_loads"]}
                app.load_project_dict(pd1)
                self.assertEqual(len(app.panels), 1)
                self.assertEqual(app.panels[0].name, app.v["lc.name"].get())
        finally:
            root.destroy()
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
