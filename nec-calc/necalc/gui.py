"""Tkinter desktop GUI (English / 繁體中文) for the NEC design calculator."""
import json
import math
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

from . import tables as T
from . import engine as E
from . import loads as L
from . import tray as TR
from . import report as R
from .codes import EDITIONS
from .i18n import tr, opt

WIRING_CODES = ("1ph2w", "1ph3w", "3ph3w", "3ph4w")
CONDUITS = ("EMT", "IMC", "RMC", "PVC40", "PVC80")
LOAD_TYPES = ("lighting", "receptacle", "heating", "equipment", "other")
CONT_DEFAULT = {"lighting": 100, "heating": 100, "receptacle": 0,
                "equipment": 0, "other": 0}

DEFAULTS = {
    # global
    "lang": "en", "edition": "2023",
    # branch / feeder
    "br.kind": "branch", "br.type": "lighting", "br.value": "1440",
    "br.unit": "VA", "br.pf": "0.9", "br.cont": "100", "br.ocpd": "",
    "br.motor_va": "0",
    # motor
    "mo.hp": "10", "mo.device": "itcb", "mo.fla": "", "mo.flc": "",
    "mo.sf": True, "mo.eeb": False,
    # transformer
    "xf.kva": "1500", "xf.pri_v": "24900", "xf.sec_v": "480",
    "xf.phases": "3", "xf.z": "5.75", "xf.loc": "any", "xf.pri_dev": "fuse",
    "xf.sec_dev": "cb", "xf.scheme": "pri_sec", "xf.pri_len": "100",
    # MV cable
    "mv.kv": "24.9", "mv.amps": "35", "mv.mat": "cu", "mv.ins": "25kV_133",
    "mv.fault": "10", "mv.time": "0.5", "mv.t1": "90", "mv.t2": "250",
    "mv.ocpd_type": "fuse", "mv.ocpd": "65", "mv.df": "1.25",
    "mv.conduit": "PVC40", "mv.od": "0", "mv.egc": True,
    # tray
    "tr.type": "ladder", "tr.depth": "4", "tr.width": "0",
    "tr.covered": False, "tr.arr": "random", "tr.ambient": "30",
    "tr.c.name": "F-1", "tr.c.kind": "lv_multi", "tr.c.size": "4/0",
    "tr.c.n": "3", "tr.c.qty": "1", "tr.c.od": "0", "tr.c.mat": "cu",
    "tr.c.ins": "25kV_133",
    # panel load calc
    "lc.name": "LP-1", "lc.system": "208Y/120", "lc.div": "1.0",
    "lc.tpf": "0.95",
    "lc.l.name": "Lighting", "lc.l.cat": "lighting", "lc.l.qty": "1",
    "lc.l.rating": "1000", "lc.l.unit": "VA", "lc.l.pf": "0.9",
    "lc.l.v": "120", "lc.l.ph": "1", "lc.l.cont": False, "lc.l.df": "",
    "lc.l.conn": "auto",
    # reference
    "ref.table": "310.16",
}

WIRING_DEFAULTS = {
    "br": dict(voltage="120", wiring="1ph2w", length="100", pf="0.9",
               vd="3", conduit="EMT"),
    "mo": dict(voltage="480", wiring="3ph3w", length="150", pf="0.85",
               vd="3", conduit="EMT"),
    "xf": dict(voltage="480", wiring="3ph4w", length="25", pf="0.9",
               vd="2", conduit="RMC"),
    "lc": dict(voltage="208", wiring="3ph4w", length="100", pf="0.9",
               vd="2", conduit="EMT"),
}
for _p, _d in WIRING_DEFAULTS.items():
    DEFAULTS.update({
        f"{_p}.w.voltage": _d["voltage"], f"{_p}.w.wiring": _d["wiring"],
        f"{_p}.w.mat": "cu", f"{_p}.w.ins": "THHN", f"{_p}.w.term": "75",
        f"{_p}.w.amb": "30", f"{_p}.w.extra": "0", f"{_p}.w.nccc": False,
        f"{_p}.w.sets": "0", f"{_p}.w.max": "500",
        f"{_p}.w.len": _d["length"], f"{_p}.w.pf": _d["pf"],
        f"{_p}.w.vd": _d["vd"], f"{_p}.w.conduit": _d["conduit"],
        f"{_p}.w.min": "12",
        # busway (Article 368); transformer secondaries default to busway
        f"{_p}.w.method": "busway" if _p == "xf" else "cable",
        f"{_p}.w.bw_type": "bw_feeder", f"{_p}.w.bw_neutral": "n100",
        f"{_p}.w.bw_ground": "g_int50", f"{_p}.w.bw_load": "concentrated",
        f"{_p}.w.bw_rating": "0", f"{_p}.w.bw_r": "0", f"{_p}.w.bw_x": "0",
        f"{_p}.w.bw_sccr": "0", f"{_p}.w.fault": "0",
    })

PANEL_EXAMPLE = [
    L.Load("Office lighting", "lighting", 12, 600, "VA", 0.95, voltage=120,
           continuous=True),
    L.Load("General receptacles", "receptacle", 60, 180, "VA", 0.9,
           voltage=120),
    L.Load("AHU-1 supply fan", "motor", 1, 10, "HP", 0.85, voltage=208,
           phases=3),
    L.Load("EF-1 exhaust fan", "motor", 2, 1, "HP", 0.8, voltage=208,
           phases=3),
    L.Load("Unit heater", "heating", 2, 5, "kW", 1.0, voltage=208, phases=1),
    L.Load("Split A/C", "cooling", 1, 7.5, "kVA", 0.88, voltage=208,
           phases=3),
    L.Load("Water heater", "equipment", 1, 4.5, "kW", 1.0, voltage=208,
           phases=1, continuous=True),
]

TRAY_EXAMPLE = [
    TR.TrayCable("FDR-1 (2 sets)", "lv_multi", "500", 3, 2),
    TR.TrayCable("FDR-2", "lv_multi", "4/0", 4, 1),
    TR.TrayCable("Branch circuits", "lv_multi", "10", 3, 12),
    TR.TrayCable("Control", "control", "14", 3, 8, od_in=0.55),
]


def _f(s, field="value"):
    try:
        return float(str(s).strip())
    except ValueError:
        raise E.CalcError("err_input", field=field)


class OptCombo(ttk.Combobox):
    """Read-only combobox that shows translated labels but stores codes."""

    def __init__(self, master, var, codes, lang, labeler=None, width=22,
                 command=None):
        self.codes = [str(c) for c in codes]
        self.var = var
        labeler = labeler or (lambda c: opt(c, lang))
        super().__init__(master, values=[labeler(c) for c in self.codes],
                         state="readonly", width=width)
        if str(var.get()) in self.codes:
            self.current(self.codes.index(str(var.get())))
        self.command = command
        self.bind("<<ComboboxSelected>>", self._on_select)

    def _on_select(self, _e=None):
        self.var.set(self.codes[self.current()])
        if self.command:
            self.command()


class App:
    def __init__(self, root):
        self.root = root
        self.v = {}
        for k, d in DEFAULTS.items():
            self.v[k] = tk.BooleanVar(value=d) if isinstance(d, bool) \
                else tk.StringVar(value=d)
        self.panel_loads = [L.Load(**vars(x)) for x in PANEL_EXAMPLE]
        self.tray_cables = [TR.TrayCable(**vars(x)) for x in TRAY_EXAMPLE]
        self.results = {}       # tab key -> (title key, Result | callable)
        self.inputs = {}        # tab key -> [(label key, value)]
        self.texts = {}         # tab key -> Text widget
        self._method_frames = {}  # wiring prefix -> (cable, busway) frames
        self.current_tab = 0
        self._setup_style()
        self.build()

    # ------------------------------------------------------------------
    @property
    def lang(self):
        return self.v["lang"].get()

    @property
    def edition(self):
        return self.v["edition"].get()

    def t(self, key, **kw):
        return tr(key, self.lang, **kw)

    def _setup_style(self):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        families = set(tkfont.families(self.root))
        for fam in ("Microsoft JhengHei UI", "Microsoft JhengHei",
                    "PingFang TC", "Noto Sans CJK TC", "WenQuanYi Zen Hei"):
            if fam in families:
                for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                             "TkHeadingFont"):
                    tkfont.nametofont(name).configure(family=fam, size=10)
                break
        mono = "Consolas" if "Consolas" in families else (
            "WenQuanYi Zen Hei Mono" if "WenQuanYi Zen Hei Mono" in families
            else "TkFixedFont")
        self.mono = (mono, 10)
        style.configure("Treeview", rowheight=22)
        style.configure("Accent.TButton", foreground="white",
                        background="#1f6feb")
        style.map("Accent.TButton", background=[("active", "#1158c7")])

    # ------------------------------------------------------------------
    def build(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.title(self.t("app_title"))
        self.texts = {}

        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill="x")
        ttk.Label(bar, text=self.t("language")).pack(side="left")
        OptCombo(bar, self.v["lang"], ("en", "zh"), self.lang,
                 labeler=lambda c: {"en": "English", "zh": "中文"}[c],
                 width=9, command=self.on_lang).pack(side="left", padx=4)
        ttk.Label(bar, text=self.t("edition")).pack(side="left", padx=(12, 0))
        OptCombo(bar, self.v["edition"], EDITIONS, self.lang,
                 labeler=lambda c: f"NFPA 70 - {c}", width=14,
                 command=self.on_edition).pack(side="left", padx=4)
        ttk.Button(bar, text=self.t("export_html"),
                   command=self.export_html).pack(side="right", padx=2)
        ttk.Button(bar, text=self.t("save"),
                   command=self.save_project).pack(side="right", padx=2)
        ttk.Button(bar, text=self.t("open"),
                   command=self.open_project).pack(side="right", padx=2)

        ttk.Label(self.root, text=self.t("disclaimer"), foreground="#57606a",
                  wraplength=1200, padding=(8, 0, 8, 6)).pack(side="bottom",
                                                              fill="x")
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        tabs = [("tab_branch", self.tab_branch), ("tab_motor", self.tab_motor),
                ("tab_xfmr", self.tab_xfmr), ("tab_mv", self.tab_mv),
                ("tab_tray", self.tab_tray), ("tab_load", self.tab_load),
                ("tab_ref", self.tab_ref)]
        for key, fn in tabs:
            f = ttk.Frame(self.nb, padding=6)
            self.nb.add(f, text=self.t(key))
            fn(f)
        self.nb.select(min(self.current_tab, len(tabs) - 1))
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        for key in list(self.results):
            self.render(key)

    def _tab_changed(self, _e=None):
        try:
            self.current_tab = self.nb.index(self.nb.select())
        except tk.TclError:
            pass

    def on_lang(self):
        self.build()

    def on_edition(self):
        # re-run calculations so code references follow the edition
        for key, fn in (("br", self.calc_branch), ("mo", self.calc_motor),
                        ("xf", self.calc_xfmr), ("mv", self.calc_mv),
                        ("tr", self.calc_tray), ("lc", self.calc_load)):
            if key in self.results:
                fn()

    # ------------------------------------------------------------------
    # small widget helpers
    # ------------------------------------------------------------------
    def _row(self, parent, r, key, widget_fn, col=0):
        ttk.Label(parent, text=self.t(key)).grid(row=r, column=col,
                                                 sticky="w", padx=4, pady=2)
        w = widget_fn(parent)
        w.grid(row=r, column=col + 1, sticky="we", padx=4, pady=2)
        return w

    def entry(self, name, width=24):
        return lambda p: ttk.Entry(p, textvariable=self.v[name], width=width)

    def combo(self, name, codes, labeler=None, command=None, width=22):
        return lambda p: OptCombo(p, self.v[name], codes, self.lang,
                                  labeler=labeler, width=width,
                                  command=command)

    def editable(self, name, values, width=22):
        return lambda p: ttk.Combobox(p, textvariable=self.v[name],
                                      values=list(values), width=width)

    def check(self, name, text_key=""):
        return lambda p: ttk.Checkbutton(p, variable=self.v[name],
                                         text=self.t(text_key)
                                         if text_key else "")

    def group(self, parent, key, col, row=0, rowspan=1):
        g = ttk.LabelFrame(parent, text=self.t(key), padding=6)
        g.grid(row=row, column=col, rowspan=rowspan, sticky="nsew", padx=4,
               pady=4)
        return g

    def results_area(self, parent, key, row=1, colspan=3):
        frm = ttk.LabelFrame(parent, text=self.t("results"), padding=4)
        frm.grid(row=row, column=0, columnspan=colspan, sticky="nsew",
                 padx=4, pady=4)
        parent.rowconfigure(row, weight=1)
        for c in range(colspan):
            parent.columnconfigure(c, weight=1)
        txt = tk.Text(frm, wrap="word", font=self.mono, height=14,
                      background="#fbfcfd", relief="flat")
        sb = ttk.Scrollbar(frm, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        txt.tag_configure("ng", foreground="#cf222e")
        txt.tag_configure("warn", foreground="#9a6700")
        txt.tag_configure("head", font=(self.mono[0], 11, "bold"),
                          foreground="#0b4f9c")
        self.texts[key] = txt
        return txt

    def wiring_group(self, parent, prefix, col, show_voltage=True,
                     show_pf=True, row=0, allow_busway=True):
        g = self.group(parent, "grp_wiring", col, row=row)
        p = prefix + ".w."
        r = 0
        if show_voltage:
            self._row(g, r, "voltage", self.editable(
                p + "voltage", ("120", "208", "240", "277", "480", "600"),
                width=10))
            r += 1
            self._row(g, r, "wiring", self.combo(p + "wiring", WIRING_CODES,
                                                 width=16))
            r += 1
        if allow_busway:
            self._row(g, r, "method", self.combo(
                p + "method", ("cable", "busway"), width=16,
                command=lambda: self._show_method(prefix))); r += 1
        self._row(g, r, "material", self.combo(p + "mat", ("cu", "al"),
                                               width=16)); r += 1
        # cable-only and busway-only fields share the same grid cell
        cab = ttk.Frame(g)
        bus = ttk.Frame(g)
        for fr in (cab, bus):
            fr.grid(row=r, column=0, columnspan=2, sticky="we")
            fr.columnconfigure(1, weight=1)
        q = 0
        self._row(cab, q, "insulation", self.combo(p + "ins", ("THHN", "XHHW"),
                                                   width=16)); q += 1
        self._row(cab, q, "term_temp", self.combo(
            p + "term", ("60", "75", "90"), labeler=lambda c: c + " °C",
            width=16)); q += 1
        self._row(cab, q, "conduit_type", self.combo(p + "conduit", CONDUITS,
                                                     width=16)); q += 1
        self._row(cab, q, "min_size", self.combo(
            p + "min", ("14", "12", "10"), labeler=T.size_label, width=16))
        q = 0
        self._row(bus, q, "bw_type", self.combo(
            p + "bw_type", ("bw_feeder", "bw_plugin"), width=16)); q += 1
        self._row(bus, q, "bw_neutral", self.combo(
            p + "bw_neutral", ("n100", "n200"), width=16)); q += 1
        self._row(bus, q, "bw_ground", self.combo(
            p + "bw_ground", ("g_int50", "g_housing"), width=16)); q += 1
        self._row(bus, q, "bw_rating", self.editable(
            p + "bw_rating", ["0"] + [str(x) for x in T.BUSWAY_RATINGS],
            width=10)); q += 1
        g2 = self.group(parent, "grp_conditions", col + 1, row=row)
        r = 0
        self._row(g2, r, "length", self.entry(p + "len", 10)); r += 1
        if show_pf:
            self._row(g2, r, "pf", self.entry(p + "pf", 10)); r += 1
        self._row(g2, r, "vd_limit", self.entry(p + "vd", 10)); r += 1
        self._row(g2, r, "ambient", self.entry(p + "amb", 10)); r += 1
        cab2 = ttk.Frame(g2)
        bus2 = ttk.Frame(g2)
        for fr in (cab2, bus2):
            fr.grid(row=r, column=0, columnspan=2, sticky="we")
            fr.columnconfigure(1, weight=1)
        q = 0
        self._row(cab2, q, "extra_ccc", self.entry(p + "extra", 10)); q += 1
        self._row(cab2, q, "sets", self.entry(p + "sets", 10)); q += 1
        self._row(cab2, q, "max_size", self.combo(
            p + "max", ("250", "350", "500", "600", "750"),
            labeler=T.size_label, width=12)); q += 1
        ttk.Checkbutton(cab2, variable=self.v[p + "nccc"],
                        text=self.t("neutral_ccc")).grid(
            row=q, column=0, columnspan=2, sticky="w", padx=4)
        q = 0
        self._row(bus2, q, "bw_load", self.combo(
            p + "bw_load", ("concentrated", "distributed"), width=16)); q += 1
        self._row(bus2, q, "bw_fault", self.entry(p + "fault", 10)); q += 1
        self._row(bus2, q, "bw_r", self.entry(p + "bw_r", 10)); q += 1
        self._row(bus2, q, "bw_x", self.entry(p + "bw_x", 10)); q += 1
        self._row(bus2, q, "bw_sccr", self.entry(p + "bw_sccr", 10)); q += 1
        self._method_frames[prefix] = (cab, cab2, bus, bus2)
        if not allow_busway:
            self.v[p + "method"].set("cable")
        self._show_method(prefix)
        return g, g2

    def _show_method(self, prefix):
        cab, cab2, bus, bus2 = self._method_frames[prefix]
        busway = self.v[prefix + ".w.method"].get() == "busway"
        for fr in (cab, cab2):
            fr.grid_remove() if busway else fr.grid()
        for fr in (bus, bus2):
            fr.grid() if busway else fr.grid_remove()

    def wiring_input(self, prefix):
        p = prefix + ".w."
        g = lambda k: self.v[p + k].get()
        return E.WiringInput(
            voltage=_f(g("voltage"), self.t("voltage")),
            wiring=g("wiring"), material=g("mat"), insulation=g("ins"),
            term_temp=int(g("term")), ambient_c=_f(g("amb"),
                                                   self.t("ambient")),
            extra_ccc=int(_f(g("extra"), self.t("extra_ccc"))),
            neutral_ccc=bool(g("nccc")),
            sets=int(_f(g("sets"), self.t("sets"))), max_size=g("max"),
            length_ft=_f(g("len"), self.t("length")),
            pf=_f(g("pf"), self.t("pf")),
            vd_limit_pct=_f(g("vd"), self.t("vd_limit")),
            conduit_type=g("conduit"), min_size=g("min"),
            edition=self.edition, method=g("method"),
            bw_type=g("bw_type"), bw_neutral=g("bw_neutral"),
            bw_ground=g("bw_ground"), bw_load=g("bw_load"),
            bw_rating=_f(g("bw_rating") or 0, self.t("bw_rating")),
            bw_r=_f(g("bw_r") or 0, self.t("bw_r")),
            bw_x=_f(g("bw_x") or 0, self.t("bw_x")),
            bw_sccr=_f(g("bw_sccr") or 0, self.t("bw_sccr")),
            fault_ka=_f(g("fault") or 0, self.t("bw_fault")))

    def calc_button(self, parent, cmd, row, col=0, text_key="calculate"):
        b = ttk.Button(parent, text=self.t(text_key), command=cmd,
                       style="Accent.TButton")
        b.grid(row=row, column=col, columnspan=2, sticky="we", padx=4,
               pady=(8, 2))
        return b

    # ------------------------------------------------------------------
    # result rendering
    # ------------------------------------------------------------------
    def _run(self, key, fn):
        try:
            fn()
        except E.CalcError as e:
            self._show_error(key, tr(e.key, self.lang, **e.params))
        except (ValueError, KeyError, ZeroDivisionError) as e:
            self._show_error(key, f"{self.t('error')}: {e}")

    def _show_error(self, key, msg):
        txt = self.texts.get(key)
        self.results.pop(key, None)
        if txt:
            txt.delete("1.0", "end")
            txt.insert("end", f"{self.t('error')}: {msg}", "ng")

    def render(self, key):
        txt = self.texts.get(key)
        item = self.results.get(key)
        if not txt or not item:
            return
        title_key, res = item
        txt.delete("1.0", "end")
        if callable(res):
            res(txt)
            return
        self._render_result(txt, res)
        for name, child in res.children.items():
            txt.insert("end", "\n" + self.t(R.CHILD_TITLES.get(name, name))
                       + "\n", "head")
            self._render_result(txt, child)

    def _render_result(self, txt, res):
        rows = R.summary_rows(res, self.lang)
        if rows:
            txt.insert("end", f"[{self.t('summary')}]\n", "head")
            w = max(R.dwidth(a) for a, _ in rows) + 2
            for a, b in rows:
                txt.insert("end", f"  {R.dpad(a, w)}{b}\n")
        txt.insert("end", f"[{self.t('steps')}]\n", "head")
        for i, (s, ref, status) in enumerate(R.step_rows(res, self.lang), 1):
            tag = "ng" if status == self.t("ng") else ""
            line = f" {i:2d}. {s}"
            if status:
                line += f"  [{status}]"
            if ref:
                line += f"   — {ref}"
            txt.insert("end", line + "\n", tag)
        warns = R.warning_rows(res, self.lang)
        if warns:
            txt.insert("end", f"[{self.t('warnings')}]\n", "head")
            for w in warns:
                txt.insert("end", f"  ! {w}\n", "warn")

    # ------------------------------------------------------------------
    # Tab: branch circuit / feeder
    # ------------------------------------------------------------------
    def tab_branch(self, f):
        g = self.group(f, "grp_load", 0)
        r = 0
        self._row(g, r, "circuit_kind", self.combo("br.kind",
                                                   ("branch", "feeder"))); r += 1
        self._row(g, r, "load_type", self.combo(
            "br.type", LOAD_TYPES, command=self._branch_type)); r += 1
        self._row(g, r, "load_input", self.entry("br.value")); r += 1
        self._row(g, r, "load_unit", self.combo(
            "br.unit", ("VA", "kVA", "W", "kW", "A"), labeler=str)); r += 1
        self._row(g, r, "pf", self.entry("br.pf")); r += 1
        self._row(g, r, "cont_pct", self.entry("br.cont")); r += 1
        self._row(g, r, "ocpd_given", self.entry("br.ocpd")); r += 1
        self._row(g, r, "largest_motor_va", self.entry("br.motor_va")); r += 1
        self.calc_button(g, self.calc_branch, r)
        self.wiring_group(f, "br", 1)
        self.results_area(f, "br")

    def _branch_type(self):
        self.v["br.cont"].set(str(CONT_DEFAULT.get(self.v["br.type"].get(),
                                                   0)))

    def calc_branch(self):
        def run():
            w = self.wiring_input("br")
            val = _f(self.v["br.value"].get(), self.t("load_input"))
            pf = _f(self.v["br.pf"].get(), self.t("pf"))
            w.pf = pf
            unit = self.v["br.unit"].get()
            phases = E.WIRING[w.wiring][0]
            amps = None
            if unit == "VA":
                va = val
            elif unit == "kVA":
                va = val * 1000
            elif unit == "W":
                va = val / pf
            elif unit == "kW":
                va = val * 1000 / pf
            else:
                amps = val
                va = val * w.voltage * (math.sqrt(3) if phases == 3 else 1)
            cont = _f(self.v["br.cont"].get(), self.t("cont_pct")) / 100.0
            ocpd_s = self.v["br.ocpd"].get().strip()
            ocpd = int(_f(ocpd_s, self.t("ocpd_given"))) if ocpd_s else None
            res = E.design_general(
                va, w, continuous_va=va * cont, ocpd=ocpd,
                kind=self.v["br.kind"].get(),
                largest_motor_va=_f(self.v["br.motor_va"].get() or 0),
                load_amps=amps)
            self.results["br"] = ("tab_branch", res)
            self.inputs["br"] = [
                ("circuit_kind", "opt_" + self.v["br.kind"].get()),
                ("load_type", "opt_" + self.v["br.type"].get()),
                ("load_input", f"{val:g} {unit}"), ("pf", f"{pf:g}"),
                ("cont_pct", self.v["br.cont"].get())] + \
                self._wiring_inputs("br")
            self.render("br")
        self._run("br", run)

    def _wiring_inputs(self, prefix):
        p = prefix + ".w."
        g = lambda k: self.v[p + k].get()
        return [("voltage", g("voltage")), ("wiring", "opt_" + g("wiring")),
                ("method", "opt_" + g("method")),
                ("material", "opt_" + g("mat")),
                ("insulation", "opt_" + g("ins")),
                ("term_temp", g("term")), ("conduit_type", g("conduit")),
                ("length", g("len")), ("vd_limit", g("vd")),
                ("ambient", g("amb"))]

    # ------------------------------------------------------------------
    # Tab: motor
    # ------------------------------------------------------------------
    def tab_motor(self, f):
        g = self.group(f, "grp_load", 0)
        r = 0
        self._row(g, r, "hp", self.combo("mo.hp", T.MOTOR_HP,
                                         labeler=lambda c: c + " HP"))
        r += 1
        self._row(g, r, "device", self.combo(
            "mo.device", ("itcb", "td_fuse", "ntd_fuse", "inst_cb"),
            width=28)); r += 1
        self._row(g, r, "nameplate_fla", self.entry("mo.fla")); r += 1
        self._row(g, r, "flc_override", self.entry("mo.flc")); r += 1
        ttk.Checkbutton(g, variable=self.v["mo.sf"], text=self.t("sf115")) \
            .grid(row=r, column=0, columnspan=2, sticky="w", padx=4); r += 1
        ttk.Checkbutton(g, variable=self.v["mo.eeb"],
                        text=self.t("design_b_ee")) \
            .grid(row=r, column=0, columnspan=2, sticky="w", padx=4); r += 1
        self.calc_button(g, self.calc_motor, r)
        self.wiring_group(f, "mo", 1, allow_busway=False)
        self.results_area(f, "mo")

    def calc_motor(self):
        def run():
            w = self.wiring_input("mo")
            fla = self.v["mo.fla"].get().strip()
            flc = self.v["mo.flc"].get().strip()
            res = E.design_motor(
                self.v["mo.hp"].get(), w, device=self.v["mo.device"].get(),
                nameplate_fla=_f(fla) if fla else None,
                sf_115=self.v["mo.sf"].get(),
                design_b_ee=self.v["mo.eeb"].get(),
                flc_override=_f(flc) if flc else None)
            self.results["mo"] = ("tab_motor", res)
            self.inputs["mo"] = [
                ("hp", self.v["mo.hp"].get()),
                ("device", "opt_" + self.v["mo.device"].get())] + \
                self._wiring_inputs("mo")
            self.render("mo")
        self._run("mo", run)

    # ------------------------------------------------------------------
    # Tab: transformer
    # ------------------------------------------------------------------
    def tab_xfmr(self, f):
        g = self.group(f, "tab_xfmr", 0)
        r = 0
        self._row(g, r, "kva", self.editable(
            "xf.kva", [str(k) for k in T.XFMR_KVA_3PH])); r += 1
        self._row(g, r, "pri_v", self.editable(
            "xf.pri_v", ("24900", "13800", "12470", "4160", "480", "208"))); r += 1
        self._row(g, r, "sec_v", self.editable(
            "xf.sec_v", ("480", "208", "240", "120"))); r += 1
        self._row(g, r, "phases", self.combo("xf.phases", ("3", "1"),
                                             labeler=lambda c: c + "Ø")); r += 1
        self._row(g, r, "z_pct", self.entry("xf.z")); r += 1
        self._row(g, r, "location", self.combo("xf.loc",
                                               ("any", "supervised"))); r += 1
        self._row(g, r, "pri_device", self.combo("xf.pri_dev",
                                                 ("fuse", "cb"))); r += 1
        self._row(g, r, "sec_device", self.combo("xf.sec_dev",
                                                 ("cb", "fuse"))); r += 1
        self._row(g, r, "lv_scheme", self.combo("xf.scheme",
                                                ("pri_sec", "pri_only"))); r += 1
        self._row(g, r, "pri_length", self.entry("xf.pri_len")); r += 1
        ttk.Label(g, text="MV primary cable: settings from \"" +
                  self.t("tab_mv") + "\" tab" if self.lang == "en" else
                  "高壓一次側電纜：沿用「" + self.t("tab_mv") + "」頁設定",
                  foreground="#57606a", wraplength=300).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=4); r += 1
        self.calc_button(g, self.calc_xfmr, r)
        self.wiring_group(f, "xf", 1, show_voltage=False)
        self.results_area(f, "xf")

    def _mv_input(self):
        g = lambda k: self.v["mv." + k].get()
        return E.MVInput(
            kv=_f(g("kv"), self.t("kv")), amps=_f(g("amps"), self.t("amps")),
            material=g("mat"), insulation_level=g("ins"),
            fault_ka=_f(g("fault"), self.t("fault_ka")),
            clear_time_s=_f(g("time"), self.t("clear_time")),
            t_oper=_f(g("t1")), t_sc=_f(g("t2")), ocpd_type=g("ocpd_type"),
            ocpd_amps=_f(g("ocpd") or 0), design_factor=_f(g("df")),
            conduit_type=g("conduit"), cable_od_in=_f(g("od") or 0),
            include_egc=bool(g("egc")), edition=self.edition)

    def calc_xfmr(self):
        def run():
            g = lambda k: self.v["xf." + k].get()
            x = E.TransformerInput(
                kva=_f(g("kva"), self.t("kva")),
                pri_v=_f(g("pri_v"), self.t("pri_v")),
                sec_v=_f(g("sec_v"), self.t("sec_v")),
                phases=int(g("phases")), z_pct=_f(g("z"), self.t("z_pct")),
                location=g("loc"), pri_device=g("pri_dev"),
                sec_device=g("sec_dev"), lv_scheme=g("scheme"),
                edition=self.edition)
            sec = self.wiring_input("xf")
            if x.phases == 1 and sec.wiring.startswith("3"):
                sec.wiring = "1ph3w"
            if x.phases == 3 and sec.wiring.startswith("1"):
                sec.wiring = "3ph4w"
            pri = None
            if x.pri_v <= 1000:
                pri = self.wiring_input("xf")
                pri.method = "cable"
                pri.wiring = "3ph3w" if x.phases == 3 else "1ph2w"
                pri.length_ft = _f(g("pri_len"), self.t("pri_length"))
            mv = self._mv_input() if x.pri_v > 1000 else None
            res = E.design_transformer(x, sec_wiring=sec, pri_wiring=pri,
                                       mv=mv)
            self.results["xf"] = ("tab_xfmr", res)
            self.inputs["xf"] = [("kva", g("kva")), ("pri_v", g("pri_v")),
                                 ("sec_v", g("sec_v")), ("z_pct", g("z")),
                                 ("location", "opt_" + g("loc")),
                                 ("pri_device", "opt_" + g("pri_dev"))]
            self.render("xf")
        self._run("xf", run)

    # ------------------------------------------------------------------
    # Tab: MV cable
    # ------------------------------------------------------------------
    def tab_mv(self, f):
        g = self.group(f, "tab_mv", 0)
        r = 0
        self._row(g, r, "kv", self.editable("mv.kv", ("24.9", "13.8",
                                                      "12.47", "34.5"))); r += 1
        self._row(g, r, "amps", self.entry("mv.amps")); r += 1
        self._row(g, r, "material", self.combo("mv.mat", ("cu", "al"))); r += 1
        self._row(g, r, "ins_level", self.combo(
            "mv.ins", ("25kV_100", "25kV_133", "35kV_100"))); r += 1
        self._row(g, r, "design_factor", self.entry("mv.df")); r += 1
        self._row(g, r, "ocpd_type", self.combo("mv.ocpd_type",
                                                ("fuse", "relay"))); r += 1
        self._row(g, r, "ocpd_amps", self.entry("mv.ocpd")); r += 1
        self.calc_button(g, self.calc_mv, r)
        g2 = self.group(f, "grp_conditions", 1)
        r = 0
        self._row(g2, r, "fault_ka", self.entry("mv.fault")); r += 1
        self._row(g2, r, "clear_time", self.entry("mv.time")); r += 1
        self._row(g2, r, "t_oper", self.entry("mv.t1")); r += 1
        self._row(g2, r, "t_sc", self.entry("mv.t2")); r += 1
        self._row(g2, r, "conduit_type", self.combo("mv.conduit",
                                                    CONDUITS)); r += 1
        self._row(g2, r, "cable_od", self.entry("mv.od")); r += 1
        ttk.Checkbutton(g2, variable=self.v["mv.egc"],
                        text=self.t("include_egc")).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=4)
        self.results_area(f, "mv", colspan=2)

    def calc_mv(self):
        def run():
            res = E.design_mv_cable(self._mv_input())
            self.results["mv"] = ("tab_mv", res)
            g = lambda k: self.v["mv." + k].get()
            self.inputs["mv"] = [("kv", g("kv")), ("amps", g("amps")),
                                 ("material", "opt_" + g("mat")),
                                 ("ins_level", "opt_" + g("ins")),
                                 ("fault_ka", g("fault")),
                                 ("clear_time", g("time")),
                                 ("ocpd_amps", g("ocpd"))]
            self.render("mv")
        self._run("mv", run)

    # ------------------------------------------------------------------
    # Tab: cable tray
    # ------------------------------------------------------------------
    def tab_tray(self, f):
        g = self.group(f, "tab_tray", 0)
        r = 0
        self._row(g, r, "tray_type", self.combo("tr.type", T.TRAY_TYPES)); r += 1
        self._row(g, r, "tray_depth", self.combo(
            "tr.depth", [str(d) for d in T.TRAY_DEPTHS],
            labeler=lambda c: c + " in")); r += 1
        self._row(g, r, "tray_width", self.editable(
            "tr.width", ["0"] + [str(w) for w in T.TRAY_WIDTHS])); r += 1
        self._row(g, r, "tray_arrangement", self.combo("tr.arr",
                                                       TR.ARRANGEMENTS)); r += 1
        self._row(g, r, "ambient", self.entry("tr.ambient")); r += 1
        ttk.Checkbutton(g, variable=self.v["tr.covered"],
                        text=self.t("tray_covered")).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=4); r += 1
        self.calc_button(g, self.calc_tray, r); r += 1
        self.calc_button(g, self.calc_capacity, r, text_key="capacity_table")

        g2 = self.group(f, "cable_kind", 1)
        r = 0
        self._row(g2, r, "col_name", self.entry("tr.c.name", 18)); r += 1
        self._row(g2, r, "cable_kind", self.combo(
            "tr.c.kind", TR.KINDS, command=self._tray_kind)); r += 1
        self.tray_size_cb = self._row(g2, r, "cable_size", self.editable(
            "tr.c.size", self._tray_sizes(), width=10)); r += 1
        self._row(g2, r, "n_cond", self.combo("tr.c.n", ("1", "2", "3", "4"),
                                              labeler=str, width=10)); r += 1
        self._row(g2, r, "cable_qty", self.entry("tr.c.qty", 10)); r += 1
        self._row(g2, r, "cable_od_in", self.entry("tr.c.od", 10)); r += 1
        self._row(g2, r, "material", self.combo("tr.c.mat", ("cu", "al"),
                                                width=10)); r += 1
        self._row(g2, r, "ins_level", self.combo(
            "tr.c.ins", ("25kV_100", "25kV_133", "35kV_100"),
            width=10)); r += 1
        bf = ttk.Frame(g2)
        bf.grid(row=r, column=0, columnspan=2, sticky="we", pady=(6, 0))
        for k, cmd in (("add", self.tray_add), ("update", self.tray_update),
                       ("delete", self.tray_delete), ("clear", self.tray_clear)):
            ttk.Button(bf, text=self.t(k), command=cmd, width=8).pack(
                side="left", padx=2)

        g3 = self.group(f, "tab_tray", 2)
        cols = ("col_name", "col_kind", "col_size", "n_cond", "col_qty",
                "col_od", "col_area")
        tv = ttk.Treeview(g3, columns=cols, show="headings", height=9,
                          selectmode="browse")
        widths = (120, 150, 70, 50, 45, 60, 70)
        for c, wdt in zip(cols, widths):
            tv.heading(c, text=self.t(c))
            tv.column(c, width=wdt, anchor="w")
        tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", self._tray_select)
        self.tray_tv = tv
        self._tray_refresh()
        self.results_area(f, "tr")

    def _tray_sizes(self):
        k = self.v["tr.c.kind"].get()
        if k == "lv_multi":
            return list(T.TC_3C_OD_TYPICAL)
        if k == "lv_single":
            return [s for s in T.WIRE_AREA["XHHW"]
                    if E.cmil_of(s) >= T.CMIL["1/0"]]
        if k in ("mv_single", "mv_multi"):
            return list(T.MV_SIZES)
        return ["14", "12", "10"]

    def _tray_kind(self):
        sizes = self._tray_sizes()
        self.tray_size_cb.configure(values=sizes)
        if self.v["tr.c.size"].get() not in sizes:
            self.v["tr.c.size"].set(sizes[len(sizes) // 2])
        k = self.v["tr.c.kind"].get()
        self.v["tr.c.n"].set("1" if k in ("lv_single", "mv_single") else "3")

    def _tray_form(self):
        g = lambda k: self.v["tr.c." + k].get()
        return TR.TrayCable(name=g("name"), kind=g("kind"), size=g("size"),
                            n_cond=int(g("n")),
                            qty=int(_f(g("qty"), self.t("cable_qty"))),
                            od_in=_f(g("od") or 0, self.t("cable_od_in")),
                            material=g("mat"), ins_level=g("ins"))

    def _tray_refresh(self):
        tv = self.tray_tv
        tv.delete(*tv.get_children())
        for i, c in enumerate(self.tray_cables):
            try:
                od = f"{c.od():.2f}" + ("*" if c.od_is_typical() else "")
                area = f"{c.area():.3f}"
            except E.CalcError:
                od, area = "?", "?"
            tv.insert("", "end", iid=str(i), values=(
                c.name, opt(c.kind, self.lang), c.size, c.n_cond, c.qty, od,
                area))

    def _tray_select(self, _e=None):
        sel = self.tray_tv.selection()
        if not sel:
            return
        c = self.tray_cables[int(sel[0])]
        for k, v in (("name", c.name), ("kind", c.kind), ("size", c.size),
                     ("n", str(c.n_cond)), ("qty", str(c.qty)),
                     ("od", f"{c.od_in:g}"), ("mat", c.material),
                     ("ins", c.ins_level)):
            self.v["tr.c." + k].set(v)

    def tray_add(self):
        try:
            self.tray_cables.append(self._tray_form())
        except E.CalcError as e:
            messagebox.showerror(self.t("error"),
                                 tr(e.key, self.lang, **e.params))
            return
        self._tray_refresh()

    def tray_update(self):
        sel = self.tray_tv.selection()
        if sel:
            try:
                self.tray_cables[int(sel[0])] = self._tray_form()
            except E.CalcError as e:
                messagebox.showerror(self.t("error"),
                                     tr(e.key, self.lang, **e.params))
                return
            self._tray_refresh()

    def tray_delete(self):
        sel = self.tray_tv.selection()
        if sel:
            del self.tray_cables[int(sel[0])]
            self._tray_refresh()

    def tray_clear(self):
        self.tray_cables = []
        self._tray_refresh()

    def _tray_input(self):
        g = lambda k: self.v["tr." + k].get()
        return TR.TrayInput(
            tray_type=g("type"), depth_in=_f(g("depth")),
            width_in=_f(g("width") or 0, self.t("tray_width")),
            covered=bool(g("covered")), arrangement=g("arr"),
            ambient_c=_f(g("ambient"), self.t("ambient")),
            cables=list(self.tray_cables), edition=self.edition)

    def calc_tray(self):
        def run():
            x = self._tray_input()
            res = TR.design_tray(x)
            self.results["tr"] = ("tab_tray", res)
            self.inputs["tr"] = [
                ("tray_type", "opt_" + x.tray_type),
                ("tray_depth", f"{x.depth_in:g} in"),
                ("tray_arrangement", "opt_" + x.arrangement),
                ("tray_covered", "opt_yes" if x.covered else "opt_no")] + [
                (c.name, f"{c.qty} × {opt(c.kind, self.lang)} {c.size} "
                         f"({c.n_cond}C), OD {c.od():.2f} in")
                for c in x.cables]
            self.render("tr")
        self._run("tr", run)

    def calc_capacity(self):
        def run():
            g = lambda k: self.v["tr." + k].get()
            c = lambda k: self.v["tr.c." + k].get()
            kind = c("kind")
            tbl = TR.capacity_table(
                kind, tray_type=g("type"), depth_in=_f(g("depth")),
                n_cond=int(c("n")), material=c("mat"), ins_level=c("ins"),
                od_in=_f(c("od") or 0))
            self.results["tr"] = ("capacity_table",
                                  self._capacity_renderer(kind, g("type"),
                                                          tbl))
            self.inputs.pop("tr", None)
            self.render("tr")
        self._run("tr", run)

    def _capacity_renderer(self, kind, tray_type, tbl):
        widths = T.TRAY_WIDTHS

        def draw(txt):
            txt.insert("end", self.t("cap_title", kind=opt(kind, self.lang),
                                     tray=opt(tray_type, self.lang))
                       + "\n", "head")
            hdr = R.dpad(self.t('col_size'), 12) + "".join(
                f'{str(w) + chr(34):>7}' for w in widths)
            txt.insert("end", hdr + "\n" + "-" * len(hdr) + "\n")
            for s, row in tbl.items():
                cells = "".join(f"{('-' if not v else v):>7}"
                                for v in row.values())
                txt.insert("end", f"{T.size_label(s) if s != '-' else s:<12}"
                           + cells + "\n")
            txt.insert("end", "\n" + self.t("w_tray_od_typical") + "\n",
                       "warn")

        def html_frag():
            import html as H
            out = [f"<p><b>{H.escape(self.t('cap_title', kind=opt(kind, self.lang), tray=opt(tray_type, self.lang)))}</b></p>",
                   "<table><tr><th>" + H.escape(self.t("col_size")) + "</th>"]
            out += [f"<th>{w}\"</th>" for w in widths]
            out.append("</tr>")
            for s, row in tbl.items():
                out.append(f"<tr><td>{H.escape(T.size_label(s))}</td>" +
                           "".join(f"<td>{v or '-'}</td>"
                                   for v in row.values()) + "</tr>")
            out.append("</table>")
            return "".join(out)
        draw.html = html_frag
        return draw

    # ------------------------------------------------------------------
    # Tab: panel load calculation
    # ------------------------------------------------------------------
    def tab_load(self, f):
        top = ttk.Frame(f)
        top.grid(row=0, column=0, columnspan=3, sticky="nsew")
        g = self.group(top, "panel_name", 0)
        r = 0
        self._row(g, r, "panel_name", self.entry("lc.name", 14)); r += 1
        self._row(g, r, "panel_system", self.combo(
            "lc.system", list(L.SYSTEMS), labeler=str, width=12)); r += 1
        self._row(g, r, "diversity", self.entry("lc.div", 14)); r += 1
        self._row(g, r, "target_pf", self.entry("lc.tpf", 14)); r += 1
        self.calc_button(g, self.calc_load, r); r += 1
        self.calc_button(g, self.calc_feeder, r, text_key="size_feeder"); r += 1
        bf = ttk.Frame(g)
        bf.grid(row=r, column=0, columnspan=2, sticky="we", pady=4)
        ttk.Button(bf, text=self.t("load_example"),
                   command=self.load_example).pack(side="left", padx=2)
        ttk.Button(bf, text=self.t("export_csv"),
                   command=self.export_csv).pack(side="left", padx=2)

        inner = ttk.Notebook(top)
        inner.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        top.columnconfigure(1, weight=1)
        pg1 = ttk.Frame(inner, padding=4)
        pg2 = ttk.Frame(inner, padding=4)
        inner.add(pg1, text=self.t("grp_load"))
        inner.add(pg2, text=self.t("size_feeder") + " - " +
                  self.t("grp_wiring"))

        g2 = self.group(pg1, "grp_load", 0)
        r = 0
        self._row(g2, r, "col_name", self.entry("lc.l.name", 20)); r += 1
        self._row(g2, r, "col_cat", self.combo("lc.l.cat", L.CATEGORIES,
                                               width=18)); r += 1
        self._row(g2, r, "col_qty", self.entry("lc.l.qty", 20)); r += 1
        self._row(g2, r, "col_rating", self.entry("lc.l.rating", 20)); r += 1
        self._row(g2, r, "col_unit", self.combo("lc.l.unit", L.UNITS,
                                                labeler=str, width=18)); r += 1
        self._row(g2, r, "pf", self.entry("lc.l.pf", 20)); r += 1
        g3 = self.group(pg1, "grp_conditions", 1)
        r = 0
        self._row(g3, r, "col_v", self.editable(
            "lc.l.v", ("120", "208", "240", "277", "480"), width=10)); r += 1
        self._row(g3, r, "phases", self.combo("lc.l.ph", ("1", "3"),
                                              labeler=lambda c: c + "Ø",
                                              width=10)); r += 1
        self._row(g3, r, "phase_conn", self.combo(
            "lc.l.conn", L.PHASE_CONN,
            labeler=lambda c: opt(c, self.lang) if c == "auto" else c,
            width=10)); r += 1
        self._row(g3, r, "df_auto", self.entry("lc.l.df", 12)); r += 1
        ttk.Checkbutton(g3, variable=self.v["lc.l.cont"],
                        text=self.t("continuous")).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=4); r += 1
        bf = ttk.Frame(pg1)
        bf.grid(row=1, column=0, columnspan=2, sticky="w", padx=4)
        for k, cmd in (("add", self.load_add), ("update", self.load_update),
                       ("delete", self.load_delete),
                       ("clear", self.load_clear)):
            ttk.Button(bf, text=self.t(k), command=cmd, width=10).pack(
                side="left", padx=2)
        # feeder wiring (voltage/system come from the panel)
        self.wiring_group(pg2, "lc", 0, show_voltage=False, show_pf=False)

        tvf = ttk.Frame(f)
        tvf.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=4)
        f.rowconfigure(1, weight=1)
        cols = R.LOAD_COLS
        tv = ttk.Treeview(tvf, columns=cols, show="headings", height=8,
                          selectmode="browse")
        widths = (150, 80, 40, 60, 45, 45, 45, 35, 45, 55, 60, 60, 55, 75, 55)
        for c, wdt in zip(cols, widths):
            tv.heading(c, text=self.t(c))
            tv.column(c, width=wdt, anchor="w" if c in ("col_name", "col_cat")
                      else "e")
        sb = ttk.Scrollbar(tvf, command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tv.bind("<<TreeviewSelect>>", self._load_select)
        self.load_tv = tv
        self.results_area(f, "lc", row=2)
        self._load_refresh()

    def _panel(self):
        return L.Panel(name=self.v["lc.name"].get(),
                       system=self.v["lc.system"].get(),
                       diversity=_f(self.v["lc.div"].get(),
                                    self.t("diversity")),
                       target_pf=_f(self.v["lc.tpf"].get(),
                                    self.t("target_pf")),
                       loads=list(self.panel_loads), edition=self.edition)

    def _load_refresh(self):
        tv = self.load_tv
        tv.delete(*tv.get_children())
        try:
            calc = L.calculate(self._panel())
        except (E.CalcError, ValueError, ZeroDivisionError):
            calc = None
        for i, ld in enumerate(self.panel_loads):
            if calc:
                vals = R.load_row_values(calc["rows"][i], self.lang)
            else:
                vals = [ld.name, opt(ld.category, self.lang), ld.qty,
                        ld.rating, ld.unit, ld.pf, ld.voltage, ld.phases,
                        "", "", "", "", "", "", ""]
            tv.insert("", "end", iid=str(i), values=vals)

    def _load_form(self):
        g = lambda k: self.v["lc.l." + k].get()
        df = g("df").strip()
        return L.Load(name=g("name"), category=g("cat"),
                      qty=int(_f(g("qty"), self.t("col_qty"))),
                      rating=_f(g("rating"), self.t("col_rating")),
                      unit=g("unit"), pf=_f(g("pf"), self.t("pf")),
                      voltage=_f(g("v"), self.t("col_v")),
                      phases=int(g("ph")), continuous=bool(g("cont")),
                      demand_factor=_f(df, self.t("df_auto")) if df else None,
                      phase_conn=g("conn"))

    def _load_select(self, _e=None):
        sel = self.load_tv.selection()
        if not sel:
            return
        ld = self.panel_loads[int(sel[0])]
        for k, v in (("name", ld.name), ("cat", ld.category),
                     ("qty", str(ld.qty)), ("rating", f"{ld.rating:g}"),
                     ("unit", ld.unit), ("pf", f"{ld.pf:g}"),
                     ("v", f"{ld.voltage:g}"), ("ph", str(ld.phases)),
                     ("cont", ld.continuous),
                     ("df", "" if ld.demand_factor is None
                      else f"{ld.demand_factor:g}"),
                     ("conn", ld.phase_conn or "auto")):
            self.v["lc.l." + k].set(v)

    def _load_guard(self, fn):
        try:
            fn()
        except E.CalcError as e:
            messagebox.showerror(self.t("error"),
                                 tr(e.key, self.lang, **e.params))
            return
        self._load_refresh()

    def load_add(self):
        self._load_guard(lambda: self.panel_loads.append(self._load_form()))

    def load_update(self):
        sel = self.load_tv.selection()
        if sel:
            def upd():
                self.panel_loads[int(sel[0])] = self._load_form()
            self._load_guard(upd)

    def load_delete(self):
        sel = self.load_tv.selection()
        if sel:
            del self.panel_loads[int(sel[0])]
            self._load_refresh()

    def load_clear(self):
        self.panel_loads = []
        self._load_refresh()

    def load_example(self):
        self.panel_loads = [L.Load(**vars(x)) for x in PANEL_EXAMPLE]
        self._load_refresh()

    def calc_load(self, feeder=False):
        def run():
            panel = self._panel()
            calc = L.calculate(panel)
            feeder_res = None
            if feeder:
                w = self.wiring_input("lc")
                feeder_res = L.size_feeder(panel, calc, w)
            self._load_refresh()

            def draw(txt):
                txt.insert("end", f"{panel.name}  ({panel.system})\n", "head")
                rows = R.load_summary_rows(calc, self.lang)
                wdt = max(R.dwidth(a) for a, _ in rows) + 2
                for a, b in rows:
                    txt.insert("end", f"  {R.dpad(a, wdt)}{b}\n")
                notes = R.load_notes(calc, self.lang)
                if notes:
                    txt.insert("end", f"[{self.t('notes')}]\n", "head")
                    for n in notes:
                        txt.insert("end", f"  • {n}\n")
                if feeder_res:
                    txt.insert("end", "\n" + self.t("size_feeder") + "\n",
                               "head")
                    self._render_result(txt, feeder_res)

            def html_frag():
                h = R.load_calc_html(panel, calc, self.lang)
                if feeder_res:
                    parts = []
                    R._html_block(feeder_res, self.lang, parts)
                    h += "".join(parts)
                return h
            draw.html = html_frag
            draw.csv = lambda: R.load_calc_csv(panel, calc, self.lang)
            self.results["lc"] = ("tab_load", draw)
            self.render("lc")
        self._run("lc", run)

    def calc_feeder(self):
        self.calc_load(feeder=True)

    # ------------------------------------------------------------------
    # Tab: reference tables
    # ------------------------------------------------------------------
    REF_TABLES = ("310.16", "310.17", "310.15(B)(1)(1)", "310.15(C)(1)",
                  "250.122", "Ch9 T4", "Ch9 T5", "Ch9 T9", "430.248",
                  "430.250", "430.52", "450.3(A)", "392.22", "MV (TYPICAL)")

    def tab_ref(self, f):
        top = ttk.Frame(f)
        top.grid(row=0, column=0, sticky="we")
        ttk.Label(top, text="NEC").pack(side="left", padx=4)
        OptCombo(top, self.v["ref.table"], self.REF_TABLES, self.lang,
                 labeler=str, width=22,
                 command=lambda: self._ref_show()).pack(side="left")
        self.results_area(f, "ref", colspan=1)
        self._ref_show()

    def _ref_show(self):
        txt = self.texts["ref"]
        txt.delete("1.0", "end")
        txt.insert("end", ref_table_text(self.v["ref.table"].get()))

    # ------------------------------------------------------------------
    # export / project files
    # ------------------------------------------------------------------
    def export_html(self):
        order = ("br", "mo", "xf", "mv", "tr", "lc")
        items, inputs = [], {}
        for key in order:
            if key not in self.results:
                continue
            title_key, res = self.results[key]
            title = self.t(title_key)
            if callable(res):
                res = res.html()
            items.append((title, res))
            if key in self.inputs:
                inputs[title] = [
                    (self.t(k), self.t(v) if str(v).startswith("opt_")
                     else v) for k, v in self.inputs[key]]
        if not items:
            messagebox.showinfo(self.t("export_html"), self.t("results")
                                + ": -")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("HTML", "*.html")],
            initialfile="nec_design_report.html")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(R.to_html(items, self.lang, self.edition, inputs))
        messagebox.showinfo(self.t("export_html"),
                            f"{self.t('saved_to')}: {path}")

    def export_csv(self):
        item = self.results.get("lc")
        if not item or not hasattr(item[1], "csv"):
            self.calc_load()
            item = self.results.get("lc")
            if not item:
                return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"{self.v['lc.name'].get()}_load_calc.csv")
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(item[1].csv())
        messagebox.showinfo(self.t("export_csv"),
                            f"{self.t('saved_to')}: {path}")

    def project_dict(self):
        return {"format": "necalc-project", "version": 1,
                "vars": {k: v.get() for k, v in self.v.items()},
                "panel_loads": [vars(x) for x in self.panel_loads],
                "tray_cables": [vars(x) for x in self.tray_cables]}

    def load_project_dict(self, d):
        for k, val in d.get("vars", {}).items():
            if k in self.v:
                self.v[k].set(val)
        self.panel_loads = [L.Load(**x) for x in d.get("panel_loads", [])]
        self.tray_cables = [TR.TrayCable(**x)
                            for x in d.get("tray_cables", [])]
        self.results.clear()
        self.inputs.clear()
        self.build()

    def save_project(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("Project", "*.json")],
            initialfile="nec_project.json")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.project_dict(), fh, ensure_ascii=False,
                          indent=2)

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("Project", "*.json")])
        if path:
            with open(path, encoding="utf-8") as fh:
                self.load_project_dict(json.load(fh))


# ---------------------------------------------------------------------------
# Reference table text
# ---------------------------------------------------------------------------
def _fmt_rows(header, rows):
    widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    line = "  ".join(f"{h:>{w}}" for h, w in zip(header, widths))
    out = [line, "-" * len(line)]
    for r in rows:
        out.append("  ".join(f"{('-' if x is None else x)!s:>{w}}"
                             for x, w in zip(r, widths)))
    return "\n".join(out)


def ref_table_text(name):
    if name == "310.16":
        rows = [(T.size_label(s), *T.AMPACITY_CU[s],
                 *(T.AMPACITY_AL.get(s) or (None,) * 3)) for s in T.SIZES]
        return "Table 310.16 (30 °C, ≤3 CCC)\n" + _fmt_rows(
            ("Size", "Cu60", "Cu75", "Cu90", "Al60", "Al75", "Al90"), rows)
    if name == "310.17":
        rows = [(T.size_label(s), *T.AMPACITY_FREE_AIR_CU[s],
                 *(T.AMPACITY_FREE_AIR_AL.get(s) or (None,) * 3))
                for s in T.SIZES]
        return "Table 310.17 (free air, 30 °C)\n" + _fmt_rows(
            ("Size", "Cu60", "Cu75", "Cu90", "Al60", "Al75", "Al90"), rows)
    if name == "310.15(B)(1)(1)":
        return "Ambient temperature correction (30 °C base)\n" + _fmt_rows(
            ("≤ °C", "60C", "75C", "90C"), T.TEMP_CORRECTION)
    if name == "310.15(C)(1)":
        rows = [("4-6", "80%"), ("7-9", "70%"), ("10-20", "50%"),
                ("21-30", "45%"), ("31-40", "40%"), ("41+", "35%")]
        return "Adjustment for >3 CCC\n" + _fmt_rows(("CCC", "Factor"), rows)
    if name == "250.122":
        return "Minimum EGC\n" + _fmt_rows(("OCPD A", "Cu", "Al"),
                                           T.EGC_TABLE)
    if name == "Ch9 T4":
        types = list(T.CONDUIT_AREA)
        rows = [(ts, *[T.CONDUIT_AREA[t].get(ts) for t in types])
                for ts in T.TRADE_SIZES]
        return "Conduit total area 100 % (in²); fill 53/31/40 %\n" + \
            _fmt_rows(("Trade", *types), rows)
    if name == "Ch9 T5":
        rows = [(T.size_label(s), T.WIRE_AREA["THHN"].get(s),
                 T.WIRE_AREA["XHHW"].get(s)) for s in T.SIZES]
        return "Insulated conductor area (in²)\n" + _fmt_rows(
            ("Size", "THHN/THWN-2", "XHHW-2"), rows)
    if name == "Ch9 T9":
        rows = [(T.size_label(s), *v) for s, v in T.TABLE9.items()]
        return "AC R & X, ohm/1000 ft, 75 °C\n" + _fmt_rows(
            ("Size", "XL PVC", "XL Stl", "RCu PVC", "RCu Al", "RCu Stl",
             "RAl PVC", "RAl Al", "RAl Stl"), rows)
    if name == "430.248":
        rows = [(hp, *v) for hp, v in T.FLC_1PH.items()]
        return "FLC single-phase motors (A)\n" + _fmt_rows(
            ("HP", *[f"{v}V" for v in T.FLC_1PH_VOLTS]), rows)
    if name == "430.250":
        rows = [(hp, *v) for hp, v in T.FLC_3PH.items()]
        return "FLC three-phase induction motors (A)\n" + _fmt_rows(
            ("HP", *[f"{v}V" for v in T.FLC_3PH_VOLTS]), rows)
    if name == "430.52":
        rows = [(k, f"{v * 100:.0f}%") for k, v in
                T.MOTOR_OCPD_PERCENT.items()]
        return "Table 430.52(C)(1) max % of FLC\n" + _fmt_rows(
            ("Device", "Max"), rows)
    if name == "450.3(A)":
        rows = [(f"{k[0]}/{k[1]}", *[f"{x * 100:.0f}%" for x in v])
                for k, v in T.XFMR_450_3A.items()]
        return "Table 450.3(A) transformers > 1000 V\n" + _fmt_rows(
            ("Location/Z", "Pri CB", "Pri Fuse", "Sec>1kV CB",
             "Sec>1kV Fuse", "Sec≤1kV"), rows)
    if name == "392.22":
        rows = [(w, T.TRAY_A_COL1[w], f"{T.TRAY_A_COL1[w]}-1.2Sd",
                 T.TRAY_A_COL3[w], f"{T.TRAY_A_COL3[w]}-Sd",
                 T.TRAY_B_COL1[w], f"{T.TRAY_B_COL1[w]}-1.1Sd")
                for w in T.TRAY_WIDTHS]
        return ("Table 392.22(A) & 392.22(B)(1) allowable fill (in²)\n" +
                _fmt_rows(("W in", "A col1", "A col2", "A col3", "A col4",
                           "B col1", "B col2"), rows))
    if name == "MV (TYPICAL)":
        rows = [(T.size_label(s), T.MV_AMPACITY_TYPICAL["cu"].get(s),
                 T.MV_AMPACITY_TYPICAL["al"].get(s),
                 T.MV_AMPACITY_AIR_TYPICAL["cu"].get(s),
                 T.MV_CABLE_OD_TYPICAL["25kV_133"].get(s))
                for s in T.MV_SIZES]
        return ("TYPICAL MV data - verify with NEC 315.60 / manufacturer\n" +
                _fmt_rows(("Size", "Duct Cu", "Duct Al", "Air Cu",
                           "OD 25kV133"), rows))
    return ""


def main():
    root = tk.Tk()
    root.geometry("1320x860")
    root.minsize(1100, 700)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
