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

    def test_live_workflow(self):
        """Edits recalculate by themselves; bad input keeps the last valid
        result marked as stale; projects save / open / restore."""
        import json
        import shutil
        import tempfile
        from unittest import mock
        from necalc import gui as G
        d = tempfile.mkdtemp()
        root = tk.Tk()
        try:
            self.assertEqual(G._num_value("1,500"), 1500.0)
            self.assertEqual(G._num_value("1-1/2"), 1.5)
            for bad in ("abc", "1/0", "nan", "2-3"):
                with self.assertRaises(ValueError):
                    G._num_value(bad)
            app = G.App(root)
            # every calculation tab has a result at start-up
            for key in G.TAB_KEYS:
                self.assertIn(key, app.results, key)
            self.assertFalse(app.modified)
            self.assertEqual(app.changed_tabs(), set())
            # live update without pressing Calculate
            app.v["br.value"].set("9600")
            app.flush()
            self.assertEqual(app.results["br"][1].summary["ocpd"], 100)
            self.assertTrue(app.modified)
            self.assertTrue(app.root.title().startswith("*"))
            self.assertIn("100 A", app.heads["br"][0].cget("text"))
            self.assertEqual(app.changed_tabs(), {"br"})
            # invalid text: red field, last result kept and marked stale
            app.v["br.value"].set("96x0")
            app.flush()
            self.assertIn("br", app.stale)
            self.assertEqual(app.results["br"][1].summary["ocpd"], 100)
            w, style = app._entries["br.value"][0]
            self.assertEqual(str(w.cget("style")), "Bad.TEntry")
            app.v["br.value"].set("1440")
            app.flush()
            self.assertNotIn("br", app.stale)
            self.assertEqual(str(w.cget("style")), "TEntry")
            # MV inputs also refresh the transformer (24.9 kV primary)
            app.v["mv.mat"].set("al")
            self.assertIn("xf", app._pending)
            app.flush()
            # list editors: harmonic drive with a fractional HP
            app.v["hm.e.hp"].set("1/2")
            app._lst_action("hm", "add")
            self.assertEqual(app.harm_drives[-1].hp, 0.5)
            app.flush()
            self.assertIn("hm", app.results)
            # the selected load row survives a live update
            app.nb.select(5)
            app.load_tv.selection_set("2")
            root.update()
            app.v["lc.l.name"].set("edited, not applied")
            app.v["lc.div"].set("1.1")
            app.flush()
            root.update()
            self.assertEqual(app.load_tv.selection(), ("2",))
            self.assertEqual(app.v["lc.l.name"].get(), "edited, not applied")
            app.v["lc.div"].set("1.0")
            app.flush()
            # copy the results
            app.copy_results("br")
            self.assertIn("A", root.clipboard_get())
            # save / open / new
            proj = os.path.join(d, "job.json")
            self.assertTrue(app.save_project(proj))
            self.assertFalse(app.modified)
            self.assertIn("job.json", app.root.title())
            app.v["br.value"].set("2000")
            app.flush()
            with mock.patch("necalc.gui.messagebox.askyesnocancel",
                            return_value=False):
                app.new_project()
            self.assertIsNone(app.project_path)
            self.assertEqual(app.v["br.value"].get(), "1440")
            self.assertFalse(app.modified)
            app.open_project(proj)
            self.assertEqual(app.project_path, proj)
            self.assertEqual(app.v["br.value"].get(), "1440")
            self.assertIn("hm", app.changed_tabs())
            # Ctrl+S saves to the same file without asking
            app.v["mo.hp"].set("25")
            app.flush()
            with mock.patch("necalc.gui.filedialog.asksaveasfilename") as ask:
                self.assertTrue(app.save_project())
                ask.assert_not_called()
            with open(proj, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["vars"]["mo.hp"], "25")
            # report: only the chosen tabs
            rep = os.path.join(d, "r.html")
            app.export_html(path=rep, keys=["br", "mo"])
            with open(rep, encoding="utf-8") as fh:
                html = fh.read()
            self.assertIn(app.t("tab_motor"), html)
            self.assertNotIn(app.t("tab_harm"), html)
            # session: closing never loses work
            with mock.patch.dict(os.environ, {"APPDATA": d}):
                app.v["xf.kva"].set("2000")
                app.flush()
                self.assertTrue(app.save_session())
                root2 = tk.Toplevel(root)
                app2 = G.App(root2, session=True)
                self.assertEqual(app2.v["xf.kva"].get(), "2000")
                self.assertEqual(app2.project_path, proj)
                self.assertTrue(app2.modified)
                self.assertIn("xf", app2.results)
        finally:
            root.destroy()
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
