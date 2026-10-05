import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from necalc import engine as E          # noqa: E402
from necalc import loads as L           # noqa: E402
from necalc import tray as TR           # noqa: E402
from necalc import report as R          # noqa: E402
from necalc.i18n import TEXT, tr        # noqa: E402


class LoadCalcTests(unittest.TestCase):
    def test_receptacle_demand(self):
        p = L.Panel(loads=[L.Load("R", "receptacle", 80, 180, "VA", 1.0)])
        c = L.calculate(p)
        self.assertAlmostEqual(c["connected"]["kva_arith"], 14.4)
        self.assertAlmostEqual(c["demand"]["kva"], 12.2)

    def test_noncoincident(self):
        p = L.Panel(loads=[
            L.Load("H", "heating", 1, 10, "kW", 1.0, voltage=208, phases=3),
            L.Load("C", "cooling", 1, 6, "kVA", 0.9, voltage=208, phases=3)])
        c = L.calculate(p)
        self.assertAlmostEqual(c["demand"]["kva"], 10.0)

    def test_pf_and_diversity(self):
        p = L.Panel(diversity=1.25, loads=[
            L.Load("M", "equipment", 1, 100, "kVA", 0.8, voltage=480,
                   phases=3)], system="480Y/277")
        c = L.calculate(p)
        self.assertAlmostEqual(c["connected"]["kw"], 80.0)
        self.assertAlmostEqual(c["connected"]["kvar"], 60.0)
        self.assertAlmostEqual(c["coincident"]["kva"], 80.0)
        # capacitor to 0.95: 64 kW x (0.75 - 0.3287)
        self.assertAlmostEqual(c["cap_kvar"], 64 * (0.75 - 0.32868), places=1)

    def test_continuous_and_motor_adders(self):
        p = L.Panel(loads=[
            L.Load("Lt", "lighting", 1, 10, "kVA", 1.0, voltage=208,
                   phases=3, continuous=True),
            L.Load("M", "motor", 1, 10, "HP", 0.85, voltage=208, phases=3)])
        c = L.calculate(p)
        m = 30.8 * 208 * 3 ** 0.5 / 1000
        self.assertAlmostEqual(c["design_kva"], 10 * 1.25 + m * 1.25,
                               places=3)

    def test_phase_balance(self):
        p = L.Panel(loads=[L.Load("Lt", "lighting", 3, 1000, "VA", 1.0)])
        c = L.calculate(p)
        a = c["phase_amps"]
        self.assertAlmostEqual(a["A"], a["B"])
        self.assertAlmostEqual(c["imbalance_pct"], 0.0)

    def test_feeder(self):
        p = L.Panel(loads=[L.Load("Lt", "lighting", 1, 30, "kVA", 1.0,
                                  voltage=208, phases=3, continuous=True)])
        c = L.calculate(p)
        f = L.size_feeder(p, c, E.WiringInput(length_ft=50))
        self.assertEqual(f.summary["ocpd"], 110)   # 83.3 A x 1.25 = 104 A

    def test_roundtrip(self):
        p = L.Panel(loads=[L.Load("Lt", "lighting")])
        q = L.Panel.from_dict(p.to_dict())
        self.assertEqual(q.loads[0].name, "Lt")


class TrayTests(unittest.TestCase):
    def test_small_multiconductor_ladder(self):
        # 12 AWG 3/C TC (0.48 in OD): 7.0 in2 / 0.181 in2 = 38 in 6 in ladder
        self.assertEqual(TR.max_cables("lv_multi", "12", 6), 38)
        self.assertEqual(TR.max_cables("lv_multi", "12", 6,
                                       tray_type="solid_bottom"), 30)

    def test_large_multiconductor_single_layer(self):
        # 4/0 3/C (1.60 in): sum of diameters <= width
        self.assertEqual(TR.max_cables("lv_multi", "4/0", 24), 15)
        # solid bottom: 90 % of width
        self.assertEqual(TR.max_cables("lv_multi", "4/0", 24,
                                       tray_type="solid_bottom"), 13)

    def test_single_conductor_rules(self):
        self.assertEqual(TR.max_cables("lv_single", "250", 6), 16)
        self.assertEqual(TR.max_cables("lv_single", "1/0", 6), 12)
        self.assertEqual(TR.max_cables("lv_single", "2", 24), 0)

    def test_mv_single_layer(self):
        self.assertEqual(TR.max_cables("mv_single", "1/0", 12), 10)

    def test_mixed_mv_lv_barrier(self):
        x = TR.TrayInput(cables=[
            TR.TrayCable("F", "lv_multi", "4/0", 3, 3),
            TR.TrayCable("MV", "mv_single", "1/0", 1, 3)])
        r = TR.design_tray(x)
        self.assertTrue(any(k == "w_tray_mv_lv" for k, _ in r.warnings))
        self.assertAlmostEqual(r.summary["req_width"], 3 * 1.60 + 3 * 1.18)
        self.assertEqual(r.summary["width"], 9)

    def test_mixed_multiconductor_col2(self):
        x = TR.TrayInput(cables=[
            TR.TrayCable("L", "lv_multi", "4/0", 3, 2),
            TR.TrayCable("S", "lv_multi", "12", 3, 20)])
        total, _, _ = TR.required_width(x)
        sd = 2 * 1.60
        a = 20 * 3.14159265 * 0.48 ** 2 / 4
        # col 1 value needed = a + 1.2 sd ; col1 = 7/6 W
        self.assertAlmostEqual(total, (a + 1.2 * sd) * 6 / 7, places=3)

    def test_ampacity_factors(self):
        x = TR.TrayInput(covered=True)
        c = TR.TrayCable("S", "lv_single", "500", 1, 3)
        a, d = TR.tray_ampacity(c, x)
        self.assertAlmostEqual(a, 700 * 0.60)
        x.covered = False
        x.arrangement = "spaced"
        a, _ = TR.tray_ampacity(c, x)
        self.assertAlmostEqual(a, 700)

    def test_specified_width(self):
        x = TR.TrayInput(width_in=12, cables=[
            TR.TrayCable("F", "lv_multi", "4/0", 3, 10)])
        r = TR.design_tray(x)
        chk = [s for s in r.steps if s.key == "st_tray_check"][0]
        self.assertFalse(chk.ok)


class I18nTests(unittest.TestCase):
    def _results(self):
        out = []
        for ed in ("2023", "2026"):
            w = E.WiringInput(voltage=120, wiring="1ph2w", length_ft=200,
                              pf=0.9, edition=ed)
            out.append(E.design_general(1800, w, ocpd=20))
            w = E.WiringInput(voltage=480, wiring="3ph3w", edition=ed)
            out.append(E.design_motor("25", w, device="inst_cb"))
            x = E.TransformerInput(kva=2500, pri_v=24900, sec_v=480,
                                   edition=ed, pri_device="cb")
            out.append(E.design_transformer(
                x, sec_wiring=E.WiringInput(edition=ed)))
            x = E.TransformerInput(kva=45, pri_v=480, sec_v=208, z_pct=3.5,
                                   lv_scheme="pri_only", edition=ed)
            out.append(E.design_transformer(
                x, sec_wiring=E.WiringInput(edition=ed),
                pri_wiring=E.WiringInput(wiring="3ph3w", edition=ed)))
            out.append(E.design_mv_cable(E.MVInput(edition=ed, ocpd_amps=65)))
            out.append(TR.design_tray(TR.TrayInput(edition=ed, cables=[
                TR.TrayCable("A", "lv_multi", "500", 3, 2),
                TR.TrayCable("B", "lv_single", "1000", 1, 3),
                TR.TrayCable("C", "lv_single", "350", 1, 3),
                TR.TrayCable("D", "mv_multi", "4/0", 3, 1),
                TR.TrayCable("E", "control", "14", 3, 4)])))
        return out

    def test_all_keys_translated(self):
        for res in self._results():
            items = [res] + list(res.children.values())
            for r in items:
                for s in r.steps:
                    self.assertIn(s.key, TEXT, s.key)
                    for lang in ("en", "zh"):
                        txt = tr(s.key, lang, **s.params)
                        self.assertNotIn("{", txt, (s.key, txt))
                for k, p in r.warnings:
                    self.assertIn(k, TEXT, k)
                    for lang in ("en", "zh"):
                        self.assertNotIn("{", tr(k, lang, **p))

    def test_edition_references(self):
        r23 = E.design_mv_cable(E.MVInput(edition="2023", ocpd_amps=65))
        r26 = E.design_mv_cable(E.MVInput(edition="2026", ocpd_amps=65))
        refs23 = {s.ref for s in r23.steps}
        refs26 = {s.ref for s in r26.steps}
        self.assertIn("240.101(A)", refs23)
        self.assertIn("Article 245", refs26)

    def test_reports(self):
        res = self._results()
        for lang in ("en", "zh"):
            html = R.to_html([("x", r) for r in res], lang, "2026")
            self.assertIn("<table>", html)
            txt = R.to_text(res[0], lang, title="t")
            self.assertTrue(txt)
        p = L.Panel(loads=[L.Load("R", "receptacle", 80, 180, "VA", 1.0)])
        c = L.calculate(p)
        self.assertIn("R", R.load_calc_csv(p, c, "zh"))


if __name__ == "__main__":
    unittest.main()
