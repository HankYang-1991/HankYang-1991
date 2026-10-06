import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from necalc import engine as E          # noqa: E402
from necalc import tables as T          # noqa: E402


class LookupTests(unittest.TestCase):
    def test_standard_ocpd(self):
        self.assertEqual(E.next_std_ocpd(15.0), 15)
        self.assertEqual(E.next_std_ocpd(15.1), 20)
        self.assertEqual(E.next_std_ocpd(162.5), 175)
        self.assertEqual(E.max_std_ocpd(225.5), 225)

    def test_temperature_correction(self):
        self.assertEqual(E.temp_factor(30, 90), 1.00)
        self.assertEqual(E.temp_factor(40, 90), 0.91)
        self.assertEqual(E.temp_factor(40, 75), 0.88)
        with self.assertRaises(E.CalcError):
            E.temp_factor(65, 60)

    def test_ccc_adjustment(self):
        self.assertEqual(E.ccc_factor(3), 1.0)
        self.assertEqual(E.ccc_factor(4), 0.8)
        self.assertEqual(E.ccc_factor(9), 0.7)
        self.assertEqual(E.ccc_factor(20), 0.5)
        self.assertEqual(E.ccc_factor(45), 0.35)

    def test_egc(self):
        self.assertEqual(E.egc_size(20), "12")
        self.assertEqual(E.egc_size(60), "10")
        self.assertEqual(E.egc_size(400), "3")
        self.assertEqual(E.egc_size(400, "al"), "1")
        self.assertEqual(E.egc_size(4000), "500")

    def test_motor_flc(self):
        self.assertEqual(E.motor_flc("50", 480, 3), 65)
        self.assertEqual(E.motor_flc("10", 208, 3), 30.8)
        self.assertEqual(E.motor_flc("1", 120, 1), 16)
        self.assertIsNone(E.motor_flc("1", 277, 1))


class ConductorTests(unittest.TestCase):
    def test_120v_20a_branch(self):
        w = E.WiringInput(voltage=120, wiring="1ph2w", length_ft=30, pf=1.0)
        r = E.design_general(1920, w, continuous_va=0)
        self.assertEqual(r.summary["ocpd"], 20)
        self.assertEqual(r.summary["size"], "12")
        self.assertEqual(r.summary["egc"], "12 AWG")
        self.assertIn('1/2', r.summary["conduit"])

    def test_continuous_125pct(self):
        w = E.WiringInput(voltage=120, wiring="1ph2w", length_ft=10, pf=1.0)
        r = E.design_general(1920, w)       # 16 A continuous -> 20 A design
        self.assertAlmostEqual(r.summary["i_design"], 20.0)
        self.assertEqual(r.summary["ocpd"], 20)

    def test_next_size_up_240_4_b(self):
        # 255 A design -> 300 A OCPD protects 250 kcmil (255 A @ 75 C)
        w = E.WiringInput(voltage=480, wiring="3ph3w", length_ft=10,
                          pf=0.9, sets=1)
        r = E.design_general(0, w, load_amps=255, continuous_va=0)
        self.assertEqual(r.summary["ocpd"], 300)
        self.assertEqual(r.summary["size"], "250")

    def test_parallel_sets(self):
        # 600 A continuous -> 750 A design -> 800 A OCPD, 2 x 500 kcmil
        w = E.WiringInput(voltage=480, wiring="3ph4w", length_ft=50, pf=0.9)
        r = E.design_general(1.0, w, load_amps=600)
        self.assertEqual(r.summary["ocpd"], 800)
        self.assertEqual(r.summary["sets"], 2)
        self.assertEqual(r.summary["size"], "500")
        self.assertEqual(r.summary["egc"], "1/0 AWG")

    def test_derating(self):
        # 12 AWG THHN, 9 CCC -> 30 x 0.7 = 21 A
        w = E.WiringInput(voltage=120, wiring="1ph2w", extra_ccc=7,
                          length_ft=10, pf=1.0)
        r = E.design_general(0, w, load_amps=16, continuous_va=0)
        self.assertEqual(r.summary["size"], "12")
        self.assertAlmostEqual(r.summary["ampacity"], 21.0)

    def test_voltage_drop_upsizing(self):
        w = E.WiringInput(voltage=120, wiring="1ph2w", length_ft=100, pf=1.0)
        r = E.design_general(1440, w)
        # 12 AWG -> 4.0 % ; 10 AWG -> 2.4 %
        self.assertEqual(r.summary["size"], "10")
        self.assertAlmostEqual(r.summary["vd_pct"], 2.4, places=2)
        # EGC increased proportionally from 14 AWG
        self.assertNotEqual(r.summary["egc"], "14 AWG")

    def test_voltage_drop_formula_3ph(self):
        vd, pct = E.voltage_drop(100, 200, "1/0", "cu", "PVC40", 0.85, 3, 480)
        r, x, _ = E.table9_impedance("1/0", "cu", "PVC40")
        z = r * 0.85 + x * math.sqrt(1 - 0.85 ** 2)
        self.assertAlmostEqual(vd, math.sqrt(3) * 100 * z * 0.2)

    def test_conduit_fill(self):
        c = E.select_conduit([(4, T.WIRE_AREA["THHN"]["12"])], "EMT")
        self.assertEqual(c["trade"], "1/2")
        c = E.select_conduit([(3, 0.7073), (1, 0.7073), (1, 0.1855)], "EMT")
        self.assertEqual(c["trade"], "3")


class MotorTests(unittest.TestCase):
    def test_50hp_480v(self):
        w = E.WiringInput(voltage=480, wiring="3ph3w", length_ft=100, pf=0.85)
        r = E.design_motor("50", w, device="itcb")
        s = r.summary
        self.assertEqual(s["flc"], 65)
        self.assertAlmostEqual(s["i_design"], 81.25)
        self.assertEqual(s["size"], "4")
        self.assertEqual(s["ocpd"], 175)          # 250 % -> 162.5 -> 175
        self.assertAlmostEqual(s["overload"], 81.25)
        self.assertEqual(s["egc"], "6 AWG")
        self.assertEqual(s["switch"], 100)        # 115 % x 65 = 74.75 A

    def test_fused_disconnect(self):
        w = E.WiringInput(voltage=480, wiring="3ph3w", length_ft=50)
        r = E.design_motor("50", w, device="td_fuse")
        self.assertEqual(r.summary["ocpd"], 125)   # 175 % x 65 = 113.75
        self.assertEqual(r.summary["switch"], 200)

    def test_td_fuse(self):
        w = E.WiringInput(voltage=480, wiring="3ph3w", length_ft=50)
        r = E.design_motor("10", w, device="td_fuse")
        self.assertEqual(r.summary["ocpd"], 25)    # 175 % x 14 = 24.5


class TransformerTests(unittest.TestCase):
    def test_lv_transformer_450_3_b(self):
        x = E.TransformerInput(kva=75, pri_v=480, sec_v=208, z_pct=4.5)
        sec = E.WiringInput(wiring="3ph4w", length_ft=10)
        pri = E.WiringInput(wiring="3ph3w", length_ft=50)
        r = E.design_transformer(x, sec_wiring=sec, pri_wiring=pri)
        s = r.summary
        self.assertAlmostEqual(s["i_pri"], 90.2, places=1)
        self.assertAlmostEqual(s["i_sec"], 208.2, places=1)
        self.assertEqual(s["pri_ocpd"], 125)
        self.assertEqual(s["pri_ocpd_max"], 225)
        self.assertEqual(s["sec_ocpd"], 300)
        self.assertIn("secondary", r.children)
        self.assertIn("primary", r.children)

    def test_mv_transformer_450_3_a(self):
        x = E.TransformerInput(kva=1500, pri_v=24900, sec_v=480, z_pct=5.75)
        r = E.design_transformer(x, mv=E.MVInput(fault_ka=5,
                                                 clear_time_s=0.2))
        s = r.summary
        self.assertAlmostEqual(s["i_pri"], 34.78, places=1)
        self.assertEqual(s["pri_ocpd_max"], 125)    # 300 % fuse -> 125E
        self.assertEqual(s["sec_ocpd"], 2500)
        mv = r.children["primary"].summary
        self.assertEqual(mv["size"], "1")           # 28 kV class min 1 AWG

    def test_lv_transformer_beyond_6000a(self):
        x = E.TransformerInput(kva=5000, pri_v=480, sec_v=208, z_pct=5.75)
        with self.assertRaises(E.CalcError) as cm:
            E.design_transformer(x, sec_wiring=E.WiringInput())
        self.assertEqual(cm.exception.key, "err_ocpd_range")

    def test_short_circuit_cmil(self):
        a = E.sc_min_cmil(10, 0.5, "cu", 90, 250)
        self.assertAlmostEqual(a, 98_280, delta=50)


class MVCableTests(unittest.TestCase):
    def test_fault_governs(self):
        m = E.MVInput(amps=40, fault_ka=25, clear_time_s=0.5)
        r = E.design_mv_cable(m)
        # 25 kA, 0.5 s -> ~245,700 cmil -> 250 kcmil
        self.assertEqual(r.summary["size"], "250")

    def test_conductor_protection_240_101(self):
        m = E.MVInput(amps=20, fault_ka=1, clear_time_s=0.1,
                      ocpd_type="fuse", ocpd_amps=400)
        r = E.design_mv_cable(m)
        self.assertGreaterEqual(3 * r.summary["ampacity"], 400)


if __name__ == "__main__":
    unittest.main()
