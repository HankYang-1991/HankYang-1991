"""Render calculation results as text, HTML or CSV in English / Chinese."""
import csv
import datetime
import html
import io
import unicodedata

from .i18n import tr


def dwidth(s):
    """Display width of a string (CJK full-width characters count as 2)."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
               for ch in str(s))


def dpad(s, width):
    """Left-justify ``s`` to ``width`` display columns."""
    s = str(s)
    return s + " " * max(width - dwidth(s), 0)

# summary fields shown per result kind: (summary key, label key, format)
SUMMARY_FIELDS = {
    "general": [("i_load", "s_i_load", "{:.1f} A"),
                ("i_design", "s_i_design", "{:.1f} A"),
                ("ocpd", "s_ocpd", "{} A"),
                ("switch", "s_switch", "{} A"),
                ("wire_text", "s_wire", "{}"),
                ("ampacity", "s_ampacity", "{:.1f} A"),
                ("vd_pct", "s_vd", "{:.2f} %")],
    "motor": [("flc", "s_flc", "{} A"),
              ("i_design", "s_i_design", "{:.1f} A"),
              ("ocpd", "s_ocpd_motor", "{:.0f} A"),
              ("overload", "s_overload", "{:.1f} A"),
              ("switch", "s_switch", "{} A"),
              ("wire_text", "s_wire", "{}"),
              ("ampacity", "s_ampacity", "{:.1f} A"),
              ("vd_pct", "s_vd", "{:.2f} %")],
    "transformer": [("i_pri", "s_i_pri", "{:.1f} A"),
                    ("i_sec", "s_i_sec", "{:.1f} A"),
                    ("isc_ka", "s_isc", "{:.1f} kA"),
                    ("pri_ocpd", "s_pri_ocpd", "{} A"),
                    ("pri_ocpd_max", "s_pri_ocpd_max", "{} A"),
                    ("sec_ocpd", "s_sec_ocpd", "{} A")],
    "mv_cable": [("i_load", "s_i_load", "{:.1f} A"),
                 ("i_design", "s_i_design", "{:.1f} A"),
                 ("wire_text", "s_mv_cable", "{}"),
                 ("ampacity", "s_ampacity", "{} A"),
                 ("sc_cmil", "s_sc_cmil", "{:,.0f} cmil"),
                 ("jam", "s_jam", "{:.2f}")],
}
SUMMARY_FIELDS["tray"] = [("tray_text", "s_tray", "{}"),
                          ("req_width", "s_req_width", "{:.2f} in"),
                          ("fill_pct", "s_tray_fill", "{:.0f} %")]
SUMMARY_FIELDS["feeder"] = SUMMARY_FIELDS["general"]
SUMMARY_FIELDS["primary"] = SUMMARY_FIELDS["general"]
SUMMARY_FIELDS["secondary"] = SUMMARY_FIELDS["general"]

CHILD_TITLES = {"primary": "grp_primary", "secondary": "grp_secondary"}


def summary_rows(res, lang):
    rows = []
    for key, label, fmt in SUMMARY_FIELDS.get(res.kind, []):
        v = res.summary.get(key)
        if v is None or v == "-":
            continue
        try:
            rows.append((tr(label, lang), fmt.format(v)))
        except (ValueError, TypeError):
            rows.append((tr(label, lang), str(v)))
    return rows


def step_rows(res, lang):
    out = []
    for s in res.steps:
        status = "" if s.ok is None else (tr("ok", lang) if s.ok
                                          else tr("ng", lang))
        out.append((tr(s.key, lang, **s.params), s.ref, status))
    return out


def warning_rows(res, lang):
    return [tr(k, lang, **p) for k, p in res.warnings]


def to_text(res, lang="en", title=None):
    lines = []
    if title:
        lines += [title, "=" * len(title)]
    _text_block(res, lang, lines)
    for name, child in res.children.items():
        t = tr(CHILD_TITLES.get(name, name), lang)
        lines += ["", t, "-" * max(len(t) * 2, 10)]
        _text_block(child, lang, lines)
    lines += ["", tr("disclaimer", lang)]
    return "\n".join(lines)


def _text_block(res, lang, lines):
    rows = summary_rows(res, lang)
    if rows:
        lines.append(f"[{tr('summary', lang)}]")
        w = max(dwidth(a) for a, _ in rows)
        for a, b in rows:
            lines.append(f"  {dpad(a, w)} : {b}")
    lines.append(f"[{tr('steps', lang)}]")
    for i, (txt, ref, status) in enumerate(step_rows(res, lang), 1):
        st = f" [{status}]" if status else ""
        rf = f"  ({ref})" if ref else ""
        lines.append(f"  {i:2d}. {txt}{st}{rf}")
    warns = warning_rows(res, lang)
    if warns:
        lines.append(f"[{tr('warnings', lang)}]")
        lines += [f"  ! {w}" for w in warns]


_CSS = """
body{font-family:Segoe UI,Microsoft JhengHei,Arial,sans-serif;margin:24px;
color:#1b1f23;background:#fff}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:20px 0 6px;
border-bottom:2px solid #1f6feb;padding-bottom:3px}
table{border-collapse:collapse;width:100%;margin:6px 0;font-size:13px}
th,td{border:1px solid #d0d7de;padding:4px 8px;text-align:left;
vertical-align:top}th{background:#f3f6fa}
.ok{color:#1a7f37;font-weight:600}.ng{color:#cf222e;font-weight:600}
.warn{color:#9a6700}.meta{color:#57606a;font-size:12px}
.disc{margin-top:24px;font-size:11px;color:#57606a}
"""


def _html_block(res, lang, parts):
    rows = summary_rows(res, lang)
    if rows:
        parts.append(f"<h2>{html.escape(tr('summary', lang))}</h2><table>")
        for a, b in rows:
            parts.append(f"<tr><th style='width:30%'>{html.escape(a)}</th>"
                         f"<td>{html.escape(b)}</td></tr>")
        parts.append("</table>")
    parts.append(f"<h2>{html.escape(tr('steps', lang))}</h2><table>"
                 "<tr><th>#</th><th></th><th>NEC</th><th></th></tr>")
    for i, (txt, ref, status) in enumerate(step_rows(res, lang), 1):
        cls = "ok" if status == tr("ok", lang) else "ng" if status else ""
        parts.append(f"<tr><td>{i}</td><td>{html.escape(txt)}</td>"
                     f"<td>{html.escape(ref)}</td>"
                     f"<td class='{cls}'>{html.escape(status)}</td></tr>")
    parts.append("</table>")
    warns = warning_rows(res, lang)
    if warns:
        parts.append(f"<h2>{html.escape(tr('warnings', lang))}</h2><ul>")
        parts += [f"<li class='warn'>{html.escape(w)}</li>" for w in warns]
        parts.append("</ul>")


def to_html(res_list, lang="en", edition="2023", inputs=None):
    """res_list: list of (title, Result) or (title, html_fragment)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [f"<!doctype html><html lang='{'zh-Hant' if lang == 'zh' else 'en'}'>"
             f"<head><meta charset='utf-8'><title>"
             f"{html.escape(tr('app_title', lang))}</title>"
             f"<style>{_CSS}</style></head><body>",
             f"<h1>{html.escape(tr('app_title', lang))}</h1>",
             f"<div class='meta'>NFPA 70 (NEC) {edition} · {now}</div>"]
    for title, res in res_list:
        parts.append(f"<h1 style='margin-top:28px'>{html.escape(title)}</h1>")
        if inputs and title in inputs:
            parts.append("<table>")
            for k, v in inputs[title]:
                parts.append(f"<tr><th style='width:30%'>{html.escape(k)}"
                             f"</th><td>{html.escape(str(v))}</td></tr>")
            parts.append("</table>")
        if isinstance(res, str):
            parts.append(res)
            continue
        _html_block(res, lang, parts)
        for name, child in res.children.items():
            parts.append(f"<h1 style='font-size:17px;margin-top:20px'>"
                         f"{html.escape(tr(CHILD_TITLES.get(name, name), lang))}"
                         f"</h1>")
            _html_block(child, lang, parts)
    parts.append(f"<p class='disc'>{html.escape(tr('disclaimer', lang))}</p>"
                 "</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Load calculation output
# ---------------------------------------------------------------------------
LOAD_COLS = ["col_name", "col_cat", "col_qty", "col_rating", "col_unit",
             "col_pf", "col_v", "col_ph", "col_cont", "col_conn", "col_kw",
             "col_kva", "col_df", "col_dkva", "col_amps"]


def load_row_values(r, lang):
    ld = r["load"]
    return [ld.name, tr("opt_" + ld.category, lang), ld.qty, f"{ld.rating:g}",
            ld.unit, f"{ld.pf:.2f}", f"{ld.voltage:g}", ld.phases,
            tr("opt_yes" if ld.continuous else "opt_no", lang),
            r.get("phase", ""), f"{r['kw']:.2f}", f"{r['kva']:.2f}",
            f"{r['df']:.3f}", f"{r['d_kva']:.2f}", f"{r['amps']:.1f}"]


def load_summary_rows(calc, lang):
    c, d, k = calc["connected"], calc["demand"], calc["coincident"]
    ph = " / ".join(f"{p}: {a:.1f} A" for p, a in calc["phase_amps"].items())
    return [
        (tr("lc_connected", lang),
         f"{c['kw']:.2f} kW, {c['kvar']:.2f} kvar, {c['kva_arith']:.2f} kVA, "
         f"PF {c['pf']:.3f}"),
        (tr("lc_demand", lang),
         f"{d['kw']:.2f} kW, {d['kvar']:.2f} kvar, {d['kva']:.2f} kVA, "
         f"PF {d['pf']:.3f}"),
        (tr("lc_overall_df", lang), f"{calc['demand_factor_overall']:.3f}"),
        (tr("lc_coincident", lang),
         f"{k['kw']:.2f} kW, {k['kva']:.2f} kVA "
         f"(÷ {k['diversity']:.2f}) → {calc['i_demand']:.1f} A"),
        (tr("lc_cont", lang), f"{calc['continuous_kva']:.2f} kVA"),
        (tr("lc_largest_motor", lang), f"{calc['largest_motor_kva']:.2f} kVA"),
        (tr("lc_design", lang),
         f"{calc['design_kva']:.2f} kVA → {calc['i_design']:.1f} A"),
        (tr("lc_phase", lang), ph),
        (tr("lc_imbalance", lang), f"{calc['imbalance_pct']:.1f} %"),
        (tr("lc_cap", lang), f"{calc['cap_kvar']:.1f} kvar"),
    ]


def load_notes(calc, lang):
    return [f"{tr(k, lang, **p)} ({ref})" for k, ref, p in calc["notes"]]


def load_calc_html(panel, calc, lang):
    parts = ["<table><tr>"]
    parts += [f"<th>{html.escape(tr(c, lang))}</th>" for c in LOAD_COLS]
    parts.append("</tr>")
    for r in calc["rows"]:
        parts.append("<tr>" + "".join(
            f"<td>{html.escape(str(v))}</td>"
            for v in load_row_values(r, lang)) + "</tr>")
    parts.append("</table><table>")
    for a, b in load_summary_rows(calc, lang):
        parts.append(f"<tr><th style='width:30%'>{html.escape(a)}</th>"
                     f"<td>{html.escape(b)}</td></tr>")
    parts.append("</table>")
    notes = load_notes(calc, lang)
    if notes:
        parts.append(f"<h2>{html.escape(tr('notes', lang))}</h2><ul>")
        parts += [f"<li>{html.escape(n)}</li>" for n in notes]
        parts.append("</ul>")
    return "".join(parts)


def load_calc_csv(panel, calc, lang):
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow([tr("panel_name", lang), panel.name, panel.system])
    wr.writerow([tr(c, lang) for c in LOAD_COLS])
    for r in calc["rows"]:
        wr.writerow(load_row_values(r, lang))
    wr.writerow([])
    for a, b in load_summary_rows(calc, lang):
        wr.writerow([a, b])
    for n in load_notes(calc, lang):
        wr.writerow([n])
    return buf.getvalue()
