/* necalc.js - JavaScript port of the necalc Python engine (engine.py,
 * loads.py, tray.py and the report helpers) for the mobile web version.
 * Tables and text come from necalc_data.js (generated from Python), and
 * web/crosscheck.js verifies this port against the Python results.
 */
(function (root) {
  "use strict";
  var DATA = (typeof module !== "undefined" && module.exports)
    ? require("./necalc_data.js") : root.NECALC_DATA;
  var T = DATA.tables;
  var SQRT3 = Math.sqrt(3);
  var EPS = 1e-9;

  // ------------------------------------------------------------------
  // small helpers
  // ------------------------------------------------------------------
  function CalcError(key, params) {
    this.key = key;
    this.params = params || {};
    this.message = key;
  }
  CalcError.prototype = Object.create(Error.prototype);

  function has(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }
  // exact float summation, same algorithm as Python's math.fsum (Shewchuk)
  // so totals match the Python engine on every Python version
  function sum(arr) {
    var partials = [], i, j, x, y, t, hi, lo = 0, n;
    for (var k = 0; k < arr.length; k++) {
      x = arr[k]; i = 0;
      for (j = 0; j < partials.length; j++) {
        y = partials[j];
        if (Math.abs(x) < Math.abs(y)) { t = x; x = y; y = t; }
        hi = x + y; lo = y - (hi - x);
        if (lo) partials[i++] = lo;
        x = hi;
      }
      partials.length = i; partials.push(x);
    }
    n = partials.length; hi = 0;
    if (n > 0) {
      hi = partials[--n];
      while (n > 0) {
        x = hi; y = partials[--n]; hi = x + y; lo = y - (hi - x);
        if (lo) break;
      }
      if (n > 0 && ((lo < 0 && partials[n - 1] < 0) || (lo > 0 && partials[n - 1] > 0))) {
        y = lo * 2; x = hi + y;
        if (y === x - hi) hi = x;
      }
    }
    return hi;
  }
  function pyRound(x, nd) {  // Python round(): exact binary value, ties to even
    return parseFloat(toFixedPy(x, nd || 0));
  }
  function ref(key, ed) {
    var refs = DATA.refs[ed] || DATA.refs["2023"];
    return has(refs, key) ? refs[key] : key;
  }
  function sizeIndex(s) { return T.SIZES.indexOf(s); }
  function sizeLabel(s) {
    return sizeIndex(s) >= 13 ? s + " kcmil" : s + " AWG";
  }

  function Result(kind) {
    this.kind = kind; this.summary = {}; this.steps = [];
    this.warnings = []; this.children = {};
  }
  Result.prototype.add = function (key, refText, ok, params) {
    this.steps.push({ key: key, ref: refText || "", ok: ok === undefined ? null : ok,
                      params: params || {} });
  };
  Result.prototype.warn = function (key, params) {
    this.warnings.push([key, params || {}]);
  };

  // ------------------------------------------------------------------
  // look-ups
  // ------------------------------------------------------------------
  function nextStdOcpd(amps, ratings) {
    var list = ratings || T.STANDARD_OCPD;
    for (var i = 0; i < list.length; i++) if (list[i] >= amps - EPS) return list[i];
    return null;
  }
  function maxStdOcpd(amps, ratings) {
    var list = ratings || T.STANDARD_OCPD, best = null;
    for (var i = 0; i < list.length; i++) if (list[i] <= amps + EPS) best = list[i];
    return best;
  }
  function nextSwitch(amps) {
    for (var i = 0; i < T.STANDARD_SWITCH.length; i++)
      if (T.STANDARD_SWITCH[i] >= amps - EPS) return T.STANDARD_SWITCH[i];
    return null;
  }
  function tempFactor(ambient, insTemp) {
    var col = T.TEMP_COLUMNS.indexOf(insTemp);
    for (var i = 0; i < T.TEMP_CORRECTION.length; i++) {
      var row = T.TEMP_CORRECTION[i];
      if (ambient <= row[0]) {
        var f = row[1 + col];
        if (f === null) throw new CalcError("err_ambient", { ambient: ambient, temp: insTemp });
        return f;
      }
    }
    throw new CalcError("err_ambient", { ambient: ambient, temp: insTemp });
  }
  function cccFactor(n) {
    for (var i = 0; i < T.CCC_ADJUSTMENT.length; i++)
      if (n <= T.CCC_ADJUSTMENT[i][0]) return T.CCC_ADJUSTMENT[i][1];
    return T.CCC_ADJUSTMENT[T.CCC_ADJUSTMENT.length - 1][1];
  }
  function baseAmpacity(size, material, col) {
    var tbl = material === "cu" ? T.AMPACITY_CU : T.AMPACITY_AL;
    if (!has(tbl, size)) return null;
    return tbl[size][T.TEMP_COLUMNS.indexOf(col)];
  }
  function egcSize(ocpd, material) {
    material = material || "cu";
    for (var i = 0; i < T.EGC_TABLE.length; i++) {
      var r = T.EGC_TABLE[i];
      if (ocpd <= r[0]) return material === "cu" ? r[1] : r[2];
    }
    var last = T.EGC_TABLE[T.EGC_TABLE.length - 1];
    return material === "cu" ? last[1] : last[2];
  }
  function cmilOf(size) {
    if (has(T.CMIL, size)) return T.CMIL[size];
    return parseInt(size, 10) * 1000;
  }
  function sizeFromCmil(cmil, material, minimum) {
    var start = minimum ? sizeIndex(minimum) : 0;
    for (var i = start; i < T.SIZES.length; i++) {
      var s = T.SIZES[i];
      if (material === "al" && s === "14") continue;
      if (T.CMIL[s] >= cmil - 1e-6) return s;
    }
    return T.SIZES[T.SIZES.length - 1];
  }
  function conduitMaterial(ct) { return ct.indexOf("PVC") === 0 ? "pvc" : "steel"; }

  function table9Impedance(size, material, ct) {
    var mat = conduitMaterial(ct), approx = false, key = size;
    if (!has(T.TABLE9, key)) {
      approx = true;
      var col = material === "al" ? 5 : 2, best = null, bestD = Infinity;
      T.SIZES.forEach(function (s) {
        if (!has(T.TABLE9, s) || T.TABLE9[s][col] === null) return;
        var d = Math.abs(T.CMIL[s] - cmilOf(size));
        if (d < bestD) { bestD = d; best = s; }
      });
      key = best;
    }
    var row = T.TABLE9[key];
    var x = mat === "pvc" ? row[0] : row[1];
    var r = material === "cu" ? (mat === "pvc" ? row[2] : row[4])
                              : (mat === "pvc" ? row[5] : row[7]);
    if (r === null) throw new CalcError("err_no_impedance", { size: size });
    if (approx) r = r * T.CMIL[key] / cmilOf(size);
    return [r, x, approx];
  }
  function effectiveZ(size, material, ct, pf) {
    var t = table9Impedance(size, material, ct);
    pf = Math.max(Math.min(pf, 1), 0);
    return [t[0] * pf + t[1] * Math.sqrt(1 - pf * pf), t[2]];
  }
  function voltageDrop(i, len, size, material, ct, pf, phases, voltage, sets) {
    var z = effectiveZ(size, material, ct, pf)[0];
    var k = phases === 3 ? SQRT3 : 2;
    var vd = k * i * z * len / 1000 / Math.max(sets || 1, 1);
    return [vd, 100 * vd / voltage];
  }

  // ------------------------------------------------------------------
  // conduit fill
  // ------------------------------------------------------------------
  function wireArea(size, insulation) {
    var areas = T.WIRE_AREA[insulation];
    if (has(areas, size)) return areas[size];
    var start = sizeIndex(size) >= 0 ? sizeIndex(size) : 0;
    for (var i = start; i < T.SIZES.length; i++) {
      var s = T.SIZES[i];
      if (has(areas, s) && cmilOf(s) >= cmilOf(size)) return areas[s];
    }
    return Math.max.apply(null, Object.keys(areas).map(function (k) { return areas[k]; }));
  }
  function selectConduit(items, ct) {
    var n = sum(items.map(function (x) { return x[0]; }));
    var total = sum(items.map(function (x) { return x[0] * x[1]; }));
    var pct = has(T.FILL_PERCENT, String(n)) ? T.FILL_PERCENT[String(n)] : T.FILL_PERCENT_OVER_2;
    for (var i = 0; i < T.TRADE_SIZES.length; i++) {
      var trade = T.TRADE_SIZES[i], area = T.CONDUIT_AREA[ct][trade];
      if (area === undefined) continue;
      if (total <= area * pct + EPS)
        return { trade: trade, wire_area: total, conduit_area: area,
                 fill_pct: 100 * total / area, max_pct: pct * 100, count: n };
    }
    return null;
  }

  // ------------------------------------------------------------------
  // wiring helpers
  // ------------------------------------------------------------------
  var WIRING = { "1ph2w": [1, 2, false], "1ph3w": [1, 2, true],
                 "3ph3w": [3, 3, false], "3ph4w": [3, 3, true] };

  function lineCurrent(va, v, phases) { return phases === 3 ? va / (SQRT3 * v) : va / v; }

  function wiringInput(o) {
    return Object.assign({ voltage: 208, wiring: "3ph4w", material: "cu",
      insulation: "THHN", term_temp: 75, ambient_c: 30, extra_ccc: 0,
      neutral_ccc: false, sets: 0, max_size: "500", length_ft: 100, pf: 0.9,
      vd_limit_pct: 3, conduit_type: "EMT", min_size: "12", edition: "2023",
      method: "cable", bw_type: "bw_feeder", bw_neutral: "n100", bw_ground: "g_int50",
      bw_load: "concentrated", bw_rating: 0, bw_r: 0, bw_x: 0, bw_sccr: 0, fault_ka: 0 }, o || {});
  }
  function ungroundedAndNeutral(w) {
    var c = WIRING[w.wiring];
    if (w.wiring === "1ph2w") return [c[0], 2, false];
    return c;
  }
  function cccCount(w) {
    var u = ungroundedAndNeutral(w), n = u[1];
    if (u[2] && w.wiring === "3ph4w" && w.neutral_ccc) n += 1;
    return n + Math.max(w.extra_ccc, 0);
  }
  function sizeCandidates(material, minSize, sets) {
    var start = sizeIndex(minSize);
    if (sets > 1) start = Math.max(start, sizeIndex("1/0"));
    var tbl = material === "cu" ? T.AMPACITY_CU : T.AMPACITY_AL;
    return T.SIZES.slice(start).filter(function (s) { return has(tbl, s); });
  }
  function checkSize(size, sets, iDesign, iLoad, ocpd, w, fT, fC, skipProt) {
    var aTerm = baseAmpacity(size, w.material, w.term_temp) * sets;
    var insT = T.INSULATION_TEMP[w.insulation];
    var aIns = baseAmpacity(size, w.material, insT);
    var aDer = aIns * fT * fC * sets;
    var aEff = Math.min(aDer, aTerm);
    var okTerm = aTerm >= iDesign - EPS, okDer = aDer >= iLoad - EPS, okProt = true;
    if (!skipProt && ocpd) {
      if (ocpd <= 800) {
        var nx = nextStdOcpd(aEff);
        okProt = aEff >= ocpd - EPS || (nx !== null && nx >= ocpd);
      } else okProt = aEff >= ocpd - EPS;
      var small = T.SMALL_CONDUCTOR_MAX_OCPD[w.material][size];
      if (small !== undefined && sets === 1 && ocpd > small) okProt = false;
    }
    return [okTerm && okDer && okProt, { a_term: aTerm, a_ins: aIns * sets,
      a_derated: aDer, a_eff: aEff, ok_term: okTerm, ok_derated: okDer, ok_prot: okProt }];
  }

  function sizeConductors(iDesign, iLoad, ocpd, w, skipProt, res) {
    if (w.method === "busway") return sizeBusway(iDesign, iLoad, ocpd, w, res);
    var ed = w.edition;
    res = res || new Result("conductors");
    var un = ungroundedAndNeutral(w), phases = un[0], nUng = un[1], hasN = un[2];
    var insT = T.INSULATION_TEMP[w.insulation];
    if (w.term_temp > insT) throw new CalcError("err_term_temp", {});
    var minSize = w.min_size;
    if (w.material === "al" && sizeIndex(minSize) < sizeIndex("12")) minSize = "12";
    var fT = tempFactor(w.ambient_c, insT);
    var nCcc = cccCount(w), fC = cccFactor(nCcc);
    res.add("st_temp_corr", ref("temp_corr", ed), null, { ambient: w.ambient_c, temp: insT, factor: fT });
    res.add("st_ccc_adj", ref("ccc_adj", ed), null, { n: nCcc, factor: fC });

    var setsList = w.sets > 0 ? [w.sets] : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    var chosen = null;
    for (var si = 0; si < setsList.length; si++) {
      var sets = setsList[si], cands = sizeCandidates(w.material, minSize, sets);
      for (var ci = 0; ci < cands.length; ci++) {
        var c = checkSize(cands[ci], sets, iDesign, iLoad, ocpd, w, fT, fC, skipProt);
        if (c[0]) { chosen = [sets, cands[ci], c[1]]; break; }
      }
      if (chosen) {
        if (w.sets > 0 || sizeIndex(chosen[1]) <= sizeIndex(w.max_size)) break;
        chosen = null;
      }
    }
    if (!chosen) throw new CalcError("err_no_conductor", { amps: pyRound(iDesign, 1) });
    var nSets = chosen[0], ampSize = chosen[1], d = chosen[2];
    res.add("st_ampacity_term", ref("termination", ed), d.ok_term,
      { size: sizeLabel(ampSize), sets: nSets, temp: w.term_temp, amps: d.a_term, need: iDesign });
    res.add("st_ampacity_derated", ref("ampacity", ed), d.ok_derated,
      { temp: insT, base: d.a_ins, ft: fT, fa: fC, amps: d.a_derated, need: iLoad });
    if (nSets > 1) res.add("st_parallel", ref("parallel", ed), null, { sets: nSets });
    if (!skipProt && ocpd)
      res.add("st_protection", ref("next_size_up", ed) + ", " + ref("small_cond", ed),
        d.ok_prot, { amps: d.a_eff, ocpd: ocpd });

    // voltage drop / upsizing
    var size = ampSize;
    var vd = voltageDrop(iLoad, w.length_ft, size, w.material, w.conduit_type, w.pf, phases, w.voltage, nSets);
    var vdV = vd[0], vdP = vd[1];
    if (w.vd_limit_pct && vdP > w.vd_limit_pct) {
      var cs = sizeCandidates(w.material, size, nSets), found = false;
      for (var k = 0; k < cs.length; k++) {
        var t = voltageDrop(iLoad, w.length_ft, cs[k], w.material, w.conduit_type, w.pf, phases, w.voltage, nSets);
        if (t[1] <= w.vd_limit_pct) { size = cs[k]; vdV = t[0]; vdP = t[1]; found = true; break; }
      }
      if (!found) {
        size = cs[cs.length - 1];
        var t2 = voltageDrop(iLoad, w.length_ft, size, w.material, w.conduit_type, w.pf, phases, w.voltage, nSets);
        vdV = t2[0]; vdP = t2[1];
        res.warn("w_vd_not_met", { limit: w.vd_limit_pct, pct: vdP });
      }
    }
    var approx = effectiveZ(size, w.material, w.conduit_type, w.pf)[1];
    res.add("st_vd", ref("vd_note", ed) + "; " + ref("impedance", ed),
      (!w.vd_limit_pct) || vdP <= w.vd_limit_pct + EPS,
      { amps: iLoad, length: w.length_ft, size: sizeLabel(size), volts: vdV, pct: vdP, limit: w.vd_limit_pct });
    if (approx) res.warn("w_z_approx", { size: sizeLabel(size) });
    var upsized = size !== ampSize;
    if (upsized) res.add("st_vd_upsize", ref("vd_note", ed), null, { old: sizeLabel(ampSize), new: sizeLabel(size) });

    // EGC
    var egc = null;
    if (ocpd) {
      egc = egcSize(ocpd, w.material);
      res.add("st_egc", ref("egc", ed), null, { ocpd: ocpd, size: sizeLabel(egc) });
      if (upsized) {
        var ratio = T.CMIL[size] / T.CMIL[ampSize];
        var newEgc = sizeFromCmil(cmilOf(egc) * ratio / 1.01, w.material);
        if (cmilOf(newEgc) > cmilOf(size)) newEgc = size;
        if (newEgc !== egc) {
          res.add("st_egc_upsize", ref("egc_upsize", ed), null,
            { ratio: ratio, old: sizeLabel(egc), new: sizeLabel(newEgc) });
          egc = newEgc;
        }
      }
      if (cmilOf(egc) > cmilOf(size)) egc = size;
      if (nSets > 1) res.add("st_egc_parallel", ref("egc_parallel", ed), null, { sets: nSets, size: sizeLabel(egc) });
    }
    var neutral = hasN ? size : null;

    var items = [[nUng, wireArea(size, w.insulation)]];
    if (neutral) items.push([1, wireArea(neutral, w.insulation)]);
    if (egc) items.push([1, wireArea(egc, w.insulation)]);
    var cond = selectConduit(items, w.conduit_type);
    if (cond)
      res.add("st_conduit", ref("fill", ed), null, { n: cond.count, area: cond.wire_area,
        trade: cond.trade, ctype: w.conduit_type, fill: cond.fill_pct, maxfill: cond.max_pct, qty: nSets });
    else res.warn("w_conduit_none", { ctype: w.conduit_type });

    var aFinal = checkSize(size, nSets, iDesign, iLoad, ocpd, w, fT, fC, true)[1].a_eff;
    Object.assign(res.summary, {
      sets: nSets, size: size, size_label: sizeLabel(size), ampacity: aFinal,
      neutral: neutral ? sizeLabel(neutral) : "-", egc: egc ? sizeLabel(egc) : "-",
      conduit: cond ? nSets + " x " + cond.trade + '" ' + w.conduit_type : "-",
      vd_pct: vdP, vd_v: vdV, n_ccc: nCcc,
      fill_pct: cond ? cond.fill_pct : null, max_fill: cond ? cond.max_pct : null,
      vd_limit: w.vd_limit_pct,
      wire_text: wireText(nSets, nUng, size, neutral, egc, w.material, w.insulation, cond, w.conduit_type)
    });
    return res;
  }

  // ------------------------------------------------------------------
  // busway (Article 368)
  // ------------------------------------------------------------------
  function buswayDerate(amb) {
    if (amb <= T.BUSWAY_AMBIENT_BASE) return 1;
    if (amb >= T.BUSWAY_HOTSPOT) throw new CalcError("err_ambient", { ambient: amb, temp: T.BUSWAY_HOTSPOT });
    return Math.sqrt((T.BUSWAY_HOTSPOT - amb) / (T.BUSWAY_HOTSPOT - T.BUSWAY_AMBIENT_BASE));
  }
  function buswayImpedance(rating, w) {
    var r = w.bw_r || T.BUSWAY_R_K[w.material] / rating;
    return [r, w.bw_x || r * T.BUSWAY_X_RATIO];
  }
  function buswaySccr(rating, w) {
    if (w.bw_sccr) return w.bw_sccr;
    var keys = Object.keys(T.BUSWAY_SCCR_TYPICAL).map(Number);
    var le = keys.filter(function (k) { return k <= rating; });
    var k = le.length ? Math.max.apply(null, le) : Math.min.apply(null, keys);
    return T.BUSWAY_SCCR_TYPICAL[String(k)];
  }
  function buswayVd(i, rating, w) {
    var z = buswayImpedance(rating, w), pf = Math.max(Math.min(w.pf, 1), 0);
    var ze = z[0] * pf + z[1] * Math.sqrt(1 - pf * pf);
    var vd = SQRT3 * i * ze / 1000 * w.length_ft / 100 * (w.bw_load === "distributed" ? 0.5 : 1);
    return [vd, 100 * vd / w.voltage];
  }
  function sizeBusway(iDesign, iLoad, ocpd, w, res) {
    var ed = w.edition;
    res = res || new Result("conductors");
    var c = WIRING[w.wiring], hasN = c[2];
    if (c[0] !== 3) throw new CalcError("err_busway_phase", {});
    if (w.voltage > 1000) throw new CalcError("err_busway_voltage", { volts: w.voltage });
    var f = buswayDerate(w.ambient_c);
    res.add("st_bw_derate", ref("busway_rating", ed), null, { ambient: w.ambient_c, factor: f });
    var plugin = w.bw_type === "bw_plugin";
    var ratings = w.bw_rating ? [w.bw_rating] : T.BUSWAY_RATINGS.filter(function (r) {
      return !plugin || r <= T.BUSWAY_PLUGIN_MAX; });
    function checks(r) {
      var a = r * f, okD = a >= iDesign - EPS, okP = true;
      if (ocpd) { var nx = nextStdOcpd(a); okP = a >= ocpd - EPS || (ocpd <= 800 && nx !== null && nx >= ocpd); }
      return [okD, okP];
    }
    var chosen = null;
    for (var i = 0; i < ratings.length; i++) { var ck = checks(ratings[i]); if (ck[0] && ck[1]) { chosen = ratings[i]; break; } }
    if (chosen === null) {
      if (!w.bw_rating) throw new CalcError("err_busway_range", { amps: pyRound(Math.max(iDesign, ocpd || 0), 1) });
      chosen = w.bw_rating;
    }
    var cc = checks(chosen);
    res.add("st_bw_select", ref("busway_rating", ed), cc[0], { rating: chosen, factor: f, amps: chosen * f, need: iDesign });
    if (ocpd) res.add("st_bw_ocpd", ref("busway_ocpd", ed), cc[1], { ocpd: ocpd, amps: chosen * f });
    var ampRating = chosen, vd = buswayVd(iLoad, chosen, w);
    if (w.vd_limit_pct && vd[1] > w.vd_limit_pct) {
      var better = null;
      if (!(w.bw_rating || w.bw_r))
        for (var j = 0; j < ratings.length; j++)
          if (ratings[j] > chosen && buswayVd(iLoad, ratings[j], w)[1] <= w.vd_limit_pct) { better = ratings[j]; break; }
      if (better) { chosen = better; vd = buswayVd(iLoad, chosen, w); }
      else res.warn("w_vd_not_met", { limit: w.vd_limit_pct, pct: vd[1] });
    }
    var z = buswayImpedance(chosen, w);
    res.add("st_bw_vd", ref("busway_vd", ed) + "; " + ref("vd_note", ed),
      (!w.vd_limit_pct) || vd[1] <= w.vd_limit_pct + EPS,
      { amps: iLoad, length: w.length_ft, r: z[0], x: z[1], load: w.bw_load, volts: vd[0], pct: vd[1], limit: w.vd_limit_pct });
    if (chosen !== ampRating) res.add("st_bw_upsize", ref("vd_note", ed), null, { old: ampRating, new: chosen });
    var sccr = buswaySccr(chosen, w);
    if (w.fault_ka) res.add("st_bw_sccr", ref("busway_sccr", ed), sccr >= w.fault_ka - EPS, { sccr: sccr, fault: w.fault_ka });
    else { res.add("st_bw_sccr_info", ref("busway_sccr", ed), null, { sccr: sccr }); res.warn("w_bw_fault_unknown", {}); }
    var neutral = hasN ? w.bw_neutral : "n0";
    res.add("st_bw_ground", ref("busway_ground", ed), null, { neutral: neutral, ground: w.bw_ground });
    res.add("st_bw_install", ref("busway_install", ed), null, {});
    if (!(w.bw_r && w.bw_x && w.bw_sccr)) res.warn("w_bw_typical", {});
    if (chosen > T.BUSWAY_COMMON_MAX) res.warn("w_bw_large", { rating: chosen });
    var text = fmtG(chosen) + "A " + (plugin ? "PLUG-IN" : "FEEDER") + " BUSWAY, " + fmtG(w.voltage) + "V 3PH " +
      (hasN ? 4 : 3) + "W" + ({ n100: ", 100% N", n200: ", 200% N" }[neutral] || "") +
      (w.bw_ground === "g_int50" ? ", 50% INT. GND" : ", HOUSING GND") +
      ", " + (w.material === "cu" ? "CU" : "AL") + ", " + fmtG(sccr) + "kA SCCR";
    Object.assign(res.summary, { method: "busway", sets: 1, size: "-", size_label: fmtG(chosen) + " A busway",
      ampacity: null, bw_ampacity: chosen * f, neutral: "-", egc: "-", conduit: "-", vd_pct: vd[1], vd_v: vd[0],
      vd_limit: w.vd_limit_pct, busway_text: text, bw_rating: chosen, sccr_ka: sccr });
    return res;
  }

  function wireText(sets, n, size, neutral, egc, material, insulation, cond, ct) {
    var mat = material === "cu" ? "CU" : "AL";
    var ins = insulation === "THHN" ? "THHN/THWN-2" : "XHHW-2";
    var parts = [n + "#" + size];
    if (neutral) parts.push("1#" + neutral + "N");
    if (egc) parts.push("1#" + egc + "G");
    var s = parts.join(" + ") + " " + mat + " " + ins;
    if (cond) s += ", " + cond.trade + '" ' + ct;
    if (sets > 1) s = "(" + sets + ") SETS OF " + s;
    return s;
  }

  // ------------------------------------------------------------------
  // general branch circuit / feeder
  // ------------------------------------------------------------------
  function designGeneral(loadVa, w, o) {
    o = o || {};
    var ed = w.edition, res = new Result("general");
    var phases = WIRING[w.wiring][0];
    var loadAmps = o.load_amps === undefined ? null : o.load_amps;
    var kind = o.kind || "branch", lmVa = o.largest_motor_va || 0;
    var ocpd = o.ocpd === undefined ? null : o.ocpd;
    if (loadAmps !== null && !loadVa) loadVa = loadAmps * w.voltage * (phases === 3 ? SQRT3 : 1);
    var contVa = (o.continuous_va === undefined || o.continuous_va === null) ? loadVa : o.continuous_va;
    contVa = Math.min(contVa, loadVa);
    var iLoad, iCont;
    if (loadAmps !== null) {
      iLoad = loadAmps;
      iCont = iLoad * (loadVa ? contVa / loadVa : 1);
    } else {
      iLoad = lineCurrent(loadVa, w.voltage, phases);
      iCont = lineCurrent(contVa, w.voltage, phases);
    }
    var iM25 = 0.25 * lineCurrent(lmVa, w.voltage, phases);
    var iDesign = iLoad + 0.25 * iCont + iM25;
    res.add("st_load_current", "", null, { va: loadVa, volts: w.voltage, phases: phases, amps: iLoad });
    res.add("st_design_current", ref(kind === "feeder" ? "cont_feeder" : "cont_branch", ed), null,
      { cont: iCont, noncont: iLoad - iCont, motor25: iM25, amps: iDesign });
    if (ocpd === null) {
      ocpd = nextStdOcpd(iDesign);
      if (ocpd === null) throw new CalcError("err_ocpd_range", { amps: pyRound(iDesign, 1) });
      res.add("st_ocpd_select", ref("std_ocpd", ed), null, { amps: iDesign, ocpd: ocpd });
    } else {
      res.add("st_ocpd_given", ref("std_ocpd", ed), ocpd >= iDesign - EPS, { ocpd: ocpd, amps: iDesign });
      if (ocpd < iDesign - EPS) res.warn("w_ocpd_small", { ocpd: ocpd, amps: pyRound(iDesign, 1) });
    }
    sizeConductors(iDesign, iLoad, ocpd, w, false, res);
    var sw = nextSwitch(ocpd);
    res.add("st_switch", ref("switch", ed), null, { amps: sw, ocpd: ocpd });
    Object.assign(res.summary, { i_load: iLoad, i_design: iDesign, ocpd: ocpd, "switch": sw });
    return res;
  }

  // ------------------------------------------------------------------
  // motor
  // ------------------------------------------------------------------
  function motorFlc(hp, voltage, phases) {
    var v = T.MOTOR_VOLT_MAP[String(pyRound(voltage, 0))];
    if (v === undefined) return null;
    var row, volts;
    if (phases === 1) { row = T.FLC_1PH[hp]; volts = T.FLC_1PH_VOLTS; }
    else { row = T.FLC_3PH[hp]; volts = T.FLC_3PH_VOLTS; }
    if (!row || volts.indexOf(v) < 0) return null;
    return row[volts.indexOf(v)];
  }
  function designMotor(hp, w, o) {
    o = o || {};
    var device = o.device || "itcb", ed = w.edition, res = new Result("motor");
    var phases = WIRING[w.wiring][0];
    var flc = o.flc_override || motorFlc(hp, w.voltage, phases);
    if (!flc) throw new CalcError("err_flc", { hp: hp, volts: w.voltage, phases: phases });
    res.add("st_motor_flc", ref("motor_flc", ed), null, { hp: hp, volts: w.voltage, phases: phases, flc: flc });
    var iDesign = 1.25 * flc;
    res.add("st_motor_cond", ref("motor_cond", ed), null, { flc: flc, amps: iDesign });
    var pct = T.MOTOR_OCPD_PERCENT[device];
    if (device === "inst_cb" && o.design_b_ee) pct = T.MOTOR_OCPD_PERCENT_DESIGN_B_EE_INST;
    var maxCalc = flc * pct, ocpd, prot;
    if (device === "inst_cb") {
      ocpd = maxCalc;
      res.add("st_motor_mcp", ref("motor_ocpd", ed), null, { pct: pct * 100, flc: flc, amps: maxCalc });
      prot = nextStdOcpd(Math.max(iDesign, 15));
    } else {
      ocpd = nextStdOcpd(Math.max(maxCalc, 15));
      res.add("st_motor_ocpd", ref("motor_ocpd", ed), null, { pct: pct * 100, flc: flc, amps: maxCalc, ocpd: ocpd });
      prot = ocpd;
    }
    sizeConductors(iDesign, flc, prot, w, true, res);
    var sf115 = o.sf_115 === undefined ? true : o.sf_115;
    var olPct = sf115 ? 1.25 : 1.15;
    var fla = o.nameplate_fla || flc, ol = fla * olPct;
    res.add("st_motor_ol", ref("motor_ol", ed), null, { fla: fla, pct: olPct * 100, amps: ol });
    var discMin = 1.15 * flc;
    var fused = device === "td_fuse" || device === "ntd_fuse";
    var sw = nextSwitch(fused ? Math.max(discMin, prot) : discMin);
    res.add("st_motor_disc", ref("motor_disc", ed), null, { flc: flc, amps: discMin, "switch": sw });
    Object.assign(res.summary, { flc: flc, i_design: iDesign, i_load: flc, ocpd: ocpd,
      ocpd_device: device, overload: ol, "switch": sw,
      va: flc * w.voltage * (phases === 3 ? SQRT3 : 1) });
    return res;
  }

  // ------------------------------------------------------------------
  // medium-voltage cable
  // ------------------------------------------------------------------
  function mvInput(o) {
    return Object.assign({ kv: 24.9, amps: 50, material: "cu", insulation_level: "25kV_133",
      fault_ka: 10, clear_time_s: 0.5, t_oper: 90, t_sc: 250, ocpd_type: "fuse",
      ocpd_amps: 0, design_factor: 1.25, conduit_type: "PVC40", cable_od_in: 0,
      include_egc: true, edition: "2023", ampacity_table: null }, o || {});
  }
  function scMinCmil(ka, t, material, t1, t2) {
    var c = T.SC_CONST[material];
    var denom = c[0] * Math.log10((t2 + c[1]) / (t1 + c[1]));
    return ka * 1000 * Math.sqrt(t / denom);
  }
  function designMvCable(m) {
    var ed = m.edition, res = new Result("mv_cable");
    var ampTbl = m.ampacity_table || T.MV_AMPACITY_TYPICAL[m.material];
    var last = T.MV_MIN_SIZE[T.MV_MIN_SIZE.length - 1][0], minSize = null;
    if (m.kv <= last)
      for (var i = 0; i < T.MV_MIN_SIZE.length; i++)
        if (m.kv <= T.MV_MIN_SIZE[i][0]) { minSize = T.MV_MIN_SIZE[i][1]; break; }
    if (minSize === null) throw new CalcError("err_mv_kv", { kv: m.kv });
    res.add("st_mv_min", ref("mv_min_size", ed), null, { kv: m.kv, size: sizeLabel(minSize) });
    var iReq = m.amps * m.design_factor;
    res.add("st_mv_design", ref("mv_feeder", ed), null, { amps: m.amps, factor: m.design_factor, req: iReq });
    var aSc = scMinCmil(m.fault_ka, m.clear_time_s, m.material, m.t_oper, m.t_sc);
    res.add("st_mv_sc", ref("sc_withstand", ed), null,
      { ka: m.fault_ka, t: m.clear_time_s, t1: m.t_oper, t2: m.t_sc, cmil: aSc });
    var mult = m.ocpd_type === "fuse" ? 3 : 6, chosen = null;
    for (var j = 0; j < T.MV_SIZES.length; j++) {
      var s = T.MV_SIZES[j];
      if (!has(ampTbl, s)) continue;
      if (T.CMIL[s] < (has(T.CMIL, minSize) ? T.CMIL[minSize] : 0)) continue;
      var a = ampTbl[s];
      if (a < iReq || T.CMIL[s] < aSc) continue;
      if (m.ocpd_amps && m.ocpd_amps > mult * a) continue;
      chosen = s; break;
    }
    if (!chosen) throw new CalcError("err_no_conductor", { amps: pyRound(iReq, 1) });
    var amp = ampTbl[chosen];
    res.add("st_mv_size", ref("mv_ampacity", ed), true,
      { size: sizeLabel(chosen), amps: amp, req: iReq, cmil: T.CMIL[chosen], sc: aSc });
    if (m.ocpd_amps)
      res.add("st_mv_ocpd", ref("mv_conductor_ocpd", ed), m.ocpd_amps <= mult * amp,
        { ocpd: m.ocpd_amps, mult: mult, amps: amp, limit: mult * amp });
    if (!m.ampacity_table) res.warn("w_mv_typical", {});
    var egc = null;
    if (m.include_egc) {
      var rating = m.ocpd_amps || nextStdOcpd(iReq) || 6000;
      egc = egcSize(rating, m.material);
      var floor = m.material === "cu" ? "6" : "4";
      if (cmilOf(egc) < cmilOf(floor)) egc = floor;
      res.add("st_mv_egc", ref("mv_egc", ed), null, { rating: rating, size: sizeLabel(egc) });
    }
    var odTbl = T.MV_CABLE_OD_TYPICAL[m.insulation_level] || T.MV_CABLE_OD_TYPICAL["25kV_133"];
    var od = m.cable_od_in || odTbl[chosen];
    var items = [[3, Math.PI * od * od / 4]];
    if (egc) items.push([1, wireArea(egc, "THHN")]);
    var cond = selectConduit(items, m.conduit_type), jam = null;
    if (cond) {
      var dId = Math.sqrt(4 * cond.conduit_area / Math.PI);
      jam = 1.05 * dId / od;
      res.add("st_conduit", ref("mv_fill", ed), null, { n: cond.count, area: cond.wire_area,
        trade: cond.trade, ctype: m.conduit_type, fill: cond.fill_pct, maxfill: cond.max_pct, qty: 1 });
      if (jam >= 2.8 && jam <= 3.2) res.warn("w_jam", { ratio: jam });
    } else res.warn("w_conduit_none", { ctype: m.conduit_type });
    if (!m.cable_od_in) res.warn("w_mv_od_typical", { od: od });
    Object.assign(res.summary, {
      size: chosen, size_label: sizeLabel(chosen), ampacity: amp, i_load: m.amps,
      i_design: iReq, sc_cmil: aSc, egc: egc ? sizeLabel(egc) : "-",
      conduit: cond ? cond.trade + '" ' + m.conduit_type : "-", od: od, jam: jam,
      fill_pct: cond ? cond.fill_pct : null, max_fill: cond ? cond.max_pct : null,
      wire_text: "3-1/C #" + chosen + " " + (m.material === "cu" ? "CU" : "AL") +
        " MV-105/MV-90 " + m.insulation_level.replace("_", " ") + "%" +
        (egc ? " + 1#" + egc + "G" : "") + (cond ? ", " + cond.trade + '" ' + m.conduit_type : "")
    });
    return res;
  }

  // ------------------------------------------------------------------
  // transformer
  // ------------------------------------------------------------------
  function transformerInput(o) {
    return Object.assign({ kva: 1500, pri_v: 24900, sec_v: 480, phases: 3, z_pct: 5.75,
      location: "any", pri_device: "fuse", sec_device: "cb", lv_scheme: "pri_sec",
      edition: "2023" }, o || {});
  }
  function designTransformer(x, secW, priW, mv) {
    var ed = x.edition, res = new Result("transformer");
    var k = x.phases === 3 ? SQRT3 : 1;
    var iPri = x.kva * 1000 / (k * x.pri_v), iSec = x.kva * 1000 / (k * x.sec_v);
    res.add("st_xfmr_fla", "", null, { kva: x.kva, pv: x.pri_v, sv: x.sec_v, ip: iPri, is_: iSec });
    var isc = x.z_pct ? iSec * 100 / x.z_pct : null;
    if (isc) res.add("st_xfmr_isc", "", null, { z: x.z_pct, isc: isc / 1000 });
    var pPct, sPct, pMax, pMaxStd, pSel, refSec;
    if (x.pri_v > 1000) {
      var zc = x.z_pct <= 6 ? "le6" : "6to10";
      if (x.z_pct > 10) throw new CalcError("err_z_range", {});
      var row = DATA.XFMR_450_3A[x.location + "|" + zc];
      pPct = x.pri_device === "fuse" ? row[1] : row[0];
      sPct = x.sec_v > 1000 ? (x.sec_device === "fuse" ? row[3] : row[2]) : row[4];
      pMax = iPri * pPct;
      var ratings = x.pri_device === "fuse" ? T.MV_FUSE_E_RATINGS : null;
      pMaxStd = ratings ? nextStdOcpd(pMax, ratings) : pyRound(pMax, 1);
      pSel = ratings ? nextStdOcpd(iPri * 1.5, ratings) : pyRound(iPri * 1.25, 1);
      if (ratings && pSel && pMaxStd && pSel > pMaxStd) pSel = pMaxStd;
      res.add("st_xfmr_pri_mv", ref("xfmr_mv", ed), null, { loc: x.location, z: x.z_pct,
        dev: x.pri_device, pct: pPct * 100, amps: pMax, std: pMaxStd, sel: pSel });
      refSec = ref("xfmr_mv", ed);
    } else {
      if (x.lv_scheme === "pri_only") {
        pPct = iPri >= 9 ? 1.25 : (iPri >= 2 ? 1.67 : 3.0); sPct = null;
      } else { pPct = 2.5; sPct = iSec >= 9 ? 1.25 : 1.67; }
      pMax = iPri * pPct;
      pMaxStd = (x.lv_scheme === "pri_only" && iPri >= 9) ? nextStdOcpd(pMax) : maxStdOcpd(pMax);
      pSel = nextStdOcpd(iPri * 1.25);
      if (pSel === null) throw new CalcError("err_ocpd_range", { amps: pyRound(iPri * 1.25, 1) });
      if (pMaxStd && pSel > pMaxStd) pSel = pMaxStd;
      res.add("st_xfmr_pri_lv", ref("xfmr_lv", ed), null, { scheme: x.lv_scheme,
        pct: pPct * 100, amps: pMax, std: pMaxStd, sel: pSel });
      refSec = ref("xfmr_lv", ed);
    }
    var sSel = null;
    if (sPct) {
      var sMax = iSec * sPct;
      sSel = nextStdOcpd(iSec * 1.25);
      if (sSel === null) throw new CalcError("err_ocpd_range", { amps: pyRound(iSec * 1.25, 1) });
      var sMaxStd = sPct === 1.25 ? nextStdOcpd(sMax) : maxStdOcpd(sMax);
      if (sMaxStd && sSel && sSel > sMaxStd) sSel = sMaxStd;
      res.add("st_xfmr_sec", refSec, null, { pct: sPct * 100, amps: sMax, std: sMaxStd, sel: sSel });
    }
    Object.assign(res.summary, { i_pri: iPri, i_sec: iSec, isc_ka: isc ? isc / 1000 : null,
      pri_ocpd: pSel, pri_ocpd_max: pMaxStd, sec_ocpd: sSel });
    if (x.pri_v > 1000) {
      var m = mv || mvInput({ edition: ed });
      m.kv = x.pri_v / 1000; m.amps = iPri;
      if (pSel) { m.ocpd_type = x.pri_device === "fuse" ? "fuse" : "relay"; m.ocpd_amps = pSel; }
      res.children.primary = designMvCable(m);
    } else if (priW) {
      priW.voltage = x.pri_v;
      var pr = new Result("primary");
      sizeConductors(iPri * 1.25, iPri, pSel, priW, false, pr);
      Object.assign(pr.summary, { ocpd: pSel, i_load: iPri, i_design: iPri * 1.25 });
      res.children.primary = pr;
    }
    if (secW && x.sec_v <= 1000) {
      secW.voltage = x.sec_v;
      if (!secW.fault_ka && isc) secW.fault_ka = isc / 1000;
      var sr = new Result("secondary");
      sizeConductors(iSec * 1.25, iSec, sSel || nextStdOcpd(iSec * 1.25), secW, false, sr);
      sr.add("st_xfmr_sec_cond", ref("xfmr_sec_cond", ed), null, {});
      Object.assign(sr.summary, { ocpd: sSel, i_load: iSec, i_design: iSec * 1.25 });
      res.children.secondary = sr;
    }
    return res;
  }

  // ------------------------------------------------------------------
  // panel load calculation
  // ------------------------------------------------------------------
  function loadItem(o) {
    return Object.assign({ name: "Load", category: "other", qty: 1, rating: 1000, unit: "VA",
      pf: 1.0, efficiency: 1.0, voltage: 120, phases: 1, continuous: false,
      demand_factor: null, phase_conn: "auto", hp: "" }, o || {});
  }
  var HP_FRAC = [[1 / 6, "1/6"], [0.25, "1/4"], [1 / 3, "1/3"], [0.5, "1/2"],
                 [0.75, "3/4"], [1.5, "1-1/2"], [7.5, "7-1/2"]];
  function hpStr(r) {
    for (var i = 0; i < HP_FRAC.length; i++) if (Math.abs(r - HP_FRAC[i][0]) < 1e-3) return HP_FRAC[i][1];
    return Number.isInteger(r) ? String(r) : String(r);
  }
  function loadKva(ld) {
    var q = Math.max(ld.qty, 0), r = ld.rating, u = ld.unit, pf = ld.pf || 1;
    if (u === "VA") return q * r / 1000;
    if (u === "kVA") return q * r;
    if (u === "W") return q * r / 1000 / pf;
    if (u === "kW") return q * r / pf;
    var k = ld.phases === 3 ? SQRT3 : 1;
    if (u === "A") return q * r * ld.voltage * k / 1000;
    if (u === "HP") {
      var flc = motorFlc(ld.hp || hpStr(r), ld.voltage, ld.phases);
      if (flc === null || flc === undefined) return q * r * 0.746 / Math.max(ld.efficiency, 0.01) / pf;
      return q * flc * ld.voltage * k / 1000;
    }
    throw new CalcError("err_unit", { unit: u });
  }
  function loadKw(ld) { return loadKva(ld) * ld.pf; }
  function loadKvar(ld) { var s = loadKva(ld), p = loadKw(ld); return Math.sqrt(Math.max(s * s - p * p, 0)); }
  function loadUnitKva(ld) { return ld.qty ? loadKva(ld) / ld.qty : 0; }
  function loadAmps(ld) {
    var k = ld.phases === 3 ? SQRT3 : 1;
    return ld.voltage ? loadKva(ld) * 1000 / (k * ld.voltage) : 0;
  }
  function panelInput(o) {
    return Object.assign({ name: "PANEL", system: "208Y/120", diversity: 1.0, target_pf: 0.95,
      loads: [], edition: "2023" }, o || {});
  }
  function phasesFor(ld, pPh, wiring) {
    if (ld.phase_conn && ld.phase_conn !== "auto") return ld.phase_conn.split("");
    if (wiring === "1ph2w") return ["A"];
    if (pPh === 1) return ld.voltage > 150 ? ["A", "B"] : null;
    if (ld.phases === 3) return ["A", "B", "C"];
    return null;
  }
  function argmin(list, fn) {
    var best = list[0], bv = fn(best);
    for (var i = 1; i < list.length; i++) { var v = fn(list[i]); if (v < bv) { bv = v; best = list[i]; } }
    return best;
  }
  function calculateLoads(panel) {
    var sys = DATA.systems[panel.system], ll = sys[0], ln = sys[1], pPh = sys[2], wiring = sys[3];
    var ed = panel.edition, rows = [], notes = [];
    panel.loads.forEach(function (ld) {
      rows.push({ load: ld, kva: loadKva(ld), kw: loadKw(ld), kvar: loadKvar(ld), amps: loadAmps(ld) });
    });
    var recKva = sum(rows.filter(function (r) { return r.load.category === "receptacle" &&
      (r.load.demand_factor === null || r.load.demand_factor === undefined); }).map(function (r) { return r.kva; }));
    var recDf = 1;
    if (recKva > 10) {
      recDf = (10 + 0.5 * (recKva - 10)) / recKva;
      notes.push(["n_receptacle", ref("receptacle_load", ed), { kva: recKva, df: recDf }]);
    }
    var heat = sum(rows.filter(function (r) { return r.load.category === "heating"; }).map(function (r) { return r.kva; }));
    var cool = sum(rows.filter(function (r) { return r.load.category === "cooling"; }).map(function (r) { return r.kva; }));
    var dropCat = null;
    if (heat > 0 && cool > 0) {
      dropCat = heat >= cool ? "cooling" : "heating";
      notes.push(["n_noncoincident", ref("noncoincident", ed), { heat: heat, cool: cool, drop: dropCat }]);
    }
    var lmKva = 0, lmFound = false;
    rows.forEach(function (r) {
      if (r.load.category !== "motor") return;
      var u = loadUnitKva(r.load);
      if (!lmFound || u > lmKva) { lmKva = u; lmFound = true; }
    });
    rows.forEach(function (r) {
      var ld = r.load, df;
      if (ld.demand_factor !== null && ld.demand_factor !== undefined) df = ld.demand_factor;
      else if (ld.category === "receptacle") df = recDf;
      else if (ld.category === dropCat) df = 0;
      else df = 1;
      r.df = df; r.d_kva = r.kva * df; r.d_kw = r.kw * df; r.d_kvar = r.kvar * df;
    });
    var phKva = { A: 0, B: 0, C: 0 };
    var letters = wiring === "1ph2w" ? ["A"] : (wiring === "1ph3w" ? ["A", "B"] : ["A", "B", "C"]);
    var pending = [];
    rows.forEach(function (r) {
      var ph = phasesFor(r.load, pPh, wiring);
      if (ph === null) pending.push(r);
      else { r.phase = ph.join(""); ph.forEach(function (p) { phKva[p] += r.d_kva / ph.length; }); }
    });
    pending.slice().sort(function (a, b) { return b.d_kva - a.d_kva; }).forEach(function (r) {
      var ld = r.load, n = Math.max(Math.trunc(ld.qty), 1), unit = r.d_kva / n, used = [];
      for (var i = 0; i < n; i++) {
        var tag;
        if (pPh === 3 && ld.voltage > ln * 1.2) {
          var best = argmin([["A", "B"], ["B", "C"], ["C", "A"]], function (p) { return phKva[p[0]] + phKva[p[1]]; });
          phKva[best[0]] += unit / 2; phKva[best[1]] += unit / 2; tag = best.join("");
        } else {
          tag = argmin(letters, function (p) { return phKva[p]; });
          phKva[tag] += unit;
        }
        if (used.indexOf(tag) < 0) used.push(tag);
      }
      r.phase = used.sort().join(",");
    });
    var connKw = sum(rows.map(function (r) { return r.kw; }));
    var connKvar = sum(rows.map(function (r) { return r.kvar; }));
    var connKva = Math.hypot(connKw, connKvar);
    var demKw = sum(rows.map(function (r) { return r.d_kw; }));
    var demKvar = sum(rows.map(function (r) { return r.d_kvar; }));
    var demKva = sum(rows.map(function (r) { return r.d_kva; }));
    var div = Math.max(panel.diversity, 1);
    var coinKw = demKw / div, coinKvar = demKvar / div, coinKva = demKva / div;
    var pf = connKva ? connKw / connKva : 1;
    var demPf = demKw ? demKw / Math.hypot(demKw, demKvar) : 1;
    var contKva = sum(rows.filter(function (r) { return r.load.continuous; }).map(function (r) { return r.d_kva; })) / div;
    var designKva = coinKva + 0.25 * contKva + 0.25 * lmKva;
    var k = pPh === 3 ? SQRT3 : 1;
    var iDemand = coinKva * 1000 / (k * ll), iDesign = designKva * 1000 / (k * ll);
    var vph = pPh === 3 ? ln : (wiring === "1ph3w" ? ll / 2 : ll);
    var phAmps = {}, phOut = {};
    letters.forEach(function (p) { phAmps[p] = phKva[p] / div * 1000 / vph; phOut[p] = phKva[p] / div; });
    var vals = letters.map(function (p) { return phAmps[p]; });
    var avg = vals.length ? sum(vals) / vals.length : 0;
    var mx = vals.length ? Math.max.apply(null, vals) : 0;
    var imb = avg ? (mx - avg) / avg * 100 : 0;
    var scale = coinKva ? designKva / coinKva : 1;
    var iFinal = Math.max(iDesign, mx * scale);
    var cap = 0;
    if (demPf < panel.target_pf && coinKw > 0)
      cap = coinKw * (Math.tan(Math.acos(demPf)) - Math.tan(Math.acos(panel.target_pf)));
    var connArith = sum(rows.map(function (r) { return r.kva; }));
    return {
      rows: rows, notes: notes,
      connected: { kw: connKw, kvar: connKvar, kva: connKva, kva_arith: connArith, pf: pf },
      demand: { kw: demKw, kvar: demKvar, kva: demKva, pf: demPf },
      coincident: { kw: coinKw, kvar: coinKvar, kva: coinKva, diversity: div },
      continuous_kva: contKva, largest_motor_kva: lmKva, design_kva: designKva,
      i_demand: iDemand, i_design_balanced: iDesign, i_design: iFinal,
      phase_kva: phOut, phase_amps: phAmps, imbalance_pct: imb, cap_kvar: cap,
      system: [ll, ln, pPh, wiring],
      demand_factor_overall: rows.length ? demKva / connArith : 1
    };
  }
  function sizeFeeder(panel, calc, w) {
    w.voltage = calc.system[0]; w.wiring = calc.system[3]; w.pf = calc.demand.pf;
    var iLoad = calc.i_demand, iDesign = calc.i_design, res = new Result("feeder");
    res.add("st_feeder_load", ref("cont_feeder", panel.edition), null, { kva: calc.coincident.kva,
      cont: calc.continuous_kva, motor: calc.largest_motor_kva, design: calc.design_kva, amps: iDesign });
    var ocpd = nextStdOcpd(iDesign);
    if (ocpd === null) throw new CalcError("err_ocpd_range", { amps: pyRound(iDesign, 1) });
    res.add("st_ocpd_select", ref("std_ocpd", panel.edition), null, { amps: iDesign, ocpd: ocpd });
    sizeConductors(iDesign, iLoad, ocpd, w, false, res);
    Object.assign(res.summary, { i_load: iLoad, i_design: iDesign, ocpd: ocpd, "switch": nextSwitch(ocpd) });
    return res;
  }

  // ------------------------------------------------------------------
  // cable tray (Article 392)
  // ------------------------------------------------------------------
  var CMIL_4_0 = T.CMIL["4/0"], CMIL_1_0 = T.CMIL["1/0"];
  function trayCable(o) {
    return Object.assign({ name: "Cable", kind: "lv_multi", size: "4/0", n_cond: 3, qty: 1,
      od_in: 0, material: "cu", ins_level: "25kV_133" }, o || {});
  }
  function trayInput(o) {
    return Object.assign({ tray_type: "ladder", depth_in: 4, width_in: 0, covered: false,
      arrangement: "random", ambient_c: 30, cables: [], edition: "2023" }, o || {});
  }
  function cableOd(c) {
    if (c.od_in) return c.od_in;
    var d;
    if (c.kind === "lv_single") {
      var a = T.WIRE_AREA.XHHW[c.size];
      if (a === undefined) throw new CalcError("err_tray_od", { size: c.size });
      return Math.sqrt(4 * a / Math.PI);
    }
    if (c.kind === "lv_multi") {
      d = T.TC_3C_OD_TYPICAL[c.size];
      if (d === undefined) throw new CalcError("err_tray_od", { size: c.size });
      return d * (c.n_cond >= 4 ? T.TC_4C_OD_FACTOR : 1);
    }
    if (c.kind === "mv_single" || c.kind === "mv_multi") {
      var tbl = T.MV_CABLE_OD_TYPICAL[c.ins_level] || T.MV_CABLE_OD_TYPICAL["25kV_133"];
      d = tbl[c.size];
      if (d === undefined) throw new CalcError("err_tray_od", { size: c.size });
      if (c.kind === "mv_multi") d = d * T.MV_3C_OD_FACTOR + T.MV_3C_JACKET_IN;
      return d;
    }
    return 0.5;
  }
  function cableArea(c) { var d = cableOd(c); return Math.PI * d * d / 4; }
  function odIsTypical(c) { return !c.od_in && c.kind !== "lv_single"; }
  function isMv(c) { return c.kind === "mv_single" || c.kind === "mv_multi"; }

  function tblPairs(tbl) {
    return Object.keys(tbl).map(function (k) { return [parseFloat(k), tbl[k]]; })
      .sort(function (a, b) { return a[0] - b[0]; });
  }
  function widthFor(tbl, value) {
    if (value <= 0) return 0;
    var p = tblPairs(tbl);
    if (value <= p[0][1]) return p[0][0] * value / p[0][1];
    for (var i = 0; i + 1 < p.length; i++) {
      var a = p[i], b = p[i + 1];
      if (a[1] <= value && value <= b[1]) return a[0] + (b[0] - a[0]) * (value - a[1]) / (b[1] - a[1]);
    }
    var l = p[p.length - 1];
    return l[0] * value / l[1];
  }
  function qtySum(list, fn) { return sum(list.map(function (c) { return c.qty * fn(c); })); }

  function lvMultiWidth(cables, x, res) {
    var ed = x.edition, solid = x.tray_type === "solid_bottom";
    var power = cables.filter(function (c) { return c.kind === "lv_multi"; });
    var control = cables.filter(function (c) { return c.kind === "control"; });
    if (!power.length && control.length) {
      var area = qtySum(control, cableArea), pct = T.TRAY_CONTROL_PCT[x.tray_type];
      var depth = Math.min(x.depth_in, 6), w0 = area / (pct * depth);
      res.add("st_tray_control", ref("tray_fill_control", ed), null,
        { area: area, pct: pct * 100, depth: depth, width: w0 });
      return w0;
    }
    var large = power.filter(function (c) { return cmilOf(c.size) >= CMIL_4_0; });
    var small = power.filter(function (c) { return cmilOf(c.size) < CMIL_4_0; }).concat(control);
    var sd = qtySum(large, cableOd), aS = qtySum(small, cableArea);
    var col = solid ? T.TRAY_A_COL3 : T.TRAY_A_COL1, k = solid ? T.TRAY_A_COL4_K : T.TRAY_A_COL2_K;
    var colName = solid ? ["3", "4"] : ["1", "2"], w;
    if (aS === 0) {
      var f = solid ? T.TRAY_SOLID_LARGE_PCT : 1;
      w = sd / f;
      res.add("st_tray_multi_large", ref("tray_fill_multi", ed), null, { sd: sd, pct: f * 100, width: w });
    } else if (sd === 0) {
      w = widthFor(col, aS);
      res.add("st_tray_multi_small", ref("tray_fill_multi", ed), null, { area: aS, col: colName[0], width: w });
    } else {
      w = Math.max(sd, widthFor(col, aS + k * sd));
      res.add("st_tray_multi_mixed", ref("tray_fill_multi", ed), null,
        { area: aS, sd: sd, k: k, col: colName[1], width: w });
    }
    return w;
  }
  function lvSingleWidth(cables, x, res) {
    var ed = x.edition;
    if (x.tray_type === "solid_bottom") res.warn("w_tray_single_solid", {});
    var small = cables.filter(function (c) { return cmilOf(c.size) < CMIL_1_0; });
    if (small.length) {
      var uniq = [];
      small.forEach(function (c) { if (uniq.indexOf(c.size) < 0) uniq.push(c.size); });
      res.warn("w_tray_single_min", { sizes: uniq.sort().join(", ") });
    }
    var s1000 = qtySum(cables.filter(function (c) { return cmilOf(c.size) >= 1000000; }), cableOd);
    var a250 = qtySum(cables.filter(function (c) { var m = cmilOf(c.size); return m >= 250000 && m < 1000000; }), cableArea);
    var anySmall = cables.some(function (c) { return cmilOf(c.size) <= CMIL_4_0; });
    var sdAll = qtySum(cables, cableOd), w = 0;
    if (anySmall) {
      w = Math.max(w, sdAll);
      res.add("st_tray_single_dia", ref("tray_fill_single", ed), null, { sd: sdAll });
    }
    if (a250 && s1000) {
      w = Math.max(w, s1000, widthFor(T.TRAY_B_COL1, a250 + T.TRAY_B_COL2_K * s1000));
      res.add("st_tray_single_mixed", ref("tray_fill_single", ed), null,
        { area: a250, sd: s1000, k: T.TRAY_B_COL2_K, width: w });
    } else if (a250) {
      w = Math.max(w, widthFor(T.TRAY_B_COL1, a250));
      res.add("st_tray_single_area", ref("tray_fill_single", ed), null, { area: a250, width: w });
    } else if (s1000 && !anySmall) {
      w = Math.max(w, s1000);
      res.add("st_tray_single_large", ref("tray_fill_single", ed), null, { sd: s1000 });
    }
    return w;
  }
  function trayAmpacity(c, x) {
    var spaced = x.arrangement === "spaced" && !x.covered, base, ft, fa, fc;
    if (c.kind === "lv_multi") {
      base = baseAmpacity(c.size, c.material, 90);
      if (base === null) return [null, {}];
      ft = tempFactor(x.ambient_c, 90); fa = cccFactor(c.n_cond);
      fc = x.covered ? T.TRAY_AMP_LV_MULTI_COVERED : 1;
      return [base * ft * fa * fc, { base: base, ft: ft, fa: fa, fc: fc, tbl: "310.16" }];
    }
    if (c.kind === "lv_single") {
      var tbl = c.material === "cu" ? T.AMPACITY_FREE_AIR_CU : T.AMPACITY_FREE_AIR_AL;
      if (!has(tbl, c.size)) return [null, {}];
      base = tbl[c.size][2];
      if (spaced) fc = 1;
      else fc = T.TRAY_AMP_LV_SINGLE[cmilOf(c.size) >= 600000 ? "ge600" : "1/0-500"][x.covered ? 1 : 0];
      ft = tempFactor(x.ambient_c, 90);
      return [base * ft * fc, { base: base, ft: ft, fa: 1, fc: fc, tbl: "310.17" }];
    }
    if (isMv(c)) {
      base = T.MV_AMPACITY_AIR_TYPICAL[c.material][c.size];
      if (base === undefined) return [null, {}];
      ft = Math.sqrt(Math.max(90 - x.ambient_c, 0) / 50);
      if (c.kind === "mv_single") { fc = spaced ? 1 : T.TRAY_AMP_MV_SINGLE[x.covered ? 1 : 0]; fa = 1; }
      else { fa = 0.8; fc = x.covered ? T.TRAY_AMP_MV_MULTI_COVERED : 1; }
      return [base * ft * fa * fc, { base: base, ft: ft, fa: fa, fc: fc, tbl: "315.60*" }];
    }
    return [null, {}];
  }
  function requiredWidth(x, res) {
    res = res || new Result("tray");
    var cables = x.cables.filter(function (c) { return c.qty > 0; });
    if (!cables.length) throw new CalcError("err_tray_empty", {});
    var sec = [];
    var lvm = cables.filter(function (c) { return c.kind === "lv_multi" || c.kind === "control"; });
    var lvs = cables.filter(function (c) { return c.kind === "lv_single"; });
    var mv = cables.filter(isMv);
    if (lvm.length) sec.push(["lv_multi", lvMultiWidth(lvm, x, res)]);
    if (lvs.length) sec.push(["lv_single", lvSingleWidth(lvs, x, res)]);
    if (mv.length) {
      var sd = qtySum(mv, cableOd);
      res.add("st_tray_mv", ref("tray_fill_mv", x.edition), null, { sd: sd });
      sec.push(["mv", sd]);
    }
    return [sum(sec.map(function (s) { return s[1]; })), sec, res];
  }
  function designTray(x) {
    var ed = x.edition, res = new Result("tray");
    var rw = requiredWidth(x, res), total = rw[0], sec = rw[1];
    var names = sec.map(function (s) { return s[0]; });
    var hasMv = names.indexOf("mv") >= 0;
    var hasLv = names.indexOf("lv_multi") >= 0 || names.indexOf("lv_single") >= 0;
    if (hasMv && hasLv) { res.add("st_tray_barrier", ref("tray_separation", ed), null, {}); res.warn("w_tray_mv_lv", {}); }
    if (sec.length > 1)
      res.add("st_tray_sum", "", null, { parts: sec.map(function (s) { return s[1].toFixed(2); }).join(" + "), width: total });
    var active = x.cables.filter(function (c) { return c.qty > 0; });
    var maxOd = Math.max.apply(null, active.map(cableOd));
    if (maxOd > x.depth_in) res.warn("w_tray_depth", { od: maxOd, depth: x.depth_in });
    if (active.some(odIsTypical)) res.warn("w_tray_od_typical", {});
    var nTrays = 1, width;
    if (x.width_in) {
      width = x.width_in;
      res.add("st_tray_check", names.indexOf("lv_multi") >= 0 ? ref("tray_fill_multi", ed) : "392.22",
        total <= width + EPS, { width: width, req: total, fill: 100 * total / width });
      if (T.TRAY_WIDTHS.indexOf(width) < 0) res.warn("w_tray_nonstd", { width: width });
    } else {
      width = null;
      for (var i = 0; i < T.TRAY_WIDTHS.length; i++) if (T.TRAY_WIDTHS[i] >= total - EPS) { width = T.TRAY_WIDTHS[i]; break; }
      if (width === null) {
        width = T.TRAY_WIDTHS[T.TRAY_WIDTHS.length - 1];
        nTrays = Math.ceil(total / width - EPS);
        res.warn("w_tray_multiple", { n: nTrays, req: total });
      }
      res.add("st_tray_select", "NEMA VE 1", null, { req: total, width: width, n: nTrays,
        fill: 100 * total / (width * nTrays) });
    }
    var ampRows = [];
    active.forEach(function (c) {
      var a = trayAmpacity(c, x);
      if (a[0] === null) return;
      var key = c.kind === "lv_multi" ? "tray_amp_lv_multi" : (c.kind === "lv_single" ? "tray_amp_lv_single" : "tray_amp_mv");
      var d = a[1];
      res.add("st_tray_amp", ref(key, ed), null, { name: c.name, size: sizeLabel(c.size), base: d.base,
        tbl: d.tbl, ft: d.ft, fa: d.fa, fc: d.fc, amps: a[0] });
      ampRows.push([c.name, c.size, a[0]]);
    });
    if (x.cables.some(isMv)) res.warn("w_tray_mv_amp_typical", {});
    if (x.cables.some(function (c) { return c.kind === "lv_single"; }))
      res.add("st_tray_single_note", ref("tray_single_min", ed), null, {});
    Object.assign(res.summary, { req_width: total, width: width, n_trays: nTrays,
      fill_pct: 100 * total / (width * nTrays),
      tray_text: (nTrays > 1 ? nTrays + " x " : "") + fmtG(width) + '" W x ' + fmtG(x.depth_in) + '" D',
      tray_type: x.tray_type, ampacities: ampRows });
    return res;
  }
  function maxCables(kind, size, width, o) {
    o = o || {};
    var x = trayInput({ tray_type: o.tray_type || "ladder", depth_in: o.depth_in || 4 });
    var c = trayCable({ kind: kind, size: size, n_cond: o.n_cond || 3, material: o.material || "cu",
      ins_level: o.ins_level || "25kV_133", od_in: o.od_in || 0, qty: 1 });
    if (kind === "lv_single" && cmilOf(size) < CMIL_1_0) return 0;
    if (kind === "lv_single" && x.tray_type === "solid_bottom") return 0;
    try { cableOd(c); } catch (e) { if (e instanceof CalcError) return null; throw e; }
    if (cableOd(c) > x.depth_in) return 0;
    x.cables = [c];
    var lo = 0, hi = 999;
    while (lo < hi) {
      var mid = Math.floor((lo + hi + 1) / 2);
      c.qty = mid;
      if (requiredWidth(x, new Result("tmp"))[0] <= width + EPS) lo = mid; else hi = mid - 1;
    }
    return lo;
  }
  function capacitySizes(kind) {
    if (kind === "lv_multi") return T.SIZES.filter(function (s) { return has(T.TC_3C_OD_TYPICAL, s); });
    if (kind === "lv_single") return T.SIZES.filter(function (s) { return has(T.WIRE_AREA.XHHW, s) && cmilOf(s) >= CMIL_1_0; });
    if (kind === "mv_single" || kind === "mv_multi") return T.MV_SIZES.slice();
    return ["-"];
  }
  function capacityTable(kind, sizes, widths, o) {
    sizes = sizes || capacitySizes(kind);
    widths = widths || T.TRAY_WIDTHS;
    return sizes.map(function (s) {
      return [s, widths.map(function (w) { return [w, maxCables(kind, s, w, o)]; })];
    });
  }

  // ------------------------------------------------------------------
  // text: Python str.format subset + translation
  // ------------------------------------------------------------------
  function group(intStr) { return intStr.replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  // toFixed with Python's rounding: exact binary ties go to the even digit
  function toFixedPy(v, n) {
    if (!isFinite(v) || Math.abs(v) >= 1e21) return v.toFixed(n);
    var long = v.toFixed(Math.min(n + 25, 100));
    var dot = long.indexOf(".");
    var tail = long.slice(dot + 1 + n);
    if (/^50*$/.test(tail)) {
      var base = n ? long.slice(0, dot + 1 + n) : long.slice(0, dot);
      var last = parseInt(base.charAt(base.length - 1), 10);
      if (last % 2 === 0) return base;
      var step = Math.pow(10, -n) * (v < 0 ? -1 : 1);
      return (parseFloat(base) + step).toFixed(n);
    }
    return v.toFixed(n);
  }
  function fmtG(v) {  // Python format(v, "g"): 6 significant digits
    if (typeof v !== "number") return String(v);
    if (v === 0) return "0";
    if (!isFinite(v)) return String(v);
    var exp = Math.floor(Math.log10(Math.abs(v)));
    var r = parseFloat(toFixedPy(v / Math.pow(10, exp), 5)) * Math.pow(10, exp);
    if (Math.abs(r) >= Math.pow(10, exp + 1)) exp += 1;
    if (exp < -4 || exp >= 6) {
      var mant = toFixedPy(v / Math.pow(10, exp), 5).replace(/\.?0+$/, "");
      return mant + "e" + (exp < 0 ? "-" : "+") + (Math.abs(exp) < 10 ? "0" : "") + Math.abs(exp);
    }
    var s = toFixedPy(v, Math.max(0, 5 - exp));
    if (s.indexOf(".") >= 0) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s;
  }
  function fmtValue(v, spec) {
    if (v === null || v === undefined) return "None";
    if (!spec) {
      if (typeof v === "boolean") return v ? "True" : "False";
      return String(v);
    }
    var m = /^(,)?(?:\.(\d+))?([fgd])?$/.exec(spec);
    if (!m || typeof v !== "number") return String(v);
    var comma = !!m[1], prec = m[2], type = m[3];
    var s;
    if (type === "g") s = fmtG(v);
    else if (type === "f") s = toFixedPy(v, prec === undefined ? 6 : parseInt(prec, 10));
    else s = String(v);
    if (comma) {
      var neg = s[0] === "-", body = neg ? s.slice(1) : s, parts = body.split(".");
      s = (neg ? "-" : "") + group(parts[0]) + (parts.length > 1 ? "." + parts[1] : "");
    }
    if (s === "-0" || /^-0\.0*$/.test(s)) s = s.slice(1);
    return s;
  }
  function pyFormat(text, params) {
    return text.replace(/\{(\w+)(?::([^}]*))?\}/g, function (all, name, spec) {
      if (!has(params, name)) throw new Error("missing " + name);
      return fmtValue(params[name], spec);
    });
  }
  function tr(key, lang, params) {
    var pair = DATA.text[key];
    var text = pair ? (lang === "zh" ? pair[1] : pair[0]) : key;
    if (params && Object.keys(params).length) {
      var p2 = {};
      Object.keys(params).forEach(function (k) {
        var v = params[k];
        p2[k] = (typeof v === "string" && has(DATA.text, "opt_" + v)) ? tr("opt_" + v, lang) : v;
      });
      try { return pyFormat(text, p2); } catch (e) { return text + " " + JSON.stringify(params); }
    }
    return text;
  }
  function opt(code, lang) { return has(DATA.text, "opt_" + code) ? tr("opt_" + code, lang) : code; }

  var SUMMARY_FIELDS = {
    general: [["i_load", "s_i_load", "{v:.1f} A"], ["i_design", "s_i_design", "{v:.1f} A"],
      ["ocpd", "s_ocpd", "{v} A"], ["switch", "s_switch", "{v} A"], ["wire_text", "s_wire", "{v}"],
      ["busway_text", "s_busway", "{v}"], ["ampacity", "s_ampacity", "{v:.1f} A"],
      ["bw_ampacity", "s_bw_ampacity", "{v:.0f} A"], ["sccr_ka", "s_sccr", "{v:g} kA"],
      ["vd_pct", "s_vd", "{v:.2f} %"]],
    motor: [["flc", "s_flc", "{v} A"], ["i_design", "s_i_design", "{v:.1f} A"],
      ["ocpd", "s_ocpd_motor", "{v:.0f} A"], ["overload", "s_overload", "{v:.1f} A"],
      ["switch", "s_switch", "{v} A"], ["wire_text", "s_wire", "{v}"],
      ["ampacity", "s_ampacity", "{v:.1f} A"], ["vd_pct", "s_vd", "{v:.2f} %"]],
    transformer: [["i_pri", "s_i_pri", "{v:.1f} A"], ["i_sec", "s_i_sec", "{v:.1f} A"],
      ["isc_ka", "s_isc", "{v:.1f} kA"], ["pri_ocpd", "s_pri_ocpd", "{v} A"],
      ["pri_ocpd_max", "s_pri_ocpd_max", "{v} A"], ["sec_ocpd", "s_sec_ocpd", "{v} A"]],
    mv_cable: [["i_load", "s_i_load", "{v:.1f} A"], ["i_design", "s_i_design", "{v:.1f} A"],
      ["wire_text", "s_mv_cable", "{v}"], ["ampacity", "s_ampacity", "{v} A"],
      ["sc_cmil", "s_sc_cmil", "{v:,.0f} cmil"], ["jam", "s_jam", "{v:.2f}"]],
    tray: [["tray_text", "s_tray", "{v}"], ["req_width", "s_req_width", "{v:.2f} in"],
      ["fill_pct", "s_tray_fill", "{v:.0f} %"]]
  };
  SUMMARY_FIELDS.feeder = SUMMARY_FIELDS.primary = SUMMARY_FIELDS.secondary = SUMMARY_FIELDS.general;

  function summaryRows(res, lang) {
    return (SUMMARY_FIELDS[res.kind] || []).filter(function (f) {
      var v = res.summary[f[0]];
      return v !== null && v !== undefined && v !== "-";
    }).map(function (f) { return [tr(f[1], lang), pyFormat(f[2], { v: res.summary[f[0]] }), f[0]]; });
  }
  function stepRows(res, lang) {
    return res.steps.map(function (s) {
      return { text: tr(s.key, lang, s.params), ref: s.ref, ok: s.ok };
    });
  }
  function warningRows(res, lang) {
    return res.warnings.map(function (w) { return tr(w[0], lang, w[1]); });
  }
  function f2(v, n) { return fmtValue(v, "." + n + "f"); }
  function loadSummaryRows(c, lang) {
    var ph = Object.keys(c.phase_amps).map(function (p) { return p + ": " + f2(c.phase_amps[p], 1) + " A"; }).join(" / ");
    return [
      [tr("lc_connected", lang), f2(c.connected.kw, 2) + " kW, " + f2(c.connected.kvar, 2) + " kvar, " +
        f2(c.connected.kva_arith, 2) + " kVA, PF " + f2(c.connected.pf, 3)],
      [tr("lc_demand", lang), f2(c.demand.kw, 2) + " kW, " + f2(c.demand.kvar, 2) + " kvar, " +
        f2(c.demand.kva, 2) + " kVA, PF " + f2(c.demand.pf, 3)],
      [tr("lc_overall_df", lang), f2(c.demand_factor_overall, 3)],
      [tr("lc_coincident", lang), f2(c.coincident.kw, 2) + " kW, " + f2(c.coincident.kva, 2) + " kVA (÷ " +
        f2(c.coincident.diversity, 2) + ") → " + f2(c.i_demand, 1) + " A"],
      [tr("lc_cont", lang), f2(c.continuous_kva, 2) + " kVA"],
      [tr("lc_largest_motor", lang), f2(c.largest_motor_kva, 2) + " kVA"],
      [tr("lc_design", lang), f2(c.design_kva, 2) + " kVA → " + f2(c.i_design, 1) + " A"],
      [tr("lc_phase", lang), ph],
      [tr("lc_imbalance", lang), f2(c.imbalance_pct, 1) + " %"],
      [tr("lc_cap", lang), f2(c.cap_kvar, 1) + " kvar"]
    ];
  }
  function loadNotes(c, lang) {
    return c.notes.map(function (n) { return tr(n[0], lang, n[2]) + " (" + n[1] + ")"; });
  }

  var API = {
    DATA: DATA, T: T, CalcError: CalcError, Result: Result, WIRING: WIRING,
    ref: ref, sizeLabel: sizeLabel, cmilOf: cmilOf, pyRound: pyRound,
    nextStdOcpd: nextStdOcpd, maxStdOcpd: maxStdOcpd, nextSwitch: nextSwitch,
    tempFactor: tempFactor, cccFactor: cccFactor, egcSize: egcSize, motorFlc: motorFlc,
    voltageDrop: voltageDrop, selectConduit: selectConduit, scMinCmil: scMinCmil,
    wiringInput: wiringInput, mvInput: mvInput, transformerInput: transformerInput,
    loadItem: loadItem, panelInput: panelInput, trayCable: trayCable, trayInput: trayInput,
    sizeConductors: sizeConductors, sizeBusway: sizeBusway, designGeneral: designGeneral, designMotor: designMotor,
    designMvCable: designMvCable, designTransformer: designTransformer,
    loadKva: loadKva, loadKw: loadKw, loadKvar: loadKvar, loadAmps: loadAmps,
    calculateLoads: calculateLoads, sizeFeeder: sizeFeeder,
    cableOd: cableOd, cableArea: cableArea, odIsTypical: odIsTypical,
    requiredWidth: requiredWidth, designTray: designTray, trayAmpacity: trayAmpacity,
    maxCables: maxCables, capacityTable: capacityTable, capacitySizes: capacitySizes,
    tr: tr, opt: opt, pyFormat: pyFormat, fmtG: fmtG, summaryRows: summaryRows,
    stepRows: stepRows, warningRows: warningRows, loadSummaryRows: loadSummaryRows,
    loadNotes: loadNotes
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else root.NECALC = API;
})(typeof self !== "undefined" ? self : this);
