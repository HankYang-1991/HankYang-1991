"""Example: 24.9 kV utility service down to 120 V branch circuits.

    24.9 kV  --[2500 kVA, Z 5.75 %]--> 480Y/277 V switchboard
             (secondary as cable, then as a 4000 A busway)
    480 V    --[75 kVA, Z 4.5 %]-----> 208Y/120 V panel LP-1
    LP-1 load calculation -> feeder, then sample 120 V branch circuits,
    a 480 V motor, and the cable tray that carries the 480 V feeders.

Run:  python examples/system_24900_to_120.py [en|zh] [2023|2026]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from necalc import engine as E, loads as L, tray as TR, report as R  # noqa

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
ed = sys.argv[2] if len(sys.argv) > 2 else "2023"


def show(title, res):
    print(R.to_text(res, lang, title=title))
    print()


# 1. Unit substation 24.9 kV -> 480Y/277 V
x = E.TransformerInput(kva=2500, pri_v=24900, sec_v=480, z_pct=5.75,
                       pri_device="fuse", sec_device="cb", edition=ed)
mv = E.MVInput(fault_ka=12.5, clear_time_s=0.3, insulation_level="25kV_133",
               conduit_type="PVC40", edition=ed)
sec = E.WiringInput(wiring="3ph4w", length_ft=30, conduit_type="RMC",
                    max_size="600", vd_limit_pct=1.0, edition=ed)
show("2500 kVA 24.9 kV - 480Y/277 V", E.design_transformer(x, sec, mv=mv))

# 1b. Same transformer with a feeder busway to the switchboard (Art. 368)
bus = E.WiringInput(wiring="3ph4w", length_ft=60, method="busway",
                    bw_neutral="n200", vd_limit_pct=1.0, edition=ed)
show("2500 kVA secondary busway", E.design_transformer(
    x, bus, mv=E.MVInput(**vars(mv))).children["secondary"])

# 2. Dry-type transformer 480 V -> 208Y/120 V
x2 = E.TransformerInput(kva=75, pri_v=480, sec_v=208, z_pct=4.5,
                        lv_scheme="pri_sec", edition=ed)
show("75 kVA 480 V - 208Y/120 V", E.design_transformer(
    x2, sec_wiring=E.WiringInput(wiring="3ph4w", length_ft=15, edition=ed),
    pri_wiring=E.WiringInput(wiring="3ph3w", length_ft=120, edition=ed)))

# 3. Panel LP-1 load calculation (PF, demand factor, diversity factor)
panel = L.Panel(name="LP-1", system="208Y/120", diversity=1.1, edition=ed,
                loads=[
    L.Load("Lighting", "lighting", 12, 600, "VA", 0.95, voltage=120,
           continuous=True),
    L.Load("Receptacles", "receptacle", 60, 180, "VA", 0.9, voltage=120),
    L.Load("EF-1", "motor", 2, 1, "HP", 0.8, voltage=208, phases=3),
    L.Load("Unit heater", "heating", 2, 5, "kW", 1.0, voltage=208),
])
calc = L.calculate(panel)
for a, b in R.load_summary_rows(calc, lang):
    print(f"  {R.dpad(a, 38)}{b}")
for n in R.load_notes(calc, lang):
    print("  *", n)
print()
show("LP-1 feeder", L.size_feeder(panel, calc,
                                  E.WiringInput(length_ft=80, edition=ed)))

# 4. 120 V branch circuits: lighting, receptacles, heater
br = E.WiringInput(voltage=120, wiring="1ph2w", length_ft=120, pf=0.95,
                   edition=ed)
show("120 V lighting circuit (1,440 VA continuous)",
     E.design_general(1440, br))
show("120 V receptacle circuit (180 VA x 8, non-continuous)",
     E.design_general(1440, br, continuous_va=0))

# 5. 480 V motor
show("30 HP 480 V motor", E.design_motor(
    "30", E.WiringInput(voltage=480, wiring="3ph3w", length_ft=200, pf=0.85,
                        edition=ed), device="itcb"))

# 6. Cable tray for 480 V feeders + 24.9 kV cables (with barrier)
t = TR.TrayInput(tray_type="ladder", depth_in=4, edition=ed, cables=[
    TR.TrayCable("MSB-F1 (2 sets)", "lv_multi", "500", 3, 2),
    TR.TrayCable("MSB-F2", "lv_multi", "4/0", 4, 1),
    TR.TrayCable("Branch", "lv_multi", "10", 3, 10),
    TR.TrayCable("24.9 kV", "mv_single", "1/0", 1, 3),
])
show("Cable tray", TR.design_tray(t))
