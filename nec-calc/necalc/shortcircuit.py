"""Available fault current and interrupting rating (IC / AIC) along a
radial path: utility -> transformer -> feeders -> panels (NEC 110.9,
110.10, 110.24).

Ohmic method: source, transformer, cable (Chapter 9 Table 9) and busway
(I-Line Table 5) impedances are added as R + jX, conductor resistance is
corrected to 25 C for the maximum fault, induction motors contribute
4 x FLC, and the symmetrical current is multiplied by the IEEE Std 1015
asymmetry factor for the device's test X/R before comparing with its
interrupting rating.
"""
import math
from dataclasses import dataclass, field, asdict

from . import tables as T
from .codes import ref
from .engine import Result, CalcError, table9_impedance, SQRT3

SEG_KINDS = ("xfmr", "cable", "busway")
XR_INF = 999.0


@dataclass
class SCSource:
    kv: float = 24.9
    fault_ka: float = 0.0       # utility available fault, 0 = infinite bus
    xr: float = 15.0
    z_tol: bool = True          # apply -10 % transformer Z tolerance
    edition: str = "2023"


@dataclass
class SCSegment:
    name: str = "MSB"
    kind: str = "xfmr"          # xfmr | cable | busway
    # transformer
    kva: float = 2500.0
    z_pct: float = 5.75
    xr: float = 8.0
    sec_v: float = 480.0
    # cable / busway
    length_ft: float = 50.0
    size: str = "500"
    sets: int = 1
    material: str = "cu"
    conduit: str = "steel"      # steel | pvc (cable reactance)
    rating: float = 2000.0      # busway rating, A
    # equipment at the bus at the end of this segment
    device: str = "lvpcb"       # mccb | iccb | lvpcb | fuse
    aic_ka: float = 0.0         # selected interrupting rating, 0 = none
    motor_a: float = 0.0        # motor FLC contributing at this bus

    def to_dict(self):
        return asdict(self)


def device_test_xr(device, rating_ka):
    if device == "lvpcb":
        return T.SC_TEST_XR["pf15"]
    if device == "mccb":
        if rating_ka <= 10:
            return T.SC_TEST_XR["pf50"]
        if rating_ka <= 20:
            return T.SC_TEST_XR["pf30"]
    return T.SC_TEST_XR["pf20"]


def asym_factor(xr, device, rating_ka):
    """IEEE 1015 multiplying factor (>= 1) for a system X/R above the
    device test X/R: peak ratio for MCCB/ICCB/fuses, rms ratio for
    LVPCB."""
    xrt = device_test_xr(device, rating_ka)
    if xr <= xrt:
        return 1.0
    if device == "lvpcb":
        mf = (math.sqrt(1 + 2 * math.exp(-2 * math.pi / xr)) /
              math.sqrt(1 + 2 * math.exp(-2 * math.pi / xrt)))
    else:
        mf = ((1 + math.exp(-math.pi / xr)) /
              (1 + math.exp(-math.pi / xrt)))
    return max(mf, 1.0)


def required_aic(total_a, xr, device):
    """Smallest standard interrupting rating >= total x MF (kA)."""
    for r in T.AIC_RATINGS:
        mf = asym_factor(xr, device, r)
        if r * 1000.0 >= total_a * mf - 1e-6:
            return r, mf
    return None, asym_factor(xr, device, T.AIC_RATINGS[-1])


def design_shortcircuit(src: SCSource, segs):
    ed = src.edition
    res = Result("shortcircuit")
    if not segs:
        raise CalcError("err_sc_empty")
    v = src.kv * 1000.0
    if src.fault_ka:
        zs = v / (SQRT3 * src.fault_ka * 1000.0)
        r_tot = zs / math.sqrt(1 + src.xr ** 2)
        x_tot = r_tot * src.xr
        res.add("st_sc_source", ref("sc_source", ed), kv=src.kv,
                ka=src.fault_ka, xr=src.xr, z=zs * 1000.0)
    else:
        r_tot = x_tot = 0.0
        res.add("st_sc_infinite", ref("sc_source", ed), kv=src.kv)
        res.warn("w_sc_infinite")

    buses = []
    labelled = False
    for seg in segs:
        if seg.kind == "xfmr":
            ratio = seg.sec_v / v
            r_tot *= ratio ** 2
            x_tot *= ratio ** 2
            tol = T.SC_Z_TOLERANCE if src.z_tol else 1.0
            zt = seg.z_pct / 100.0 * seg.sec_v ** 2 / (seg.kva * 1000.0) * tol
            rt = zt / math.sqrt(1 + seg.xr ** 2)
            xt = rt * seg.xr
            r_tot += rt
            x_tot += xt
            v = seg.sec_v
            res.add("st_sc_xfmr", ref("sc_xfmr", ed), name=seg.name,
                    kva=seg.kva, z=seg.z_pct, tol=tol, xr=seg.xr,
                    r=rt * 1000.0, x=xt * 1000.0, volts=seg.sec_v)
        else:
            if v > 1000:
                raise CalcError("err_sc_mv_segment", name=seg.name)
            t0 = T.SC_COND_T0[seg.material]
            if seg.kind == "cable":
                r9, x9, _ = table9_impedance(
                    seg.size, seg.material,
                    "PVC40" if seg.conduit == "pvc" else "RMC")
                f = (t0 + T.SC_COND_TEMP) / (t0 + 75.0)
                sets = max(int(seg.sets), 1)
                rr = r9 * f * seg.length_ft / 1000.0 / sets
                xx = x9 * seg.length_ft / 1000.0 / sets
                res.add("st_sc_cable", ref("sc_cable", ed), name=seg.name,
                        sets=sets, size=seg.size, length=seg.length_ft,
                        r=rr * 1000.0, x=xx * 1000.0, corr=f)
            else:
                row = T.ILINE_IMPEDANCE[seg.material].get(seg.rating)
                if row is None:
                    raise CalcError("err_busway_data", rating=seg.rating)
                f = (t0 + T.SC_COND_TEMP) / (t0 + 80.0)
                rr = row[0] / 1000.0 * f * seg.length_ft / 100.0
                xx = row[1] / 1000.0 * seg.length_ft / 100.0
                res.add("st_sc_busway", ref("sc_busway", ed), name=seg.name,
                        rating=seg.rating, length=seg.length_ft,
                        r=rr * 1000.0, x=xx * 1000.0, corr=f)
            r_tot += rr
            x_tot += xx

        z = math.hypot(r_tot, x_tot)
        if z <= 0:
            raise CalcError("err_sc_infinite_bus", name=seg.name)
        isc = v / (SQRT3 * z)
        xr = min(x_tot / r_tot, XR_INF) if r_tot > 0 else XR_INF
        motor = T.SC_MOTOR_MULT * seg.motor_a
        total = isc + motor
        res.add("st_sc_bus", ref("sc_bus", ed), name=seg.name, volts=v,
                r=r_tot * 1000.0, x=x_tot * 1000.0, xr=xr,
                isc=isc / 1000.0, motor=motor / 1000.0,
                total=total / 1000.0)
        req, mf_req = required_aic(total, xr, seg.device)
        if req is None:
            res.add("st_sc_required_none", ref("sc_series", ed),
                    name=seg.name, dev=seg.device, mf=mf_req,
                    adj=total * mf_req / 1000.0, ok=False)
            res.warn("w_sc_exceeds", name=seg.name, ka=total / 1000.0)
        else:
            res.add("st_sc_required", ref("sc_device", ed), name=seg.name,
                    dev=seg.device, xrt=device_test_xr(seg.device, req),
                    mf=mf_req, adj=total * mf_req / 1000.0, req=req)
        ok = None
        if seg.aic_ka:
            mf_sel = asym_factor(xr, seg.device, seg.aic_ka)
            ok = seg.aic_ka * 1000.0 >= total * mf_sel - 1e-6
            res.add("st_sc_aic", ref("sc_device", ed), ok=ok, name=seg.name,
                    aic=seg.aic_ka, mf=mf_sel, adj=total * mf_sel / 1000.0)
        if not labelled and v <= 1000:
            labelled = True
            res.add("st_sc_label", ref("sc_label", ed), name=seg.name,
                    total=total / 1000.0)
        buses.append({"name": seg.name, "volts": v, "isc_ka": isc / 1000.0,
                      "motor_ka": motor / 1000.0,
                      "total_ka": total / 1000.0, "xr": xr,
                      "required_ka": req, "selected_ka": seg.aic_ka or None,
                      "ok": ok})
    if any(s.motor_a for s in segs):
        res.warn("w_sc_motor")
    res.summary.update({
        "buses": buses,
        "bus_count": len(buses),
        "max_fault_ka": max(b["total_ka"] for b in buses),
        "all_ok": all(b["ok"] is not False and b["required_ka"] is not None
                      for b in buses),
    })
    return res
