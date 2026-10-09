"""VFD harmonic current / voltage distortion at the point of common
coupling (PCC) per IEEE 519-2022, transformer K-factor, mitigation options
and active harmonic filter sizing.

Each drive's fundamental input current comes from its output power
(HP x load / efficiency, displacement PF by front end) or a nameplate
input current.  Harmonic currents use a typical spectrum for the front
end, optionally scaled to a manufacturer THDi.  Same-order currents of
all drives are added arithmetically (conservative).  Voltage harmonics
are estimated as V_h % = 100 x h x I_h / I_sc.
"""
import math
from dataclasses import dataclass, field, asdict

from . import tables as T
from .codes import ref
from .engine import Result, CalcError, SQRT3

# mitigation option -> mapping of drive front ends
MITIGATIONS = {
    "mit_ac5": {"6p": "6p_ac5"},
    "mit_passive": {"6p": "6p_passive", "6p_ac3": "6p_passive",
                    "6p_ac5": "6p_passive", "6p_dc": "6p_passive"},
    "mit_18p": {"6p": "18p", "6p_ac3": "18p", "6p_ac5": "18p",
                "6p_dc": "18p"},
}


@dataclass
class HarmDrive:
    name: str = "VFD-1"
    qty: int = 1
    hp: float = 50.0
    drive_type: str = "6p_ac3"
    load_pct: float = 100.0
    input_a: float = 0.0        # rated input current per drive, 0 = calc
    thd_pct: float = 0.0        # manufacturer THDi, 0 = typical spectrum

    def to_dict(self):
        return asdict(self)


@dataclass
class HarmInput:
    voltage: float = 480.0
    isc_ka: float = 50.0        # available fault current at the PCC
    il_a: float = 0.0           # maximum demand load current, 0 = connected
    linear_a: float = 0.0       # other (linear) load current at the PCC
    drives: list = field(default_factory=list)
    edition: str = "2023"


def spectrum_thd(kind):
    return math.sqrt(sum(v * v for v in T.HARM_SPECTRA[kind].values()))


def drive_fundamental(d: HarmDrive, voltage):
    """Total fundamental input current of the drive group (A)."""
    load = d.load_pct / 100.0
    if d.input_a:
        unit = d.input_a * load
    else:
        p_in = d.hp * 0.746 * load / T.HARM_DRIVE_EFF          # kW
        unit = p_in * 1000.0 / (SQRT3 * voltage * T.HARM_DPF[d.drive_type])
    return unit * max(int(d.qty), 0)


def drive_harmonics(d: HarmDrive, kind, voltage, use_override=True):
    """{h: amps} for a drive group with front end ``kind``."""
    i1 = drive_fundamental(d, voltage)
    spec = T.HARM_SPECTRA[kind]
    scale = 1.0
    if use_override and d.thd_pct:
        scale = d.thd_pct / spectrum_thd(kind)
    return {h: i1 * spec[h] / 100.0 * scale for h in T.HARM_ORDERS}


def ieee519_current_limits(ratio):
    for upper, ind, tdd in T.IEEE519_I_LIMITS:
        if ratio < upper:
            return ind, tdd
    return T.IEEE519_I_LIMITS[-1][1], T.IEEE519_I_LIMITS[-1][2]


def individual_limit(h, ind):
    b = T.IEEE519_H_BANDS
    for k in range(len(b) - 1):
        if b[k] <= h < b[k + 1]:
            return ind[k]
    return ind[-1]


def voltage_limits(voltage):
    kv = voltage / 1000.0
    for upper, ind, thd in T.IEEE519_V_LIMITS:
        if kv <= upper:
            return ind, thd
    return T.IEEE519_V_LIMITS[-1][1], T.IEEE519_V_LIMITS[-1][2]


def analyze(x: HarmInput, kinds=None, use_override=True):
    """Totals for the PCC.  ``kinds`` optionally replaces each drive's
    front end (list aligned with x.drives)."""
    ih = {h: 0.0 for h in T.HARM_ORDERS}
    i1 = 0.0
    for n, d in enumerate(x.drives):
        kind = kinds[n] if kinds else d.drive_type
        same = kind == d.drive_type
        for h, a in drive_harmonics(d, kind, x.voltage,
                                    use_override and same).items():
            ih[h] += a
        i1 += drive_fundamental(d, x.voltage)
    il = x.il_a or (i1 + x.linear_a)
    if il <= 0:
        raise CalcError("err_h_no_load")
    isc = x.isc_ka * 1000.0
    ratio = isc / il
    ind, tdd_lim = ieee519_current_limits(ratio)
    h_rms = math.sqrt(math.fsum(a * a for a in ih.values()))
    tdd = 100.0 * h_rms / il
    vh = {h: 100.0 * h * a / isc for h, a in ih.items()}
    vthd = math.sqrt(math.fsum(v * v for v in vh.values()))
    i_fund = i1 + x.linear_a
    k_num = i_fund ** 2 + math.fsum(a * a * h * h for h, a in ih.items())
    k_den = i_fund ** 2 + h_rms ** 2
    return {"ih": ih, "i1": i1, "il": il, "isc": isc, "ratio": ratio,
            "ind": ind, "tdd_lim": tdd_lim, "h_rms": h_rms, "tdd": tdd,
            "vh": vh, "vthd": vthd, "k": k_num / k_den if k_den else 1.0}


def _compliant(a, v_ind, v_thd):
    ok_i = all(100.0 * amp / a["il"] <= individual_limit(h, a["ind"]) + 1e-9
               for h, amp in a["ih"].items())
    return (ok_i and a["tdd"] <= a["tdd_lim"] + 1e-9 and
            a["vthd"] <= v_thd + 1e-9 and
            max(a["vh"].values()) <= v_ind + 1e-9)


def ahf_size(required_a):
    """(units, frame A) of the smallest active filter combination."""
    if required_a <= 0:
        return 0, 0
    for s in T.AHF_SIZES:
        if s >= required_a - 1e-9:
            return 1, s
    big = T.AHF_SIZES[-1]
    return math.ceil(required_a / big - 1e-9), big


def design_harmonics(x: HarmInput):
    ed = x.edition
    res = Result("harmonics")
    drives = [d for d in x.drives if d.qty > 0]
    if not drives:
        raise CalcError("err_h_empty")
    x.drives = drives
    for d in drives:
        i1 = drive_fundamental(d, x.voltage)
        thd = d.thd_pct or spectrum_thd(d.drive_type)
        res.add("st_h_drive", ref("h_drive", ed), name=d.name, qty=d.qty,
                hp=d.hp, kind=d.drive_type, load=d.load_pct, i1=i1, thd=thd)
    a = analyze(x)
    v_ind, v_thd = voltage_limits(x.voltage)
    res.add("st_h_il", ref("h_limits", ed), il=a["il"],
            src="il_given" if x.il_a else "il_connected",
            isc=x.isc_ka, ratio=a["ratio"], tdd=a["tdd_lim"])
    if not x.il_a:
        res.warn("w_h_il_connected")
    for h in T.HARM_ORDERS:
        pct = 100.0 * a["ih"][h] / a["il"]
        lim = individual_limit(h, a["ind"])
        res.add("st_h_order", ref("h_limits", ed), ok=pct <= lim + 1e-9,
                h=h, amps=a["ih"][h], pct=pct, lim=lim)
    res.add("st_h_tdd", ref("h_limits", ed), ok=a["tdd"] <= a["tdd_lim"]
            + 1e-9, rms=a["h_rms"], tdd=a["tdd"], lim=a["tdd_lim"])
    vmax = max(a["vh"].values())
    res.add("st_h_vthd", ref("h_vlimits", ed),
            ok=a["vthd"] <= v_thd + 1e-9 and vmax <= v_ind + 1e-9,
            vthd=a["vthd"], lim=v_thd, vmax=vmax, vlim=v_ind)
    k_rated = next((k for k in T.K_RATINGS if k >= a["k"] - 1e-9),
                   T.K_RATINGS[-1])
    res.add("st_h_k", ref("h_kfactor", ed), k=a["k"], kr=k_rated)
    compliant = _compliant(a, v_ind, v_thd)

    # ---- mitigation options ------------------------------------------
    options = []
    for code, mapping in MITIGATIONS.items():
        kinds = [mapping.get(d.drive_type, d.drive_type) for d in drives]
        if kinds == [d.drive_type for d in drives]:
            continue
        b = analyze(x, kinds)
        ok = _compliant(b, v_ind, v_thd)
        res.add("st_h_option", ref("h_mitigation", ed), ok=ok, opt=code,
                tdd=b["tdd"], vthd=b["vthd"])
        options.append({"code": code, "tdd": b["tdd"], "vthd": b["vthd"],
                        "ok": ok})

    # ---- active harmonic filter (proportional cancellation) ----------
    k_need = 0.0
    if a["h_rms"] > 0:
        k_need = max(0.0, 1 - T.AHF_TARGET * a["tdd_lim"] * a["il"] / 100.0
                     / a["h_rms"])
        for h, amp in a["ih"].items():
            if amp > 0:
                lim_a = T.AHF_TARGET * individual_limit(h, a["ind"]) \
                    * a["il"] / 100.0
                k_need = max(k_need, 1 - lim_a / amp)
            vlim_a = T.AHF_TARGET * v_ind * a["isc"] / (100.0 * h)
            if amp > 0:
                k_need = max(k_need, 1 - vlim_a / amp)
        k_v = 1 - T.AHF_TARGET * v_thd / a["vthd"] if a["vthd"] else 0.0
        k_need = min(max(k_need, k_v, 0.0), 1.0)
    req = k_need * a["h_rms"]
    units, frame = ahf_size(req)
    if units:
        res.add("st_h_ahf", ref("h_ahf", ed), rms=a["h_rms"],
                k=k_need * 100.0, req=req, units=units, frame=frame,
                tdd=a["tdd"] * (1 - k_need), vthd=a["vthd"] * (1 - k_need))
        ahf_text = f"{units} x {frame} A" if units > 1 else f"{frame} A"
    else:
        res.add("st_h_ahf_none", ref("h_ahf", ed))
        ahf_text = "-"
    res.warn("w_h_typical")
    if any(d.input_a == 0 for d in drives):
        res.warn("w_h_estimated")

    res.summary.update({
        "tdd": a["tdd"], "tdd_limit": a["tdd_lim"], "vthd": a["vthd"],
        "vthd_limit": v_thd, "ratio": a["ratio"], "il": a["il"],
        "k_factor": a["k"], "k_rated": k_rated, "ahf_req": req,
        "ahf_text": ahf_text, "compliant": compliant,
        "harmonics": [{"h": h, "amps": a["ih"][h],
                       "pct": 100.0 * a["ih"][h] / a["il"],
                       "lim": individual_limit(h, a["ind"]),
                       "vpct": a["vh"][h]} for h in T.HARM_ORDERS],
        "options": options,
    })
    return res
