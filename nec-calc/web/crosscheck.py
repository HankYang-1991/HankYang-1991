"""Generate randomized cases, run them through the Python engine and write
the results to crosscheck_cases.json.  web/crosscheck.js then runs the same
cases through the JavaScript port (necalc.js) and compares the outputs.

    python web/crosscheck.py [n_per_kind] && node web/crosscheck.js
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from necalc import engine as E, loads as L, tray as TR, report as R  # noqa
from necalc import tables as T  # noqa: E402
from necalc.i18n import tr  # noqa: E402

LANGS = ("en", "zh")


def ser_result(res):
    out = {
        "kind": res.kind,
        "summary": res.summary,
        "steps": [{"key": s.key, "ref": s.ref, "ok": s.ok, "params": s.params,
                   "text": {lg: tr(s.key, lg, **s.params) for lg in LANGS}}
                  for s in res.steps],
        "warnings": [{"key": k, "params": p,
                      "text": {lg: tr(k, lg, **p) for lg in LANGS}}
                     for k, p in res.warnings],
        "summary_rows": {lg: [list(r) for r in R.summary_rows(res, lg)]
                         for lg in LANGS},
        "children": {k: ser_result(v) for k, v in res.children.items()},
    }
    return out


def run(fn):
    try:
        return {"ok": fn()}
    except E.CalcError as e:
        return {"error": e.key, "params": e.params}


def rnd_wiring(rng, voltage=None, wiring=None):
    v = voltage or rng.choice([120, 208, 240, 277, 480])
    if wiring is None:
        if v in (120, 277):
            wiring = "1ph2w"
        else:
            wiring = rng.choice(["1ph2w", "1ph3w", "3ph3w", "3ph4w"])
    return dict(
        voltage=v, wiring=wiring, material=rng.choice(["cu", "cu", "al"]),
        insulation=rng.choice(["THHN", "XHHW"]),
        term_temp=rng.choice([60, 75, 75, 90]),
        ambient_c=rng.choice([10, 20, 30, 30, 35, 40, 45, 50, 58]),
        extra_ccc=rng.choice([0, 0, 0, 1, 3, 6, 12]),
        neutral_ccc=rng.random() < 0.3,
        sets=rng.choice([0, 0, 0, 1, 2, 3]),
        max_size=rng.choice(["250", "350", "500", "600", "750"]),
        length_ft=round(rng.uniform(5, 900), 1),
        pf=round(rng.uniform(0.6, 1.0), 2),
        vd_limit_pct=rng.choice([0, 2, 3, 3, 5]),
        conduit_type=rng.choice(["EMT", "IMC", "RMC", "PVC40", "PVC80"]),
        min_size=rng.choice(["14", "12", "12", "10"]),
        edition=rng.choice(["2023", "2026"]),
        method=rng.choice(["cable", "cable", "busway"]),
        bw_type=rng.choice(["bw_feeder", "bw_plugin"]),
        bw_neutral=rng.choice(["n100", "n200"]),
        bw_ground=rng.choice(["g_int50", "g_housing"]),
        bw_load=rng.choice(["concentrated", "distributed"]),
        bw_rating=rng.choice([0, 0, 0, 0, 800, 2500, 4000]),
        bw_r=rng.choice([0, 0, 0, 0.5]), bw_x=rng.choice([0, 0, 0.2]),
        bw_sccr=rng.choice([0, 0, 65, 100]),
        fault_ka=rng.choice([0, 0, 25.0, 65.0, 120.0]))


def case_general(rng):
    w = rnd_wiring(rng)
    use_amps = rng.random() < 0.3
    load_va = 0.0 if use_amps else round(rng.uniform(100, 450000), 1)
    args = dict(load_va=load_va, w=w,
                continuous_va=(None if rng.random() < 0.4 else
                               round(load_va * rng.random(), 1)),
                ocpd=(None if rng.random() < 0.7 else
                      rng.choice(T.STANDARD_OCPD[:20])),
                kind=rng.choice(["branch", "feeder"]),
                largest_motor_va=rng.choice([0, 0, 5000, 20000]),
                load_amps=(round(rng.uniform(1, 1200), 1) if use_amps
                           else None))
    a = dict(args)
    wi = E.WiringInput(**a.pop("w"))
    return "design_general", args, run(
        lambda: ser_result(E.design_general(a.pop("load_va"), wi, **a)))


def case_motor(rng):
    v, wiring = rng.choice([(115, "1ph2w"), (120, "1ph2w"), (208, "1ph2w"),
                            (230, "1ph2w"), (208, "3ph3w"), (230, "3ph3w"),
                            (240, "3ph3w"), (460, "3ph3w"), (480, "3ph3w"),
                            (575, "3ph3w"), (600, "3ph3w"), (277, "1ph2w")])
    w = rnd_wiring(rng, v, wiring)
    args = dict(hp=rng.choice(T.MOTOR_HP), w=w,
                device=rng.choice(["itcb", "td_fuse", "ntd_fuse", "inst_cb"]),
                nameplate_fla=(None if rng.random() < 0.6 else
                               round(rng.uniform(1, 300), 1)),
                sf_115=rng.random() < 0.6, design_b_ee=rng.random() < 0.3,
                flc_override=(None if rng.random() < 0.85 else
                              round(rng.uniform(1, 300), 1)))
    a = dict(args)
    wi = E.WiringInput(**a.pop("w"))
    return "design_motor", args, run(
        lambda: ser_result(E.design_motor(a.pop("hp"), wi, **a)))


def rnd_mv(rng):
    return dict(kv=rng.choice([4.16, 12.47, 13.8, 24.9, 24.9, 34.5, 46]),
                amps=round(rng.uniform(5, 450), 1),
                material=rng.choice(["cu", "al"]),
                insulation_level=rng.choice(["25kV_100", "25kV_133",
                                             "35kV_100"]),
                fault_ka=round(rng.uniform(1, 40), 1),
                clear_time_s=rng.choice([0.05, 0.1, 0.2, 0.5, 1.0]),
                t_oper=90.0, t_sc=rng.choice([250.0, 200.0]),
                ocpd_type=rng.choice(["fuse", "relay"]),
                ocpd_amps=rng.choice([0, 0, 40, 100, 200, 400, 1200]),
                design_factor=rng.choice([1.0, 1.25]),
                conduit_type=rng.choice(["PVC40", "PVC80", "RMC"]),
                cable_od_in=rng.choice([0, 0, 1.25, 1.6]),
                include_egc=rng.random() < 0.8,
                edition=rng.choice(["2023", "2026"]))


def case_mv(rng):
    args = dict(m=rnd_mv(rng))
    return "design_mv_cable", args, run(
        lambda: ser_result(E.design_mv_cable(E.MVInput(**args["m"]))))


def case_xfmr(rng):
    pri = rng.choice([24900, 13800, 12470, 4160, 480, 480, 208])
    sec = rng.choice([v for v in (4160, 480, 240, 208, 120) if v < pri])
    phases = rng.choice([3, 3, 1])
    kva = rng.choice(T.XFMR_KVA_3PH if phases == 3 else T.XFMR_KVA_1PH)
    x = dict(kva=kva, pri_v=pri, sec_v=sec, phases=phases,
             z_pct=round(rng.uniform(1.5, 10.5), 2),
             location=rng.choice(["any", "supervised"]),
             pri_device=rng.choice(["fuse", "cb"]),
             sec_device=rng.choice(["fuse", "cb"]),
             lv_scheme=rng.choice(["pri_sec", "pri_only"]),
             edition=rng.choice(["2023", "2026"]))
    sw = rnd_wiring(rng, sec, "3ph4w" if phases == 3 else "1ph3w")
    sw["max_size"] = rng.choice(["500", "600", "750"])
    pw = rnd_wiring(rng, pri, "3ph3w" if phases == 3 else "1ph2w")
    args = dict(x=x, sec=sw if rng.random() < 0.9 else None,
                pri=pw if rng.random() < 0.8 else None,
                mv=rnd_mv(rng) if rng.random() < 0.7 else None)

    def go():
        return ser_result(E.design_transformer(
            E.TransformerInput(**x),
            E.WiringInput(**args["sec"]) if args["sec"] else None,
            E.WiringInput(**args["pri"]) if args["pri"] else None,
            E.MVInput(**args["mv"]) if args["mv"] else None))
    return "design_transformer", args, run(go)


def rnd_load(rng):
    unit = rng.choice(L.UNITS)
    cat = rng.choice(L.CATEGORIES)
    phases = rng.choice([1, 1, 3])
    v = rng.choice([120, 208, 240, 277, 480]) if phases == 1 else \
        rng.choice([208, 480, 240])
    if unit == "HP":
        rating = rng.choice([0.5, 1, 1.5, 2, 3, 5, 7.5, 10, 15, 25, 50, 12.5])
    else:
        rating = round(rng.uniform(0.2 if unit in ("kVA", "kW") else 50,
                                   60 if unit in ("kVA", "kW") else 9000), 2)
    return dict(name=f"L{rng.randint(1, 99)}", category=cat,
                qty=rng.choice([1, 1, 2, 3, 6, 20]), rating=rating, unit=unit,
                pf=round(rng.uniform(0.6, 1.0), 2), voltage=v, phases=phases,
                continuous=rng.random() < 0.4,
                demand_factor=(None if rng.random() < 0.75 else
                               round(rng.uniform(0.3, 1.0), 2)),
                phase_conn=(rng.choice(L.PHASE_CONN) if rng.random() < 0.15
                            else "auto"))


def ser_calc(c):
    return {
        "rows": [{k: r[k] for k in ("kva", "kw", "kvar", "amps", "df",
                                    "d_kva", "phase")} for r in c["rows"]],
        "notes": [[k, rf, p] for k, rf, p in c["notes"]],
        **{k: c[k] for k in ("connected", "demand", "coincident",
                             "continuous_kva", "largest_motor_kva",
                             "design_kva", "i_demand", "i_design_balanced",
                             "i_design", "phase_kva", "phase_amps",
                             "imbalance_pct", "cap_kvar",
                             "demand_factor_overall")},
        "summary_rows": {lg: [list(r) for r in R.load_summary_rows(c, lg)]
                         for lg in LANGS},
        "note_text": {lg: R.load_notes(c, lg) for lg in LANGS},
    }


def case_loads(rng):
    system = rng.choice(list(L.SYSTEMS))
    p = dict(name="P", system=system,
             diversity=rng.choice([1.0, 1.0, 1.1, 1.3, 0.8]),
             target_pf=rng.choice([0.9, 0.95, 0.98]),
             edition=rng.choice(["2023", "2026"]),
             loads=[rnd_load(rng) for _ in range(rng.randint(1, 12))])
    if system.startswith("1") or system.startswith("240"):
        for ld in p["loads"]:
            ld["phases"] = 1
            if ld["phase_conn"] in ("C", "BC", "CA", "ABC"):
                ld["phase_conn"] = "auto"
    if system == "120 1PH":
        for ld in p["loads"]:
            ld["phase_conn"] = "auto"
    w = rnd_wiring(rng)
    args = dict(panel=p, w=w)

    def go():
        panel = L.Panel.from_dict(p)
        c = L.calculate(panel)
        out = ser_calc(c)
        try:
            out["feeder"] = ser_result(L.size_feeder(panel, c,
                                                     E.WiringInput(**w)))
        except E.CalcError as e:
            out["feeder"] = {"error": e.key}
        return out
    return "loads", args, run(go)


def rnd_cable(rng):
    kind = rng.choice(TR.KINDS)
    if kind == "lv_multi":
        size = rng.choice(list(T.TC_3C_OD_TYPICAL))
    elif kind == "lv_single":
        size = rng.choice(["2", "1/0", "2/0", "4/0", "250", "350", "500",
                           "750", "1000", "1250", "2000"])
    elif kind in ("mv_single", "mv_multi"):
        size = rng.choice(T.MV_SIZES)
    else:
        size = "14"
    return dict(name=f"C{rng.randint(1, 99)}", kind=kind, size=size,
                n_cond=rng.choice([1, 3, 4]), qty=rng.choice([0, 1, 2, 3, 6,
                                                              12, 30]),
                od_in=rng.choice([0, 0, 0, 0.6, 1.1]),
                material=rng.choice(["cu", "al"]),
                ins_level=rng.choice(["25kV_100", "25kV_133", "35kV_100"]))


def case_tray(rng):
    x = dict(tray_type=rng.choice(T.TRAY_TYPES),
             depth_in=rng.choice(T.TRAY_DEPTHS),
             width_in=rng.choice([0, 0, 0, 6, 12, 15, 24, 36]),
             covered=rng.random() < 0.3,
             arrangement=rng.choice(TR.ARRANGEMENTS),
             ambient_c=rng.choice([20, 30, 40, 50]),
             edition=rng.choice(["2023", "2026"]),
             cables=[rnd_cable(rng) for _ in range(rng.randint(1, 6))])
    return "design_tray", dict(x=x), run(
        lambda: ser_result(TR.design_tray(TR.TrayInput.from_dict(x))))


def case_capacity(rng):
    kind = rng.choice(TR.KINDS)
    kw = dict(tray_type=rng.choice(T.TRAY_TYPES),
              depth_in=rng.choice(T.TRAY_DEPTHS), n_cond=rng.choice([3, 4]),
              material=rng.choice(["cu", "al"]),
              ins_level=rng.choice(["25kV_100", "25kV_133", "35kV_100"]),
              od_in=rng.choice([0, 0, 0.7]))
    tbl = TR.capacity_table(kind, **kw)
    return "capacity", dict(kind=kind, kw=kw), {
        "ok": [[s, [[w, n] for w, n in row.items()]] for s, row in tbl.items()]}


def case_format(rng):
    vals = [rng.uniform(-1e7, 1e7), rng.uniform(0, 1), rng.uniform(0, 1e-4),
            rng.choice([0.0, 1.0, 24900.0, 1e6, 123456.7, 0.5, 2.675,
                        0.125, 0.375, 831.25, 21948.5, 2.5, 3.5, -4.25,
                        1234567.5, 0.00012345, 999999.5, 24.9, 7.5e-5])]
    out = []
    for v in vals:
        for spec in ("g", ".1f", ".2f", ",.0f", ".3f"):
            out.append([v, spec, format(v, spec)])
    return "format", {}, {"ok": out}


KINDS = [case_general, case_motor, case_mv, case_xfmr, case_loads,
         case_tray, case_format]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    rng = random.Random(20261006)
    cases = []
    for fn in KINDS:
        for _ in range(n):
            name, args, result = fn(rng)
            cases.append({"fn": name, "args": args, "result": result})
    for _ in range(max(n // 15, 4)):
        name, args, result = case_capacity(rng)
        cases.append({"fn": name, "args": args, "result": result})
    out = os.path.join(HERE, "crosscheck_cases.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(cases, fh, ensure_ascii=False)
    errs = sum(1 for c in cases if "error" in c["result"])
    print(f"wrote {len(cases)} cases ({errs} expected errors) to {out}")


if __name__ == "__main__":
    main()
