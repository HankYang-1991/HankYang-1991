# nec-calc — working rules

## Keep the development spec in sync (required on every update)
`docs/SPEC.md` (軟體開發規格書) is updated in the **same commit** as any change to features, UI, data formats, calculation rules, tests or the build:
1. Bump `__version__` in `necalc/__init__.py` (feature +0.1, fix +0.0.1) and set the same number in the spec's "對應程式版本" row and "文件更新日期".
2. Add a row at the top of the spec's 修訂紀錄 (version, date, what changed).
3. Update every affected section (FR-xx functional requirements, UI-xx rules, shortcuts, data formats, tests table, roadmap).
`tests/test_spec.py` fails if the version, revision row, modules, tabs or test files are out of sync.

## Code rules
- Standard library only (Tkinter, zipfile, xml); no third-party packages.
- All user-visible text lives in `necalc/i18n.py` with both English and Traditional Chinese; no duplicate keys.
- Calculation code (`engine`, `tray`, `loads`, `shortcircuit`, `harmonics`) returns `Result` objects with i18n step keys and NEC refs from `codes.py`; the GUI holds no NEC logic.
- After editing `tables.py`, `codes.py` or `i18n.py`, run `python web/build_data.py` so the web version uses the same data.

## Checks before committing
```bash
python -m unittest discover -s tests            # all tests (GUI tests need a display)
xvfb-run -a python3 -m unittest discover -s tests   # Linux without a display (needs python3-tk)
```
