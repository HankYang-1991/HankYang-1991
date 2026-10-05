"""Core NEC calculation engine: conductors, OCPD, EGC, conduit fill,
voltage drop, motor / transformer / medium-voltage circuit design.

Every design function returns a ``Result`` that contains summary values and
a list of ``Step`` records (i18n key + NEC reference + parameters) so the
same calculation can be reported in English or Chinese.
"""
import math
from dataclasses import dataclass, field
from typing import Optional

from . import tables as T
from .codes import ref

SQRT3 = math.sqrt(3.0)


class CalcError(Exception):
    """Raised for invalid input. ``key``/``params`` are i18n friendly."""

    def __init__(self, key, **params):
        super().__init__(key)
        self.key = key
        self.params = params


@dataclass
class Step:
    key: str                 # i18n template key
    ref: str = ""            # NEC reference text
    params: dict = field(default_factory=dict)
    ok: Optional[bool] = None  # None = informational


@dataclass
class Result:
    kind: str
    summary: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)
    warnings: list = field(default_factory=list)  # list of (key, params)
    children: dict = field(default_factory=dict)  # sub-results

    def add(self, key, ref_text="", ok=None, **params):
        self.steps.append(Step(key, ref_text, params, ok))

    def warn(self, key, **params):
        self.warnings.append((key, params))


# ---------------------------------------------------------------------------
# Basic look-ups
# ---------------------------------------------------------------------------
def next_std_ocpd(amps, ratings=None):
    """Smallest standard rating >= amps (240.6(A))."""
    for r in ratings or T.STANDARD_OCPD:
        if r >= amps - 1e-9:
            return r
    return None


def max_std_ocpd(amps, ratings=None):
    """Largest standard rating <= amps."""
    best = None
    for r in ratings or T.STANDARD_OCPD:
        if r <= amps + 1e-9:
            best = r
    return best


def next_switch(amps):
    for r in T.STANDARD_SWITCH:
        if r >= amps - 1e-9:
            return r
    return None


def temp_factor(ambient_c, insulation_temp):
    col = T.TEMP_COLUMNS.index(insulation_temp)
    for upper, *factors in T.TEMP_CORRECTION:
        if ambient_c <= upper:
            f = factors[col]
            if f is None:
                raise CalcError("err_ambient", ambient=ambient_c,
                                temp=insulation_temp)
            return f
    raise CalcError("err_ambient", ambient=ambient_c, temp=insulation_temp)


def ccc_factor(n_ccc):
    for upper, f in T.CCC_ADJUSTMENT:
        if n_ccc <= upper:
            return f
    return T.CCC_ADJUSTMENT[-1][1]


def base_ampacity(size, material, temp_col):
    tbl = T.AMPACITY_CU if material == "cu" else T.AMPACITY_AL
    row = tbl.get(size)
    if row is None:
        return None
    return row[T.TEMP_COLUMNS.index(temp_col)]


def egc_size(ocpd, material="cu"):
    for limit, cu, al in T.EGC_TABLE:
        if ocpd <= limit:
            return cu if material == "cu" else al
    return T.EGC_TABLE[-1][1 if material == "cu" else 2]


def size_from_cmil(cmil, material="cu", minimum=None):
    """Smallest standard size whose area is >= cmil."""
    start = T.size_index(minimum) if minimum else 0
    for s in T.SIZES[start:]:
        if material == "al" and s == "14":
            continue
        if T.CMIL[s] >= cmil - 1e-6:
            return s
    return T.SIZES[-1]


def cmil_of(size):
    if size in T.CMIL:
        return T.CMIL[size]
    return int(size) * 1000  # kcmil sizes outside SIZES (e.g. 1200)


def conduit_material(conduit_type):
    return "pvc" if conduit_type.startswith("PVC") else "steel"


def table9_impedance(size, material, conduit_type):
    """Return (R, X) ohm/1000 ft from Chapter 9 Table 9.

    Sizes not listed in Table 9 are approximated by scaling R of the nearest
    listed size by circular-mil ratio (flagged as approximate)."""
    mat = conduit_material(conduit_type)
    approx = False
    key = size
    if key not in T.TABLE9:
        approx = True
        listed = [s for s in T.TABLE9 if T.TABLE9[s][5 if material == "al"
                                                     else 2] is not None]
        key = min(listed, key=lambda s: abs(T.CMIL[s] - cmil_of(size)))
    row = T.TABLE9[key]
    x = row[0] if mat == "pvc" else row[1]
    if material == "cu":
        r = row[2] if mat == "pvc" else row[4]
    else:
        r = row[5] if mat == "pvc" else row[7]
    if r is None:
        raise CalcError("err_no_impedance", size=size)
    if approx:
        r = r * T.CMIL[key] / cmil_of(size)
    return r, x, approx


def effective_z(size, material, conduit_type, pf):
    r, x, approx = table9_impedance(size, material, conduit_type)
    pf = max(min(pf, 1.0), 0.0)
    sin = math.sqrt(1 - pf * pf)
    return r * pf + x * sin, approx


def voltage_drop(i, length_ft, size, material, conduit_type, pf, phases,
                 voltage, sets=1):
    """Return (volts, percent) using Table 9 effective Z method."""
    z, _ = effective_z(size, material, conduit_type, pf)
    k = SQRT3 if phases == 3 else 2.0
    vd = k * i * z * length_ft / 1000.0 / max(sets, 1)
    return vd, 100.0 * vd / voltage


# ---------------------------------------------------------------------------
# Conduit fill
# ---------------------------------------------------------------------------
def wire_area(size, insulation):
    areas = T.WIRE_AREA[insulation]
    if size in areas:
        return areas[size]
    # size not in Table 5 for this insulation: use next larger listed size
    for s in T.SIZES[T.size_index(size) if size in T.SIZES else 0:]:
        if s in areas and cmil_of(s) >= cmil_of(size):
            return areas[s]
    return max(areas.values())


def select_conduit(items, conduit_type, max_trade=None):
    """items: list of (count, area_in2). Returns dict or None."""
    n = sum(c for c, _ in items)
    total = sum(c * a for c, a in items)
    pct = T.FILL_PERCENT.get(n, T.FILL_PERCENT_OVER_2)
    for trade in T.TRADE_SIZES:
        area = T.CONDUIT_AREA[conduit_type].get(trade)
        if area is None:
            continue
        if total <= area * pct + 1e-9:
            return {"trade": trade, "wire_area": total, "conduit_area": area,
                    "fill_pct": 100.0 * total / area, "max_pct": pct * 100,
                    "count": n}
        if max_trade and trade == max_trade:
            break
    return None


# ---------------------------------------------------------------------------
# Wiring configuration helpers
# ---------------------------------------------------------------------------
WIRING = {
    # key: (phases for VD/current, ungrounded conductors, neutral)
    "1ph2w": (1, 2, False),   # L-N (2 wires: L + N) or L-L 2 wire
    "1ph3w": (1, 2, True),    # 120/240 V  L1 + L2 + N
    "3ph3w": (3, 3, False),
    "3ph4w": (3, 3, True),
}


def line_current(va, voltage, phases):
    return va / (SQRT3 * voltage) if phases == 3 else va / voltage


# ---------------------------------------------------------------------------
# Low-voltage (<= 1000 V) conductor / OCPD design
# ---------------------------------------------------------------------------
@dataclass
class WiringInput:
    voltage: float = 208.0
    wiring: str = "3ph4w"          # see WIRING
    material: str = "cu"           # "cu" | "al"
    insulation: str = "THHN"       # "THHN" | "XHHW"
    term_temp: int = 75            # 60 | 75 | 90 (110.14(C))
    ambient_c: float = 30.0
    extra_ccc: int = 0             # other CCC sharing the raceway
    neutral_ccc: bool = False      # neutral counted as CCC (310.15(E))
    sets: int = 0                  # parallel sets, 0 = auto
    max_size: str = "500"          # preferred max size for auto sets
    length_ft: float = 100.0
    pf: float = 0.9
    vd_limit_pct: float = 3.0
    conduit_type: str = "EMT"
    min_size: str = "12"           # design minimum (e.g. 12 AWG practice)
    edition: str = "2023"


def _ungrounded_and_neutral(w: WiringInput):
    phases, n_ungrounded, has_neutral = WIRING[w.wiring]
    if w.wiring == "1ph2w":
        # count as 2 CCC (line + neutral or two lines), no separate neutral
        return phases, 2, False
    return phases, n_ungrounded, has_neutral


def ccc_count(w: WiringInput):
    phases, n_wires, has_neutral = _ungrounded_and_neutral(w)
    n = n_wires
    if has_neutral and w.wiring == "3ph4w" and w.neutral_ccc:
        n += 1
    return n + max(w.extra_ccc, 0)


def _size_candidates(material, min_size, sets):
    start = T.size_index(min_size)
    if sets > 1:
        start = max(start, T.size_index("1/0"))
    sizes = T.SIZES[start:]
    tbl = T.AMPACITY_CU if material == "cu" else T.AMPACITY_AL
    return [s for s in sizes if s in tbl]


def _check_size(size, sets, i_design, i_load, ocpd, w, f_temp, f_ccc,
                skip_protection):
    """Return (ok, details) for one candidate size."""
    a_term = base_ampacity(size, w.material, w.term_temp) * sets
    ins_temp = T.INSULATION_TEMP[w.insulation]
    a_ins = base_ampacity(size, w.material, ins_temp)
    a_derated = a_ins * f_temp * f_ccc * sets
    a_eff = min(a_derated, a_term)
    ok_term = a_term >= i_design - 1e-9
    ok_derated = a_derated >= i_load - 1e-9
    ok_prot = True
    if not skip_protection and ocpd:
        if ocpd <= 800:
            ok_prot = a_eff >= ocpd - 1e-9 or next_std_ocpd(a_eff) >= ocpd
        else:
            ok_prot = a_eff >= ocpd - 1e-9
        small = T.SMALL_CONDUCTOR_MAX_OCPD[w.material].get(size)
        if small is not None and sets == 1 and ocpd > small:
            ok_prot = False
    return ok_term and ok_derated and ok_prot, {
        "a_term": a_term, "a_ins": a_ins * sets, "a_derated": a_derated,
        "a_eff": a_eff, "ok_term": ok_term, "ok_derated": ok_derated,
        "ok_prot": ok_prot,
    }


def size_conductors(i_design, i_load, ocpd, w: WiringInput,
                    skip_protection=False, res: Optional[Result] = None):
    """Select conductor size, parallel sets, EGC, neutral, conduit, VD.

    i_design: current used for termination check (incl. 125 % factors)
    i_load:   actual load current (for derated ampacity & voltage drop)
    ocpd:     overcurrent device rating protecting the conductors
    skip_protection: True for motor circuits (430.52 / 240.4(G))
    """
    ed = w.edition
    res = res or Result("conductors")
    phases, n_ungrounded, has_neutral = _ungrounded_and_neutral(w)
    ins_temp = T.INSULATION_TEMP[w.insulation]
    if w.term_temp > ins_temp:
        raise CalcError("err_term_temp")
    min_size = w.min_size
    if w.material == "al" and T.size_index(min_size) < T.size_index("12"):
        min_size = "12"

    f_temp = temp_factor(w.ambient_c, ins_temp)
    n_ccc = ccc_count(w)
    f_ccc = ccc_factor(n_ccc)
    res.add("st_temp_corr", ref("temp_corr", ed), ambient=w.ambient_c,
            temp=ins_temp, factor=f_temp)
    res.add("st_ccc_adj", ref("ccc_adj", ed), n=n_ccc, factor=f_ccc)

    sets_to_try = [w.sets] if w.sets > 0 else list(range(1, 13))
    chosen = None
    for sets in sets_to_try:
        for size in _size_candidates(w.material, min_size, sets):
            ok, d = _check_size(size, sets, i_design, i_load, ocpd, w,
                                f_temp, f_ccc, skip_protection)
            if ok:
                chosen = (sets, size, d)
                break
        if chosen:
            if w.sets > 0 or T.size_index(chosen[1]) <= \
                    T.size_index(w.max_size):
                break
            chosen = None
    if not chosen:
        raise CalcError("err_no_conductor", amps=round(i_design, 1))

    sets, amp_size, d = chosen
    res.add("st_ampacity_term", ref("termination", ed),
            ok=d["ok_term"], size=T.size_label(amp_size), sets=sets,
            temp=w.term_temp, amps=d["a_term"], need=i_design)
    res.add("st_ampacity_derated", ref("ampacity", ed), ok=d["ok_derated"],
            temp=ins_temp, base=d["a_ins"], ft=f_temp, fa=f_ccc,
            amps=d["a_derated"], need=i_load)
    if sets > 1:
        res.add("st_parallel", ref("parallel", ed), sets=sets)
    if not skip_protection and ocpd:
        res.add("st_protection", ref("next_size_up", ed) + ", " +
                ref("small_cond", ed), ok=d["ok_prot"], amps=d["a_eff"],
                ocpd=ocpd)

    # ---- voltage drop / upsizing --------------------------------------
    size = amp_size
    vd_v, vd_pct = voltage_drop(i_load, w.length_ft, size, w.material,
                                w.conduit_type, w.pf, phases, w.voltage, sets)
    if w.vd_limit_pct and vd_pct > w.vd_limit_pct:
        cands = _size_candidates(w.material, size, sets)
        for s in cands:
            v, p = voltage_drop(i_load, w.length_ft, s, w.material,
                                w.conduit_type, w.pf, phases, w.voltage, sets)
            if p <= w.vd_limit_pct:
                size, vd_v, vd_pct = s, v, p
                break
        else:
            size = cands[-1]
            vd_v, vd_pct = voltage_drop(i_load, w.length_ft, size,
                                        w.material, w.conduit_type, w.pf,
                                        phases, w.voltage, sets)
            res.warn("w_vd_not_met", limit=w.vd_limit_pct, pct=vd_pct)
    _, approx = effective_z(size, w.material, w.conduit_type, w.pf)
    res.add("st_vd", ref("vd_note", ed) + "; " + ref("impedance", ed),
            ok=(not w.vd_limit_pct) or vd_pct <= w.vd_limit_pct + 1e-9,
            amps=i_load, length=w.length_ft, size=T.size_label(size),
            volts=vd_v, pct=vd_pct, limit=w.vd_limit_pct)
    if approx:
        res.warn("w_z_approx", size=T.size_label(size))
    upsized = size != amp_size
    if upsized:
        res.add("st_vd_upsize", ref("vd_note", ed),
                old=T.size_label(amp_size), new=T.size_label(size))

    # ---- EGC -----------------------------------------------------------
    egc = None
    if ocpd:
        egc = egc_size(ocpd, w.material)
        res.add("st_egc", ref("egc", ed), ocpd=ocpd, size=T.size_label(egc))
        if upsized:
            ratio = T.CMIL[size] / T.CMIL[amp_size]
            # 1 % tolerance absorbs rounding of tabulated circular mils
            new_egc = size_from_cmil(cmil_of(egc) * ratio / 1.01,
                                     w.material)
            if cmil_of(new_egc) > cmil_of(size):
                new_egc = size
            if new_egc != egc:
                res.add("st_egc_upsize", ref("egc_upsize", ed),
                        ratio=ratio, old=T.size_label(egc),
                        new=T.size_label(new_egc))
                egc = new_egc
        if cmil_of(egc) > cmil_of(size):
            egc = size
        if sets > 1:
            res.add("st_egc_parallel", ref("egc_parallel", ed), sets=sets,
                    size=T.size_label(egc))

    neutral = size if has_neutral else None

    # ---- conduit fill (one set per raceway) ---------------------------
    items = [(n_ungrounded, wire_area(size, w.insulation))]
    if neutral:
        items.append((1, wire_area(neutral, w.insulation)))
    if egc:
        items.append((1, wire_area(egc, w.insulation)))
    cond = select_conduit(items, w.conduit_type)
    if cond:
        res.add("st_conduit", ref("fill", ed), n=cond["count"],
                area=cond["wire_area"], trade=cond["trade"],
                ctype=w.conduit_type, fill=cond["fill_pct"],
                maxfill=cond["max_pct"], qty=sets)
    else:
        res.warn("w_conduit_none", ctype=w.conduit_type)

    a_final = _check_size(size, sets, i_design, i_load, ocpd, w, f_temp,
                          f_ccc, True)[1]["a_eff"]
    res.summary.update({
        "sets": sets,
        "size": size,
        "size_label": T.size_label(size),
        "ampacity": a_final,
        "neutral": T.size_label(neutral) if neutral else "-",
        "egc": T.size_label(egc) if egc else "-",
        "conduit": (f'{sets} x {cond["trade"]}" {w.conduit_type}'
                    if cond else "-"),
        "vd_pct": vd_pct,
        "vd_v": vd_v,
        "n_ccc": n_ccc,
        "wire_text": _wire_text(sets, n_ungrounded, size, neutral, egc,
                                w.material, w.insulation, cond,
                                w.conduit_type),
    })
    return res


def _wire_text(sets, n, size, neutral, egc, material, insulation, cond,
               ctype):
    mat = "CU" if material == "cu" else "AL"
    ins = "THHN/THWN-2" if insulation == "THHN" else "XHHW-2"
    parts = [f"{n}#{size}"]
    if neutral:
        parts.append(f"1#{neutral}N")
    if egc:
        parts.append(f"1#{egc}G")
    s = " + ".join(parts) + f" {mat} {ins}"
    if cond:
        s += f', {cond["trade"]}" {ctype}'
    if sets > 1:
        s = f"({sets}) SETS OF " + s
    return s


# ---------------------------------------------------------------------------
# General branch circuit / feeder (lighting, receptacle, heating, other)
# ---------------------------------------------------------------------------
def design_general(load_va, w: WiringInput, continuous_va=None,
                   ocpd=None, kind="branch", largest_motor_va=0.0,
                   load_amps=None):
    """Design a branch circuit or feeder for a general (non-motor) load.

    load_va:        total load (VA) - non-continuous + continuous
    continuous_va:  portion that is continuous (3 h or more), default all
    largest_motor_va: adds 25 % of largest motor (feeders, 430.24)
    load_amps:      if given, overrides VA->A conversion (total amps)
    """
    ed = w.edition
    res = Result("general")
    phases = WIRING[w.wiring][0]
    if load_amps is not None and not load_va:
        load_va = load_amps * w.voltage * (SQRT3 if phases == 3 else 1.0)
    if continuous_va is None:
        continuous_va = load_va
    continuous_va = min(continuous_va, load_va)
    if load_amps is not None:
        i_load = load_amps
        ratio = (continuous_va / load_va) if load_va else 1.0
        i_cont = i_load * ratio
    else:
        i_load = line_current(load_va, w.voltage, phases)
        i_cont = line_current(continuous_va, w.voltage, phases)
    i_motor25 = 0.25 * line_current(largest_motor_va, w.voltage, phases)
    i_design = i_load + 0.25 * i_cont + i_motor25
    res.add("st_load_current", "", va=load_va, volts=w.voltage,
            phases=phases, amps=i_load)
    res.add("st_design_current",
            ref("cont_feeder" if kind == "feeder" else "cont_branch", ed),
            cont=i_cont, noncont=i_load - i_cont, motor25=i_motor25,
            amps=i_design)

    if ocpd is None:
        ocpd = next_std_ocpd(i_design)
        if ocpd is None:
            raise CalcError("err_ocpd_range", amps=round(i_design, 1))
        res.add("st_ocpd_select", ref("std_ocpd", ed), amps=i_design,
                ocpd=ocpd)
    else:
        res.add("st_ocpd_given", ref("std_ocpd", ed), ocpd=ocpd,
                ok=ocpd >= i_design - 1e-9, amps=i_design)
        if ocpd < i_design - 1e-9:
            res.warn("w_ocpd_small", ocpd=ocpd, amps=round(i_design, 1))

    size_conductors(i_design, i_load, ocpd, w, res=res)
    switch = next_switch(ocpd)
    res.add("st_switch", ref("switch", ed), amps=switch, ocpd=ocpd)
    res.summary.update({"i_load": i_load, "i_design": i_design,
                        "ocpd": ocpd, "switch": switch})
    return res


# ---------------------------------------------------------------------------
# Motor branch circuit
# ---------------------------------------------------------------------------
def motor_flc(hp, voltage, phases):
    v = T.MOTOR_VOLT_MAP.get(int(round(voltage)))
    if v is None:
        return None
    if phases == 1:
        row = T.FLC_1PH.get(hp)
        if not row or v not in T.FLC_1PH_VOLTS:
            return None
        return row[T.FLC_1PH_VOLTS.index(v)]
    row = T.FLC_3PH.get(hp)
    if not row or v not in T.FLC_3PH_VOLTS:
        return None
    return row[T.FLC_3PH_VOLTS.index(v)]


def design_motor(hp, w: WiringInput, device="itcb", nameplate_fla=None,
                 sf_115=True, design_b_ee=False, flc_override=None):
    ed = w.edition
    res = Result("motor")
    phases = WIRING[w.wiring][0]
    flc = flc_override or motor_flc(hp, w.voltage, phases)
    if not flc:
        raise CalcError("err_flc", hp=hp, volts=w.voltage, phases=phases)
    res.add("st_motor_flc", ref("motor_flc", ed), hp=hp, volts=w.voltage,
            phases=phases, flc=flc)

    i_design = 1.25 * flc
    res.add("st_motor_cond", ref("motor_cond", ed), flc=flc, amps=i_design)

    pct = T.MOTOR_OCPD_PERCENT[device]
    if device == "inst_cb" and design_b_ee:
        pct = T.MOTOR_OCPD_PERCENT_DESIGN_B_EE_INST
    max_calc = flc * pct
    if device == "inst_cb":
        ocpd = max_calc  # adjustable MCP: report maximum trip setting
        res.add("st_motor_mcp", ref("motor_ocpd", ed), pct=pct * 100,
                flc=flc, amps=max_calc)
        ocpd_frame = next_std_ocpd(max(i_design, 15))
        prot_rating = ocpd_frame
    else:
        ocpd = next_std_ocpd(max(max_calc, 15))
        res.add("st_motor_ocpd", ref("motor_ocpd", ed), pct=pct * 100,
                flc=flc, amps=max_calc, ocpd=ocpd)
        prot_rating = ocpd

    size_conductors(i_design, flc, prot_rating, w, skip_protection=True,
                    res=res)

    ol_pct = 1.25 if sf_115 else 1.15
    fla = nameplate_fla or flc
    ol = fla * ol_pct
    res.add("st_motor_ol", ref("motor_ol", ed), fla=fla, pct=ol_pct * 100,
            amps=ol)
    disc_min = 1.15 * flc
    # fusible switch must also accept the fuse rating; for breaker
    # protection the local disconnect only needs the 115 % FLC rating
    fused = device in ("td_fuse", "ntd_fuse")
    switch = next_switch(max(disc_min, prot_rating) if fused else disc_min)
    res.add("st_motor_disc", ref("motor_disc", ed), flc=flc,
            amps=disc_min, switch=switch)
    res.summary.update({"flc": flc, "i_design": i_design, "i_load": flc,
                        "ocpd": ocpd, "ocpd_device": device,
                        "overload": ol, "switch": switch,
                        "va": flc * w.voltage * (SQRT3 if phases == 3
                                                 else 1)})
    return res


# ---------------------------------------------------------------------------
# Medium-voltage cable (e.g. 24.9 kV)
# ---------------------------------------------------------------------------
@dataclass
class MVInput:
    kv: float = 24.9
    amps: float = 50.0
    material: str = "cu"
    insulation_level: str = "25kV_133"
    fault_ka: float = 10.0
    clear_time_s: float = 0.5
    t_oper: float = 90.0
    t_sc: float = 250.0
    ocpd_type: str = "fuse"       # "fuse" | "relay"
    ocpd_amps: float = 0.0        # fuse continuous rating / relay pickup
    design_factor: float = 1.25
    conduit_type: str = "PVC40"
    cable_od_in: float = 0.0      # 0 = typical
    include_egc: bool = True
    edition: str = "2023"
    ampacity_table: Optional[dict] = None  # override MV ampacities


def sc_min_cmil(fault_ka, t_s, material, t1, t2):
    k, tk = T.SC_CONST[material]
    denom = k * math.log10((t2 + tk) / (t1 + tk))
    return fault_ka * 1000.0 * math.sqrt(t_s / denom)


def design_mv_cable(m: MVInput):
    ed = m.edition
    res = Result("mv_cable")
    amp_tbl = m.ampacity_table or T.MV_AMPACITY_TYPICAL[m.material]
    min_size = next(s for kv, s in T.MV_MIN_SIZE if m.kv <= kv) \
        if m.kv <= T.MV_MIN_SIZE[-1][0] else None
    if min_size is None:
        raise CalcError("err_mv_kv", kv=m.kv)
    res.add("st_mv_min", ref("mv_min_size", ed), kv=m.kv,
            size=T.size_label(min_size))

    i_req = m.amps * m.design_factor
    res.add("st_mv_design", ref("mv_feeder", ed), amps=m.amps,
            factor=m.design_factor, req=i_req)
    a_sc = sc_min_cmil(m.fault_ka, m.clear_time_s, m.material, m.t_oper,
                       m.t_sc)
    res.add("st_mv_sc", ref("sc_withstand", ed), ka=m.fault_ka,
            t=m.clear_time_s, t1=m.t_oper, t2=m.t_sc, cmil=a_sc)
    mult = 3.0 if m.ocpd_type == "fuse" else 6.0

    chosen = None
    for s in T.MV_SIZES:
        if s not in amp_tbl:
            continue
        if T.CMIL[s] < T.CMIL.get(min_size, 0):
            continue
        amp = amp_tbl[s]
        if amp < i_req or T.CMIL[s] < a_sc:
            continue
        if m.ocpd_amps and m.ocpd_amps > mult * amp:
            continue
        chosen = s
        break
    if not chosen:
        raise CalcError("err_no_conductor", amps=round(i_req, 1))
    amp = amp_tbl[chosen]
    res.add("st_mv_size", ref("mv_ampacity", ed), size=T.size_label(chosen),
            amps=amp, req=i_req, cmil=T.CMIL[chosen], sc=a_sc, ok=True)
    if m.ocpd_amps:
        res.add("st_mv_ocpd", ref("mv_conductor_ocpd", ed),
                ok=m.ocpd_amps <= mult * amp, ocpd=m.ocpd_amps,
                mult=mult, amps=amp, limit=mult * amp)
    if m.ampacity_table is None:
        res.warn("w_mv_typical")

    # EGC 250.190(C)(3): per 250.122, not smaller than 6 AWG Cu / 4 AWG Al
    egc = None
    if m.include_egc:
        rating = m.ocpd_amps or next_std_ocpd(i_req) or 6000
        egc = egc_size(rating, m.material)
        floor = "6" if m.material == "cu" else "4"
        if cmil_of(egc) < cmil_of(floor):
            egc = floor
        res.add("st_mv_egc", ref("mv_egc", ed), rating=rating,
                size=T.size_label(egc))

    od = m.cable_od_in or T.MV_CABLE_OD_TYPICAL.get(
        m.insulation_level, T.MV_CABLE_OD_TYPICAL["25kV_133"]).get(chosen)
    items = [(3, math.pi * od * od / 4.0)]
    if egc:
        items.append((1, wire_area(egc, "THHN")))
    cond = select_conduit(items, m.conduit_type)
    jam = None
    if cond:
        d_id = math.sqrt(4 * cond["conduit_area"] / math.pi)
        jam = 1.05 * d_id / od  # 1.05 allows for bends (IEEE 1185 practice)
        res.add("st_conduit", ref("mv_fill", ed), n=cond["count"],
                area=cond["wire_area"], trade=cond["trade"],
                ctype=m.conduit_type, fill=cond["fill_pct"],
                maxfill=cond["max_pct"], qty=1)
        if 2.8 <= jam <= 3.2:
            res.warn("w_jam", ratio=jam)
    else:
        res.warn("w_conduit_none", ctype=m.conduit_type)
    if not m.cable_od_in:
        res.warn("w_mv_od_typical", od=od)

    res.summary.update({
        "size": chosen, "size_label": T.size_label(chosen), "ampacity": amp,
        "i_load": m.amps, "i_design": i_req, "sc_cmil": a_sc,
        "egc": T.size_label(egc) if egc else "-",
        "conduit": f'{cond["trade"]}" {m.conduit_type}' if cond else "-",
        "od": od, "jam": jam,
        "wire_text": (f"3-1/C #{chosen} {'CU' if m.material == 'cu' else 'AL'}"
                      f" MV-105/MV-90 {m.insulation_level.replace('_', ' ')}%"
                      + (f" + 1#{egc}G" if egc else "")
                      + (f', {cond["trade"]}" {m.conduit_type}'
                         if cond else "")),
    })
    return res


# ---------------------------------------------------------------------------
# Transformer (e.g. 24.9 kV -> 480Y/277 V, 480 V -> 208Y/120 V)
# ---------------------------------------------------------------------------
@dataclass
class TransformerInput:
    kva: float = 1500.0
    pri_v: float = 24900.0
    sec_v: float = 480.0
    phases: int = 3
    z_pct: float = 5.75
    location: str = "any"           # "any" | "supervised"
    pri_device: str = "fuse"        # "fuse" | "cb"
    sec_device: str = "cb"
    lv_scheme: str = "pri_sec"      # 450.3(B): "pri_only" | "pri_sec"
    edition: str = "2023"


def design_transformer(x: TransformerInput, sec_wiring: WiringInput = None,
                       pri_wiring: WiringInput = None,
                       mv: MVInput = None):
    ed = x.edition
    res = Result("transformer")
    k = SQRT3 if x.phases == 3 else 1.0
    i_pri = x.kva * 1000.0 / (k * x.pri_v)
    i_sec = x.kva * 1000.0 / (k * x.sec_v)
    res.add("st_xfmr_fla", "", kva=x.kva, pv=x.pri_v, sv=x.sec_v,
            ip=i_pri, is_=i_sec)
    isc = i_sec * 100.0 / x.z_pct if x.z_pct else None
    if isc:
        res.add("st_xfmr_isc", "", z=x.z_pct, isc=isc / 1000.0)

    if x.pri_v > 1000:
        zc = "le6" if x.z_pct <= 6.0 else "6to10"
        if x.z_pct > 10.0:
            raise CalcError("err_z_range")
        p_cb, p_fu, s_hv_cb, s_hv_fu, s_lv = T.XFMR_450_3A[(x.location, zc)]
        p_pct = p_fu if x.pri_device == "fuse" else p_cb
        if x.sec_v > 1000:
            s_pct = s_hv_fu if x.sec_device == "fuse" else s_hv_cb
        else:
            s_pct = s_lv
        p_max = i_pri * p_pct
        ratings = T.MV_FUSE_E_RATINGS if x.pri_device == "fuse" else None
        p_max_std = next_std_ocpd(p_max, ratings) if ratings else \
            round(p_max, 1)
        # typical practice: fuse ~150-200 % FLA to ride through inrush
        p_sel = next_std_ocpd(i_pri * 1.5, ratings) if ratings else \
            round(i_pri * 1.25, 1)
        if ratings and p_sel and p_max_std and p_sel > p_max_std:
            p_sel = p_max_std
        res.add("st_xfmr_pri_mv", ref("xfmr_mv", ed), loc=x.location,
                z=x.z_pct, dev=x.pri_device, pct=p_pct * 100, amps=p_max,
                std=p_max_std, sel=p_sel)
        ref_sec = ref("xfmr_mv", ed)
    else:
        if x.lv_scheme == "pri_only":
            p_pct = 1.25 if i_pri >= 9 else (1.67 if i_pri >= 2 else 3.0)
            s_pct = None
        else:
            p_pct = 2.50
            s_pct = 1.25 if i_sec >= 9 else 1.67
        p_max = i_pri * p_pct
        if x.lv_scheme == "pri_only" and i_pri >= 9:
            p_max_std = next_std_ocpd(p_max)
        else:
            p_max_std = max_std_ocpd(p_max)
        p_sel = next_std_ocpd(i_pri * 1.25)
        if p_max_std and p_sel > p_max_std:
            p_sel = p_max_std
        res.add("st_xfmr_pri_lv", ref("xfmr_lv", ed), scheme=x.lv_scheme,
                pct=p_pct * 100, amps=p_max, std=p_max_std, sel=p_sel)
        ref_sec = ref("xfmr_lv", ed)

    s_sel = None
    if s_pct:
        s_max = i_sec * s_pct
        s_sel = next_std_ocpd(i_sec * 1.25)
        s_max_std = next_std_ocpd(s_max) if s_pct in (1.25,) \
            else max_std_ocpd(s_max)
        if s_max_std and s_sel and s_sel > s_max_std:
            s_sel = s_max_std
        res.add("st_xfmr_sec", ref_sec, pct=s_pct * 100, amps=s_max,
                std=s_max_std, sel=s_sel)

    res.summary.update({"i_pri": i_pri, "i_sec": i_sec, "isc_ka":
                        (isc / 1000.0) if isc else None,
                        "pri_ocpd": p_sel, "pri_ocpd_max": p_max_std,
                        "sec_ocpd": s_sel})

    # ---- conductors ----------------------------------------------------
    if x.pri_v > 1000:
        m = mv or MVInput(edition=ed)
        m.kv = x.pri_v / 1000.0
        m.amps = i_pri
        if p_sel:
            m.ocpd_type = "fuse" if x.pri_device == "fuse" else "relay"
            m.ocpd_amps = p_sel
        res.children["primary"] = design_mv_cable(m)
    elif pri_wiring is not None:
        pri_wiring.voltage = x.pri_v
        pr = Result("primary")
        size_conductors(i_pri * 1.25, i_pri, p_sel, pri_wiring, res=pr)
        pr.summary.update({"ocpd": p_sel, "i_load": i_pri,
                           "i_design": i_pri * 1.25})
        res.children["primary"] = pr

    if sec_wiring is not None and x.sec_v <= 1000:
        sec_wiring.voltage = x.sec_v
        sr = Result("secondary")
        size_conductors(i_sec * 1.25, i_sec, s_sel or next_std_ocpd(
            i_sec * 1.25), sec_wiring, res=sr)
        sr.add("st_xfmr_sec_cond", ref("xfmr_sec_cond", ed))
        sr.summary.update({"ocpd": s_sel, "i_load": i_sec,
                           "i_design": i_sec * 1.25})
        res.children["secondary"] = sr
    return res
