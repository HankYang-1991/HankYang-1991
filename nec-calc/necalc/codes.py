"""Code-section references per NEC edition.

The calculation methods used by this program are the same in NEC 2023 and
NEC 2026 for systems 1000 V and below.  The main structural change in NEC
2026 is that requirements for branch circuits, feeders and overcurrent
protection over 1000 V ac were relocated into new Articles 235 and 245.

Edit this file if your AHJ's adopted edition uses different numbering.
"""

EDITIONS = ("2023", "2026")

_BASE = {
    "ampacity": "Table 310.16",
    "temp_corr": "Table 310.15(B)(1)(1)",
    "ccc_adj": "Table 310.15(C)(1)",
    "neutral_ccc": "310.15(E)",
    "parallel": "310.10(G)",
    "termination": "110.14(C)",
    "small_cond": "240.4(D)",
    "next_size_up": "240.4(B)",
    "std_ocpd": "240.6(A)",
    "cont_branch": "210.19(A)(1) / 210.20(A)",
    "cont_feeder": "215.2(A)(1) / 215.3",
    "vd_note": "210.19 / 215.2 Informational Notes (3% / 5%)",
    "egc": "Table 250.122",
    "egc_upsize": "250.122(B)",
    "egc_parallel": "250.122(F)",
    "mv_egc": "250.190(C)(3)",
    "switch": "404 / 430.109 (fusible / non-fusible switch rating)",
    "fill": "Chapter 9, Tables 1, 4, 5",
    "impedance": "Chapter 9, Table 9",
    "motor_flc": "430.6(A)(1), Tables 430.248 / 430.250",
    "motor_cond": "430.22",
    "motor_feeder": "430.24",
    "motor_ocpd": "430.52, Table 430.52(C)(1)",
    "motor_ol": "430.32(A)(1)",
    "motor_disc": "430.110(A)",
    "xfmr_mv": "Table 450.3(A)",
    "xfmr_lv": "Table 450.3(B)",
    "xfmr_sec_cond": "240.21(C)",
    "lighting_load": "220.41 / 220.42",
    "receptacle_load": "220.47 (Table 220.47)",
    "motor_load": "220.50",
    "noncoincident": "220.60",
    "mv_ampacity": "315.60",
    "mv_min_size": "Table 315.10(A)",
    "mv_conductor_ocpd": "240.101(A)",
    "mv_feeder": "215.2(B)",
    "mv_fill": "Chapter 9, Table 1 (cables)",
    "sc_withstand": "ICEA P-32-382 / 110.10",
    "tray_uses": "392.10",
    "tray_single_min": "392.10(B)(1)",
    "tray_separation": "392.20(B)",
    "tray_fill_multi": "392.22(A), Table 392.22(A)",
    "tray_fill_control": "392.22(A)(2) / (A)(4)",
    "tray_fill_single": "392.22(B)(1), Table 392.22(B)(1)",
    "tray_fill_mv": "392.22(C)",
    "tray_amp_lv_multi": "392.80(A)(1), Table 310.16",
    "tray_amp_lv_single": "392.80(A)(2), Table 310.17",
    "tray_amp_mv": "392.80(B), 315.60",
    "tray_egc": "392.60",
    "busway_rating": "UL 857 (40 °C ambient rating)",
    "busway_ocpd": "368.17(A), 240.4(B)",
    "busway_vd": "Manufacturer R / X data",
    "busway_sccr": "110.10, UL 857",
    "busway_ground": "368.60, 250.118",
    "busway_install": "368.10, 368.12, 368.17(C), 368.30",
}

_2026_OVERRIDES = {
    # Over 1000 V requirements relocated in NEC 2026
    "mv_conductor_ocpd": "Article 245",
    "mv_feeder": "Article 235",
}

REFS = {
    "2023": dict(_BASE),
    "2026": {**_BASE, **_2026_OVERRIDES},
}


def ref(key, edition="2023"):
    return REFS.get(edition, REFS["2023"]).get(key, key)
