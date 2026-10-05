# NEC Electrical Design Calculator · NEC 電氣設計計算軟體

A design tool for US projects, from **24.9 kV three-phase** down to **120 V single-phase** equipment circuits (motors, lighting, electric heat, receptacles), based on **NFPA 70 (NEC) 2023 / 2026**. The interface switches between **English and Traditional Chinese (中文)**.

美國專案電氣設計計算工具，涵蓋 **24.9 kV 三相**到 **120 V 單相**設備迴路（馬達、燈具、電熱、插座），依 **NEC 2023 / 2026** 選定開關、線徑、管徑及電纜架，並計算負載。介面可切換**中文／英文**。

Pure Python with **no third-party packages** (Tkinter GUI from the standard library).
純 Python，**不需安裝任何套件**（GUI 使用內建 Tkinter）。

![Branch circuit (中文)](docs/branch_zh.png)

| Cable tray 電纜架 | Panel load calc |
|---|---|
| ![tray](docs/tray_zh.png) | ![load](docs/load_en.png) |

---

## Features · 功能

| Module 模組 | What it does 內容 | NEC |
|---|---|---|
| **Branch / Feeder 分路／幹線** | Load in VA/kVA/W/kW/A with PF. Applies 125 % to continuous load and 25 % to the largest motor, then picks the standard OCPD, conductor, EGC, conduit and disconnect, and checks voltage drop. 依功因換算負載，連續負載 ×125 %、最大馬達 +25 %，選定標準保護設備、導線、接地線、導線管、開關，並檢查壓降。 | 210.19/210.20, 215.2/215.3, 240.4(B)(D), 240.6(A), 110.14(C), 310.15, 310.16, 250.122(B)(F), Ch. 9 Tables 1/4/5/9 |
| **Motor 馬達** | FLC from the NEC tables, 125 % conductors, maximum SC/GF device by type (ITCB, TD fuse, NTD fuse, MCP), overload setting, and an HP-rated disconnect. 查表 FLC、125 % 導線、依保護設備型式之上限、過載設定、馬力額定開關。 | 430.6, 430.22, 430.32, Table 430.52, 430.110, Tables 430.248/250 |
| **Transformer 變壓器** | Primary and secondary FLA, secondary bolted fault, and maximum/selected OCPD (> 1000 V and ≤ 1000 V). For a 24.9 kV primary it sizes the MV cable; otherwise it sizes the LV primary and secondary conductors. 一、二次額定電流、短路電流、保護上限與選定值；24.9 kV 一次側自動選高壓電纜。 | Table 450.3(A), Table 450.3(B), 240.21(C) |
| **MV Cable 24.9 kV 高壓電纜** | Minimum size by voltage, design ampacity, short-circuit withstand (ICEA), conductor protection (fuse ≤ 3×, relay ≤ 6×), EGC, conduit fill and jam ratio. 依電壓最小線徑、安培容量、短路耐受、導線保護、接地線、管填充、卡線比。 | 315.10, 315.60, 240.101(A) → Art. 245 (2026), 250.190(C)(3) |
| **Cable Tray 電纜架** | Ladder, ventilated-trough and solid-bottom trays with any mix of LV multiconductor, LV single-conductor, control and MV cables. Sizes the tray width; MV and LV in one tray require a barrier. Gives ampacity in tray (covered or spaced) and a **capacity table** (max cables per 6"–36" width). 梯型／通風槽／實底電纜架；低壓多芯、低壓單芯、控制、中壓電纜混合敷設寬度選定；中低壓同架隔板檢查；蓋板／間距安培容量修正；**容量對照表**。 | 392.10, 392.20(B), 392.22(A)(B)(C), Tables 392.22(A)/(B)(1), 392.80, Table 310.17 |
| **Panel Load Calc 盤負載計算** | Per-load kW/kvar/kVA from PF. Demand factor: automatic receptacle 10 kVA + 50 % and non-coincident heating/cooling, or a manual DF. Diversity factor, automatic phase balancing, imbalance %, capacitor kvar to reach the target PF, and feeder sizing. Exports to CSV. 功率因數、需量因數（自動或自訂）、參差因數、自動平衡相位、不平衡率、功因改善電容、幹線選定、CSV 匯出。 | 220.47, 220.50, 220.60, 430.24, 215.2 |
| **Reference 參考資料** | Built-in NEC tables for checking the data. 內建 NEC 表格，可直接檢視核對。 | 310.16, 310.17, 250.122, Ch. 9, 430, 450.3(A), 392.22 |

Other features · 其他：
- One-click switch between **NEC 2023 and NEC 2026**. The calculation method is the same for ≤ 1000 V. For > 1000 V the code references follow the 2026 move into the new Articles 235 and 245. 一鍵切換 NEC 2023 / 2026。
- **HTML report** export with inputs, results, numbered calculation steps and NEC references, in the selected language. 匯出 HTML 計算書（含輸入、結果、步驟與條文）。
- Save and open projects as JSON. 專案存檔／開啟。

## Quick start · 快速開始

```bash
# Python 3.9+  (Windows / macOS: Tkinter is included with python.org installers)
cd nec-calc
python run_gui.py            # GUI 圖形介面
python -m necalc             # same 同上

python examples/system_24900_to_120.py zh 2026   # 24.9 kV → 120 V example in Chinese, NEC 2026
python -m unittest discover -s tests             # run tests 執行測試
```

### Use as a Python library · 當作 Python 函式庫使用

```python
from necalc import engine as E, loads as L, tray as TR, report as R

w = E.WiringInput(voltage=480, wiring="3ph3w", length_ft=200, pf=0.85)
res = E.design_motor("30", w, device="itcb")
print(R.to_text(res, "zh"))          # or "en"
print(res.summary["wire_text"])      # 3#8 + 1#8G CU THHN/THWN-2, 3/4" EMT

tray = TR.TrayInput(tray_type="ladder", cables=[
    TR.TrayCable("FDR-1", "lv_multi", "500", n_cond=3, qty=2),
    TR.TrayCable("MV-1", "mv_single", "1/0", n_cond=1, qty=3)])
print(R.to_text(TR.design_tray(tray), "en"))
print(TR.capacity_table("lv_multi", sizes=["12", "4/0", "500"]))
```

## Design rules used · 設計邏輯

**Conductor selection 導線選定** (`engine.size_conductors`). The smallest size that passes all of these checks:
1. Ampacity in the termination temperature column (60/75/90 °C, 110.14(C)) ≥ design current (125 % continuous + 100 % non-continuous [+25 % largest motor]).
2. 90 °C ampacity × ambient correction × CCC adjustment ≥ actual load current.
3. Conductor protected by its OCPD. The next standard size up is allowed at ≤ 800 A (240.4(B)); above 800 A ampacity must be ≥ the OCPD. Small-conductor limits apply (240.4(D)). Motor circuits are exempt per 240.4(G).
4. Parallel sets are added automatically once the size passes the chosen maximum (default 500 kcmil). Each set is at least 1/0 and runs in its own raceway with a full-size EGC.
5. If voltage drop (Chapter 9 Table 9, effective Z = R·cosθ + X·sinθ) exceeds the limit, the conductor is upsized and the EGC is increased in proportion (250.122(B)).

**Cable tray 電纜架** (`tray.design_tray`). Cables are grouped as LV multiconductor/control (392.22(A)), LV single conductor (392.22(B)(1)) and MV (392.22(C)). The required widths of the groups are added together (a barrier is required when MV and LV share a tray). The smallest NEMA VE 1 width (6, 9, 12, 18, 24, 30, 36 in) that fits is selected.
> Note: Table 392.22 and NEMA VE 1 list only the standard widths 6/9/12/18/24/30/36 in. A non-standard width such as 15" can be entered in "Width". Its allowable fill is interpolated and flagged.
> 註：表 392.22 及 NEMA VE 1 標準寬度為 6/9/12/18/24/30/36 in；15" 等非標準寬度可於「寬度」欄輸入，程式以內插計算並提示。

## Data sources & limitations · 資料來源與限制

- NEC values are in `necalc/tables.py`. Code references for each edition are in `necalc/codes.py`. Both are plain data and easy to audit or adjust.
  NEC 數值集中在 `tables.py`，條文編號在 `codes.py`，皆可自行稽核修改。
- Values marked **TYPICAL** are **not NEC values** and the program prints a warning whenever it uses them. Verify them with NEC 315.60 or the cable manufacturer:
  標示 **TYPICAL（典型值）** 的資料非 NEC 規範值，使用時程式會發出警告，請以 NEC 315.60 或製造商資料確認：
  - MV cable ampacity (in duct and in free air) and OD 高壓電纜安培容量與外徑
  - Type TC multiconductor cable OD TC 多芯電纜外徑
  - Typical E-rated MV fuse ratings 高壓 E 級熔絲額定
- Out of scope (use ETAP or similar): short-circuit studies beyond the infinite-bus estimate, arc flash, coordination, harmonic heating, and dwelling-unit (Article 220 Part III/IV) calculations.
  未涵蓋：完整短路／電弧閃絡／保護協調（請用 ETAP）、住宅單元負載計算。
- **This is a design aid. Every result must be checked by a qualified engineer against the edition the AHJ has adopted.**
  **本軟體為設計輔助工具，結果須由合格工程師依 AHJ 採用版本複核。**

## Project layout · 專案結構

```
nec-calc/
├── run_gui.py              GUI launcher
├── necalc/
│   ├── tables.py           NEC tables (310.16/17, 250.122, Ch.9, 430, 450, 392 …)
│   ├── codes.py            Section references per edition (2023 / 2026)
│   ├── engine.py           Conductor/OCPD/EGC/conduit/VD, motor, transformer, MV
│   ├── tray.py             Cable tray (Article 392)
│   ├── loads.py            Panel load calculation (PF, DF, diversity)
│   ├── i18n.py             English / 中文 text
│   ├── report.py           Text / HTML / CSV output
│   └── gui.py              Tkinter GUI
├── examples/system_24900_to_120.py
└── tests/
```
