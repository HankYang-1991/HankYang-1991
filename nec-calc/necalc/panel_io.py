"""Import / export of panel load lists (Excel .xlsx and CSV).

Workbook layout (template and export):
  Panels  - one row per panel: name, system, diversity factor, target PF,
            feeder length
  Loads   - one row per load group, linked to its panel by name
An export adds a Summary sheet (one row per panel, SUM-formula totals) and
a schedule sheet per panel with the calculated values.

The reader is tolerant: English or Chinese headers and common
abbreviations, category / unit / yes-no words in either language,
percentages, fractions (1-1/2 HP), R/S/T phase names, a Panel column that is
filled only on the first row of each group, a single-sheet list with a
System column, and the per-panel CSV this program exports.  Everything it
had to assume is returned as a list of (i18n key, params) notes.
"""
import csv
import datetime
import io
import math
import os
import re
import zipfile
import xml.etree.ElementTree as ET

from . import engine as E
from . import loads as L
from . import report as R
from . import xlsx as X
from .codes import ref
from .i18n import TEXT, tr, opt

LANGS = ("en", "zh")

# Loads / Panels sheet columns (export order) -> header i18n key
LOAD_FIELDS = ("panel", "circuit", "name", "category", "qty", "rating",
               "unit", "pf", "voltage", "phases", "continuous",
               "demand_factor", "phase_conn")
PANEL_FIELDS = ("panel", "system", "diversity", "target_pf",
                "feeder_length")
HEAD_KEY = {"panel": "xl_panel", "circuit": "xl_circuit", "name": "xl_name",
            "category": "xl_cat", "qty": "xl_qty", "rating": "xl_rating",
            "unit": "xl_unit", "pf": "xl_pf", "voltage": "xl_v",
            "phases": "xl_ph", "continuous": "xl_cont",
            "demand_factor": "xl_df", "phase_conn": "xl_conn",
            "system": "xl_system", "diversity": "xl_div",
            "target_pf": "xl_tpf", "feeder_length": "xl_flen"}

DEFAULT_PF = 1.0
DEFAULT_MOTOR_PF = 0.85
DEFAULT_TPF = 0.95
M_TO_FT = 3.28084


def _norm(s):
    """Lower-case, keep only ASCII letters/digits and CJK characters."""
    return re.sub(r"[^0-9a-z一-鿿]", "", str(s).lower())


# ---------------------------------------------------------------------------
# header recognition
# ---------------------------------------------------------------------------
_ALIASES = {
    "panel": ("panel", "panelname", "panelboard", "panelno", "board",
              "盤", "盤名", "盤號", "盤名稱", "配電盤", "分電盤", "盤體"),
    "circuit": ("circuit", "circuitno", "circuitnumber", "ckt", "cktno",
                "cct", "no", "迴路", "迴路編號", "迴路號", "回路", "編號"),
    "name": ("description", "name", "loadname", "loaddescription",
             "circuitdescription", "equipment", "equipmentname", "item",
             "名稱", "負載名稱", "負載", "說明", "設備名稱", "用途", "品名"),
    "category": ("category", "type", "loadtype", "loadcategory", "class",
                 "類別", "種類", "負載類別", "負載種類", "類型"),
    "qty": ("qty", "quantity", "count", "數量", "台數", "只數", "個數"),
    "rating": ("rating", "ratingperunit", "unitrating", "capacity",
               "額定", "額定每台", "容量", "額定容量", "單台容量", "每台容量"),
    "unit": ("unit", "units", "單位"),
    "pf": ("pf", "powerfactor", "功率因數", "功率因素", "功因"),
    "voltage": ("voltage", "volts", "volt", "voltagev", "v", "電壓", "電壓v"),
    "phases": ("phases", "ph", "noofphases", "numberofphases", "相數"),
    "phase_any": ("phase", "相", "相別"),
    "phase_conn": ("phaseconnection", "phaseconn", "conn", "connection",
                   "接相", "接線相", "相序"),
    "continuous": ("continuous", "cont", "continuousload", "連續",
                   "連續負載", "連續性"),
    "demand_factor": ("demandfactor", "df", "demand", "需量因數",
                      "需量因素", "需量係數", "需用率", "需量率"),
    "system": ("system", "panelsystem", "系統", "盤系統", "電壓系統",
               "供電系統"),
    "diversity": ("diversity", "diversityfactor", "參差因數", "參差因素",
                  "參差係數"),
    "target_pf": ("targetpf", "targetpowerfactor", "目標功率因數",
                  "目標功因"),
    "feeder_length": ("feederlength", "feederlengthft", "length", "lengthft",
                      "幹線長度", "饋線長度", "長度"),
    # a "Demand kVA" column marks a calculated schedule (our own exports)
    "_demand_kva": ("demandkva", "需量kva"),
    "_ignore": ("kvar", "dfused", "採用需量因數", "voltagedrop", "vd",
                "壓降", "電壓降", "status", "狀態", "remarks", "notes",
                "備註", "phasea", "phaseb", "phasec", "phaseassigned",
                "接相配置結果", "designkva", "designcurrent", "設計kva",
                "connected", "connectedload", "連接", "連接負載"),
}
# a value column that can stand in for "Rating" when there is none
_RATING_UNITS = {"VA": "va", "kVA": "kva", "W": "w", "kW": "kw",
                 "HP": "hp", "A": "a"}
for _u, _n in _RATING_UNITS.items():
    _ALIASES["rating:" + _u] = (_n, "load" + _n, "rating" + _n,
                                "額定" + _n, "容量" + _n, "負載" + _n)
_ALIASES["rating:A"] += ("amps", "amp", "current", "currenta", "fla",
                         "電流", "電流a", "負載電流")
_ALIASES["rating:HP"] += ("馬力",)
_ALIASES["rating:kW"] += ("功率kw", "負載功率kw")
_ALIASES["rating:W"] += ("功率w", "負載功率w")

_EXACT = {}
for _f, _al in _ALIASES.items():
    for _a in _al:
        _EXACT.setdefault(_a, _f)
# prefix matches ("Rating (per unit)" -> rating); short ASCII words such as
# "conn" / "cont" only match exactly ("Connected kW", "Control")
_PREFIX = sorted((a for a in _EXACT
                  if (len(a) >= 4 and a not in ("conn", "cont"))
                  or (len(a) >= 2 and not a.isascii())),
                 key=len, reverse=True)

_PANEL_SHEETS = {"panels", "panel", "panellist", "panelboards", "盤清單",
                 "盤", "配電盤", "盤表", "盤體清單"}
_LOAD_SHEETS = {"loads", "load", "loadlist", "loadschedule", "負載清單",
                "負載", "負載表", "負載明細"}
_TOTAL_WORDS = ("total", "subtotal", "grandtotal", "合計", "總計", "小計")


def match_header(h):
    """Field name for a header cell, or None."""
    n = _norm(h)
    if not n:
        return None
    if n in _EXACT:
        return _EXACT[n]
    for a in _PREFIX:
        if n.startswith(a):
            return _EXACT[a]
    return None


def _header_cols(row):
    cols = {}
    for c, v in enumerate(row):
        if v is None or isinstance(v, (bool, int, float)):
            continue
        f = match_header(v)
        if f and f not in cols.values():
            cols[c] = f
    return cols


def _is_loads(cols):
    f = set(cols.values())
    has_rating = "rating" in f or any(x.startswith("rating:") for x in f)
    return has_rating and bool(f & {"name", "category", "circuit"})


def _is_panels(cols):
    f = set(cols.values())
    return ("panel" in f and bool(f & {"system", "diversity", "target_pf"})
            and not _is_loads(cols))


def _find_header(rows, test, limit=30):
    best = (None, {})
    for i, row in enumerate(rows[:limit]):
        cols = _header_cols(row)
        if test(cols) and len(cols) > len(best[1]):
            best = (i, cols)
    return best


def _len_in_m(header):
    h = str(header or "").lower()
    return bool(re.search(r"[(\[（]\s*m\s*[)\]）]|公尺|米", h))


def _resolve_load_cols(cols):
    """field -> column index; default unit from a 'Load (VA)' style
    rating header."""
    fields = {}
    for c in sorted(cols):
        fields.setdefault(cols[c], c)
    unit = None
    if "rating" not in fields:
        rc = sorted((c, f) for f, c in fields.items()
                    if f.startswith("rating:"))
        if rc:
            fields["rating"] = rc[0][0]
            unit = rc[0][1].split(":", 1)[1]
    if "phase_any" in fields:
        c = fields.pop("phase_any")
        if "phases" in fields and "phase_conn" not in fields:
            fields["phase_conn"] = c
        elif "phase_conn" in fields and "phases" not in fields:
            fields["phases"] = c
        elif "phases" not in fields:
            fields["phase_any"] = c
    return fields, unit


# ---------------------------------------------------------------------------
# value parsing
# ---------------------------------------------------------------------------
_NUM_RE = re.compile(r"^(?:(\d+)-)?(\d*\.?\d+)(?:/(\d+))?"
                     r"([a-z一-鿿]*)$")


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _num(v):
    """-> (value or None, percent flag, unit suffix); ValueError if text."""
    if _blank(v):
        return None, False, ""
    if isinstance(v, bool):
        raise ValueError(v)
    if isinstance(v, (int, float)):
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError(v)
        return float(v), False, ""
    s = str(v).strip().lower()
    s = re.sub(r"[\s,　]", "", s)
    pct = s.endswith("%") or s.endswith("％")
    if pct:
        s = s[:-1]
    m = _NUM_RE.match(s)
    if not m:
        raise ValueError(v)
    whole, num, den, suffix = m.groups()
    if whole and not den:
        raise ValueError(v)
    x = float(num)
    if den:
        if float(den) == 0:
            raise ValueError(v)
        x /= float(den)
    if whole:
        x += float(whole)
    return x, pct, suffix


def _frac(v, pct):
    """PF / demand factor: 0.85, 85 or 85% -> 0.85."""
    if pct:
        return v / 100.0
    if v > 1.0:
        if 10.0 <= v <= 100.0:
            return v / 100.0
        raise ValueError(v)
    return v


def _text(v):
    """Cell value as text (1.0 -> '1')."""
    if _blank(v):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


_TRUE = {"y", "yes", "true", "t", "1", "x", "v", "c", "o", "是", "有", "連續",
         "√", "✓", "✔", "○", "●"}
_FALSE = {"n", "no", "false", "f", "0", "否", "無", "-", "×", "非連續",
          "不連續"}


def _bool(v):
    """-> True / False, or None if not recognised."""
    if _blank(v):
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip().lower()
    if s in _TRUE or _norm(s) in _TRUE:
        return True
    if s in _FALSE or _norm(s) in _FALSE:
        return False
    return None


_CAT_ALIASES = {
    "lighting": ("lighting", "light", "lights", "lt", "ltg", "lamp",
                 "照明", "燈", "燈具", "電燈"),
    "receptacle": ("receptacle", "receptacles", "recept", "rec", "recp",
                   "outlet", "outlets", "plug", "插座", "插座迴路",
                   "一般插座", "插座負載"),
    "motor": ("motor", "motors", "mtr", "m", "fan", "pump", "馬達", "電動機",
              "風機", "泵浦", "水泵"),
    "heating": ("heating", "heat", "heater", "htr", "電熱", "電熱器", "加熱",
                "加熱器", "暖氣"),
    "cooling": ("cooling", "cool", "ac", "aircon", "airconditioning",
                "airconditioner", "hvac", "冷氣", "空調", "冷氣機", "冷卻"),
    "equipment": ("equipment", "equip", "eqpt", "eq", "設備", "機器"),
    "other": ("other", "others", "misc", "miscellaneous", "spare", "space",
              "其他", "其它", "備用", "預備"),
}
_CAT = {}
for _c, _al in _CAT_ALIASES.items():
    for _a in _al:
        _CAT[_norm(_a)] = _c
    for _lg in LANGS:
        _CAT[_norm(opt(_c, _lg))] = _c

_UNIT = {u.lower(): u for u in L.UNITS}
_UNIT.update({"amp": "A", "amps": "A", "安培": "A", "馬力": "HP",
              "瓦": "W", "千瓦": "kW", "kv.a": "kVA", "kw.": "kW"})

_AUTO_WORDS = {"auto", "automatic", "a", "自動", "自动"}


def _unit(v):
    if _blank(v):
        return None
    s = str(v).strip().lower()
    return _UNIT.get(s) or _UNIT.get(_norm(s))


def _phase_conn(v):
    """-> code in L.PHASE_CONN, or None if not recognised."""
    if _blank(v):
        return "auto"
    s = str(v).strip()
    if _norm(s) in _AUTO_WORDS or s.lower() in _AUTO_WORDS:
        return "auto"
    u = re.sub(r"[\s,\-/+&、，．.]", "", s.upper())
    u = u.replace("L1", "A").replace("L2", "B").replace("L3", "C")
    u = u.translate(str.maketrans("RST", "ABC"))
    if not u or set(u) - set("ABC"):
        return None
    k = "".join(sorted(set(u)))
    return {"AC": "CA"}.get(k, k)


def _phases(v):
    """-> (1 or 3, line-to-line flag), or None if not recognised."""
    if _blank(v):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = v
    else:
        s = str(v).strip().lower()
        if s in ("單相", "单相"):
            return 1, False
        if s in ("三相",):
            return 3, False
        m = re.match(r"^(\d)\s*(?:ø|φ|ph|p|phase|相|w)?", s)
        if not m:
            return None
        n = int(m.group(1))
    if n == 1:
        return 1, False
    if n == 2:                    # 2-pole: single-phase line-to-line
        return 1, True
    if n == 3:
        return 3, False
    return None


def system_code(v):
    """Normalise a panel system name to a key of L.SYSTEMS (or None)."""
    if _blank(v):
        return None
    s = str(v).strip()
    if s in L.SYSTEMS:
        return s
    u = s.upper().replace("Δ", "D").replace("DELTA", "D").replace("單相", "1PH")
    digits = re.findall(r"\d+", u)
    nums = set(digits)
    if "208" in nums and "120" in nums:
        return "208Y/120"
    if "480" in nums and "277" in nums:
        return "480Y/277"
    if "240" in nums and "120" in nums:
        return "240/120 1PH"
    if "480" in nums and not nums - {"480", "3", "4"}:
        return "480D"
    if "120" in nums and not nums - {"120", "1", "2"}:
        return "120 1PH"
    return None


# ---------------------------------------------------------------------------
# reader
# ---------------------------------------------------------------------------
class _Notes(list):
    def add(self, key, **params):
        self.append((key, params))


def _read_csv(path):
    with open(path, "rb") as fh:
        data = fh.read()
    for enc in ("utf-8-sig", "cp950", "gb18030", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    counts = {d: len(re.sub(r'"[^"]*"', "", first).split(d)) - 1
              for d in (",", ";", "\t")}
    delim = max(counts, key=counts.get) if max(counts.values()) else ","
    rows = []
    for r in csv.reader(io.StringIO(text), delimiter=delim):
        rows.append([c if c.strip() else None for c in r])
    return rows


def read_panels(path, edition="2023"):
    """Read panels and loads from an .xlsx / .xlsm / .csv file.

    Returns (panels, notes) where notes is a list of (i18n key, params).
    Raises E.CalcError if the file cannot be read or holds no load list."""
    base = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xls":
        raise E.CalcError("err_xls", file=base)
    try:
        if ext in (".csv", ".txt", ".tsv"):
            stem = os.path.splitext(base)[0] or "CSV"
            sheets = {stem: _read_csv(path)}
        else:
            sheets = X.read_xlsx(path)
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError,
            ValueError, UnicodeError) as e:
        raise E.CalcError("err_import", file=base, msg=str(e) or
                          type(e).__name__)
    return parse_sheets(sheets, edition)


def _top_meta(rows):
    """'Panel: LP-1' / 'System | 208Y/120' style cells above the header."""
    meta = {}
    for row in rows:
        cells = [_text(v) for v in row]
        for i, s in enumerate(cells):
            if not s:
                continue
            m = re.match(r"^([^:：]+)[:：]\s*(.+)$", s)
            label, val = (m.group(1), m.group(2)) if m else (
                s, next((x for x in cells[i + 1:] if x), ""))
            f = match_header(label)
            if f in ("panel", "system") and val and f not in meta:
                meta[f] = val.strip()
    if "system" not in meta:            # e.g. "Panel | LP-1 | 208Y/120"
        for row in rows:
            for v in row:
                for tok in re.split(r"[\s—–,;|]+", _text(v)):
                    if tok and system_code(tok):
                        meta["system"] = system_code(tok)
                        return meta
    return meta


def _panel_meta(rows, hdr, cols, sheet, notes):
    """Panels sheet -> {lower name: dict}, in sheet order."""
    fields = {}
    for c in sorted(cols):
        fields.setdefault(cols[c], c)
    in_m = "feeder_length" in fields and \
        _len_in_m(rows[hdr][fields["feeder_length"]])
    out = {}
    for i in range(hdr + 1, len(rows)):
        row = rows[i]
        get = lambda f: row[fields[f]] if f in fields and \
            fields[f] < len(row) else None
        name = _text(get("panel"))
        if not name or _norm(name).startswith(_TOTAL_WORDS):
            continue
        where = f"{sheet}!{i + 1}"
        if name.lower() in out:
            notes.add("io_dup_panel", where=where, name=name)
            continue
        out[name.lower()] = _panel_props(name, get, where, notes, in_m)
    return out


def _panel_props(name, get, where, notes, in_m=False):
    """Parse system / diversity / target PF / feeder length of one row;
    blank or invalid values are left out."""
    d = {"name": name}
    raw = get("system")
    if not _blank(raw):
        sysc = system_code(raw)
        if sysc is None:
            notes.add("io_bad_system", where=where, value=_text(raw))
        else:
            d["system"] = sysc
    raw = get("diversity")
    if not _blank(raw):
        try:
            v, pct, _ = _num(raw)
            v = v / 100.0 if pct else v
            if v <= 0:
                raise ValueError(raw)
            if v < 1.0:
                notes.add("io_coincidence", where=where, value=f"{v:g}",
                          div=f"{1.0 / v:.3f}")
                v = 1.0 / v
            d["diversity"] = v
        except ValueError:
            notes.add("io_bad_num", where=where, field="xl_div",
                      value=_text(raw), default="1.0")
    raw = get("target_pf")
    if not _blank(raw):
        try:
            v = _frac(*_num(raw)[:2])
            if not 0 < v <= 1.0:
                raise ValueError(raw)
            d["target_pf"] = v
        except ValueError:
            notes.add("io_bad_num", where=where, field="xl_tpf",
                      value=_text(raw), default=f"{DEFAULT_TPF:g}")
    raw = get("feeder_length")
    if not _blank(raw):
        try:
            v, _, suffix = _num(raw)
            if v < 0:
                raise ValueError(raw)
            if suffix in ("m", "米", "公尺") or (in_m and suffix != "ft"):
                notes.add("io_m_to_ft", where=where, m=f"{v:g}",
                          ft=f"{v * M_TO_FT:.0f}")
                v *= M_TO_FT
            d["feeder_length_ft"] = v
        except ValueError:
            notes.add("io_bad_num", where=where, field="xl_flen",
                      value=_text(raw), default="-")
    return d


def _load_rows(rows, hdr, fields, unit_default, sheet, notes, computed):
    """-> list of (panel name or None, Load, voltage given, line-to-line,
    row panel props)."""
    out = []
    cur_panel = None
    in_m = "feeder_length" in fields and \
        _len_in_m(rows[hdr][fields["feeder_length"]])
    for i in range(hdr + 1, len(rows)):
        row = rows[i]
        where = f"{sheet}!{i + 1}"
        if all(_blank(v) for v in row):
            if computed and out:
                break           # summary block of an exported schedule
            continue
        get = lambda f: row[fields[f]] if f in fields and \
            fields[f] < len(row) else None
        pname = _text(get("panel"))
        if pname:
            cur_panel = pname
        name = _text(get("name"))
        if _norm(name).startswith(_TOTAL_WORDS) or \
                _norm(pname).startswith(_TOTAL_WORDS):
            if computed:
                break           # totals of an exported schedule
            continue
        raw = get("rating")
        try:
            rating, _, suffix = _num(raw)
        except ValueError:
            rating, suffix = None, ""
        if rating is None or rating < 0:
            if name or not _blank(raw):
                notes.add("io_skip_rating", where=where,
                          value=_text(raw) or "-")
            continue
        raw_u = get("unit")
        unit = _unit(raw_u) if not _blank(raw_u) else (
            _unit(suffix) or unit_default or "VA")
        if unit is None:
            notes.add("io_bad_unit", where=where, value=_text(raw_u))
            continue
        # category
        raw = get("category")
        cat = "other"
        if not _blank(raw):
            cat = _CAT.get(_norm(raw))
            if cat is None:
                notes.add("io_bad_cat", where=where, value=_text(raw))
                cat = "other"
        # quantity
        qty = 1
        raw = get("qty")
        if not _blank(raw):
            try:
                q, _, _ = _num(raw)
                if q < 0:
                    raise ValueError(raw)
                qty = int(round(q))
            except ValueError:
                notes.add("io_bad_num", where=where, field="xl_qty",
                          value=_text(raw), default="1")
        # power factor
        pf = DEFAULT_MOTOR_PF if cat == "motor" else DEFAULT_PF
        raw = get("pf")
        if not _blank(raw):
            try:
                v = _frac(*_num(raw)[:2])
                if not 0 < v <= 1.0:
                    raise ValueError(raw)
                pf = v
            except ValueError:
                notes.add("io_bad_num", where=where, field="xl_pf",
                          value=_text(raw), default=f"{pf:g}")
        # phases / phase connection
        phases, l2l, conn = 1, False, "auto"
        raw_ph = get("phases")
        raw_conn = get("phase_conn")
        raw_any = get("phase_any")
        if not _blank(raw_any):
            if _phases(raw_any) is not None:
                raw_ph = raw_any
            else:
                raw_conn = raw_any
        if not _blank(raw_ph):
            ph = _phases(raw_ph)
            if ph is None:
                notes.add("io_bad_phases", where=where, value=_text(raw_ph),
                          default="1")
            else:
                phases, l2l = ph
        if not computed and not _blank(raw_conn):
            conn = _phase_conn(raw_conn)
            if conn is None:
                notes.add("io_bad_conn", where=where, value=_text(raw_conn))
                conn = "auto"
            elif len(conn) == 3 and phases == 1:
                phases = 3
        # voltage
        volt = None
        raw = get("voltage")
        if not _blank(raw):
            try:
                v, _, _ = _num(raw)
                if v <= 0:
                    raise ValueError(raw)
                volt = v
            except ValueError:
                notes.add("io_bad_num", where=where, field="xl_v",
                          value=_text(raw), default="io_from_system")
        # continuous
        raw = get("continuous")
        cont = _bool(raw)
        if cont is None:
            notes.add("io_bad_bool", where=where, value=_text(raw))
            cont = False
        # demand factor
        df = None
        raw = get("demand_factor")
        if not computed and not _blank(raw) and \
                _norm(raw) not in _AUTO_WORDS:
            try:
                v = _frac(*_num(raw)[:2])
                if not 0 <= v <= 1.0:
                    raise ValueError(raw)
                df = v
            except ValueError:
                notes.add("io_bad_num", where=where, field="xl_df",
                          value=_text(raw), default="opt_auto")
        ld = L.Load(name=name or f"Load {len(out) + 1}", category=cat,
                    qty=qty, rating=rating, unit=unit, pf=pf,
                    voltage=volt or 0.0, phases=phases, continuous=cont,
                    demand_factor=df, phase_conn=conn,
                    circuit=_text(get("circuit")))
        props = _panel_props(cur_panel or "", get, where, notes, in_m)
        out.append((cur_panel, ld, volt is not None, l2l, props))
    return out


def _infer_system(loads):
    volts = {round(ld.voltage) for ld in loads if ld.voltage}
    if volts & {277, 480}:
        return "480Y/277"
    if volts and volts <= {120, 240}:
        return "240/120 1PH"
    return "208Y/120"


def parse_sheets(sheets, edition="2023"):
    """{sheet name: rows} -> (panels, notes).  See read_panels."""
    notes = _Notes()
    info = {}
    for name, rows in sheets.items():
        info[name] = (_find_header(rows, _is_loads),
                      _find_header(rows, _is_panels))
    pnames = {_norm(tr("xl_sh_panels", lg)) for lg in LANGS} | _PANEL_SHEETS
    lnames = {_norm(tr("xl_sh_loads", lg)) for lg in LANGS} | _LOAD_SHEETS
    cand = [n for n in sheets if info[n][1][0] is not None]
    panel_sheet = next((n for n in cand if _norm(n) in pnames),
                       next((n for n in cand if info[n][0][0] is None),
                            None))
    loads_named = [n for n in sheets if info[n][0][0] is not None
                   and _norm(n) in lnames]
    load_sheets = loads_named[:1] or [
        n for n in sheets if info[n][0][0] is not None and n != panel_sheet]
    if not load_sheets and panel_sheet is None:
        raise E.CalcError("io_no_data")

    meta = {}
    if panel_sheet is not None:
        hdr, cols = info[panel_sheet][1]
        meta = _panel_meta(sheets[panel_sheet], hdr, cols, panel_sheet,
                           notes)

    entries = []        # (panel name, Load, volt given, l2l, props)
    for sh in load_sheets:
        rows = sheets[sh]
        hdr, cols = info[sh][0]
        fields, unit_default = _resolve_load_cols(cols)
        computed = "_demand_kva" in fields
        if computed:
            notes.add("io_computed", where=sh)
        top = _top_meta(rows[:hdr])
        if top.get("panel"):
            default = top["panel"]
        elif "panel" in fields:
            default = next((m["name"] for m in meta.values()), None) or sh
        elif len(meta) == 1:
            default = next(iter(meta.values()))["name"]
        elif _norm(sh) in lnames or len(load_sheets) == 1 and meta:
            default = next((m["name"] for m in meta.values()), "PANEL-1")
            if len(meta) > 1:
                notes.add("io_no_panel_col", where=sh, name=default)
        else:
            default = sh
        sys_top = system_code(top.get("system"))
        for pname, ld, vg, l2l, props in _load_rows(
                rows, hdr, fields, unit_default, sh, notes, computed):
            pname = pname or default
            if sys_top and "system" not in props:
                props["system"] = sys_top
            entries.append((pname, ld, vg, l2l, props))

    # assemble panels: Panels-sheet order first, then new names
    panels, by_key = [], {}

    def get_panel(name):
        k = name.strip().lower()
        if k not in by_key:
            m = meta.get(k, {"name": name.strip()})
            p = L.Panel(name=m["name"], system=m.get("system", ""),
                        diversity=m.get("diversity", 1.0),
                        target_pf=m.get("target_pf", DEFAULT_TPF),
                        loads=[], edition=edition,
                        feeder_length_ft=m.get("feeder_length_ft", 0.0))
            by_key[k] = p
            panels.append(p)
        return by_key[k]

    for m in meta.values():
        get_panel(m["name"])
    pending, assigned = {}, {}
    for pname, ld, vg, l2l, props in entries:
        p = get_panel(pname)
        p.loads.append(ld)
        pending.setdefault(id(p), []).append((ld, vg, l2l))
        if pname.strip().lower() not in meta:
            # single-sheet list: first non-blank System / Diversity / ...
            done = assigned.setdefault(id(p), set())
            for attr in ("system", "diversity", "target_pf",
                         "feeder_length_ft"):
                if attr in props and attr not in done:
                    setattr(p, attr, props[attr])
                    done.add(attr)
    for p in panels:
        if not p.system:
            p.system = _infer_system(p.loads)
            notes.add("io_new_panel", name=p.name, system=p.system)
        ll, ln, pph, wiring = L.SYSTEMS[p.system]
        for ld, vg, l2l in pending.get(id(p), []):
            if ld.phases == 3 and pph == 1:
                notes.add("io_3ph_on_1ph", name=ld.name, panel=p.name)
                ld.phases = 1
            if not vg:
                ld.voltage = ll if (ld.phases == 3 or l2l or
                                    wiring in ("1ph2w", "3ph3w")) else ln
                ld.voltage = round(ld.voltage, 1)
    if not any(p.loads for p in panels):
        notes.add("io_no_loads")
    return panels, notes


def issue_lines(notes, lang="en"):
    """Translate (key, params) notes; params that are i18n keys
    (xl_* / io_* / opt_*) are translated too."""
    out = []
    for k, p in notes:
        p2 = {a: tr(v, lang) if isinstance(v, str) and v in TEXT and
              v.startswith(("xl_", "io_", "opt_")) else v
              for a, v in p.items()}
        out.append(tr(k, lang, **p2))
    return out


# ---------------------------------------------------------------------------
# calculation of every panel
# ---------------------------------------------------------------------------
def calculate_all(panels, edition="2023", wiring_fn=None):
    """Calculate each panel (and size its feeder if wiring_fn is given:
    wiring_fn(panel) -> engine.WiringInput).

    Returns [{"panel", "calc", "feeder", "error", "feeder_error"}]."""
    out = []
    for p in panels:
        q = L.Panel(name=p.name, system=p.system, diversity=p.diversity,
                    target_pf=p.target_pf, loads=list(p.loads),
                    edition=edition, feeder_length_ft=p.feeder_length_ft)
        item = {"panel": q, "calc": None, "feeder": None, "error": None,
                "feeder_error": None}
        try:
            item["calc"] = L.calculate(q)
        except E.CalcError as e:
            item["error"] = (e.key, e.params)
        except (ValueError, KeyError, ZeroDivisionError) as e:
            item["error"] = ("io_calc_error", {"msg": str(e)})
        if item["calc"] and wiring_fn and q.loads and \
                item["calc"]["i_design"] > 0:
            try:
                item["feeder"] = L.size_feeder(q, item["calc"],
                                               wiring_fn(q))
            except E.CalcError as e:
                item["feeder_error"] = (e.key, e.params)
            except (ValueError, KeyError, ZeroDivisionError) as e:
                item["feeder_error"] = ("io_calc_error", {"msg": str(e)})
        out.append(item)
    return out


def feeder_text(item):
    f = item.get("feeder")
    if not f:
        return ""
    s = f.summary
    return s.get("busway_text") or s.get("wire_text") or ""


SUMMARY_COLS = ("xl_panel", "xl_system", "ps_conn", "ps_dem", "ps_coin",
                "ps_design", "ps_amps", "ps_ocpd", "ps_vd", "ps_feeder")


def summary_table(results, lang="en"):
    """Rows of strings for an on-screen / HTML / CSV all-panel summary.
    Returns (header, rows, total row, error lines)."""
    head = [tr(k, lang) for k in SUMMARY_COLS]
    rows, errors = [], []
    tot = {"conn": [], "dem": [], "coin": [], "design": []}
    for it in results:
        p, c = it["panel"], it["calc"]
        if it["error"]:
            k, prm = it["error"]
            errors.append(f"{p.name}: {tr(k, lang, **prm)}")
            rows.append([p.name, p.system] + ["-"] * (len(head) - 2))
            continue
        tot["conn"].append(c["connected"]["kva_arith"])
        tot["dem"].append(c["demand"]["kva"])
        tot["coin"].append(c["coincident"]["kva"])
        tot["design"].append(c["design_kva"])
        f = it["feeder"]
        if it["feeder_error"]:
            k, prm = it["feeder_error"]
            errors.append(f"{p.name} ({tr('size_feeder', lang)}): "
                          f"{tr(k, lang, **prm)}")
        rows.append([
            p.name, p.system, f"{c['connected']['kva_arith']:.2f}",
            f"{c['demand']['kva']:.2f}", f"{c['coincident']['kva']:.2f}",
            f"{c['design_kva']:.2f}", f"{c['i_design']:.1f}",
            f"{f.summary['ocpd']}" if f else "-",
            f"{f.summary['vd_pct']:.2f}" if f and
            f.summary.get("vd_pct") is not None else "-",
            feeder_text(it) or "-"])
    total = [tr("xl_total", lang), ""] + \
        [f"{math.fsum(tot[k]):.2f}" for k in ("conn", "dem", "coin",
                                              "design")] + \
        [""] * (len(head) - 6)
    return head, rows, total, errors


def summary_text_lines(results, lang="en"):
    head, rows, total, errors = summary_table(results, lang)
    table = [head] + rows + [total]
    n = len(head) - 1               # feeder text (last) is not padded
    widths = [max(R.dwidth(r[i]) for r in table) for i in range(n)]
    lines = []
    for j, r in enumerate(table):
        cells = [R.dpad(r[i], widths[i]) if i < 2 else
                 " " * (widths[i] - R.dwidth(r[i])) + r[i]
                 for i in range(n)]
        lines.append("  ".join(cells + [r[n]]).rstrip())
        if j == 0 or j == len(table) - 2:
            lines.append("-" * sum(w + 2 for w in widths))
    return lines, errors


def summary_html(results, lang="en"):
    import html as H
    head, rows, total, errors = summary_table(results, lang)
    out = ["<table><tr>"] + [f"<th>{H.escape(h)}</th>" for h in head] + \
        ["</tr>"]
    for r in rows + [total]:
        out.append("<tr>" + "".join(f"<td>{H.escape(str(v))}</td>"
                                    for v in r) + "</tr>")
    out.append("</table>")
    if errors:
        out.append("<ul>" + "".join(f"<li class='ng'>{H.escape(e)}</li>"
                                    for e in errors) + "</ul>")
    return "".join(out)


def summary_csv(results, lang="en"):
    head, rows, total, errors = summary_table(results, lang)
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(head)
    for r in rows + [total]:
        wr.writerow(r)
    for e in errors:
        wr.writerow([e])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# writer
# ---------------------------------------------------------------------------
def _quote(sheet):
    return "'" + sheet.replace("'", "''") + "'"


def _input_sheets(wb, panels, lang, blank_rows=0):
    """Panels and Loads sheets (re-importable input format)."""
    shp = wb.add_sheet(tr("xl_sh_panels", lang))
    shp.append([tr(HEAD_KEY[f], lang) for f in PANEL_FIELDS], "header")
    shp.freeze_rows = 1
    for p in panels:
        shp.append([p.name, p.system, p.diversity, p.target_pf,
                    p.feeder_length_ft or None], "input")
    for _ in range(blank_rows // 4):
        shp.append([None] * len(PANEL_FIELDS), "input")
    shp.widths = {0: 14, 1: 14, 2: 16, 3: 12, 4: 34}
    shp.validations.append(("B2:B500", list(L.SYSTEMS)))

    shl = wb.add_sheet(tr("xl_sh_loads", lang))
    shl.append([tr(HEAD_KEY[f], lang) for f in LOAD_FIELDS], "header")
    shl.freeze_rows = 1
    yes, no = tr("opt_yes", lang), tr("opt_no", lang)
    for p in panels:
        for ld in p.loads:
            shl.append([
                p.name, ld.circuit or None, ld.name,
                opt(ld.category, lang), ld.qty, ld.rating, ld.unit, ld.pf,
                ld.voltage, ld.phases, yes if ld.continuous else no,
                ld.demand_factor,
                opt("auto", lang) if ld.phase_conn in ("auto", "", None)
                else ld.phase_conn], "input")
    for _ in range(blank_rows):
        shl.append([None] * len(LOAD_FIELDS), "input")
    shl.widths = {0: 10, 1: 10, 2: 28, 3: 16, 4: 7, 5: 16, 6: 7, 7: 7,
                  8: 11, 9: 8, 10: 11, 11: 24, 12: 16}
    shl.validations += [
        ("A2:A2000", _quote(shp.name) + "!$A$2:$A$500"),
        ("D2:D2000", [opt(c, lang) for c in L.CATEGORIES]),
        ("G2:G2000", list(L.UNITS)),
        ("J2:J2000", ["1", "3"]),
        ("K2:K2000", [yes, no]),
        ("M2:M2000", [opt("auto", lang)] + list(L.PHASE_CONN[1:])),
    ]
    return shp, shl


def _sum_formula(sh, col, r0, r1, values):
    vals = [v for v in values if isinstance(v, (int, float))]
    return X.Formula(f"SUM({X.cell_ref(r0, col)}:{X.cell_ref(r1, col)})",
                     math.fsum(vals))


def _summary_sheet(wb, results, lang, edition, stamp):
    sh = wb.add_sheet(tr("xl_sh_summary", lang))
    sh.append([tr("xl_title_summary", lang)], "title")
    sh.append([tr("xl_note_generated", lang, ed=edition, date=stamp)],
              "note")
    sh.skip()
    cols = [
        ("xl_panel", lambda it, c, f: it["panel"].name, "cell", None),
        ("xl_system", lambda it, c, f: it["panel"].system, "cell", None),
        ("xl_nloads", lambda it, c, f: len(it["panel"].loads), "int", "sum"),
        ("xl_conn_kw", lambda it, c, f: c["connected"]["kw"], "num2", "sum"),
        ("xl_conn_kvar", lambda it, c, f: c["connected"]["kvar"], "num2",
         "sum"),
        ("xl_conn_kva", lambda it, c, f: c["connected"]["kva_arith"], "num2",
         "sum"),
        ("xl_conn_pf", lambda it, c, f: c["connected"]["pf"], "num3", "pf"),
        ("xl_dem_kva", lambda it, c, f: c["demand"]["kva"], "num2", "sum"),
        ("xl_overall_df", lambda it, c, f: c["demand_factor_overall"],
         "num3", "df"),
        ("xl_div", lambda it, c, f: c["coincident"]["diversity"], "num2",
         None),
        ("xl_coin_kva", lambda it, c, f: c["coincident"]["kva"], "num2",
         "sum"),
        ("xl_cont_kva", lambda it, c, f: c["continuous_kva"], "num2", "sum"),
        ("xl_motor_kva", lambda it, c, f: c["largest_motor_kva"], "num2",
         None),
        ("xl_design_kva", lambda it, c, f: c["design_kva"], "num2", "sum"),
        ("xl_design_a", lambda it, c, f: c["i_design"], "num1", None),
        ("xl_pha", lambda it, c, f: c["phase_amps"].get("A"), "num1", None),
        ("xl_phb", lambda it, c, f: c["phase_amps"].get("B"), "num1", None),
        ("xl_phc", lambda it, c, f: c["phase_amps"].get("C"), "num1", None),
        ("xl_imb", lambda it, c, f: c["imbalance_pct"], "num1", None),
        ("xl_cap", lambda it, c, f: c["cap_kvar"], "num1", "sum"),
        ("xl_ocpd", lambda it, c, f: f.summary["ocpd"] if f else None, "int",
         None),
        ("xl_feeder", lambda it, c, f: feeder_text(it) or None, "cell",
         None),
        ("xl_vd", lambda it, c, f: f.summary.get("vd_pct") if f else None,
         "num2", None),
    ]
    hr = sh.append([tr(k, lang) for k, *_ in cols] + [tr("xl_status", lang)],
                   "header")
    sh.freeze_rows = hr + 1
    first = sh.next_row
    colvals = {i: [] for i in range(len(cols))}
    for it in results:
        c, f = it["calc"], it["feeder"]
        vals, styles = [], []
        for i, (_, getter, st, _) in enumerate(cols):
            v = None
            if c is not None or i < 3:
                try:
                    v = getter(it, c, f)
                except (KeyError, TypeError):
                    v = None
            vals.append(v)
            styles.append(st)
            colvals[i].append(v)
        if it["error"]:
            k, prm = it["error"]
            vals.append(tr(k, lang, **prm))
            styles.append("bad")
        elif it["feeder_error"]:
            k, prm = it["feeder_error"]
            vals.append(tr("size_feeder", lang) + ": " + tr(k, lang, **prm))
            styles.append("bad")
        else:
            vals.append(tr("xl_ok", lang))
            styles.append("good")
        sh.append(vals, styles)
    last = sh.next_row - 1
    if results:
        trow = sh.next_row
        vals = [tr("xl_total", lang)] + [None] * (len(cols) - 1)
        styles = ["total_text"] * len(cols)
        idx = {k: i for i, (k, *_) in enumerate(cols)}
        for i, (k, _, st, agg) in enumerate(cols):
            if agg == "sum":
                vals[i] = _sum_formula(sh, i, first, last, colvals[i])
                styles[i] = "total"
        kw, kvar = vals[idx["xl_conn_kw"]], vals[idx["xl_conn_kvar"]]
        rkw = X.cell_ref(trow, idx["xl_conn_kw"])
        rkv = X.cell_ref(trow, idx["xl_conn_kvar"])
        s = math.hypot(kw.cached, kvar.cached)
        vals[idx["xl_conn_pf"]] = X.Formula(
            f"IF(SQRT({rkw}^2+{rkv}^2)=0,1,{rkw}/SQRT({rkw}^2+{rkv}^2))",
            kw.cached / s if s else 1.0)
        styles[idx["xl_conn_pf"]] = "total"
        ckva, dkva = vals[idx["xl_conn_kva"]], vals[idx["xl_dem_kva"]]
        rc = X.cell_ref(trow, idx["xl_conn_kva"])
        rd = X.cell_ref(trow, idx["xl_dem_kva"])
        vals[idx["xl_overall_df"]] = X.Formula(
            f"IF({rc}=0,1,{rd}/{rc})",
            dkva.cached / ckva.cached if ckva.cached else 1.0)
        styles[idx["xl_overall_df"]] = "total"
        sh.append(vals, styles)
        sh.append([tr("xl_total_note", lang)], "note")
    notes = []
    for it in results:
        if it["calc"]:
            notes += [f"{it['panel'].name}: {n}"
                      for n in R.load_notes(it["calc"], lang)]
    if notes:
        sh.skip()
        sh.append([tr("notes", lang)], "total_text")
        for n in notes:
            sh.append([n], "default")
    sh.widths = {0: 14, 1: 12, 2: 7}
    for i in range(3, len(cols)):
        sh.widths[i] = 11
    sh.widths[len(cols) - 2] = 52
    sh.widths[len(cols)] = 30
    return sh


def _panel_sheet(wb, it, lang, edition):
    p, c, f = it["panel"], it["calc"], it["feeder"]
    sh = wb.add_sheet(p.name)
    ll, ln, pph, wiring = L.SYSTEMS[p.system]
    sh.append([tr("xl_title_panel", lang, name=p.name, system=p.system)],
              "title")
    sh.append([tr("xl_panel_meta", lang, div=f"{p.diversity:g}",
                  tpf=f"{p.target_pf:g}", ed=edition)], "note")
    if it["error"]:
        k, prm = it["error"]
        sh.append([tr(k, lang, **prm)], "bad")
        return sh
    sh.skip()
    heads = ("xl_circuit", "xl_name", "xl_cat", "xl_qty", "xl_rating",
             "xl_unit", "xl_pf", "xl_v", "xl_ph", "xl_cont", "xl_conn_used",
             "xl_kw", "xl_kvar", "xl_kva", "xl_dfv", "xl_dkva", "xl_amps")
    hr = sh.append([tr(h, lang) for h in heads], "header")
    sh.freeze_rows = hr + 1
    styles = ["cell", "cell", "cell", "int", "cell", "cell", "num2", "cell",
              "int", "cell", "cell", "num2", "num2", "num2", "num3", "num2",
              "num1"]
    first = sh.next_row
    yes, no = tr("opt_yes", lang), tr("opt_no", lang)
    for r in c["rows"]:
        ld = r["load"]
        sh.append([ld.circuit or None, ld.name, opt(ld.category, lang),
                   ld.qty, ld.rating, ld.unit, ld.pf, ld.voltage, ld.phases,
                   yes if ld.continuous else no, r.get("phase", ""),
                   r["kw"], r["kvar"], r["kva"], r["df"], r["d_kva"],
                   r["amps"]], styles)
    last = sh.next_row - 1
    if c["rows"]:
        vals = [None, tr("xl_total", lang)] + [None] * 15
        st = ["total_text"] * 17
        for col, key in ((11, "kw"), (12, "kvar"), (13, "kva"),
                         (15, "d_kva")):
            vals[col] = _sum_formula(sh, col, first, last,
                                     [r[key] for r in c["rows"]])
            st[col] = "total"
        sh.append(vals, st)
    sh.append([None, tr("xl_sched_note", lang)], "note")
    sh.skip()
    sh.append([None, tr("summary", lang)], ["default", "total_text"])
    for a, b in R.load_summary_rows(c, lang):
        sh.append([None, a, b])
    notes = R.load_notes(c, lang)
    if notes:
        sh.skip()
        sh.append([None, tr("notes", lang)], ["default", "total_text"])
        for n in notes:
            sh.append([None, n])
    if f or it["feeder_error"]:
        sh.skip()
        sh.append([None, tr("size_feeder", lang)],
                  ["default", "total_text"])
        if it["feeder_error"]:
            k, prm = it["feeder_error"]
            sh.append([None, tr(k, lang, **prm)], ["default", "bad"])
        else:
            for a, b in R.summary_rows(f, lang):
                sh.append([None, a, b])
            for w in R.warning_rows(f, lang):
                sh.append([None, "! " + w])
    sh.widths = {0: 10, 1: 30, 2: 14, 3: 6, 4: 9, 5: 6, 6: 6, 7: 7, 8: 5,
                 9: 8, 10: 10, 11: 9, 12: 9, 13: 9, 14: 8, 15: 11, 16: 9}
    return sh


def write_results(path, panels, results, lang="en", edition="2023"):
    """Workbook with Summary, Panels, Loads and one schedule per panel."""
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    wb = X.Workbook()
    _summary_sheet(wb, results, lang, edition, stamp)
    _input_sheets(wb, panels, lang)
    for it in results:
        _panel_sheet(wb, it, lang, edition)
    wb.save(path)


def example_panels(edition="2023"):
    lp = L.Panel("LP-1", "208Y/120", 1.0, 0.95,
                 [L.Load(**vars(x)) for x in L.EXAMPLE_LOADS], edition)
    dp = L.Panel("DP-1", "480Y/277", 1.1, 0.95, [
        L.Load("Corridor lighting", "lighting", 20, 400, "VA", 0.95,
               voltage=277, continuous=True, circuit="1,3"),
        L.Load("AHU-2 supply fan", "motor", 1, 30, "HP", 0.86, voltage=480,
               phases=3, circuit="5,7,9"),
        L.Load("CHW pump", "motor", 2, 15, "HP", 0.85, voltage=480,
               phases=3, circuit="11-21"),
        L.Load("Duct heater", "heating", 1, 30, "kW", 1.0, voltage=480,
               phases=3, circuit="2,4,6"),
        L.Load("Kitchen equipment", "equipment", 1, 45, "kW", 0.95,
               voltage=480, phases=3, circuit="8,10,12"),
    ], edition, 150.0)
    return [lp, dp]


def _instructions_sheet(wb, lang, edition):
    sh = wb.add_sheet(tr("xl_sh_instr", lang))
    sh.append([tr("xl_ins_title", lang)], "title")
    sh.append([tr("xl_note_template", lang, ed=edition)], "note")
    sh.skip()
    for i in range(1, 6):
        sh.append([tr(f"xl_ins_{i}", lang)])
    sh.skip()
    sh.append([tr(k, lang) for k in ("xl_ins_sheet", "xl_ins_col",
                                     "xl_ins_req", "xl_ins_vals",
                                     "xl_ins_ex")], "header")
    ex_p = example_panels(edition)[0]
    ex = ex_p.loads[0]
    yes, no = tr("opt_yes", lang), tr("opt_no", lang)
    p_sheet, l_sheet = tr("xl_sh_panels", lang), tr("xl_sh_loads", lang)
    refs = dict(rec=ref("receptacle_load", edition),
                nc=ref("noncoincident", edition),
                cont=ref("cont_feeder", edition),
                flc=ref("motor_flc", edition),
                mot=ref("motor_feeder", edition))
    rows = [
        (p_sheet, "panel", yes, "LP-1"),
        (p_sheet, "system", yes, ex_p.system),
        (p_sheet, "diversity", no, f"{ex_p.diversity:g}"),
        (p_sheet, "target_pf", no, f"{ex_p.target_pf:g}"),
        (p_sheet, "feeder_length", no, "150"),
        (l_sheet, "panel", yes, "LP-1"),
        (l_sheet, "circuit", no, ex.circuit),
        (l_sheet, "name", yes, ex.name),
        (l_sheet, "category", no, opt(ex.category, lang)),
        (l_sheet, "qty", no, str(ex.qty)),
        (l_sheet, "rating", yes, f"{ex.rating:g}"),
        (l_sheet, "unit", no, ex.unit),
        (l_sheet, "pf", no, f"{ex.pf:g}"),
        (l_sheet, "voltage", no, f"{ex.voltage:g}"),
        (l_sheet, "phases", no, str(ex.phases)),
        (l_sheet, "continuous", no, yes),
        (l_sheet, "demand_factor", no, ""),
        (l_sheet, "phase_conn", no, opt("auto", lang)),
    ]
    for sheet, fld, req, exv in rows:
        key = f"xl_help_{fld}" if not (sheet == l_sheet and fld == "panel") \
            else "xl_help_load_panel"
        sh.append([sheet, tr(HEAD_KEY[fld], lang), req,
                   tr(key, lang, **refs), exv],
                  ["cell", "cell", "cell", "cell", "input"])
    sh.skip()
    sh.append([tr("xl_ins_method", lang, **refs)], "note")
    sh.widths = {0: 14, 1: 30, 2: 9, 3: 90, 4: 18}
    return sh


def write_template(path, lang="en", edition="2023"):
    """Blank input workbook with instructions and example rows."""
    wb = X.Workbook()
    _instructions_sheet(wb, lang, edition)
    _input_sheets(wb, example_panels(edition), lang, blank_rows=100)
    wb.save(path)
