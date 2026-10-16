"""Build the desktop package:  python tools/build_desktop.py [out_dir]

Creates dist/NEC-Calculator-<version>.zip containing
  NEC-Calculator.pyzw          the whole program in one file (double-click
                               on Windows once Python 3.9+ is installed)
  Start-NEC-Calculator.bat     Windows launcher
  start_mac.command            macOS launcher
  start_linux.sh               Linux launcher
  Excel/                       panel list templates (English / 中文)
  mobile-web/                  offline copy of the browser version
  source/                      Python source, web port, examples, tests
  README.txt                   how to install and start (English / 中文)
Only the Python standard library is used, so nothing else is installed.
"""
import os
import shutil
import stat
import sys
import tempfile
import zipapp
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from necalc import __version__                  # noqa: E402
from necalc import panel_io as PIO              # noqa: E402

NAME = "NEC-Calculator"
SKIP = {"__pycache__", "crosscheck_cases.json"}

MAIN = """import sys

try:
    import tkinter  # noqa: F401
except ImportError:
    sys.exit("Tkinter is missing. Windows / macOS: reinstall Python from "
             "python.org with 'tcl/tk' ticked. Linux: sudo apt install "
             "python3-tk")

from necalc.gui import main

main()
"""

BAT = r"""@echo off
rem NEC Electrical Calculator - Windows launcher
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 "%~dp0NEC-Calculator.pyzw" & exit /b 0)
where pythonw >nul 2>nul && (start "" pythonw "%~dp0NEC-Calculator.pyzw" & exit /b 0)
where python >nul 2>nul && (python "%~dp0NEC-Calculator.pyzw" & exit /b 0)
echo.
echo  Python 3.9 or later is required:  https://www.python.org/downloads/
echo  During installation tick "Add python.exe to PATH".
echo.
pause
"""

MAC = """#!/bin/sh
# NEC Electrical Calculator - macOS launcher (double-click in Finder)
cd "$(dirname "$0")" || exit 1
exec python3 NEC-Calculator.pyzw
"""

LINUX = """#!/bin/sh
# NEC Electrical Calculator - Linux launcher (needs python3-tk)
cd "$(dirname "$0")" || exit 1
exec python3 NEC-Calculator.pyzw "$@"
"""

README = """NEC Electrical Calculator {ver} - desktop version
NEC 電氣計算軟體 {ver} - 電腦版
=====================================================================

1. Install Python 3.9 or later (free) / 安裝 Python 3.9 以上 (免費)
   https://www.python.org/downloads/
   Windows: tick "Add python.exe to PATH" during installation.
            安裝時請勾選「Add python.exe to PATH」。
   macOS:   use the python.org installer (it includes Tkinter).
            請使用 python.org 安裝程式 (已含 Tkinter)。
   Linux:   sudo apt install python3 python3-tk

2. Unzip this folder anywhere, e.g. Desktop or D:\\Tools.
   將整個資料夾解壓縮到任意位置，例如桌面或 D:\\Tools。

3. Start / 啟動
   Windows: double-click NEC-Calculator.pyzw
            (or Start-NEC-Calculator.bat)
            直接點兩下 NEC-Calculator.pyzw (或 Start-NEC-Calculator.bat)
   macOS:   double-click start_mac.command
            (first time: right-click > Open / 第一次請按右鍵 > 打開)
   Linux:   ./start_linux.sh
   Any OS:  python NEC-Calculator.pyzw

Contents / 內容
   NEC-Calculator.pyzw   the whole program in one file / 單一檔案主程式
   Excel/                panel load list templates / 盤負載清單 Excel 範本
                         (Panel Load tab > Import Excel / CSV)
                         (盤負載計算頁 > 匯入 Excel / CSV)
   mobile-web/index.html browser version, works offline / 網頁版 (可離線)
   source/               Python source code and tests / 原始碼與測試

Modules / 功能
   Branch / feeder, motor, transformer (24.9 kV - 120 V), MV cable,
   busway (Schneider I-Line), cable tray, panel load calculation with
   Excel import / export, short circuit / IC rating, VFD harmonics and
   filters, NEC reference tables.  English / 中文, NEC 2023 / 2026.
   分路／幹線、馬達、變壓器、高壓電纜、匯流排槽、電纜架、盤負載計算
   (Excel 匯入匯出)、短路／IC 值、變頻器諧波與濾波器、NEC 參考表。

This is a design aid. Every result must be checked by a qualified
engineer against the NEC edition adopted by the AHJ.
本軟體為設計輔助工具，結果須由合格工程師依 AHJ 採用版本複核。
"""


def _copytree(src, dst):
    shutil.copytree(src, dst, ignore=lambda d, names: [
        n for n in names if n in SKIP or n.endswith(".pyc")])


def _write(path, text, crlf=False, bom=False):
    if crlf:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8",
              newline="") as fh:
        fh.write(text)


def build(out_dir=None):
    out_dir = out_dir or os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="necalc_build_")
    try:
        pkg = os.path.join(work, NAME)
        os.makedirs(pkg)
        # one-file program: necalc package + __main__ in a zip application
        app = os.path.join(work, "app")
        _copytree(os.path.join(ROOT, "necalc"), os.path.join(app, "necalc"))
        _write(os.path.join(app, "__main__.py"), MAIN)
        zipapp.create_archive(app, os.path.join(pkg, NAME + ".pyzw"),
                              interpreter="/usr/bin/env python3",
                              compressed=True)
        _write(os.path.join(pkg, "Start-NEC-Calculator.bat"), BAT, crlf=True)
        _write(os.path.join(pkg, "start_mac.command"), MAC)
        _write(os.path.join(pkg, "start_linux.sh"), LINUX)
        _write(os.path.join(pkg, "README.txt"),
               README.format(ver=__version__), crlf=True, bom=True)
        xl = os.path.join(pkg, "Excel")
        os.makedirs(xl)
        PIO.write_template(os.path.join(xl, "panel_list_template.xlsx"),
                           "en")
        PIO.write_template(os.path.join(xl, "盤負載清單範本.xlsx"), "zh")
        web = os.path.join(pkg, "mobile-web")
        os.makedirs(web)
        for f in ("index.html", "necalc.js", "necalc_data.js"):
            shutil.copy2(os.path.join(ROOT, "web", f), web)
        src = os.path.join(pkg, "source")
        for d in ("necalc", "examples", "tests", "docs", "tools", "web"):
            _copytree(os.path.join(ROOT, d), os.path.join(src, d))
        for f in ("run_gui.py", "README.md"):
            shutil.copy2(os.path.join(ROOT, f), src)

        target = os.path.join(out_dir, f"{NAME}-{__version__}.zip")
        execs = {"start_mac.command", "start_linux.sh", NAME + ".pyzw"}
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for base, dirs, files in os.walk(pkg):
                dirs.sort()
                for name in sorted(files):
                    full = os.path.join(base, name)
                    rel = os.path.relpath(full, work).replace(os.sep, "/")
                    info = zipfile.ZipInfo.from_file(full, rel)
                    mode = 0o755 if name in execs else 0o644
                    info.external_attr = (stat.S_IFREG | mode) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with open(full, "rb") as fh:
                        z.writestr(info, fh.read())
        return target
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
