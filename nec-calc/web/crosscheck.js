// Compare the JavaScript port (necalc.js) with the Python engine results in
// crosscheck_cases.json (written by crosscheck.py).  Exit code 1 on mismatch.
//   python web/crosscheck.py && node web/crosscheck.js
"use strict";
const fs = require("fs");
const path = require("path");
const N = require("./necalc.js");

const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "crosscheck_cases.json"), "utf8"));
const LANGS = ["en", "zh"];

function serResult(res) {
  const out = {
    kind: res.kind, summary: res.summary,
    steps: res.steps.map(s => ({ key: s.key, ref: s.ref, ok: s.ok, params: s.params,
      text: Object.fromEntries(LANGS.map(l => [l, N.tr(s.key, l, s.params)])) })),
    warnings: res.warnings.map(w => ({ key: w[0], params: w[1],
      text: Object.fromEntries(LANGS.map(l => [l, N.tr(w[0], l, w[1])])) })),
    summary_rows: Object.fromEntries(LANGS.map(l => [l, N.summaryRows(res, l).map(r => [r[0], r[1]])])),
    children: {},
  };
  for (const k of Object.keys(res.children)) out.children[k] = serResult(res.children[k]);
  return out;
}

function run(fn) {
  try { return { ok: fn() }; }
  catch (e) {
    if (e instanceof N.CalcError) return { error: e.key, params: e.params };
    throw e;
  }
}

function runCase(c) {
  const a = c.args;
  switch (c.fn) {
    case "design_general":
      return run(() => serResult(N.designGeneral(a.load_va, N.wiringInput(a.w), {
        continuous_va: a.continuous_va, ocpd: a.ocpd, kind: a.kind,
        largest_motor_va: a.largest_motor_va, load_amps: a.load_amps })));
    case "design_motor":
      return run(() => serResult(N.designMotor(a.hp, N.wiringInput(a.w), {
        device: a.device, nameplate_fla: a.nameplate_fla, sf_115: a.sf_115,
        design_b_ee: a.design_b_ee, flc_override: a.flc_override })));
    case "design_mv_cable":
      return run(() => serResult(N.designMvCable(N.mvInput(a.m))));
    case "design_transformer":
      return run(() => serResult(N.designTransformer(N.transformerInput(a.x),
        a.sec ? N.wiringInput(a.sec) : null, a.pri ? N.wiringInput(a.pri) : null,
        a.mv ? N.mvInput(a.mv) : null)));
    case "loads":
      return run(() => {
        const p = N.panelInput(Object.assign({}, a.panel, { loads: a.panel.loads.map(N.loadItem) }));
        const c2 = N.calculateLoads(p);
        const out = {
          rows: c2.rows.map(r => ({ kva: r.kva, kw: r.kw, kvar: r.kvar, amps: r.amps, df: r.df,
            d_kva: r.d_kva, phase: r.phase })),
          notes: c2.notes,
        };
        for (const k of ["connected", "demand", "coincident", "continuous_kva", "largest_motor_kva",
          "design_kva", "i_demand", "i_design_balanced", "i_design", "phase_kva", "phase_amps",
          "imbalance_pct", "cap_kvar", "demand_factor_overall"]) out[k] = c2[k];
        out.summary_rows = Object.fromEntries(LANGS.map(l => [l, N.loadSummaryRows(c2, l)]));
        out.note_text = Object.fromEntries(LANGS.map(l => [l, N.loadNotes(c2, l)]));
        try { out.feeder = serResult(N.sizeFeeder(p, c2, N.wiringInput(a.w))); }
        catch (e) { if (e instanceof N.CalcError) out.feeder = { error: e.key }; else throw e; }
        return out;
      });
    case "design_tray":
      return run(() => serResult(N.designTray(N.trayInput(Object.assign({}, a.x,
        { cables: a.x.cables.map(N.trayCable) })))));
    case "shortcircuit":
      return run(() => serResult(N.designShortcircuit(N.scSource(a.src), a.segs.map(N.scSegment))));
    case "harmonics":
      return run(() => serResult(N.designHarmonics(N.harmInput(Object.assign({}, a.x,
        { drives: a.x.drives.map(N.harmDrive) })))));
    case "capacity":
      return { ok: N.capacityTable(a.kind, null, null, a.kw) };
    case "format":
      return { ok: c.result.ok.map(([v, spec]) => [v, spec, N.pyFormat("{v:" + spec + "}", { v })]) };
  }
  throw new Error("unknown fn " + c.fn);
}

function norm(s) {
  return String(s).replace(/-0\.0\b/g, "0.0").replace(/(\d)\.0(?![\d])/g, "$1");
}

// compare a = python, b = js; only keys present in python are required
function cmp(a, b, where, errs) {
  if (errs.length > 40) return;
  if (a === null || a === undefined) {
    if (!(b === null || b === undefined)) errs.push(`${where}: py=${a} js=${JSON.stringify(b)}`);
    return;
  }
  if (typeof a === "number") {
    if (typeof b !== "number" || Math.abs(a - b) > 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)))
      errs.push(`${where}: py=${a} js=${b}`);
    return;
  }
  if (typeof a === "string" || typeof a === "boolean") {
    if (typeof a === "string" ? norm(a) !== norm(b) : a !== b)
      errs.push(`${where}: py=${JSON.stringify(a)} js=${JSON.stringify(b)}`);
    return;
  }
  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) {
      errs.push(`${where}: length py=${a.length} js=${b && b.length}`);
      return;
    }
    a.forEach((x, i) => cmp(x, b[i], `${where}[${i}]`, errs));
    return;
  }
  if (typeof a === "object") {
    if (typeof b !== "object" || b === null) { errs.push(`${where}: js missing object`); return; }
    for (const k of Object.keys(a)) cmp(a[k], b[k], `${where}.${k}`, errs);
  }
}

let bad = 0;
const counts = {};
cases.forEach((c, i) => {
  counts[c.fn] = (counts[c.fn] || 0) + 1;
  let js;
  try { js = runCase(c); }
  catch (e) { bad++; if (bad <= 10) console.log(`#${i} ${c.fn} JS exception: ${e.stack}`); return; }
  const errs = [];
  if (c.fn === "format") {
    c.result.ok.forEach(([v, spec, py], j) => {
      if (py !== js.ok[j][2]) errs.push(`format ${v} ${spec}: py=${py} js=${js.ok[j][2]}`);
    });
  } else cmp(c.result, js, c.fn, errs);
  if (errs.length) {
    bad++;
    if (bad <= 10) console.log(`#${i} ${c.fn} mismatch:\n  ` + errs.slice(0, 8).join("\n  "));
  }
});
console.log("cases:", JSON.stringify(counts));
console.log(bad ? `FAILED: ${bad} of ${cases.length} cases differ` : `OK: all ${cases.length} cases match`);
process.exit(bad ? 1 : 0);
