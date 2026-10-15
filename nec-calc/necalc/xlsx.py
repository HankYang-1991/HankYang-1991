"""Minimal .xlsx writer and reader using only the Python standard library.

Writer: worksheets with inline strings, numbers, booleans and formulas
(with cached values so every reader shows numbers), a small style set
(Arial), column widths, a frozen header row and dropdown data validations.
Excel recalculates formulas on open (fullCalcOnLoad).

Reader: values of every sheet in a workbook saved by Excel, LibreOffice
or this writer (shared strings, inline strings, numbers, booleans).
"""
import re
import zipfile
import datetime
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = ("http://schemas.openxmlformats.org/officeDocument/2006/"
          "relationships")
_BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
_BAD_SHEET = re.compile(r"[\[\]:*?/\\]")


class Formula:
    """A formula with an optional cached result."""

    def __init__(self, expr, cached=None):
        self.expr = expr.lstrip("=")
        self.cached = cached


def col_letter(n):
    """0-based column index -> 'A', 'B', ... 'AA'."""
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def cell_ref(row, col):
    """0-based row/col -> 'A1'."""
    return f"{col_letter(col)}{row + 1}"


def _text(s):
    return escape(_BAD_XML.sub("", str(s)))


# style name -> cellXfs index (see _STYLES_XML)
STYLE = {"default": 0, "header": 1, "title": 2, "note": 3, "num2": 4,
         "num1": 5, "int": 6, "num3": 7, "input": 8, "input_num": 9,
         "total": 10, "total_text": 11, "cell": 12, "pct": 13,
         "bad": 14, "good": 15}

_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="3"><numFmt numFmtId="164" formatCode="0.00"/>
<numFmt numFmtId="165" formatCode="0.0"/><numFmt numFmtId="166" formatCode="0.000"/></numFmts>
<fonts count="7">
<font><sz val="10"/><name val="Arial"/><family val="2"/></font>
<font><b/><sz val="10"/><name val="Arial"/><family val="2"/></font>
<font><b/><sz val="14"/><name val="Arial"/><family val="2"/></font>
<font><i/><sz val="9"/><color rgb="FF595959"/><name val="Arial"/><family val="2"/></font>
<font><sz val="10"/><color rgb="FF0000FF"/><name val="Arial"/><family val="2"/></font>
<font><b/><sz val="10"/><color rgb="FFC00000"/><name val="Arial"/><family val="2"/></font>
<font><b/><sz val="10"/><color rgb="FF00804B"/><name val="Arial"/><family val="2"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFD9E1F2"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="3">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFBFBFBF"/></left><right style="thin"><color rgb="FFBFBFBF"/></right><top style="thin"><color rgb="FFBFBFBF"/></top><bottom style="thin"><color rgb="FFBFBFBF"/></bottom><diagonal/></border>
<border><left/><right/><top style="thin"><color rgb="FF000000"/></top><bottom style="double"><color rgb="FF000000"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="16">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="1" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="166" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="164" fontId="1" fillId="0" borderId="2" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="2" xfId="0" applyFont="1" applyBorder="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
<xf numFmtId="10" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="0" fontId="5" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/>
<xf numFmtId="0" fontId="6" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


class Sheet:
    def __init__(self, name):
        self.name = name
        self.cells = {}          # (row, col) -> (value, style)
        self.widths = {}         # col -> width
        self.freeze_rows = 0
        self.validations = []    # (sqref, [values] or "Sheet!$A$2:$A$9")
        self.next_row = 0

    def set(self, row, col, value, style="default"):
        self.cells[(row, col)] = (value, style)

    def append(self, values, styles=None):
        """Write a row at the next free row; returns its 0-based index."""
        r = self.next_row
        for c, v in enumerate(values):
            st = styles[c] if isinstance(styles, (list, tuple)) else \
                (styles or "default")
            if v is not None or st != "default":
                self.set(r, c, v, st)
        self.next_row = r + 1
        return r

    def skip(self, n=1):
        self.next_row += n

    def _cell_xml(self, row, col, value, style):
        ref = cell_ref(row, col)
        s = STYLE.get(style, 0)
        sa = f' s="{s}"' if s else ""
        if value is None:
            return f'<c r="{ref}"{sa}/>'
        if isinstance(value, Formula):
            f = f"<f>{_text(value.expr)}</f>"
            cv = value.cached
            if cv is None:
                return f'<c r="{ref}"{sa}>{f}</c>'
            if isinstance(cv, bool):
                return f'<c r="{ref}"{sa} t="b">{f}<v>{int(cv)}</v></c>'
            if isinstance(cv, (int, float)):
                return f'<c r="{ref}"{sa}>{f}<v>{repr(float(cv))}</v></c>'
            return f'<c r="{ref}"{sa} t="str">{f}<v>{_text(cv)}</v></c>'
        if isinstance(value, bool):
            return f'<c r="{ref}"{sa} t="b"><v>{int(value)}</v></c>'
        if isinstance(value, (int, float)):
            if value != value or value in (float("inf"), float("-inf")):
                return f'<c r="{ref}"{sa}/>'
            v = str(value) if isinstance(value, int) else repr(float(value))
            return f'<c r="{ref}"{sa}><v>{v}</v></c>'
        return (f'<c r="{ref}"{sa} t="inlineStr"><is><t xml:space="preserve">'
                f'{_text(value)}</t></is></c>')

    def xml(self):
        parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                 f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">']
        if self.cells:
            mr = max(r for r, _ in self.cells)
            mc = max(c for _, c in self.cells)
            parts.append(f'<dimension ref="A1:{cell_ref(mr, mc)}"/>')
        parts.append('<sheetViews><sheetView workbookViewId="0">')
        if self.freeze_rows:
            top = cell_ref(self.freeze_rows, 0)
            parts.append(f'<pane ySplit="{self.freeze_rows}" topLeftCell="{top}"'
                         ' activePane="bottomLeft" state="frozen"/>'
                         '<selection pane="bottomLeft"/>')
        parts.append('</sheetView></sheetViews>'
                     '<sheetFormatPr defaultRowHeight="13.2"/>')
        if self.widths:
            parts.append("<cols>")
            for c in sorted(self.widths):
                parts.append(f'<col min="{c + 1}" max="{c + 1}" '
                             f'width="{self.widths[c]}" customWidth="1"/>')
            parts.append("</cols>")
        parts.append("<sheetData>")
        rows = {}
        for (r, c), vs in self.cells.items():
            rows.setdefault(r, {})[c] = vs
        for r in sorted(rows):
            parts.append(f'<row r="{r + 1}">')
            for c in sorted(rows[r]):
                v, st = rows[r][c]
                parts.append(self._cell_xml(r, c, v, st))
            parts.append("</row>")
        parts.append("</sheetData>")
        if self.validations:
            parts.append(f'<dataValidations count="{len(self.validations)}">')
            for sqref, values in self.validations:
                if isinstance(values, str):     # range, e.g. Panels!$A$2:$A$500
                    f1 = _text(values.lstrip("="))
                else:
                    f1 = '"' + _text(",".join(str(v) for v in values)[:255]) \
                        + '"'
                parts.append(
                    f'<dataValidation type="list" allowBlank="1" '
                    f'showInputMessage="1" showErrorMessage="0" '
                    f'sqref="{sqref}"><formula1>{f1}</formula1>'
                    f'</dataValidation>')
            parts.append("</dataValidations>")
        parts.append('<pageMargins left="0.5" right="0.5" top="0.75" '
                     'bottom="0.75" header="0.3" footer="0.3"/>')
        parts.append("</worksheet>")
        return "".join(parts)


def safe_sheet_name(name, used):
    base = _BAD_SHEET.sub("_", str(name)).strip("'") or "Sheet"
    base = base[:31]
    cand, n = base, 2
    while cand.lower() in {u.lower() for u in used}:
        suffix = f" ({n})"
        cand = base[:31 - len(suffix)] + suffix
        n += 1
    return cand


class Workbook:
    def __init__(self):
        self.sheets = []

    def add_sheet(self, name):
        sh = Sheet(safe_sheet_name(name, [s.name for s in self.sheets]))
        self.sheets.append(sh)
        return sh

    def save(self, path):
        n = len(self.sheets)
        now = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
              'content-types">'
              '<Default Extension="rels" ContentType="application/'
              'vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/'
              'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
              '<Override PartName="/xl/styles.xml" ContentType="application/'
              'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
              '<Override PartName="/docProps/core.xml" ContentType="application/'
              'vnd.openxmlformats-package.core-properties+xml"/>'
              '<Override PartName="/docProps/app.xml" ContentType="application/'
              'vnd.openxmlformats-officedocument.extended-properties+xml"/>']
        for i in range(n):
            ct.append(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                      'ContentType="application/vnd.openxmlformats-'
                      'officedocument.spreadsheetml.worksheet+xml"/>')
        ct.append("</Types>")
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/'
                'package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.'
                'org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.'
                'org/package/2006/relationships/metadata/core-properties" '
                'Target="docProps/core.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.'
                'org/officeDocument/2006/relationships/extended-properties" '
                'Target="docProps/app.xml"/></Relationships>')
        wb = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
              '<bookViews><workbookView/></bookViews><sheets>']
        for i, sh in enumerate(self.sheets):
            wb.append(f'<sheet name="{_text(sh.name)}" sheetId="{i + 1}" '
                      f'r:id="rId{i + 1}"/>')
        wb.append('</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/>'
                  '</workbook>')
        wrels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/'
                 'package/2006/relationships">']
        for i in range(n):
            wrels.append(f'<Relationship Id="rId{i + 1}" Type="http://schemas.'
                         'openxmlformats.org/officeDocument/2006/relationships/'
                         f'worksheet" Target="worksheets/sheet{i + 1}.xml"/>')
        wrels.append(f'<Relationship Id="rId{n + 1}" Type="http://schemas.'
                     'openxmlformats.org/officeDocument/2006/relationships/'
                     'styles" Target="styles.xml"/></Relationships>')
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org'
                '/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" '
                'xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<dc:creator>NEC Electrical Calculator</dc:creator>'
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}'
                '</dcterms:created></cp:coreProperties>')
        app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Properties xmlns="http://schemas.openxmlformats.org/'
               'officeDocument/2006/extended-properties">'
               '<Application>NEC Electrical Calculator</Application>'
               '</Properties>')
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", "".join(ct))
            z.writestr("_rels/.rels", rels)
            z.writestr("docProps/core.xml", core)
            z.writestr("docProps/app.xml", app)
            z.writestr("xl/workbook.xml", "".join(wb))
            z.writestr("xl/_rels/workbook.xml.rels", "".join(wrels))
            z.writestr("xl/styles.xml", _STYLES_XML)
            for i, sh in enumerate(self.sheets):
                z.writestr(f"xl/worksheets/sheet{i + 1}.xml", sh.xml())


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _children(el, name):
    return [c for c in el if _local(c.tag) == name]


def _all_text(el):
    """Concatenated <t> text of a shared/inline string (incl. rich runs,
    excluding phonetic runs)."""
    out = []
    for node in el.iter():
        if _local(node.tag) == "rPh":
            continue
        if _local(node.tag) == "t" and node.text:
            out.append(node.text)
    # iter() also visits <t> inside <rPh>; remove those
    ph = []
    for r in el.iter():
        if _local(r.tag) == "rPh":
            ph += [t.text for t in r.iter() if _local(t.tag) == "t" and t.text]
    for p in ph:
        if p in out:
            out.remove(p)
    return "".join(out)


def _resolve(base_dir, target):
    if target.startswith("/"):
        return target.lstrip("/")
    parts = (base_dir + "/" + target).split("/")
    stack = []
    for p in parts:
        if p == "..":
            if stack:
                stack.pop()
        elif p and p != ".":
            stack.append(p)
    return "/".join(stack)


def read_xlsx(path):
    """Return {sheet name: [[cell values...], ...]} in workbook order.
    Values are str, float, bool or None."""
    out = {}
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        wb_path = "xl/workbook.xml"
        if "_rels/.rels" in names:
            for rel in ET.fromstring(z.read("_rels/.rels")):
                if rel.get("Type", "").endswith("/officeDocument"):
                    wb_path = _resolve("", rel.get("Target"))
        wb_dir = wb_path.rsplit("/", 1)[0] if "/" in wb_path else ""
        rels_path = (wb_dir + "/" if wb_dir else "") + "_rels/" + \
            wb_path.rsplit("/", 1)[-1] + ".rels"
        targets = {}
        shared_path = None
        if rels_path in names:
            for rel in ET.fromstring(z.read(rels_path)):
                tgt = _resolve(wb_dir, rel.get("Target", ""))
                targets[rel.get("Id")] = tgt
                if rel.get("Type", "").endswith("/sharedStrings"):
                    shared_path = tgt
        shared = []
        if shared_path and shared_path in names:
            for si in ET.fromstring(z.read(shared_path)):
                if _local(si.tag) == "si":
                    shared.append(_all_text(si))
        wb = ET.fromstring(z.read(wb_path))
        sheets_el = next((e for e in wb if _local(e.tag) == "sheets"), [])
        for sh in sheets_el:
            rid = next((v for k, v in sh.attrib.items()
                        if _local(k) == "id"), None)
            tgt = targets.get(rid)
            if not tgt or tgt not in names:
                continue
            out[sh.get("name")] = _read_sheet(z.read(tgt), shared)
    return out


def _read_sheet(data, shared):
    root = ET.fromstring(data)
    sd = next((e for e in root if _local(e.tag) == "sheetData"), None)
    rows = {}
    if sd is None:
        return []
    next_r = 0
    for row in sd:
        if _local(row.tag) != "row":
            continue
        r = int(row.get("r", next_r + 1)) - 1
        next_r = r + 1
        cells = {}
        next_c = 0
        for c in row:
            if _local(c.tag) != "c":
                continue
            ref = c.get("r")
            if ref:
                m = re.match(r"([A-Za-z]+)", ref)
                ci = col_index(m.group(1))
            else:
                ci = next_c
            next_c = ci + 1
            t = c.get("t", "n")
            v_el = next((e for e in c if _local(e.tag) == "v"), None)
            raw = v_el.text if v_el is not None else None
            if t == "s":
                val = shared[int(raw)] if raw is not None else None
            elif t == "inlineStr":
                is_el = next((e for e in c if _local(e.tag) == "is"), None)
                val = _all_text(is_el) if is_el is not None else None
            elif t in ("str",):
                val = raw
            elif t == "b":
                val = raw == "1" if raw is not None else None
            elif t == "e":
                val = None
            else:
                try:
                    val = float(raw) if raw is not None else None
                except ValueError:
                    val = raw
            cells[ci] = val
        if cells:
            rows[r] = cells
    if not rows:
        return []
    width = max(max(c) for c in rows.values()) + 1
    return [[rows.get(r, {}).get(c) for c in range(width)]
            for r in range(max(rows) + 1)]
