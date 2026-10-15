"""English / Traditional Chinese text for UI, calculation steps and reports."""

LANGS = ("en", "zh")

TEXT = {
    # ---------------- application / common ----------------
    "app_title": ("NEC Electrical Design Calculator (24.9 kV to 120 V)",
                  "NEC 電氣設計計算軟體 (24.9 kV 至 120 V)"),
    "language": ("Language", "語言"),
    "edition": ("NEC edition", "NEC 版本"),
    "calculate": ("Calculate", "計算"),
    "export_html": ("Export report (HTML)", "匯出報告 (HTML)"),
    "export_csv": ("Export CSV", "匯出 CSV"),
    "save": ("Save project", "儲存專案"),
    "open": ("Open project", "開啟專案"),
    "results": ("Results", "計算結果"),
    "summary": ("Summary", "摘要"),
    "steps": ("Calculation steps", "計算步驟"),
    "warnings": ("Warnings", "警告"),
    "notes": ("Notes", "說明"),
    "error": ("Error", "錯誤"),
    "ok": ("OK", "符合"),
    "ng": ("NG", "不符合"),
    "disclaimer": (
        "Design aid only. Verify all results against the NEC edition adopted "
        "by the AHJ, manufacturer data and engineering judgment. Values "
        "marked TYPICAL are not NEC values.",
        "本軟體僅為設計輔助工具，所有結果須依主管機關 (AHJ) 採用之 NEC 版本、"
        "製造商資料及工程判斷複核。標示「典型值」之數據非 NEC 規範值。"),
    "saved_to": ("Saved to", "已儲存至"),

    # ---------------- tabs ----------------
    "tab_branch": ("Branch / Feeder", "分路 / 幹線"),
    "tab_motor": ("Motor", "馬達"),
    "tab_xfmr": ("Transformer", "變壓器"),
    "tab_mv": ("MV Cable 24.9 kV", "高壓電纜 24.9 kV"),
    "tab_load": ("Panel Load Calc", "盤負載計算"),
    "tab_ref": ("Reference", "參考資料"),

    # ---------------- wiring inputs ----------------
    "grp_load": ("Load", "負載"),
    "grp_wiring": ("Wiring method", "配線方式"),
    "grp_conditions": ("Installation conditions", "安裝條件"),
    "voltage": ("Voltage (V)", "電壓 (V)"),
    "wiring": ("System", "系統"),
    "material": ("Conductor material", "導體材質"),
    "insulation": ("Insulation", "絕緣"),
    "term_temp": ("Termination rating (°C)", "端子溫度額定 (°C)"),
    "ambient": ("Ambient temp (°C)", "周溫 (°C)"),
    "extra_ccc": ("Other CCC in raceway", "同管其他載流導體數"),
    "neutral_ccc": ("Neutral is CCC (non-linear)", "中性線計為載流導體 (非線性負載)"),
    "sets": ("Parallel sets (0 = auto)", "並聯組數 (0 = 自動)"),
    "max_size": ("Max size for auto parallel", "自動並聯最大線徑"),
    "length": ("One-way length (ft)", "單程長度 (ft)"),
    "pf": ("Power factor", "功率因數"),
    "vd_limit": ("Voltage-drop limit (%)", "壓降限制 (%)"),
    "conduit_type": ("Conduit type", "導線管種類"),
    "min_size": ("Minimum size", "最小線徑"),
    "load_va": ("Load (VA)", "負載 (VA)"),
    "load_input": ("Load value", "負載數值"),
    "load_unit": ("Unit", "單位"),
    "cont_pct": ("Continuous portion (%)", "連續負載比例 (%)"),
    "ocpd_given": ("OCPD rating (A, blank = auto)", "保護設備額定 (A，空白 = 自動)"),
    "circuit_kind": ("Circuit type", "迴路類型"),
    "load_type": ("Load type", "負載種類"),
    "largest_motor_va": ("Largest motor (VA, feeders)", "最大馬達 (VA，幹線用)"),

    # ---------------- motor ----------------
    "hp": ("Motor HP", "馬達馬力 (HP)"),
    "device": ("SC/GF protective device", "短路/接地故障保護設備"),
    "nameplate_fla": ("Nameplate FLA (blank = table)", "銘牌 FLA (空白 = 查表)"),
    "flc_override": ("FLC override (non-table voltage)", "FLC 自訂 (非表列電壓)"),
    "sf115": ("Service factor ≥ 1.15 or temp rise ≤ 40 °C",
              "服務係數 ≥ 1.15 或溫升 ≤ 40 °C"),
    "design_b_ee": ("Design B energy-efficient", "Design B 高效率馬達"),

    # ---------------- transformer ----------------
    "kva": ("Rating (kVA)", "容量 (kVA)"),
    "pri_v": ("Primary voltage (V)", "一次側電壓 (V)"),
    "sec_v": ("Secondary voltage (V)", "二次側電壓 (V)"),
    "phases": ("Phases", "相數"),
    "z_pct": ("Impedance Z (%)", "阻抗 Z (%)"),
    "location": ("Location", "場所"),
    "pri_device": ("Primary device", "一次側保護"),
    "sec_device": ("Secondary device", "二次側保護"),
    "lv_scheme": ("≤1000 V protection scheme", "≤1000 V 保護方式"),
    "sec_length": ("Secondary length (ft)", "二次側長度 (ft)"),
    "pri_length": ("Primary length (ft)", "一次側長度 (ft)"),
    "grp_primary": ("Primary conductors", "一次側導線"),
    "grp_secondary": ("Secondary conductors", "二次側導線"),

    # ---------------- MV ----------------
    "kv": ("System voltage (kV)", "系統電壓 (kV)"),
    "amps": ("Load current (A)", "負載電流 (A)"),
    "ins_level": ("Insulation level", "絕緣等級"),
    "fault_ka": ("Available fault (kA)", "故障電流 (kA)"),
    "clear_time": ("Clearing time (s)", "清除時間 (s)"),
    "t_oper": ("Operating temp (°C)", "運轉溫度 (°C)"),
    "t_sc": ("Short-circuit temp (°C)", "短路溫度 (°C)"),
    "ocpd_type": ("Protection type", "保護型式"),
    "ocpd_amps": ("Fuse rating / relay pickup (A)", "熔絲額定 / 電驛始動值 (A)"),
    "design_factor": ("Design factor", "設計係數"),
    "cable_od": ("Cable OD (in, 0 = typical)", "電纜外徑 (in，0 = 典型值)"),
    "include_egc": ("Include EGC in conduit", "管內含接地線"),

    # ---------------- load calc ----------------
    "panel_name": ("Panel", "盤名"),
    "panel_system": ("Panel system", "盤系統"),
    "diversity": ("Diversity factor (≥1)", "參差因數 (≥1)"),
    "target_pf": ("Target PF", "目標功率因數"),
    "add": ("Add", "新增"),
    "update": ("Update", "更新"),
    "delete": ("Delete", "刪除"),
    "clear": ("Clear all", "全部清除"),
    "load_example": ("Load example", "載入範例"),
    "size_feeder": ("Size feeder", "選定幹線"),
    "col_ckt": ("Ckt", "迴路"),
    "col_name": ("Description", "名稱"),
    "col_cat": ("Category", "類別"),
    "col_qty": ("Qty", "數量"),
    "col_rating": ("Rating", "額定"),
    "col_unit": ("Unit", "單位"),
    "col_pf": ("PF", "PF"),
    "col_v": ("V", "V"),
    "col_ph": ("Ph", "相"),
    "col_cont": ("Cont.", "連續"),
    "col_df": ("DF", "需量因數"),
    "col_conn": ("Phase", "接相"),
    "col_kva": ("kVA", "kVA"),
    "col_kw": ("kW", "kW"),
    "col_dkva": ("Demand kVA", "需量 kVA"),
    "col_amps": ("A", "A"),
    "df_auto": ("DF (blank = auto)", "需量因數 (空白 = 自動)"),
    "phase_conn": ("Phase connection", "接相"),
    "continuous": ("Continuous (≥3 h)", "連續負載 (≥3 小時)"),
    "lc_connected": ("Connected load", "連接負載"),
    "lc_demand": ("Demand load (after DF)", "需量負載 (乘需量因數後)"),
    "lc_coincident": ("Coincident demand (after diversity)",
                      "同時需量 (除以參差因數後)"),
    "lc_design": ("Feeder design load", "幹線設計負載"),
    "lc_phase": ("Phase loading", "各相負載"),
    "lc_imbalance": ("Phase imbalance", "三相不平衡率"),
    "lc_cap": ("Capacitor to reach target PF", "改善至目標功因所需電容"),
    "lc_overall_df": ("Overall demand factor", "整體需量因數"),
    "lc_cont": ("Continuous load", "連續負載"),
    "lc_largest_motor": ("Largest motor", "最大馬達"),

    # ---------------- summary labels ----------------
    "s_i_load": ("Load current", "負載電流"),
    "s_i_design": ("Design current", "設計電流"),
    "s_ocpd": ("Breaker / fuse", "斷路器 / 熔絲"),
    "s_switch": ("Disconnect switch", "隔離開關"),
    "s_wire": ("Conductors", "導線"),
    "s_size": ("Phase conductor", "相線"),
    "s_sets": ("Parallel sets", "並聯組數"),
    "s_neutral": ("Neutral", "中性線"),
    "s_egc": ("EGC", "設備接地線"),
    "s_conduit": ("Conduit", "導線管"),
    "s_vd": ("Voltage drop", "壓降"),
    "s_ampacity": ("Conductor ampacity", "導線安培容量"),
    "s_flc": ("Motor FLC", "馬達滿載電流 FLC"),
    "s_overload": ("Overload setting", "過載保護設定"),
    "s_ocpd_motor": ("Branch SC/GF device", "分路短路/接地保護"),
    "s_i_pri": ("Primary FLA", "一次側額定電流"),
    "s_i_sec": ("Secondary FLA", "二次側額定電流"),
    "s_isc": ("Secondary fault (infinite bus)", "二次側短路電流 (無限匯流排)"),
    "s_pri_ocpd": ("Primary OCPD (selected)", "一次側保護 (選定)"),
    "s_pri_ocpd_max": ("Primary OCPD (max)", "一次側保護 (上限)"),
    "s_sec_ocpd": ("Secondary OCPD", "二次側保護"),
    "s_mv_cable": ("MV cable", "高壓電纜"),
    "s_sc_cmil": ("Min. area for short circuit", "短路耐受最小截面積"),
    "s_jam": ("Jam ratio", "卡線比 (Jam ratio)"),

    # ---------------- option labels ----------------
    "opt_cu": ("Copper", "銅"),
    "opt_al": ("Aluminum", "鋁"),
    "opt_THHN": ("THHN/THWN-2 (90 °C)", "THHN/THWN-2 (90 °C)"),
    "opt_XHHW": ("XHHW-2 (90 °C)", "XHHW-2 (90 °C)"),
    "opt_1ph2w": ("1Ø 2W", "單相二線"),
    "opt_1ph3w": ("1Ø 3W (120/240)", "單相三線 (120/240)"),
    "opt_3ph3w": ("3Ø 3W", "三相三線"),
    "opt_3ph4w": ("3Ø 4W", "三相四線"),
    "opt_EMT": ("EMT", "EMT 電氣金屬管"),
    "opt_IMC": ("IMC", "IMC 中型金屬管"),
    "opt_RMC": ("RMC", "RMC 厚金屬管"),
    "opt_PVC40": ("PVC Sch 40", "PVC Sch 40"),
    "opt_PVC80": ("PVC Sch 80", "PVC Sch 80"),
    "opt_ntd_fuse": ("Non-time-delay fuse", "非延時熔絲"),
    "opt_td_fuse": ("Dual-element (time-delay) fuse", "雙元件延時熔絲"),
    "opt_inst_cb": ("Instantaneous-trip CB (MCP)", "瞬時跳脫斷路器 (MCP)"),
    "opt_itcb": ("Inverse-time CB", "反時限斷路器"),
    "opt_any": ("Any location", "任何場所"),
    "opt_supervised": ("Supervised location", "受監督場所"),
    "opt_fuse": ("Fuse", "熔絲"),
    "opt_cb": ("Circuit breaker", "斷路器"),
    "opt_relay": ("Breaker + relay", "斷路器 + 保護電驛"),
    "opt_pri_only": ("Primary only", "僅一次側保護"),
    "opt_pri_sec": ("Primary + secondary", "一次側 + 二次側保護"),
    "opt_25kV_100": ("25 kV 100 %", "25 kV 100 %"),
    "opt_25kV_133": ("25 kV 133 %", "25 kV 133 %"),
    "opt_35kV_100": ("35 kV 100 %", "35 kV 100 %"),
    "opt_branch": ("Branch circuit", "分路"),
    "opt_feeder": ("Feeder", "幹線"),
    "opt_lighting": ("Lighting", "照明"),
    "opt_receptacle": ("Receptacle", "插座"),
    "opt_motor": ("Motor", "馬達"),
    "opt_heating": ("Heating", "電熱"),
    "opt_cooling": ("Cooling / A/C", "空調"),
    "opt_equipment": ("Equipment", "設備"),
    "opt_other": ("Other", "其他"),
    "opt_auto": ("Auto", "自動"),
    "opt_yes": ("Yes", "是"),
    "opt_no": ("No", "否"),

    # ---------------- calculation steps ----------------
    "st_load_current": (
        "Load current: {va:,.0f} VA / ({phases}Ø, {volts:g} V) = {amps:.1f} A",
        "負載電流：{va:,.0f} VA / ({phases}相, {volts:g} V) = {amps:.1f} A"),
    "st_design_current": (
        "Design current = 125% × {cont:.1f} A (continuous) + {noncont:.1f} A "
        "(non-continuous) + {motor25:.1f} A (25% largest motor) = {amps:.1f} A",
        "設計電流 = 125% × {cont:.1f} A (連續) + {noncont:.1f} A (非連續) + "
        "{motor25:.1f} A (最大馬達 25%) = {amps:.1f} A"),
    "st_ocpd_select": (
        "OCPD: next standard rating ≥ {amps:.1f} A → {ocpd} A",
        "保護設備：選用 ≥ {amps:.1f} A 之標準額定 → {ocpd} A"),
    "st_ocpd_given": (
        "OCPD specified {ocpd} A (must be ≥ design current {amps:.1f} A)",
        "指定保護設備 {ocpd} A (須 ≥ 設計電流 {amps:.1f} A)"),
    "st_temp_corr": (
        "Ambient {ambient:g} °C, {temp} °C insulation → correction factor "
        "{factor:.2f}",
        "周溫 {ambient:g} °C，{temp} °C 絕緣 → 溫度修正係數 {factor:.2f}"),
    "st_ccc_adj": (
        "{n} current-carrying conductors in raceway → adjustment factor "
        "{factor:.2f}",
        "管內載流導體 {n} 條 → 調整係數 {factor:.2f}"),
    "st_ampacity_term": (
        "{sets} × {size} at {temp} °C termination column: {amps:.0f} A ≥ "
        "{need:.1f} A",
        "{sets} × {size} 依 {temp} °C 端子欄位：{amps:.0f} A ≥ {need:.1f} A"),
    "st_ampacity_derated": (
        "Derated ampacity: {base:.0f} A ({temp} °C) × {ft:.2f} × {fa:.2f} = "
        "{amps:.1f} A ≥ load {need:.1f} A",
        "修正後安培容量：{base:.0f} A ({temp} °C) × {ft:.2f} × {fa:.2f} = "
        "{amps:.1f} A ≥ 負載 {need:.1f} A"),
    "st_parallel": (
        "{sets} conductors in parallel per phase (min. 1/0 AWG, each set in "
        "its own raceway)",
        "每相 {sets} 條並聯 (最小 1/0 AWG，每組獨立配管)"),
    "st_protection": (
        "Conductor protection: ampacity {amps:.1f} A protected by {ocpd} A "
        "OCPD (next size up permitted ≤ 800 A; small-conductor limits)",
        "導線保護：安培容量 {amps:.1f} A 由 {ocpd} A 保護 (≤ 800 A 允許取上一級；"
        "小線徑限制)"),
    "st_vd": (
        "Voltage drop: {amps:.1f} A, {length:g} ft, {size} → {volts:.2f} V "
        "= {pct:.2f}% (limit {limit:g}%)",
        "壓降：{amps:.1f} A，{length:g} ft，{size} → {volts:.2f} V = "
        "{pct:.2f}% (限制 {limit:g}%)"),
    "st_vd_upsize": (
        "Conductor increased from {old} to {new} for voltage drop",
        "因壓降將導線由 {old} 加大至 {new}"),
    "st_egc": ("EGC for {ocpd} A OCPD: {size}",
               "{ocpd} A 保護設備之設備接地線：{size}"),
    "st_egc_upsize": (
        "EGC increased proportionally (×{ratio:.2f}) from {old} to {new}",
        "設備接地線依比例 (×{ratio:.2f}) 由 {old} 加大至 {new}"),
    "st_egc_parallel": (
        "Full-size EGC {size} in each of {sets} parallel raceways",
        "{sets} 組並聯配管各配置全尺寸接地線 {size}"),
    "st_conduit": (
        "Conduit fill: {n} conductors, {area:.4f} in² → {qty} × {trade}\" "
        "{ctype} ({fill:.1f}% ≤ {maxfill:.0f}%)",
        "導線管填充：{n} 條導線，{area:.4f} in² → {qty} × {trade}\" {ctype} "
        "({fill:.1f}% ≤ {maxfill:.0f}%)"),
    "st_switch": (
        "Disconnect switch: {amps} A (≥ {ocpd} A fuse/OCPD)",
        "隔離開關：{amps} A (≥ {ocpd} A 熔絲/保護設備)"),
    "st_motor_flc": (
        "Motor FLC from NEC table: {hp} HP, {phases}Ø, {volts:g} V → {flc} A",
        "馬達 FLC 查 NEC 表：{hp} HP，{phases} 相，{volts:g} V → {flc} A"),
    "st_motor_cond": (
        "Branch conductors ≥ 125% × {flc} A = {amps:.1f} A",
        "分路導線 ≥ 125% × {flc} A = {amps:.1f} A"),
    "st_motor_ocpd": (
        "SC/GF device ≤ {pct:.0f}% × {flc} A = {amps:.1f} A → {ocpd} A "
        "(next standard size permitted)",
        "短路/接地保護 ≤ {pct:.0f}% × {flc} A = {amps:.1f} A → {ocpd} A "
        "(允許取上一標準額定)"),
    "st_motor_mcp": (
        "MCP trip setting ≤ {pct:.0f}% × {flc} A = {amps:.1f} A",
        "MCP 跳脫設定 ≤ {pct:.0f}% × {flc} A = {amps:.1f} A"),
    "st_motor_ol": (
        "Overload: {pct:.0f}% × {fla} A = {amps:.1f} A",
        "過載保護：{pct:.0f}% × {fla} A = {amps:.1f} A"),
    "st_motor_disc": (
        "Disconnect ≥ 115% × {flc} A = {amps:.1f} A → {switch} A, HP rated",
        "隔離開關 ≥ 115% × {flc} A = {amps:.1f} A → {switch} A (須具馬力額定)"),
    "st_xfmr_fla": (
        "{kva:g} kVA: primary {pv:g} V → {ip:.1f} A; secondary {sv:g} V → "
        "{is_:.1f} A",
        "{kva:g} kVA：一次側 {pv:g} V → {ip:.1f} A；二次側 {sv:g} V → "
        "{is_:.1f} A"),
    "st_xfmr_isc": (
        "Secondary bolted fault (infinite source) = FLA / Z({z:g}%) = "
        "{isc:.1f} kA",
        "二次側短路電流 (無限電源) = FLA / Z({z:g}%) = {isc:.1f} kA"),
    "st_xfmr_pri_mv": (
        "Primary ({loc}, Z = {z:g}%, {dev}): max {pct:.0f}% = {amps:.1f} A "
        "→ max standard {std}; selected {sel}",
        "一次側 ({loc}，Z = {z:g}%，{dev})：上限 {pct:.0f}% = {amps:.1f} A → "
        "標準上限 {std}；選用 {sel}"),
    "st_xfmr_pri_lv": (
        "Primary ({scheme}): max {pct:.0f}% = {amps:.1f} A → max {std} A; "
        "selected {sel} A",
        "一次側 ({scheme})：上限 {pct:.0f}% = {amps:.1f} A → 上限 {std} A；"
        "選用 {sel} A"),
    "st_xfmr_sec": (
        "Secondary: max {pct:.0f}% = {amps:.1f} A → max {std} A; selected "
        "{sel} A",
        "二次側：上限 {pct:.0f}% = {amps:.1f} A → 上限 {std} A；選用 {sel} A"),
    "st_xfmr_sec_cond": (
        "Secondary conductors sized for secondary OCPD; check tap length "
        "rules",
        "二次側導線依二次側保護設備選定；並須檢討分接長度規定"),
    "st_mv_min": ("Minimum conductor size for {kv:g} kV: {size}",
                  "{kv:g} kV 最小導線尺寸：{size}"),
    "st_mv_design": ("Design ampacity = {amps:.1f} A × {factor:g} = {req:.1f} A",
                     "設計安培容量 = {amps:.1f} A × {factor:g} = {req:.1f} A"),
    "st_mv_sc": (
        "Short-circuit withstand: {ka:g} kA for {t:g} s, {t1:g}→{t2:g} °C "
        "→ min. {cmil:,.0f} cmil",
        "短路耐受：{ka:g} kA，{t:g} 秒，{t1:g}→{t2:g} °C → 最小 {cmil:,.0f} cmil"),
    "st_mv_size": (
        "Selected {size}: ampacity {amps} A ≥ {req:.1f} A; {cmil:,} cmil ≥ "
        "{sc:,.0f} cmil",
        "選用 {size}：安培容量 {amps} A ≥ {req:.1f} A；{cmil:,} cmil ≥ "
        "{sc:,.0f} cmil"),
    "st_mv_ocpd": (
        "Conductor protection: {ocpd:g} A ≤ {mult:g} × {amps} A = {limit:g} A",
        "導線保護：{ocpd:g} A ≤ {mult:g} × {amps} A = {limit:g} A"),
    "st_mv_egc": (
        "EGC for {rating:g} A protection: {size} (min. 6 AWG Cu / 4 AWG Al)",
        "{rating:g} A 保護之接地線：{size} (最小 6 AWG 銅 / 4 AWG 鋁)"),
    "st_feeder_load": (
        "Feeder: {kva:.1f} kVA + 25% × {cont:.1f} kVA (continuous) + 25% × "
        "{motor:.1f} kVA (largest motor) = {design:.1f} kVA → {amps:.1f} A",
        "幹線：{kva:.1f} kVA + 25% × {cont:.1f} kVA (連續) + 25% × "
        "{motor:.1f} kVA (最大馬達) = {design:.1f} kVA → {amps:.1f} A"),

    # ---------------- notes ----------------
    "n_receptacle": (
        "Receptacle demand: {kva:.1f} kVA → first 10 kVA at 100%, remainder "
        "at 50% (effective DF {df:.3f})",
        "插座需量：{kva:.1f} kVA → 前 10 kVA 以 100%，其餘 50% (等效需量因數 "
        "{df:.3f})"),
    "n_noncoincident": (
        "Non-coincident loads: heating {heat:.1f} kVA vs cooling {cool:.1f} "
        "kVA → {drop} omitted",
        "非同時負載：電熱 {heat:.1f} kVA 與空調 {cool:.1f} kVA → 省略{drop}"),

    # ---------------- warnings ----------------
    "w_vd_not_met": (
        "Voltage drop {pct:.2f}% exceeds {limit:g}% even at largest size - "
        "add parallel sets",
        "即使最大線徑壓降仍為 {pct:.2f}% (超過 {limit:g}%)，請增加並聯組數"),
    "w_z_approx": (
        "{size} is not listed in Chapter 9 Table 9 - impedance approximated",
        "{size} 未列於第 9 章表 9，阻抗為近似值"),
    "w_conduit_none": (
        "No single {ctype} conduit fits - use more raceways",
        "單一 {ctype} 導線管無法容納，請增加配管"),
    "w_ocpd_small": (
        "Specified OCPD {ocpd} A is smaller than design current {amps} A",
        "指定保護設備 {ocpd} A 小於設計電流 {amps} A"),
    "w_mv_typical": (
        "MV ampacity uses TYPICAL values (3-1/C Cu in one duct, 20 °C earth). "
        "Verify with NEC 315.60 tables or manufacturer data.",
        "高壓安培容量採用典型值 (三條單芯銅線同一管路，土壤 20 °C)，"
        "請依 NEC 315.60 表或製造商資料確認。"),
    "w_mv_od_typical": (
        "Cable OD {od:.2f} in is TYPICAL - verify with manufacturer",
        "電纜外徑 {od:.2f} in 為典型值，請向製造商確認"),
    "w_jam": (
        "Jam ratio {ratio:.2f} is between 2.8 and 3.2 - risk of cable jamming "
        "during pull; consider another conduit size",
        "卡線比 {ratio:.2f} 介於 2.8 與 3.2 之間，拉線時有卡線風險，建議改變管徑"),


    # ---------------- cable tray ----------------
    "tab_tray": ("Cable Tray", "電纜架"),
    "tray_type": ("Tray type", "電纜架型式"),
    "tray_depth": ("Usable depth (in)", "可用深度 (in)"),
    "tray_width": ("Width (in, 0 = auto)", "寬度 (in，0 = 自動)"),
    "tray_covered": ("Solid cover > 6 ft", "實心蓋板 > 6 ft"),
    "tray_arrangement": ("Arrangement", "敷設方式"),
    "cable_kind": ("Cable type", "電纜種類"),
    "n_cond": ("Cond./cable", "芯數"),
    "cable_size": ("Size", "線徑"),
    "cable_qty": ("Qty (cables)", "數量 (條)"),
    "cable_od_in": ("OD (in, 0 = auto)", "外徑 (in，0 = 自動)"),
    "capacity_table": ("Capacity table", "容量對照表"),
    "cap_title": ("Max. number of cables per tray width ({kind}, {tray})",
                  "各寬度電纜架可敷設最大條數 ({kind}，{tray})"),
    "col_od": ("OD in", "外徑 in"),
    "col_area": ("Area in²", "面積 in²"),
    "col_kind": ("Type", "種類"),
    "col_size": ("Size", "線徑"),
    "s_tray": ("Cable tray", "電纜架"),
    "s_req_width": ("Required width", "需求寬度"),
    "s_tray_fill": ("Width utilization", "寬度使用率"),
    "opt_ladder": ("Ladder", "梯型"),
    "opt_vented_trough": ("Ventilated trough", "通風槽型"),
    "opt_solid_bottom": ("Solid bottom", "實底型"),
    "opt_random": ("Random lay / multilayer", "隨意敷設 / 多層"),
    "opt_spaced": ("Single layer, spaced 1 dia.", "單層且間距 ≥ 1 倍外徑"),
    "opt_lv_multi": ("LV multiconductor (TC/MC)", "低壓多芯 (TC/MC)"),
    "opt_lv_single": ("LV single conductor (≥1/0)", "低壓單芯 (≥1/0)"),
    "opt_control": ("Control / signal", "控制 / 信號"),
    "opt_mv_single": ("MV single conductor", "中壓單芯"),
    "opt_mv_multi": ("MV 3-conductor", "中壓三芯"),
    "st_tray_control": (
        "Control/signal only: {area:.2f} in² ≤ {pct:.0f}% × W × {depth:g} in "
        "→ W ≥ {width:.2f} in",
        "僅控制/信號電纜：{area:.2f} in² ≤ {pct:.0f}% × W × {depth:g} in → "
        "W ≥ {width:.2f} in"),
    "st_tray_multi_large": (
        "All multiconductor cables ≥ 4/0: Σ diameters {sd:.2f} in ≤ "
        "{pct:.0f}% × W (single layer) → W ≥ {width:.2f} in",
        "多芯電纜皆 ≥ 4/0：外徑總和 {sd:.2f} in ≤ {pct:.0f}% × W (單層) → "
        "W ≥ {width:.2f} in"),
    "st_tray_multi_small": (
        "All multiconductor cables < 4/0: Σ areas {area:.2f} in² ≤ Table "
        "392.22(A) column {col} → W ≥ {width:.2f} in",
        "多芯電纜皆 < 4/0：截面積總和 {area:.2f} in² ≤ 表 392.22(A) 第 {col} 欄 "
        "→ W ≥ {width:.2f} in"),
    "st_tray_multi_mixed": (
        "Mixed: Σ areas (< 4/0) {area:.2f} in² ≤ column {col} value − "
        "{k:g} × Sd ({sd:.2f} in, ≥ 4/0 single layer) → W ≥ {width:.2f} in",
        "混合敷設：< 4/0 截面積總和 {area:.2f} in² ≤ 第 {col} 欄數值 − "
        "{k:g} × Sd ({sd:.2f} in，≥ 4/0 單層) → W ≥ {width:.2f} in"),
    "st_tray_single_dia": (
        "Single conductors include 1/0–4/0: Σ diameters of all single "
        "conductors {sd:.2f} in ≤ W",
        "單芯電纜含 1/0–4/0：所有單芯外徑總和 {sd:.2f} in ≤ W"),
    "st_tray_single_area": (
        "250–900 kcmil: Σ areas {area:.2f} in² ≤ Table 392.22(B)(1) col. 1 "
        "→ W ≥ {width:.2f} in",
        "250–900 kcmil：截面積總和 {area:.2f} in² ≤ 表 392.22(B)(1) 第 1 欄 → "
        "W ≥ {width:.2f} in"),
    "st_tray_single_mixed": (
        "Mixed: Σ areas (250–900 kcmil) {area:.2f} in² ≤ col. 1 − {k:g} × Sd "
        "({sd:.2f} in, ≥ 1000 kcmil) → W ≥ {width:.2f} in",
        "混合：250–900 kcmil 截面積 {area:.2f} in² ≤ 第 1 欄 − {k:g} × Sd "
        "({sd:.2f} in，≥ 1000 kcmil) → W ≥ {width:.2f} in"),
    "st_tray_single_large": (
        "All ≥ 1000 kcmil: Σ diameters {sd:.2f} in ≤ W",
        "皆 ≥ 1000 kcmil：外徑總和 {sd:.2f} in ≤ W"),
    "st_tray_mv": (
        "Cables over 2000 V: Σ diameters {sd:.2f} in ≤ W, single layer",
        "2000 V 以上電纜：外徑總和 {sd:.2f} in ≤ W，單層敷設"),
    "st_tray_barrier": (
        "MV and LV cables in the same tray: solid fixed barrier required "
        "(widths of each section added)",
        "中壓與低壓電纜同架：須設置固定實心隔板 (各區寬度相加)"),
    "st_tray_sum": ("Total required width = {parts} = {width:.2f} in",
                    "總需求寬度 = {parts} = {width:.2f} in"),
    "st_tray_select": (
        "Required {req:.2f} in → select {n} × {width:g} in tray "
        "(utilization {fill:.0f}%)",
        "需求 {req:.2f} in → 選用 {n} × {width:g} in 電纜架 (使用率 {fill:.0f}%)"),
    "st_tray_check": (
        "Specified width {width:g} in vs required {req:.2f} in "
        "(utilization {fill:.0f}%)",
        "指定寬度 {width:g} in，需求 {req:.2f} in (使用率 {fill:.0f}%)"),
    "st_tray_amp": (
        "{name} ({size}): {base} A (Table {tbl}) × {ft:.2f} (ambient) × "
        "{fa:.2f} × {fc:.2f} (tray) = {amps:.0f} A",
        "{name} ({size})：{base} A (表 {tbl}) × {ft:.2f} (周溫) × {fa:.2f} × "
        "{fc:.2f} (電纜架) = {amps:.0f} A"),
    "st_tray_single_note": (
        "Single conductors in tray: 1/0 AWG min., listed/marked for CT use, "
        "industrial establishment with qualified persons; 1/0–4/0 in ladder "
        "tray with rung spacing ≤ 9 in",
        "單芯電纜敷設於電纜架：最小 1/0 AWG，須標示 CT use，限有合格人員維護之"
        "工業場所；1/0–4/0 須用橫檔間距 ≤ 9 in 之梯型架"),
    "w_tray_mv_lv": (
        "MV (> 2000 V) and LV cables share the tray - provide a solid fixed "
        "barrier or use separate trays (392.20(B))",
        "中壓 (> 2000 V) 與低壓電纜同架，須加固定實心隔板或分架敷設 (392.20(B))"),
    "w_tray_depth": (
        "Cable OD {od:.2f} in exceeds tray usable depth {depth:g} in",
        "電纜外徑 {od:.2f} in 超過電纜架可用深度 {depth:g} in"),
    "w_tray_od_typical": (
        "Cable ODs marked auto are TYPICAL values - verify with the cable "
        "manufacturer",
        "自動外徑為典型值，請向電纜製造商確認"),
    "w_tray_nonstd": (
        "{width:g} in is not a NEMA VE 1 / Table 392.22 standard width - "
        "allowable fill interpolated",
        "{width:g} in 非 NEMA VE 1 / 表 392.22 標準寬度，容許填充量以內插計算"),
    "w_tray_multiple": (
        "Required width {req:.1f} in exceeds 36 in - use {n} trays and divide "
        "cables",
        "需求寬度 {req:.1f} in 超過 36 in，請使用 {n} 座電纜架並分配電纜"),
    "w_tray_single_solid": (
        "392.22(B) fill rules for single conductors apply to ladder / "
        "ventilated trough trays",
        "392.22(B) 單芯電纜填充規定適用於梯型 / 通風槽型電纜架"),
    "w_tray_single_min": (
        "Single conductors smaller than 1/0 AWG ({sizes}) are not permitted "
        "in cable tray",
        "小於 1/0 AWG 之單芯電纜 ({sizes}) 不得敷設於電纜架"),
    "w_tray_mv_amp_typical": (
        "MV ampacity in tray uses TYPICAL free-air values - verify with NEC "
        "315.60 tables",
        "中壓電纜架安培容量採典型自由空氣值，請依 NEC 315.60 表確認"),
    "err_tray_empty": ("No cables in tray", "電纜架內無電纜"),
    "err_tray_od": ("No OD data for size {size} - enter OD",
                    "{size} 無外徑資料，請輸入外徑"),


    # ---------------- web / mobile ----------------
    "web_subtitle": ("24.9 kV to 120 V · NEC conductor, OCPD, conduit, "
                     "cable tray and load calculations",
                     "24.9 kV 至 120 V · 依 NEC 選定導線、保護設備、導線管、"
                     "電纜架及負載計算"),
    "nav_branch": ("Branch", "分路"),
    "nav_motor": ("Motor", "馬達"),
    "nav_xfmr": ("Xfmr", "變壓器"),
    "nav_mv": ("MV", "高壓"),
    "nav_tray": ("Tray", "電纜架"),
    "nav_load": ("Load", "負載"),
    "copy_results": ("Copy results", "複製結果"),
    "copied": ("Copied", "已複製"),
    "copy_failed": ("Copy blocked - text selected, copy it manually",
                    "無法自動複製，已選取文字，請手動複製"),
    "more_settings": ("Wiring and conditions", "配線與安裝條件"),
    "cables_in_tray": ("Cables in tray", "電纜清單"),
    "loads_in_panel": ("Loads", "負載清單"),
    "edit": ("Edit", "編輯"),
    "cancel": ("Cancel", "取消"),
    "save_item": ("Save", "儲存"),
    "add_cable": ("Add cable", "新增電纜"),
    "add_load": ("Add load", "新增負載"),
    "confirm_clear": ("Tap again to clear all", "再按一次以全部清除"),
    "auto_calc_note": ("Results update as you type.", "輸入時自動計算。"),
    "mv_from_tab": ("The MV primary cable uses the settings on the MV tab "
                    "(fault current, insulation, conduit).",
                    "一次側高壓電纜沿用「高壓」頁設定（故障電流、絕緣、管種）。"),
    "empty_tray": ("No cables yet. Add the first cable above.",
                   "尚無電纜，請由上方新增第一條。"),
    "empty_load": ("No loads yet. Add the first load above.",
                   "尚無負載，請由上方新增第一筆。"),
    "example_note": ("Example data - replace with your project values.",
                     "範例資料，請改為專案數值。"),
    "vd_meter": ("Voltage drop vs limit", "壓降 / 限制"),
    "fill_meter": ("Conduit fill vs 40 %", "導線管填充 / 40 %"),
    "tray_meter": ("Tray width used", "電纜架寬度使用率"),


    # ---------------- busway (Article 368, Schneider I-Line) ----------------
    "method": ("Conductor type", "配線型式"),
    "opt_cable": ("Cable in conduit", "電纜 / 導線管"),
    "opt_busway": ("Busway (I-Line)", "匯流排槽 (I-Line)"),
    "grp_busway": ("Busway", "匯流排槽"),
    "bw_type": ("Busway type", "匯流排槽型式"),
    "opt_bw_feeder": ("Feeder (800 A and up)", "饋線型 (800 A 以上)"),
    "opt_bw_plugin": ("Plug-in", "插接型"),
    "bw_neutral": ("Neutral", "中性線"),
    "opt_n100": ("100 % neutral (standard)", "100 % 中性線 (標準)"),
    "opt_harm_x": ("Harmonic rated X (THD 15–35 %)",
                   "諧波額定 X (THD 15–35 %)"),
    "opt_harm_y": ("Harmonic rated Y (THD > 35 %)",
                   "諧波額定 Y (THD > 35 %)"),
    "opt_n0": ("No neutral (3-wire)", "無中性線 (三線式)"),
    "bw_ground": ("Ground", "接地"),
    "opt_g_int50": ("50 % aluminum integral ground bus (G)",
                    "50 % 鋁製內建接地匯流排 (G)"),
    "opt_g_int50cu": ("50 % copper integral ground bus (GG)",
                      "50 % 銅製內建接地匯流排 (GG)"),
    "opt_g_housing": ("Housing only (225–600 A)", "僅外殼接地 (225–600 A)"),
    "bw_bracing": ("Short-circuit bracing", "短路耐受等級"),
    "opt_std": ("Standard bracing", "標準耐受"),
    "opt_high": ("High short circuit (H)", "高短路耐受 (H)"),
    "opt_br_std": ("standard bracing", "標準耐受"),
    "opt_br_high": ("high short circuit, H", "高短路耐受 H"),
    "bw_load": ("Load distribution", "負載分布"),
    "opt_concentrated": ("concentrated at end", "末端集中負載"),
    "opt_distributed": ("uniformly distributed", "均勻分布負載"),
    "bw_rating": ("Busway rating (A, 0 = auto)", "匯流排槽額定 (A，0 = 自動)"),
    "bw_runs": ("Parallel runs (0 = auto)", "並聯路數 (0 = 自動)"),
    "bw_r": ("R (mΩ/100 ft, 0 = I-Line data)", "R (mΩ/100 ft，0 = I-Line 資料)"),
    "bw_x": ("X (mΩ/100 ft, 0 = I-Line data)", "X (mΩ/100 ft，0 = I-Line 資料)"),
    "bw_sccr": ("SCCR (kA, 0 = I-Line data)", "短路耐受 (kA，0 = I-Line 資料)"),
    "bw_fault": ("Available fault (kA, 0 = unknown)",
                 "可用故障電流 (kA，0 = 未知)"),
    "s_busway": ("Busway", "匯流排槽"),
    "s_bw_label": ("Busway rating", "匯流排槽額定"),
    "s_sccr": ("Busway SCCR", "匯流排槽短路耐受"),
    "s_bw_ampacity": ("Busway ampacity (derated)", "匯流排槽容量 (降額後)"),
    "st_bw_derate": (
        "I-Line rated 55 °C rise over 40 °C ambient; ambient {ambient:g} °C "
        "→ derating factor {factor:.3f}",
        "I-Line 額定為周溫 40 °C、溫升 55 °C；周溫 {ambient:g} °C → 降額係數 "
        "{factor:.3f}"),
    "st_bw_select": (
        "{runs} × {rating:g} A × {factor:.3f} = {amps:.0f} A ≥ design current "
        "{need:.1f} A",
        "{runs} × {rating:g} A × {factor:.3f} = {amps:.0f} A ≥ 設計電流 "
        "{need:.1f} A"),
    "st_bw_ocpd": (
        "Busway protected at its rating: OCPD {ocpd:g} A vs {amps:.0f} A "
        "(next standard size up permitted only ≤ 800 A)",
        "匯流排槽依額定保護：保護設備 {ocpd:g} A 對 {amps:.0f} A "
        "(僅 ≤ 800 A 時可取上一級標準額定)"),
    "st_bw_vd": (
        "Voltage drop: {amps:.1f} A per run, {length:g} ft, R {r:.2f} / "
        "X {x:.2f} mΩ per 100 ft, {load} → {volts:.2f} V = {pct:.2f}% "
        "(limit {limit:g}%)",
        "壓降：每路 {amps:.1f} A，{length:g} ft，R {r:.2f} / X {x:.2f} "
        "mΩ/100 ft，{load} → {volts:.2f} V = {pct:.2f}% (限制 {limit:g}%)"),
    "st_bw_upsize": (
        "Busway increased from {old:g} A to {new:g} A for voltage drop",
        "因壓降將匯流排槽由 {old:g} A 加大至 {new:g} A"),
    "st_bw_sccr": (
        "Short-circuit rating {sccr:g} kA ({bracing}) ≥ available fault "
        "{fault:.1f} kA",
        "短路耐受 {sccr:g} kA ({bracing}) ≥ 可用故障電流 {fault:.1f} kA"),
    "st_bw_sccr_info": (
        "Short-circuit rating {sccr:g} kA ({bracing}) - compare with the "
        "available fault current",
        "短路耐受 {sccr:g} kA ({bracing})，請與可用故障電流比對"),
    "st_bw_ground": (
        "Neutral: {neutral}; ground: {ground}, DC resistance {rg:.1f} mΩ per "
        "100 ft (Table 6); bond per Article 250",
        "中性線：{neutral}；接地：{ground}，直流電阻 {rg:.1f} mΩ/100 ft "
        "(表 6)；依第 250 條接地搭接"),
    "st_bw_ground_h": (
        "Neutral: {neutral}; ground: {ground}; bond per Article 250",
        "中性線：{neutral}；接地：{ground}；依第 250 條接地搭接"),
    "st_bw_catalog": (
        "I-Line catalog prefix: {cat} (confirm the full catalog number with "
        "Schneider Electric)",
        "I-Line 型號字首：{cat} (完整型號請向施耐德電機確認)"),
    "st_bw_install": (
        "Dry, accessible locations (outdoor / wet only if identified); "
        "support at ≤ 5 ft unless marked otherwise; taps through plug-in "
        "devices with overcurrent protection",
        "安裝於乾燥、可觸及處 (戶外/潮濕場所須為適用型)；支撐間距 ≤ 5 ft "
        "(除非另有標示)；分歧須經具過電流保護之插接裝置"),
    "w_bw_data": (
        "Impedance and SCCR from Schneider Electric I-Line catalog "
        "5600CT9101 (03/2018) - confirm current data for the project",
        "阻抗與短路耐受取自施耐德 I-Line 型錄 5600CT9101 (2018/03)，"
        "請向原廠確認專案適用之最新資料"),
    "w_bw_parallel": (
        "{runs} parallel runs of {rating:g} A: equal length and impedance, "
        "same construction - confirm with Schneider Electric and the AHJ",
        "{runs} 路 {rating:g} A 並聯：須同長度、同阻抗、同構造，"
        "請向施耐德電機及主管機關確認"),
    "w_bw_no_high": (
        "High short-circuit bracing is not offered at {rating:g} A in this "
        "construction - standard bracing used",
        "此構造之 {rating:g} A 無高短路耐受型，改用標準耐受"),
    "w_bw_fitting150": (
        "Certain I-Line fittings are UL rated 150 kA at this rating "
        "(Table 1, note 1)",
        "此額定部分 I-Line 配件之 UL 短路耐受為 150 kA (表 1 註 1)"),
    "w_bw_harmonic_small": (
        "Harmonic-rated I-Line is offered 800–5000 A only - 100 % neutral "
        "used",
        "諧波額定 I-Line 僅 800–5000 A 提供，改用 100 % 中性線"),
    "w_bw_ground_std": (
        "I-Line 800–5000 A includes a 50 % integral ground bus as standard",
        "I-Line 800–5000 A 標準配備 50 % 內建接地匯流排"),
    "w_bw_gg_small": (
        "Copper ground bus (GG) is offered 800–5000 A only - aluminum "
        "ground (G) used",
        "銅接地匯流排 (GG) 僅 800–5000 A 提供，改用鋁接地 (G)"),
    "w_bw_1ph_catalog": (
        "Single-phase I-Line: confirm the catalog number with Schneider "
        "Electric",
        "單相 I-Line：型號請向施耐德電機確認"),
    "w_bw_fault_unknown": (
        "Available fault current not entered - busway SCCR not checked",
        "未輸入可用故障電流，未檢核匯流排槽短路耐受"),
    "pri_method": ("Primary conductor type", "一次側配線型式"),
    "sec_method": ("Secondary conductor type", "二次側配線型式"),
    "pri_fault": ("Primary available fault (kA, 0 = unknown)",
                  "一次側可用故障電流 (kA，0 = 未知)"),
    "pri_bw_note": ("A primary busway uses the busway settings of the "
                    "secondary (type, ground, bracing, material).",
                    "一次側匯流排槽沿用二次側之匯流排槽設定（型式、接地、"
                    "耐受等級、材質）。"),
    "w_pri_busway_mv": (
        "Primary {volts:g} V is above 600 V - I-Line busway does not apply; "
        "MV cable sized instead",
        "一次側 {volts:g} V 高於 600 V，不適用 I-Line 匯流排槽，"
        "改以高壓電纜計算"),
    "err_busway_voltage": (
        "I-Line busway is rated 600 V ({volts:g} V given)",
        "I-Line 匯流排槽額定 600 V (輸入 {volts:g} V)"),
    "err_busway_data": (
        "No I-Line data for {rating:g} A in this construction - enter R, X "
        "and SCCR",
        "此構造無 {rating:g} A 之 I-Line 資料，請輸入 R、X 及短路耐受"),
    "err_busway_range": ("No I-Line busway (up to 2 parallel runs) covers "
                         "{amps} A",
                         "I-Line 匯流排槽 (最多 2 路並聯) 無法滿足 {amps} A"),


    # ---------------- short circuit / IC ----------------
    "tab_sc": ("Short Circuit / IC", "短路 / IC 值"),
    "nav_sc": ("Fault", "短路"),
    "grp_source": ("Utility source", "電源 (台電 / 公用電力)"),
    "src_kv": ("Source voltage (kV)", "電源電壓 (kV)"),
    "src_fault": ("Available fault (kA, 0 = infinite)",
                  "可用故障電流 (kA，0 = 無限大)"),
    "src_xr": ("Source X/R", "電源 X/R"),
    "z_tol": ("Apply −10 % transformer Z tolerance (worst case)",
              "變壓器阻抗 −10 % 公差 (最嚴重情況)"),
    "sc_path": ("Radial path (source → load)", "放射路徑 (電源 → 負載)"),
    "seg_kind": ("Element", "元件"),
    "opt_xfmr": ("Transformer", "變壓器"),
    "seg_name": ("Bus / panel name", "匯流排 / 盤名"),
    "xr": ("X/R", "X/R"),
    "conduit_mag": ("Conduit", "導線管"),
    "opt_steel": ("Steel (magnetic)", "鋼管 (磁性)"),
    "opt_pvc": ("PVC / aluminum", "PVC / 鋁管"),
    "device_type": ("Protective device", "保護設備"),
    "opt_mccb": ("Molded-case CB (MCCB)", "塑殼斷路器 (MCCB)"),
    "opt_iccb": ("Insulated-case CB (ICCB)", "絕緣殼斷路器 (ICCB)"),
    "opt_lvpcb": ("LV power CB (ACB)", "低壓電力斷路器 (ACB)"),
    "aic_sel": ("Device IC rating (kA, 0 = recommend)",
                "設備 IC 額定 (kA，0 = 建議)"),
    "motor_load": ("Motor load at bus (A FLC)", "匯流排馬達負載 (A FLC)"),
    "add_segment": ("Add element", "新增元件"),
    "empty_list": ("Nothing here yet. Add the first item above.",
                   "尚無資料，請由上方新增第一筆。"),
    "busway_rating_a": ("Busway rating (A)", "匯流排槽額定 (A)"),
    "s_sc_max": ("Maximum fault", "最大故障電流"),
    "s_sc_buses": ("Buses", "匯流排數"),
    "col_bus": ("Bus", "匯流排"),
    "col_isc": ("I_sc sym", "對稱短路"),
    "col_xr": ("X/R", "X/R"),
    "col_req": ("Min. IC", "最小 IC"),
    "col_sel": ("Selected", "選用"),
    "st_sc_source": (
        "Utility: {kv:g} kV, {ka:g} kA, X/R {xr:g} → Z = {z:.2f} mΩ",
        "電源：{kv:g} kV，{ka:g} kA，X/R {xr:g} → Z = {z:.2f} mΩ"),
    "st_sc_infinite": (
        "Utility at {kv:g} kV taken as an infinite bus (Z = 0)",
        "{kv:g} kV 電源視為無限大匯流排 (Z = 0)"),
    "st_sc_xfmr": (
        "{name}: {kva:g} kVA, Z {z:g}% × {tol:.2f}, X/R {xr:g} → R {r:.3f} / "
        "X {x:.3f} mΩ at {volts:g} V (upstream referred by turns ratio²)",
        "{name}：{kva:g} kVA，Z {z:g}% × {tol:.2f}，X/R {xr:g} → R {r:.3f} / "
        "X {x:.3f} mΩ (於 {volts:g} V，上游阻抗依匝比平方換算)"),
    "st_sc_cable": (
        "{name}: {sets} × #{size}, {length:g} ft → R {r:.3f} / X {x:.3f} mΩ "
        "(R × {corr:.3f} to 25 °C)",
        "{name}：{sets} × #{size}，{length:g} ft → R {r:.3f} / X {x:.3f} mΩ "
        "(R × {corr:.3f} 換算至 25 °C)"),
    "st_sc_busway": (
        "{name}: {rating:g} A I-Line busway, {length:g} ft → R {r:.3f} / "
        "X {x:.3f} mΩ (R × {corr:.3f} to 25 °C)",
        "{name}：{rating:g} A I-Line 匯流排槽，{length:g} ft → R {r:.3f} / "
        "X {x:.3f} mΩ (R × {corr:.3f} 換算至 25 °C)"),
    "st_sc_bus": (
        "{name} ({volts:g} V): Z = {r:.3f} + j{x:.3f} mΩ, X/R {xr:.1f} → "
        "{isc:.1f} kA + motors {motor:.1f} kA = {total:.1f} kA sym.",
        "{name} ({volts:g} V)：Z = {r:.3f} + j{x:.3f} mΩ，X/R {xr:.1f} → "
        "{isc:.1f} kA + 馬達 {motor:.1f} kA = {total:.1f} kA (對稱)"),
    "st_sc_required": (
        "{name}: {dev} test X/R {xrt:.2f}, factor {mf:.3f} → {adj:.1f} kA → "
        "minimum interrupting rating {req} kA",
        "{name}：{dev} 試驗 X/R {xrt:.2f}，修正係數 {mf:.3f} → {adj:.1f} kA "
        "→ 最小啟斷容量 {req} kA"),
    "st_sc_required_none": (
        "{name}: {dev}, factor {mf:.3f} → {adj:.1f} kA exceeds 200 kA",
        "{name}：{dev}，修正係數 {mf:.3f} → {adj:.1f} kA 超過 200 kA"),
    "st_sc_aic": (
        "{name}: selected {aic:g} kA vs {adj:.1f} kA (factor {mf:.3f})",
        "{name}：選用 {aic:g} kA 對 {adj:.1f} kA (修正係數 {mf:.3f})"),
    "st_sc_label": (
        "{name}: field-mark the available fault current ({total:.1f} kA) and "
        "the calculation date on service equipment",
        "{name}：於受電設備現場標示可用故障電流 ({total:.1f} kA) 及計算日期"),
    "w_sc_infinite": (
        "Utility source taken as infinite - conservative; enter the "
        "utility's available fault current for a closer value",
        "電源視為無限大 (保守)；輸入電力公司提供之故障電流可得較準確值"),
    "w_sc_exceeds": (
        "{name}: {ka:.1f} kA - use current-limiting fuses or a tested series "
        "combination (240.86)",
        "{name}：{ka:.1f} kA，請採用限流熔絲或經試驗之串聯額定組合 (240.86)"),
    "w_sc_motor": (
        "Motor contribution taken as 4 × FLC at each bus where entered "
        "(conservative)",
        "馬達貢獻以各匯流排輸入之 FLC × 4 計 (保守)"),
    "err_sc_empty": ("Add at least one element to the path",
                     "請至少新增一個元件"),
    "err_sc_mv_segment": (
        "{name}: cable / busway elements are for systems ≤ 1000 V - add a "
        "transformer first",
        "{name}：電纜 / 匯流排槽元件適用 ≤ 1000 V，請先加入變壓器"),
    "err_sc_infinite_bus": (
        "{name}: zero impedance with an infinite source - add a transformer "
        "or a utility fault level",
        "{name}：無限大電源且阻抗為零，請加入變壓器或電源故障電流"),

    # ---------------- harmonics ----------------
    "tab_harm": ("Harmonics / Filters", "諧波 / 濾波器"),
    "nav_harm": ("Harm.", "諧波"),
    "grp_pcc": ("Point of common coupling (PCC)", "共同耦合點 (PCC)"),
    "pcc_v": ("PCC voltage (V)", "PCC 電壓 (V)"),
    "pcc_isc": ("Available fault at PCC (kA)", "PCC 可用故障電流 (kA)"),
    "pcc_il": ("Max demand current I_L (A, 0 = connected)",
               "最大需量電流 I_L (A，0 = 依連接負載)"),
    "linear_a": ("Other linear load (A)", "其他線性負載 (A)"),
    "drives": ("Drives", "變頻器清單"),
    "add_drive": ("Add drive", "新增變頻器"),
    "drive_type": ("Front end", "前端整流型式"),
    "load_pct": ("Load (%)", "負載率 (%)"),
    "input_a": ("Rated input current (A, 0 = calc)",
                "額定輸入電流 (A，0 = 計算)"),
    "thd_pct": ("Manufacturer THDi (%, 0 = typical)",
                "原廠 THDi (%，0 = 典型值)"),
    "opt_6p": ("6-pulse, no reactor", "6 脈波，無電抗器"),
    "opt_6p_ac3": ("6-pulse + 3 % AC line reactor", "6 脈波 + 3 % 交流電抗器"),
    "opt_6p_ac5": ("6-pulse + 5 % AC line reactor", "6 脈波 + 5 % 交流電抗器"),
    "opt_6p_dc": ("6-pulse + DC choke", "6 脈波 + 直流電抗器"),
    "opt_12p": ("12-pulse", "12 脈波"),
    "opt_18p": ("18-pulse", "18 脈波"),
    "opt_afe": ("Active front end (AFE)", "主動前端 (AFE)"),
    "opt_6p_passive": ("6-pulse + passive harmonic filter",
                       "6 脈波 + 被動諧波濾波器"),
    "opt_mit_ac5": ("Add 5 % line reactors to 6-pulse drives without one",
                    "無電抗器之 6 脈波加裝 5 % 電抗器"),
    "opt_mit_passive": ("Passive harmonic filter on each 6-pulse drive",
                        "每台 6 脈波加裝被動諧波濾波器"),
    "opt_mit_18p": ("Replace 6-pulse drives with 18-pulse",
                    "6 脈波改用 18 脈波變頻器"),
    "opt_il_given": ("entered", "輸入值"),
    "opt_il_connected": ("connected load", "依連接負載"),
    "s_h_tdd": ("Current TDD", "電流 TDD"),
    "s_h_tdd_lim": ("TDD limit", "TDD 限制"),
    "s_h_vthd": ("Voltage THD", "電壓 THD"),
    "s_h_ratio": ("I_sc / I_L", "I_sc / I_L"),
    "s_h_k": ("K-factor", "K 因數"),
    "s_h_ahf": ("Active harmonic filter", "主動諧波濾波器"),
    "col_h": ("h", "h"),
    "col_ih": ("I_h (A)", "I_h (A)"),
    "col_pct_il": ("% of I_L", "% I_L"),
    "col_limit": ("Limit %", "限制 %"),
    "col_vh": ("V_h %", "V_h %"),
    "col_option": ("Mitigation", "改善方案"),
    "st_h_drive": (
        "{name}: {qty} × {hp:g} HP, {kind}, {load:g} % load → fundamental "
        "{i1:.1f} A, THDi {thd:.1f} %",
        "{name}：{qty} × {hp:g} HP，{kind}，負載 {load:g} % → 基本波 "
        "{i1:.1f} A，THDi {thd:.1f} %"),
    "st_h_il": (
        "I_L = {il:.1f} A ({src}); I_sc = {isc:g} kA → I_sc/I_L = "
        "{ratio:.0f} → TDD limit {tdd:g} %",
        "I_L = {il:.1f} A ({src})；I_sc = {isc:g} kA → I_sc/I_L = "
        "{ratio:.0f} → TDD 限制 {tdd:g} %"),
    "st_h_order": (
        "h{h}: {amps:.1f} A = {pct:.2f} % of I_L (limit {lim:g} %)",
        "h{h}：{amps:.1f} A = I_L 之 {pct:.2f} % (限制 {lim:g} %)"),
    "st_h_tdd": (
        "Harmonic current {rms:.1f} A → TDD {tdd:.2f} % (limit {lim:g} %)",
        "諧波電流 {rms:.1f} A → TDD {tdd:.2f} % (限制 {lim:g} %)"),
    "st_h_vthd": (
        "Voltage THD ≈ {vthd:.2f} % (limit {lim:g} %); largest individual "
        "{vmax:.2f} % (limit {vlim:g} %)",
        "電壓 THD ≈ {vthd:.2f} % (限制 {lim:g} %)；最大單次 {vmax:.2f} % "
        "(限制 {vlim:g} %)"),
    "st_h_k": (
        "K-factor {k:.2f} → K-{kr} rated transformer if it feeds mainly "
        "these loads",
        "K 因數 {k:.2f} → 若變壓器主要供應此類負載，選用 K-{kr} 額定"),
    "st_h_option": (
        "{opt}: TDD {tdd:.2f} %, voltage THD {vthd:.2f} %",
        "{opt}：TDD {tdd:.2f} %，電壓 THD {vthd:.2f} %"),
    "st_h_ahf": (
        "Active harmonic filter at PCC: cancel {k:.0f} % of {rms:.1f} A = "
        "{req:.1f} A → {units} × {frame} A (TDD → {tdd:.2f} %, "
        "voltage THD → {vthd:.2f} %)",
        "PCC 主動諧波濾波器：消除 {rms:.1f} A 之 {k:.0f} % = {req:.1f} A → "
        "{units} × {frame} A (TDD → {tdd:.2f} %，電壓 THD → {vthd:.2f} %)"),
    "st_h_ahf_none": (
        "No active harmonic filter needed (within 90 % of IEEE 519 limits)",
        "不需主動諧波濾波器 (已在 IEEE 519 限制之 90 % 以內)"),
    "w_h_typical": (
        "Harmonic spectra are TYPICAL for each front end - enter the drive "
        "manufacturer's THDi or a harmonic study for final design",
        "諧波頻譜為各整流型式之典型值，最終設計請輸入原廠 THDi 或進行諧波分析"),
    "w_h_il_connected": (
        "I_L taken from the connected load; IEEE 519 uses the maximum demand "
        "current (12-month average) - a lower I_L gives a higher TDD",
        "I_L 依連接負載計算；IEEE 519 採最大需量電流 (12 個月平均)，"
        "實際 I_L 較低時 TDD 會較高"),
    "w_h_estimated": (
        "Drive input current estimated from HP, efficiency 0.92 and "
        "displacement PF - enter nameplate input current where known",
        "變頻器輸入電流依 HP、效率 0.92 及位移功因估算，"
        "已知銘牌輸入電流時請輸入"),
    "err_h_empty": ("Add at least one drive", "請至少新增一台變頻器"),
    "err_h_no_load": ("PCC load current is zero", "PCC 負載電流為零"),

    # ---------------- Excel / CSV panel list ----------------
    "panel_list": ("Panels", "盤清單"),
    "new_panel": ("New panel", "新增盤"),
    "delete_panel": ("Delete panel", "刪除盤"),
    "feeder_len_panel": ("Feeder length ft (blank = wiring tab)",
                         "幹線長度 ft (空白=依配線頁)"),
    "import_excel": ("Import Excel / CSV", "匯入 Excel / CSV"),
    "export_excel": ("Export Excel", "匯出 Excel"),
    "excel_template": ("Excel template", "Excel 範本"),
    "calc_all_panels": ("Calculate all panels", "計算全部盤"),
    "all_panels_title": ("All panels", "全部盤"),
    "import_replace_q": (
        "Replace the current panels with the {n} imported panel(s)?\n\n"
        "Yes = replace all\nNo = add, and update panels with the same name",
        "以匯入的 {n} 個盤取代目前所有盤？\n\n是 = 全部取代\n否 = 新增，同名的盤則更新"),
    "imported_n": ("Imported {panels} panel(s) and {loads} load row(s) "
                   "from {file}", "已從 {file} 匯入 {panels} 個盤、{loads} 筆負載"),
    "import_notes": ("Import notes", "匯入注意事項"),
    "confirm_delete_panel": ("Delete panel {name} and its {n} load row(s)?",
                             "刪除盤 {name} 及其 {n} 筆負載？"),
    "ps_conn": ("Conn. kVA", "連接kVA"),
    "ps_dem": ("Demand kVA", "需量kVA"),
    "ps_coin": ("Coinc. kVA", "同時kVA"),
    "ps_design": ("Design kVA", "設計kVA"),
    "ps_amps": ("Design A", "設計A"),
    "ps_ocpd": ("OCPD A", "保護器A"),
    "ps_vd": ("VD %", "壓降%"),
    "ps_feeder": ("Feeder", "幹線"),
    "xl_panel": ("Panel", "盤名"),
    "xl_circuit": ("Circuit", "迴路"),
    "xl_name": ("Description", "負載名稱"),
    "xl_cat": ("Category", "類別"),
    "xl_qty": ("Qty", "數量"),
    "xl_rating": ("Rating (per unit)", "額定 (每台)"),
    "xl_unit": ("Unit", "單位"),
    "xl_pf": ("PF", "功率因數"),
    "xl_v": ("Voltage (V)", "電壓 (V)"),
    "xl_ph": ("Phases", "相數"),
    "xl_cont": ("Continuous", "連續負載"),
    "xl_df": ("Demand factor (blank = auto)", "需量因數 (空白=自動)"),
    "xl_conn": ("Phase connection", "接相"),
    "xl_system": ("System", "系統"),
    "xl_div": ("Diversity factor", "參差因數"),
    "xl_tpf": ("Target PF", "目標功率因數"),
    "xl_flen": ("Feeder length (ft, blank = program setting)",
                "幹線長度 (ft，空白=依程式設定)"),
    "xl_sh_panels": ("Panels", "盤清單"),
    "xl_sh_loads": ("Loads", "負載清單"),
    "xl_sh_summary": ("Summary", "彙總"),
    "xl_sh_instr": ("Instructions", "說明"),
    "xl_title_summary": ("Panel load summary", "盤負載彙總"),
    "xl_note_generated": (
        "NEC Electrical Calculator, NFPA 70 (NEC) {ed}, {date}. Values are "
        "calculated by the program (NEC tables); totals use SUM formulas. "
        "Edit the Panels / Loads sheets and import the file again to "
        "recalculate.",
        "NEC 電氣計算軟體，NFPA 70 (NEC) {ed}，{date}。數值由程式依 NEC 表格"
        "計算，合計列使用 SUM 公式。修改「盤清單」/「負載清單」後重新匯入即可重算。"),
    "xl_nloads": ("Load rows", "負載筆數"),
    "xl_conn_kw": ("Connected kW", "連接 kW"),
    "xl_conn_kvar": ("Connected kvar", "連接 kvar"),
    "xl_conn_kva": ("Connected kVA", "連接 kVA"),
    "xl_conn_pf": ("Connected PF", "連接功因"),
    "xl_dem_kva": ("Demand kVA (after DF)", "需量 kVA (乘需量因數)"),
    "xl_overall_df": ("Overall DF", "整體需量因數"),
    "xl_coin_kva": ("Coincident kVA (÷ diversity)", "同時需量 kVA (÷參差)"),
    "xl_cont_kva": ("Continuous kVA", "連續負載 kVA"),
    "xl_motor_kva": ("Largest motor kVA", "最大馬達 kVA"),
    "xl_design_kva": ("Feeder design kVA", "幹線設計 kVA"),
    "xl_design_a": ("Design current (A)", "設計電流 (A)"),
    "xl_pha": ("Phase A (A)", "A 相 (A)"),
    "xl_phb": ("Phase B (A)", "B 相 (A)"),
    "xl_phc": ("Phase C (A)", "C 相 (A)"),
    "xl_imb": ("Imbalance %", "不平衡率 %"),
    "xl_cap": ("Capacitor kvar (to target PF)", "電容 kvar (至目標功因)"),
    "xl_ocpd": ("Feeder OCPD (A)", "幹線保護器 (A)"),
    "xl_feeder": ("Feeder conductors / busway", "幹線線材 / 匯流排槽"),
    "xl_vd": ("Voltage drop %", "電壓降 %"),
    "xl_status": ("Status", "狀態"),
    "xl_ok": ("OK", "正常"),
    "xl_total": ("Total", "合計"),
    "xl_total_note": (
        "Totals are arithmetic sums of the panels; no diversity between "
        "panels is applied.", "合計為各盤算術和，未計入盤與盤之間的參差。"),
    "xl_title_panel": ("Panel {name} — {system}", "盤 {name} — {system}"),
    "xl_panel_meta": ("Diversity {div} · Target PF {tpf} · NFPA 70 (NEC) {ed}",
                      "參差因數 {div} · 目標功因 {tpf} · NFPA 70 (NEC) {ed}"),
    "xl_conn_used": ("Phase (assigned)", "接相 (配置結果)"),
    "xl_kw": ("kW", "kW"),
    "xl_kvar": ("kvar", "kvar"),
    "xl_kva": ("kVA", "kVA"),
    "xl_dfv": ("DF used", "採用需量因數"),
    "xl_dkva": ("Demand kVA", "需量 kVA"),
    "xl_amps": ("Current (A)", "電流 (A)"),
    "xl_sched_note": (
        "Calculated by the program; edit the Loads sheet and re-import to "
        "recalculate.", "由程式計算；請修改「負載清單」後重新匯入以重算。"),
    "xl_ins_title": ("Panel load list – how to use", "盤負載清單 – 使用說明"),
    "xl_note_template": (
        "Template for the NEC Electrical Calculator (NFPA 70 {ed}).",
        "NEC 電氣計算軟體範本 (NFPA 70 {ed})。"),
    "xl_ins_1": (
        "1. List every panel on the Panels sheet: name, system, diversity "
        "factor, target PF and (optional) feeder length.",
        "1. 在「盤清單」工作表列出每一個盤：盤名、系統、參差因數、目標功率因數，"
        "幹線長度可選填。"),
    "xl_ins_2": (
        "2. List the loads on the Loads sheet, one row per load group; the "
        "Panel column links each row to its panel.",
        "2. 在「負載清單」工作表每列輸入一組負載，「盤名」欄指定所屬的盤。"),
    "xl_ins_3": (
        "3. Blue text on a yellow fill marks input cells. The filled rows are "
        "examples - overwrite or delete them.",
        "3. 黃底藍字為輸入欄位；已填入的列為範例，可直接覆寫或刪除。"),
    "xl_ins_4": (
        "4. In the program: Panel load tab → Import Excel / CSV, then "
        "Calculate all panels, or Export Excel for a results workbook.",
        "4. 程式中：盤負載頁 → 匯入 Excel / CSV，再按「計算全部盤」，"
        "或「匯出 Excel」取得計算結果活頁簿。"),
    "xl_ins_5": (
        "Blank cells use the defaults below. Rows without a numeric rating "
        "are skipped and listed in the import notes. Chinese or English "
        "headers and values are both accepted.",
        "空白欄位使用下表預設值；沒有數字額定值的列會被略過並列於匯入注意事項。"
        "中文或英文欄名及內容皆可。"),
    "xl_ins_sheet": ("Sheet", "工作表"),
    "xl_ins_col": ("Column", "欄位"),
    "xl_ins_req": ("Required", "必填"),
    "xl_ins_vals": ("Allowed values / default", "可用值 / 預設值"),
    "xl_ins_ex": ("Example", "範例"),
    "xl_help_panel": ("Unique panel name", "盤名 (不可重複)"),
    "xl_help_system": (
        "208Y/120, 480Y/277, 480D, 240/120 1PH or 120 1PH",
        "208Y/120、480Y/277、480D、240/120 1PH 或 120 1PH"),
    "xl_help_diversity": (
        "≥ 1.0; coincident demand = demand ÷ diversity. A value below 1 is "
        "read as a coincidence factor (diversity = 1 / value). Blank = 1.0",
        "≥ 1.0；同時需量 = 需量 ÷ 參差因數。小於 1 的值視為同時率 "
        "(參差因數 = 1 / 值)。空白 = 1.0"),
    "xl_help_target_pf": ("Target power factor for capacitor sizing; "
                          "blank = 0.95", "電容器計算用目標功率因數；空白 = 0.95"),
    "xl_help_feeder_length": (
        "One-way feeder length in ft for voltage drop (a value like 45m is "
        "converted); blank = feeder length on the Panel load tab",
        "電壓降計算用單程幹線長度 (ft，輸入如 45m 會自動換算)；空白 = 盤負載頁設定"),
    "xl_help_load_panel": (
        "Panel name from the Panels sheet; blank = same as the row above",
        "須與「盤清單」的盤名相同；空白 = 同上一列"),
    "xl_help_circuit": ("Circuit number(s), free text", "迴路編號 (自由輸入)"),
    "xl_help_name": ("Load description", "負載名稱 / 說明"),
    "xl_help_category": (
        "Lighting, Receptacle, Motor, Heating, Cooling / A/C, Equipment, "
        "Other (blank = Other). Receptacles over 10 kVA get the NEC {rec} "
        "demand factor; heating and cooling are non-coincident ({nc})",
        "照明、插座、馬達、電熱、空調、設備、其他 (空白 = 其他)。插座超過 10 kVA "
        "依 NEC {rec} 取需量因數；電熱與空調視為不同時負載 ({nc})"),
    "xl_help_qty": ("Number of identical loads; blank = 1",
                    "相同負載數量；空白 = 1"),
    "xl_help_rating": ("Rating of ONE unit, in the Unit column",
                       "單台額定值，單位見「單位」欄"),
    "xl_help_unit": (
        "VA, kVA, W, kW, HP or A; blank = VA. HP uses the motor full-load "
        "current of NEC {flc}",
        "VA、kVA、W、kW、HP 或 A；空白 = VA。HP 依 NEC {flc} 馬達滿載電流計算"),
    "xl_help_pf": ("0-1 or %; blank = 1.0 (motors 0.85)",
                   "0-1 或 %；空白 = 1.0 (馬達 0.85)"),
    "xl_help_voltage": (
        "Load voltage; blank = line-to-neutral for 1Ø loads (line-to-line on "
        "480D), line-to-line for 3Ø loads",
        "負載電壓；空白 = 單相取相電壓 (480D 取線電壓)，三相取線電壓"),
    "xl_help_phases": ("1 or 3 (2 = 2-pole, single-phase line-to-line); "
                       "blank = 1", "1 或 3 (2 = 雙極單相線間負載)；空白 = 1"),
    "xl_help_continuous": (
        "Yes / No (load runs 3 h or more); blank = No. The feeder adds 25 % "
        "of continuous load ({cont})",
        "是 / 否 (連續 3 小時以上)；空白 = 否。幹線另加連續負載的 25 % ({cont})"),
    "xl_help_demand_factor": (
        "0-1 or %; blank = automatic per NEC ({rec}, {nc}), otherwise 1.0",
        "0-1 或 %；空白 = 依 NEC 自動 ({rec}、{nc})，其餘為 1.0"),
    "xl_help_phase_conn": (
        "Auto, A, B, C, AB, BC, CA or ABC (R/S/T accepted); blank = Auto "
        "(the program balances the phases)",
        "自動、A、B、C、AB、BC、CA 或 ABC (可用 R/S/T)；空白 = 自動 (程式自動平衡)"),
    "xl_ins_method": (
        "Method: demand = connected × DF; coincident = Σ demand ÷ diversity; "
        "feeder design = coincident + 25 % continuous ({cont}) + 25 % "
        "largest motor ({mot}).",
        "計算方式：需量 = 連接負載 × 需量因數；同時需量 = Σ 需量 ÷ 參差因數；"
        "幹線設計負載 = 同時需量 + 連續負載 25 % ({cont}) + 最大馬達 25 % ({mot})。"),
    "io_dup_panel": ("{where}: panel {name} is listed twice - first row used",
                     "{where}：盤 {name} 重複，採用第一列"),
    "io_bad_system": (
        "{where}: '{value}' is not a supported system (208Y/120, 480Y/277, "
        "480D, 240/120 1PH, 120 1PH)",
        "{where}：不支援的系統「{value}」(可用 208Y/120、480Y/277、480D、"
        "240/120 1PH、120 1PH)"),
    "io_coincidence": (
        "{where}: diversity {value} is below 1 - read as a coincidence "
        "factor, diversity = {div}",
        "{where}：參差因數 {value} 小於 1，視為同時率，參差因數 = {div}"),
    "io_bad_num": ("{where}: {field} '{value}' is not valid - {default} used",
                   "{where}：{field}「{value}」無效，改用 {default}"),
    "io_m_to_ft": ("{where}: feeder length {m} m = {ft} ft",
                   "{where}：幹線長度 {m} m = {ft} ft"),
    "io_skip_rating": ("{where}: row skipped - rating '{value}' is not a "
                       "number", "{where}：額定值「{value}」非數字，略過此列"),
    "io_bad_unit": ("{where}: row skipped - unknown unit '{value}'",
                    "{where}：未知單位「{value}」，略過此列"),
    "io_bad_cat": ("{where}: unknown category '{value}' - Other used",
                   "{where}：未知類別「{value}」，改為「其他」"),
    "io_bad_phases": ("{where}: phases '{value}' not recognised - {default} "
                      "used", "{where}：無法辨識相數「{value}」，改用 {default}"),
    "io_bad_conn": ("{where}: phase connection '{value}' not recognised - "
                    "Auto used", "{where}：無法辨識接相「{value}」，改為自動"),
    "io_bad_bool": ("{where}: continuous '{value}' not recognised - No used",
                    "{where}：無法辨識連續負載「{value}」，改為否"),
    "io_from_system": ("the panel system voltage", "盤系統電壓"),
    "io_computed": (
        "{where}: calculated schedule - kW / kVA / DF / phase columns were "
        "ignored; demand factors and phase connection set to Auto",
        "{where}：此為計算結果表，已忽略 kW / kVA / 需量因數 / 接相欄，"
        "需量因數與接相改為自動"),
    "io_no_panel_col": ("{where}: no Panel column - all rows assigned to "
                        "{name}", "{where}：無「盤名」欄，全部負載歸入 {name}"),
    "io_new_panel": ("Panel {name}: system not given - {system} assumed, "
                     "please check", "盤 {name}：未指定系統，假設為 {system}，請確認"),
    "io_3ph_on_1ph": ("{name} ({panel}): 3-phase load on a single-phase "
                      "panel - set to 1 phase",
                      "{name} ({panel})：單相盤上的三相負載，已改為單相"),
    "io_no_loads": ("No load rows were found", "未找到任何負載資料"),
    "io_calc_error": ("Calculation error: {msg}", "計算錯誤：{msg}"),
    "io_no_data": (
        "No panel or load list found - the file needs a header row with at "
        "least Description and Rating columns (see Excel template)",
        "找不到盤或負載清單 - 檔案需有標題列，至少包含「負載名稱」與「額定」欄"
        " (請參考 Excel 範本)"),
    "err_xls": ("{file}: the old .xls format is not supported - save it as "
                ".xlsx or CSV", "{file}：不支援舊版 .xls 格式，請另存為 .xlsx 或 CSV"),
    "err_import": ("Cannot read {file}: {msg}", "無法讀取 {file}：{msg}"),

    # ---------------- errors ----------------
    "err_ambient": ("Ambient {ambient} °C not permitted for {temp} °C "
                    "conductors", "周溫 {ambient} °C 不適用於 {temp} °C 導線"),
    "err_no_impedance": ("No impedance data for {size}",
                         "{size} 無阻抗資料"),
    "err_term_temp": ("Termination rating cannot exceed insulation rating",
                      "端子溫度額定不可高於絕緣溫度額定"),
    "err_no_conductor": ("No conductor size satisfies {amps} A",
                         "無導線尺寸可滿足 {amps} A"),
    "err_ocpd_range": ("{amps} A is beyond standard OCPD ratings",
                       "{amps} A 超出標準保護設備額定"),
    "err_flc": ("No NEC table FLC for {hp} HP, {phases}Ø, {volts} V - "
                "enter FLC override",
                "NEC 表中無 {hp} HP，{phases} 相，{volts} V 之 FLC，請輸入自訂值"),
    "err_mv_kv": ("{kv} kV is beyond 35 kV", "{kv} kV 超過 35 kV"),
    "err_z_range": ("Transformer impedance over 10% is not covered by "
                    "Table 450.3(A)", "變壓器阻抗超過 10% 不在表 450.3(A) 範圍"),
    "err_unit": ("Unknown unit {unit}", "未知單位 {unit}"),
    "err_input": ("Invalid input: {field}", "輸入錯誤：{field}"),
}


def tr(key, lang="en", **params):
    """Translate ``key`` and format with ``params``."""
    pair = TEXT.get(key)
    if pair is None:
        text = key
    else:
        text = pair[1] if lang == "zh" else pair[0]
    if params:
        # translate option codes passed as parameters
        p2 = {}
        for k, v in params.items():
            if isinstance(v, str) and ("opt_" + v) in TEXT:
                p2[k] = tr("opt_" + v, lang)
            else:
                p2[k] = v
        try:
            return text.format(**p2)
        except (KeyError, ValueError, IndexError):
            return text + " " + str(params)
    return text


def opt(code, lang="en"):
    return tr("opt_" + code, lang) if ("opt_" + code) in TEXT else code
