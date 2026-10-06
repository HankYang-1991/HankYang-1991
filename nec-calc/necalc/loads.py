"""Panel / feeder load calculation with power factor, demand factor and
diversity factor.

Method (non-dwelling occupancies):
  * Each load: connected kW, kvar, kVA from rating and power factor.
  * Demand factor (DF): user value, or automatic per NEC:
      - receptacles: first 10 kVA at 100 %, remainder at 50 % (220.47)
      - heating vs. cooling: non-coincident, the smaller group is omitted
        (220.60)
      - everything else 100 %
  * Diversity factor (>= 1.0): coincident demand = sum of demands / diversity
  * Feeder design load adds 25 % of continuous loads (215.2(A)(1)) and
    25 % of the largest motor (430.24).
"""
import math
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import engine as E
from .codes import ref

CATEGORIES = ("lighting", "receptacle", "motor", "heating", "cooling",
              "equipment", "other")
UNITS = ("VA", "kVA", "W", "kW", "HP", "A")
PHASE_CONN = ("auto", "A", "B", "C", "AB", "BC", "CA", "ABC")

SYSTEMS = {
    # key: (LL voltage, LN voltage, phases, wiring)
    "208Y/120": (208.0, 120.0, 3, "3ph4w"),
    "480Y/277": (480.0, 277.0, 3, "3ph4w"),
    "480D": (480.0, 480.0 / math.sqrt(3), 3, "3ph3w"),
    "240/120 1PH": (240.0, 120.0, 1, "1ph3w"),
    "120 1PH": (120.0, 120.0, 1, "1ph2w"),
}


@dataclass
class Load:
    name: str = "Load"
    category: str = "other"
    qty: int = 1
    rating: float = 1000.0          # per unit, in `unit`
    unit: str = "VA"
    pf: float = 1.0
    efficiency: float = 1.0         # used only for kW unit on motors/HP
    voltage: float = 120.0
    phases: int = 1
    continuous: bool = False
    demand_factor: Optional[float] = None  # None -> automatic
    phase_conn: str = "auto"
    hp: str = ""                    # for unit == "HP"

    # ---- connected values -------------------------------------------
    def kva(self):
        q = max(self.qty, 0)
        r = self.rating
        u = self.unit
        if u == "VA":
            return q * r / 1000.0
        if u == "kVA":
            return q * r
        if u == "W":
            return q * r / 1000.0 / (self.pf or 1.0)
        if u == "kW":
            return q * r / (self.pf or 1.0)
        if u == "A":
            k = math.sqrt(3) if self.phases == 3 else 1.0
            return q * r * self.voltage * k / 1000.0
        if u == "HP":
            hp = self.hp or _hp_str(r)
            flc = E.motor_flc(hp, self.voltage, self.phases)
            if flc is None:
                # fallback: 746 W/HP with efficiency & PF
                return q * r * 0.746 / max(self.efficiency, 0.01) / \
                    (self.pf or 1.0)
            k = math.sqrt(3) if self.phases == 3 else 1.0
            return q * flc * self.voltage * k / 1000.0
        raise E.CalcError("err_unit", unit=u)

    def kw(self):
        return self.kva() * self.pf

    def kvar(self):
        s = self.kva()
        return math.sqrt(max(s * s - self.kw() ** 2, 0.0))

    def unit_kva(self):
        return self.kva() / self.qty if self.qty else 0.0

    def amps(self):
        k = math.sqrt(3) if self.phases == 3 else 1.0
        return self.kva() * 1000.0 / (k * self.voltage) if self.voltage \
            else 0.0


def _hp_str(r):
    table = {1 / 6: "1/6", 0.25: "1/4", 1 / 3: "1/3", 0.5: "1/2",
             0.75: "3/4", 1.5: "1-1/2", 7.5: "7-1/2"}
    for k, v in table.items():
        if abs(r - k) < 1e-3:
            return v
    return str(int(r)) if float(r).is_integer() else str(r)


@dataclass
class Panel:
    name: str = "PANEL"
    system: str = "208Y/120"
    diversity: float = 1.0
    target_pf: float = 0.95
    loads: list = field(default_factory=list)
    edition: str = "2023"

    def to_dict(self):
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d):
        p = cls(**{k: v for k, v in d.items() if k != "loads"})
        p.loads = [Load(**ld) for ld in d.get("loads", [])]
        return p


def _phases_for(load: Load, panel_phases, wiring):
    """Return list of phase letters this load connects to."""
    if load.phase_conn not in ("auto", None, ""):
        return list(load.phase_conn)
    if wiring == "1ph2w":
        return ["A"]
    if panel_phases == 1:
        return ["A", "B"] if load.voltage > 150 else None
    if load.phases == 3:
        return ["A", "B", "C"]
    return None  # auto single-phase


def calculate(panel: Panel):
    """Return a dict with per-load rows, category totals and panel totals."""
    ll, ln, pphases, wiring = SYSTEMS[panel.system]
    ed = panel.edition
    rows = []
    cat = {c: {"kva": 0.0, "kw": 0.0, "kvar": 0.0} for c in CATEGORIES}
    for ld in panel.loads:
        r = {"load": ld, "kva": ld.kva(), "kw": ld.kw(), "kvar": ld.kvar(),
             "amps": ld.amps()}
        rows.append(r)
        c = cat.setdefault(ld.category, {"kva": 0.0, "kw": 0.0, "kvar": 0.0})
        c["kva"] += r["kva"]
        c["kw"] += r["kw"]
        c["kvar"] += r["kvar"]

    notes = []
    # ---- automatic demand factors ----------------------------------
    rec_kva = math.fsum(r["kva"] for r in rows if r["load"].category == "receptacle"
                  and r["load"].demand_factor is None)
    rec_df = 1.0
    if rec_kva > 10.0:
        rec_df = (10.0 + 0.5 * (rec_kva - 10.0)) / rec_kva
        notes.append(("n_receptacle", ref("receptacle_load", ed),
                      {"kva": rec_kva, "df": rec_df}))

    heat = math.fsum(r["kva"] for r in rows if r["load"].category == "heating")
    cool = math.fsum(r["kva"] for r in rows if r["load"].category == "cooling")
    drop_cat = None
    if heat > 0 and cool > 0:
        drop_cat = "cooling" if heat >= cool else "heating"
        notes.append(("n_noncoincident", ref("noncoincident", ed),
                      {"heat": heat, "cool": cool, "drop": drop_cat}))

    motors = [r for r in rows if r["load"].category == "motor"]
    largest_motor = max(motors, key=lambda r: r["load"].unit_kva(),
                        default=None)
    largest_motor_kva = largest_motor["load"].unit_kva() if largest_motor \
        else 0.0

    for r in rows:
        ld = r["load"]
        if ld.demand_factor is not None:
            df = ld.demand_factor
        elif ld.category == "receptacle":
            df = rec_df
        elif ld.category == drop_cat:
            df = 0.0
        else:
            df = 1.0
        r["df"] = df
        r["d_kva"] = r["kva"] * df
        r["d_kw"] = r["kw"] * df
        r["d_kvar"] = r["kvar"] * df

    # ---- phase assignment (connected kVA) --------------------------
    phase_kva = {"A": 0.0, "B": 0.0, "C": 0.0}
    letters = {"1ph2w": ["A"], "1ph3w": ["A", "B"]}.get(wiring,
                                                         ["A", "B", "C"])
    pending = []
    for r in rows:
        ph = _phases_for(r["load"], pphases, wiring)
        if ph is None:
            pending.append(r)
        else:
            r["phase"] = "".join(ph)
            for p in ph:
                phase_kva[p] += r["d_kva"] / len(ph)
    # greedy balance of automatic single-phase loads (largest first)
    # (each unit of a multi-quantity row is a separate circuit)
    for r in sorted(pending, key=lambda r: -r["d_kva"]):
        ld = r["load"]
        n = max(int(ld.qty), 1)
        unit = r["d_kva"] / n
        used_ph = []
        for _ in range(n):
            if pphases == 3 and ld.voltage > ln * 1.2:
                # line-to-line single-phase load: least-loaded pair
                pairs = [("A", "B"), ("B", "C"), ("C", "A")]
                best = min(pairs,
                           key=lambda p: phase_kva[p[0]] + phase_kva[p[1]])
                for p in best:
                    phase_kva[p] += unit / 2
                tag = "".join(best)
            else:
                tag = min(letters, key=lambda p: phase_kva[p])
                phase_kva[tag] += unit
            if tag not in used_ph:
                used_ph.append(tag)
        r["phase"] = ",".join(sorted(used_ph))

    # ---- totals -----------------------------------------------------
    conn_kw = math.fsum(r["kw"] for r in rows)
    conn_kvar = math.fsum(r["kvar"] for r in rows)
    conn_kva = math.hypot(conn_kw, conn_kvar)
    dem_kw = math.fsum(r["d_kw"] for r in rows)
    dem_kvar = math.fsum(r["d_kvar"] for r in rows)
    dem_kva_arith = math.fsum(r["d_kva"] for r in rows)
    div = max(panel.diversity, 1.0)
    coin_kw = dem_kw / div
    coin_kvar = dem_kvar / div
    coin_kva = dem_kva_arith / div
    pf = conn_kw / conn_kva if conn_kva else 1.0
    dem_pf = dem_kw / math.hypot(dem_kw, dem_kvar) if dem_kw else 1.0

    cont_kva = math.fsum(r["d_kva"] for r in rows if r["load"].continuous) / div
    design_kva = coin_kva + 0.25 * cont_kva + 0.25 * largest_motor_kva

    k = math.sqrt(3) if pphases == 3 else 1.0
    v_line = ll
    i_demand = coin_kva * 1000.0 / (k * v_line)
    i_design = design_kva * 1000.0 / (k * v_line)

    # phase currents (demand, after diversity) and imbalance
    vph = ln if pphases == 3 else (ll / 2.0 if wiring == "1ph3w" else ll)
    used = [p for p in letters]
    phase_amps = {p: phase_kva[p] / div * 1000.0 / vph for p in used}
    avg = math.fsum(phase_amps.values()) / len(used) if used else 0.0
    imbalance = (max(phase_amps.values()) - avg) / avg * 100.0 if avg else 0
    # size feeder on the larger of balanced design current and worst phase
    scale = design_kva / coin_kva if coin_kva else 1.0
    i_design_phase = max(phase_amps.values(), default=0.0) * scale
    i_design_final = max(i_design, i_design_phase)

    # capacitor kvar to reach target PF
    cap = 0.0
    if dem_pf < panel.target_pf and coin_kw > 0:
        cap = coin_kw * (math.tan(math.acos(dem_pf)) -
                         math.tan(math.acos(panel.target_pf)))

    return {
        "rows": rows, "categories": cat, "notes": notes,
        "connected": {"kw": conn_kw, "kvar": conn_kvar, "kva": conn_kva,
                      "kva_arith": math.fsum(r["kva"] for r in rows), "pf": pf},
        "demand": {"kw": dem_kw, "kvar": dem_kvar, "kva": dem_kva_arith,
                   "pf": dem_pf},
        "coincident": {"kw": coin_kw, "kvar": coin_kvar, "kva": coin_kva,
                       "diversity": div},
        "continuous_kva": cont_kva,
        "largest_motor_kva": largest_motor_kva,
        "design_kva": design_kva,
        "i_demand": i_demand,
        "i_design_balanced": i_design,
        "i_design": i_design_final,
        "phase_kva": {p: phase_kva[p] / div for p in used},
        "phase_amps": phase_amps,
        "imbalance_pct": imbalance,
        "cap_kvar": cap,
        "system": (ll, ln, pphases, wiring),
        "demand_factor_overall": (dem_kva_arith / math.fsum(r["kva"] for r in rows)
                                  if rows else 1.0),
    }


def size_feeder(panel: Panel, calc: dict, w: "E.WiringInput"):
    """Size the panel feeder from a load calculation result."""
    ll, ln, pphases, wiring = calc["system"]
    w.voltage = ll
    w.wiring = wiring
    w.pf = calc["demand"]["pf"]
    i_load = calc["i_demand"]
    i_design = calc["i_design"]
    res = E.Result("feeder")
    res.add("st_feeder_load", ref("cont_feeder", panel.edition),
            kva=calc["coincident"]["kva"], cont=calc["continuous_kva"],
            motor=calc["largest_motor_kva"], design=calc["design_kva"],
            amps=i_design)
    ocpd = E.next_std_ocpd(i_design)
    if ocpd is None:
        raise E.CalcError("err_ocpd_range", amps=round(i_design, 1))
    res.add("st_ocpd_select", ref("std_ocpd", panel.edition),
            amps=i_design, ocpd=ocpd)
    E.size_conductors(i_design, i_load, ocpd, w, res=res)
    res.summary.update({"i_load": i_load, "i_design": i_design,
                        "ocpd": ocpd, "switch": E.next_switch(ocpd)})
    return res
