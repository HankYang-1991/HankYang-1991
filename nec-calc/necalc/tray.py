"""Cable tray selection per NEC Article 392.

Supported scenarios
  * LV (<= 2000 V) multiconductor power / control cables   - 392.22(A)
      ladder or ventilated trough  -> Table 392.22(A) col. 1 / col. 2
      solid bottom                 -> Table 392.22(A) col. 3 / col. 4
      control / signal cables only -> 50 % (ladder) / 40 % (solid) of W x D
  * LV single-conductor cables (1/0 AWG and larger)          - 392.22(B)(1)
  * MV (> 2000 V) single or multiconductor cables            - 392.22(C)
  * MV and LV in the same tray need a solid fixed barrier    - 392.20(B)
  * Ampacity in tray                                         - 392.80
"""
import math
from dataclasses import dataclass, field, asdict

from . import tables as T
from .codes import ref
from .engine import (Result, CalcError, temp_factor, ccc_factor,
                     base_ampacity, cmil_of)

KINDS = ("lv_multi", "lv_single", "control", "mv_single", "mv_multi")
ARRANGEMENTS = ("random", "spaced")

CMIL_4_0 = T.CMIL["4/0"]
CMIL_1_0 = T.CMIL["1/0"]


@dataclass
class TrayCable:
    name: str = "Cable"
    kind: str = "lv_multi"
    size: str = "4/0"
    n_cond: int = 3          # power conductors in a multiconductor cable
    qty: int = 1             # number of cables (single conductors: count)
    od_in: float = 0.0       # 0 = typical / NEC Chapter 9 Table 5
    material: str = "cu"
    ins_level: str = "25kV_133"

    # -- geometry ---------------------------------------------------------
    def od(self):
        if self.od_in:
            return self.od_in
        if self.kind == "lv_single":
            a = T.WIRE_AREA["XHHW"].get(self.size)
            if a is None:
                raise CalcError("err_tray_od", size=self.size)
            return math.sqrt(4 * a / math.pi)
        if self.kind == "lv_multi":
            d = T.TC_3C_OD_TYPICAL.get(self.size)
            if d is None:
                raise CalcError("err_tray_od", size=self.size)
            return d * (T.TC_4C_OD_FACTOR if self.n_cond >= 4 else 1.0)
        if self.kind in ("mv_single", "mv_multi"):
            tbl = T.MV_CABLE_OD_TYPICAL.get(self.ins_level,
                                            T.MV_CABLE_OD_TYPICAL["25kV_133"])
            d = tbl.get(self.size)
            if d is None:
                raise CalcError("err_tray_od", size=self.size)
            if self.kind == "mv_multi":
                d = d * T.MV_3C_OD_FACTOR + T.MV_3C_JACKET_IN
            return d
        return 0.50  # control cable default

    def area(self):
        d = self.od()
        return math.pi * d * d / 4.0

    def od_is_typical(self):
        return not self.od_in and self.kind != "lv_single"

    def is_mv(self):
        return self.kind in ("mv_single", "mv_multi")


@dataclass
class TrayInput:
    tray_type: str = "ladder"        # ladder | vented_trough | solid_bottom
    depth_in: float = 4.0
    width_in: float = 0.0            # 0 = auto-select standard width
    covered: bool = False            # solid cover > 6 ft
    arrangement: str = "random"      # random | spaced (single layer)
    ambient_c: float = 30.0
    cables: list = field(default_factory=list)
    edition: str = "2023"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        x = cls(**{k: v for k, v in d.items() if k != "cables"})
        x.cables = [TrayCable(**c) for c in d.get("cables", [])]
        return x


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _table_value(table, width):
    """Table 392.22 value at ``width`` (linear interpolation between listed
    widths, proportional below 6 in / beyond 36 in)."""
    ws = sorted(table)
    if width in table:
        return table[width]
    if width <= ws[0]:
        return table[ws[0]] * width / ws[0]
    if width >= ws[-1]:
        return table[ws[-1]] * width / ws[-1]
    for a, b in zip(ws, ws[1:]):
        if a <= width <= b:
            return table[a] + (table[b] - table[a]) * (width - a) / (b - a)
    return 0.0


def _width_for(table, value):
    """Inverse of _table_value: smallest width whose table value >= value."""
    if value <= 0:
        return 0.0
    ws = sorted(table)
    if value <= table[ws[0]]:
        return ws[0] * value / table[ws[0]]
    for a, b in zip(ws, ws[1:]):
        if table[a] <= value <= table[b]:
            return a + (b - a) * (value - table[a]) / (table[b] - table[a])
    return ws[-1] * value / table[ws[-1]]


def _expand(cables, kinds):
    return [c for c in cables if c.kind in kinds and c.qty > 0]


# ---------------------------------------------------------------------------
# Required width per section
# ---------------------------------------------------------------------------
def _lv_multi_width(cables, x, res):
    """392.22(A) - multiconductor power and/or control cables."""
    ed = x.edition
    solid = x.tray_type == "solid_bottom"
    power = [c for c in cables if c.kind == "lv_multi"]
    control = [c for c in cables if c.kind == "control"]
    if not power and control:
        area = sum(c.qty * c.area() for c in control)
        pct = T.TRAY_CONTROL_PCT[x.tray_type]
        depth = min(x.depth_in, 6.0)
        w = area / (pct * depth)
        res.add("st_tray_control", ref("tray_fill_control", ed), area=area,
                pct=pct * 100, depth=depth, width=w)
        return w, {"rule": "control", "area": area}

    large = [c for c in power if cmil_of(c.size) >= CMIL_4_0]
    small = [c for c in power if cmil_of(c.size) < CMIL_4_0] + control
    sd = sum(c.qty * c.od() for c in large)
    a_s = sum(c.qty * c.area() for c in small)
    if solid:
        col, k, col_name = T.TRAY_A_COL3, T.TRAY_A_COL4_K, "3/4"
    else:
        col, k, col_name = T.TRAY_A_COL1, T.TRAY_A_COL2_K, "1/2"
    if a_s == 0:
        w = sd / (T.TRAY_SOLID_LARGE_PCT if solid else 1.0)
        res.add("st_tray_multi_large", ref("tray_fill_multi", ed), sd=sd,
                pct=(T.TRAY_SOLID_LARGE_PCT if solid else 1.0) * 100,
                width=w)
    elif sd == 0:
        w = _width_for(col, a_s)
        res.add("st_tray_multi_small", ref("tray_fill_multi", ed), area=a_s,
                col=col_name.split("/")[0], width=w)
    else:
        w = max(sd, _width_for(col, a_s + k * sd))
        res.add("st_tray_multi_mixed", ref("tray_fill_multi", ed), area=a_s,
                sd=sd, k=k, col=col_name.split("/")[1], width=w)
    return w, {"rule": "multi", "sd": sd, "area": a_s, "col": col, "k": k,
               "solid": solid}


def _lv_single_width(cables, x, res):
    """392.22(B)(1) - single conductors 1/0 AWG and larger."""
    ed = x.edition
    if x.tray_type == "solid_bottom":
        res.warn("w_tray_single_solid")
    small = [c for c in cables if cmil_of(c.size) < CMIL_1_0]
    if small:
        res.warn("w_tray_single_min",
                 sizes=", ".join(sorted({c.size for c in small})))
    s1000 = sum(c.qty * c.od() for c in cables
                if cmil_of(c.size) >= 1_000_000)
    a250 = sum(c.qty * c.area() for c in cables
               if 250_000 <= cmil_of(c.size) < 1_000_000)
    any_small = any(cmil_of(c.size) <= CMIL_4_0 for c in cables)
    sd_all = sum(c.qty * c.od() for c in cables)
    w = 0.0
    if any_small:
        w = max(w, sd_all)
        res.add("st_tray_single_dia", ref("tray_fill_single", ed), sd=sd_all)
    if a250 and s1000:
        w = max(w, s1000, _width_for(T.TRAY_B_COL1,
                                     a250 + T.TRAY_B_COL2_K * s1000))
        res.add("st_tray_single_mixed", ref("tray_fill_single", ed),
                area=a250, sd=s1000, k=T.TRAY_B_COL2_K, width=w)
    elif a250:
        w = max(w, _width_for(T.TRAY_B_COL1, a250))
        res.add("st_tray_single_area", ref("tray_fill_single", ed),
                area=a250, width=w)
    elif s1000 and not any_small:
        w = max(w, s1000)
        res.add("st_tray_single_large", ref("tray_fill_single", ed), sd=s1000)
    return w, {"rule": "single", "s1000": s1000, "a250": a250,
               "sd_all": sd_all, "any_small": any_small}


def _mv_width(cables, x, res):
    """392.22(C) - cables over 2000 V: sum of diameters <= width, 1 layer."""
    sd = sum(c.qty * c.od() for c in cables)
    res.add("st_tray_mv", ref("tray_fill_mv", x.edition), sd=sd)
    return sd, {"rule": "mv", "sd": sd}


# ---------------------------------------------------------------------------
# Ampacity in tray - 392.80
# ---------------------------------------------------------------------------
def tray_ampacity(c: TrayCable, x: TrayInput):
    """Return (amps, detail dict) for one cable in the tray."""
    spaced = x.arrangement == "spaced" and not x.covered
    if c.kind == "lv_multi":
        base = base_ampacity(c.size, c.material, 90)
        if base is None:
            return None, {}
        ft = temp_factor(x.ambient_c, 90)
        fa = ccc_factor(c.n_cond)
        fc = T.TRAY_AMP_LV_MULTI_COVERED if x.covered else 1.0
        return base * ft * fa * fc, {"base": base, "ft": ft, "fa": fa,
                                     "fc": fc, "tbl": "310.16"}
    if c.kind == "lv_single":
        tbl = T.AMPACITY_FREE_AIR_CU if c.material == "cu" else \
            T.AMPACITY_FREE_AIR_AL
        row = tbl.get(c.size)
        if row is None:
            return None, {}
        base = row[2]
        if spaced:
            fc = 1.0
        else:
            key = "ge600" if cmil_of(c.size) >= 600_000 else "1/0-500"
            fc = T.TRAY_AMP_LV_SINGLE[key][1 if x.covered else 0]
        ft = temp_factor(x.ambient_c, 90)
        return base * ft * fc, {"base": base, "ft": ft, "fa": 1.0, "fc": fc,
                                "tbl": "310.17"}
    if c.kind in ("mv_single", "mv_multi"):
        base = T.MV_AMPACITY_AIR_TYPICAL[c.material].get(c.size)
        if base is None:
            return None, {}
        # 315.60(D) style correction from 40 C ambient, 90 C conductor
        ft = math.sqrt(max(90.0 - x.ambient_c, 0.0) / 50.0)
        if c.kind == "mv_single":
            fc = 1.0 if spaced else T.TRAY_AMP_MV_SINGLE[1 if x.covered
                                                         else 0]
            fa = 1.0
        else:
            fa = 0.80  # 3/C vs isolated single conductor (TYPICAL)
            fc = T.TRAY_AMP_MV_MULTI_COVERED if x.covered else 1.0
        return base * ft * fa * fc, {"base": base, "ft": ft, "fa": fa,
                                     "fc": fc, "tbl": "315.60*"}
    return None, {}


# ---------------------------------------------------------------------------
# Main design function
# ---------------------------------------------------------------------------
def required_width(x: TrayInput, res=None):
    """Return (total required width, sections dict)."""
    res = res or Result("tray")
    cables = [c for c in x.cables if c.qty > 0]
    if not cables:
        raise CalcError("err_tray_empty")
    sections = {}
    lv_multi = _expand(cables, ("lv_multi", "control"))
    lv_single = _expand(cables, ("lv_single",))
    mv = _expand(cables, ("mv_single", "mv_multi"))
    if lv_multi:
        sections["lv_multi"] = _lv_multi_width(lv_multi, x, res)
    if lv_single:
        sections["lv_single"] = _lv_single_width(lv_single, x, res)
    if mv:
        sections["mv"] = _mv_width(mv, x, res)
    total = sum(w for w, _ in sections.values())
    return total, sections, res


def design_tray(x: TrayInput):
    ed = x.edition
    res = Result("tray")
    total, sections, _ = required_width(x, res)
    has_mv = "mv" in sections
    has_lv = "lv_multi" in sections or "lv_single" in sections
    if has_mv and has_lv:
        res.add("st_tray_barrier", ref("tray_separation", ed))
        res.warn("w_tray_mv_lv")
    if len(sections) > 1:
        res.add("st_tray_sum", "", parts=" + ".join(
            f"{w:.2f}" for w, _ in sections.values()), width=total)

    max_od = max(c.od() for c in x.cables if c.qty > 0)
    if max_od > x.depth_in:
        res.warn("w_tray_depth", od=max_od, depth=x.depth_in)
    if any(c.od_is_typical() for c in x.cables if c.qty > 0):
        res.warn("w_tray_od_typical")

    n_trays = 1
    if x.width_in:
        width = x.width_in
        ok = total <= width + 1e-9
        res.add("st_tray_check", ref("tray_fill_multi", ed)
                if "lv_multi" in sections else "392.22", ok=ok,
                width=width, req=total, fill=100 * total / width)
        if width not in T.TRAY_WIDTHS:
            res.warn("w_tray_nonstd", width=width)
    else:
        width = next((w for w in T.TRAY_WIDTHS if w >= total - 1e-9), None)
        if width is None:
            n_trays = math.ceil(total / T.TRAY_WIDTHS[-1] - 1e-9)
            width = T.TRAY_WIDTHS[-1]
            res.warn("w_tray_multiple", n=n_trays, req=total)
        res.add("st_tray_select", "NEMA VE 1", req=total, width=width,
                n=n_trays, fill=100 * total / (width * n_trays))

    # ampacity of each cable in the tray (392.80)
    amp_rows = []
    for c in x.cables:
        if c.qty <= 0:
            continue
        a, d = tray_ampacity(c, x)
        if a is None:
            continue
        key = {"lv_multi": "tray_amp_lv_multi",
               "lv_single": "tray_amp_lv_single"}.get(c.kind, "tray_amp_mv")
        res.add("st_tray_amp", ref(key, ed), name=c.name,
                size=T.size_label(c.size),
                base=d["base"], tbl=d["tbl"], ft=d["ft"], fa=d["fa"],
                fc=d["fc"], amps=a)
        amp_rows.append((c.name, c.size, a))
    if any(c.is_mv() for c in x.cables):
        res.warn("w_tray_mv_amp_typical")
    if any(c.kind == "lv_single" for c in x.cables):
        res.add("st_tray_single_note", ref("tray_single_min", ed))

    res.summary.update({
        "req_width": total,
        "width": width,
        "n_trays": n_trays,
        "fill_pct": 100 * total / (width * n_trays),
        "tray_text": (f"{n_trays} x " if n_trays > 1 else "") +
                     f'{width:g}" W x {x.depth_in:g}" D',
        "tray_type": x.tray_type,
        "ampacities": amp_rows,
    })
    return res


# ---------------------------------------------------------------------------
# Capacity table: maximum number of identical cables per tray width
# ---------------------------------------------------------------------------
def max_cables(kind, size, width, tray_type="ladder", depth_in=4.0, n_cond=3,
               material="cu", ins_level="25kV_133", od_in=0.0, limit=999):
    x = TrayInput(tray_type=tray_type, depth_in=depth_in)
    c = TrayCable(kind=kind, size=size, n_cond=n_cond, material=material,
                  ins_level=ins_level, od_in=od_in, qty=1)
    if kind == "lv_single" and cmil_of(size) < CMIL_1_0:
        return 0
    if kind == "lv_single" and tray_type == "solid_bottom":
        return 0
    try:
        c.od()
    except CalcError:
        return None
    if c.od() > depth_in:
        return 0
    x.cables = [c]
    lo, hi = 0, limit
    # required width is monotonic in qty -> binary search
    while lo < hi:
        mid = (lo + hi + 1) // 2
        c.qty = mid
        w, _, _ = required_width(x, Result("tmp"))
        if w <= width + 1e-9:
            lo = mid
        else:
            hi = mid - 1
    return lo


def capacity_table(kind, sizes=None, widths=None, **kw):
    """Return {size: {width: max_count}}."""
    widths = widths or T.TRAY_WIDTHS
    if sizes is None:
        if kind == "lv_multi":
            sizes = list(T.TC_3C_OD_TYPICAL)
        elif kind == "lv_single":
            sizes = [s for s in T.WIRE_AREA["XHHW"]
                     if cmil_of(s) >= CMIL_1_0]
        elif kind in ("mv_single", "mv_multi"):
            sizes = list(T.MV_SIZES)
        else:
            sizes = ["-"]
    out = {}
    for s in sizes:
        out[s] = {w: max_cables(kind, s, w, **kw) for w in widths}
    return out
