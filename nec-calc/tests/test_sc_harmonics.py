import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from necalc import shortcircuit as SC   # noqa: E402
from necalc import harmonics as HM      # noqa: E402
from necalc import engine as E          # noqa: E402


class ShortCircuitTests(unittest.TestCase):
    def test_transformer_infinite_bus(self):
        # 2500 kVA 480 V Z 5.75 %, infinite source, no tolerance
        r = SC.design_shortcircuit(
            SC.SCSource(z_tol=False),
            [SC.SCSegment("MSB", "xfmr", kva=2500, z_pct=5.75, xr=8,
                          sec_v=480)])
        fla = 2500e3 / (math.sqrt(3) * 480)
        self.assertAlmostEqual(r.summary["buses"][0]["isc_ka"],
                               fla / 0.0575 / 1000, places=6)

    def test_tolerance_and_motor(self):
        r = SC.design_shortcircuit(
            SC.SCSource(z_tol=True),
            [SC.SCSegment("MSB", "xfmr", kva=2500, z_pct=5.75, xr=8,
                          sec_v=480, motor_a=500)])
        b = r.summary["buses"][0]
        fla = 2500e3 / (math.sqrt(3) * 480)
        self.assertAlmostEqual(b["isc_ka"], fla / (0.0575 * 0.9) / 1000)
        self.assertAlmostEqual(b["motor_ka"], 2.0)

    def test_utility_source_reduces_fault(self):
        segs = [SC.SCSegment("MSB", "xfmr", kva=2500, z_pct=5.75, xr=8,
                             sec_v=480)]
        inf = SC.design_shortcircuit(SC.SCSource(), segs)
        fin = SC.design_shortcircuit(SC.SCSource(fault_ka=10, xr=15),
                                     segs)
        self.assertLess(fin.summary["max_fault_ka"],
                        inf.summary["max_fault_ka"])

    def test_asymmetry_factors(self):
        # X/R at or below the test X/R -> no adjustment
        self.assertEqual(SC.asym_factor(4.9, "mccb", 65), 1.0)
        # IEEE 1015 peak ratio for MCCB > 20 kA, X/R 10
        mf = (1 + math.exp(-math.pi / 10)) / (1 + math.exp(-math.pi / 4.9))
        self.assertAlmostEqual(SC.asym_factor(10, "mccb", 65), mf)
        # LVPCB rms ratio, test X/R 6.59
        mf = (math.sqrt(1 + 2 * math.exp(-2 * math.pi / 8)) /
              math.sqrt(1 + 2 * math.exp(-2 * math.pi / 6.59)))
        self.assertAlmostEqual(SC.asym_factor(8, "lvpcb", 65), mf)
        # MCCB rated <= 10 kA is tested at X/R 1.73
        self.assertEqual(SC.device_test_xr("mccb", 10), 1.73)

    def test_required_and_selected_aic(self):
        r = SC.design_shortcircuit(
            SC.SCSource(),
            [SC.SCSegment("MSB", "xfmr", kva=2500, z_pct=5.75, xr=8,
                          sec_v=480, device="lvpcb", aic_ka=42)])
        b = r.summary["buses"][0]
        self.assertEqual(b["required_ka"], 65)
        self.assertFalse(b["ok"])

    def test_downstream_cable_and_transformer(self):
        r = SC.design_shortcircuit(
            SC.SCSource(),
            [SC.SCSegment("MSB", "xfmr", kva=2500, z_pct=5.75, xr=8,
                          sec_v=480),
             SC.SCSegment("DP", "cable", length_ft=200, size="500", sets=2),
             SC.SCSegment("T1", "xfmr", kva=75, z_pct=4.5, xr=3,
                          sec_v=208)])
        ka = [b["total_ka"] for b in r.summary["buses"]]
        self.assertGreater(ka[0], ka[1])
        self.assertLess(ka[2], 75e3 / (math.sqrt(3) * 208) / 0.0405 / 1000)

    def test_mv_cable_rejected(self):
        with self.assertRaises(E.CalcError):
            SC.design_shortcircuit(SC.SCSource(),
                                   [SC.SCSegment("X", "cable")])


class HarmonicsTests(unittest.TestCase):
    def _x(self, **kw):
        d = dict(voltage=480, isc_ka=52.3, linear_a=400, drives=[
            HM.HarmDrive("AHU", 4, 50, "6p"),
            HM.HarmDrive("CHWP", 3, 75, "6p_ac3"),
            HM.HarmDrive("CT", 2, 40, "6p_dc")])
        d.update(kw)
        return HM.HarmInput(**d)

    def test_ieee519_limit_rows(self):
        self.assertEqual(HM.ieee519_current_limits(10)[1], 5.0)
        self.assertEqual(HM.ieee519_current_limits(20)[1], 8.0)
        self.assertEqual(HM.ieee519_current_limits(58)[1], 12.0)
        self.assertEqual(HM.ieee519_current_limits(500)[1], 15.0)
        self.assertEqual(HM.ieee519_current_limits(2000)[1], 20.0)
        ind = HM.ieee519_current_limits(58)[0]
        self.assertEqual(HM.individual_limit(5, ind), 10.0)
        self.assertEqual(HM.individual_limit(11, ind), 4.5)
        self.assertEqual(HM.individual_limit(37, ind), 0.7)
        self.assertEqual(HM.voltage_limits(480), (5.0, 8.0))
        self.assertEqual(HM.voltage_limits(4160), (3.0, 5.0))

    def test_single_drive_tdd_equals_thdi(self):
        x = HM.HarmInput(voltage=480, isc_ka=50, drives=[
            HM.HarmDrive("D", 1, 100, "6p_ac3")])
        a = HM.analyze(x)
        self.assertAlmostEqual(a["tdd"], HM.spectrum_thd("6p_ac3"))

    def test_thd_override_scales_spectrum(self):
        x = HM.HarmInput(voltage=480, isc_ka=50, drives=[
            HM.HarmDrive("D", 1, 100, "6p", thd_pct=40.0)])
        self.assertAlmostEqual(HM.analyze(x)["tdd"], 40.0)

    def test_design_and_ahf(self):
        r = HM.design_harmonics(self._x())
        s = r.summary
        self.assertFalse(s["compliant"])
        self.assertEqual(s["tdd_limit"], 12.0)
        self.assertEqual(s["ahf_text"], "200 A")
        step = [st for st in r.steps if st.key == "st_h_ahf"][0]
        self.assertLessEqual(step.params["tdd"], 0.9 * 12.0 + 1e-9)
        codes = {o["code"]: o["ok"] for o in s["options"]}
        self.assertFalse(codes["mit_ac5"])
        self.assertTrue(codes["mit_18p"])

    def test_k_factor_linear_only(self):
        x = HM.HarmInput(voltage=480, isc_ka=50, drives=[
            HM.HarmDrive("D", 1, 10, "afe")], linear_a=1000)
        self.assertAlmostEqual(HM.analyze(x)["k"], 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
