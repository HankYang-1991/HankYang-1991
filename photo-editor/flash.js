/* 暗房 Darkroom — compact-camera flash looks (閃光燈美圖).
   Emulates direct on-camera flash (bright subject, dark falloff, soft blown highlights)
   combined with each camera's colour rendering, plus skin smoothing and a 7-segment date stamp.
   These are look-alike styles, not official profiles of any manufacturer. */
(() => {
'use strict';
const D = window.Darkroom;
const { $, $$, clamp } = D;

/* ---------- presets ----------
   flash 0..1 strength · reach 0..1 light radius · bgDark 0..1 background fall-off · flashTemp + = cooler flash
   temp/tint −1..1 white balance · contrast −0.5..1 · fade black lift · sat/vib −1..1
   mix 3×3 channel mixer · split amount with shadow/highlight tints · mono · grain · vignette · bloom · soft
   smooth/white skin retouch · date stamp on by default */
const PRESETS = [
  { id: 'gr-pos', name: 'GR 正片', brand: '理光 Ricoh', flash: .55, reach: .45, bgDark: .45, flashTemp: .2, temp: .08, tint: .06, contrast: .45, fade: .02, sat: .25, vib: .15,
    split: .07, sh: [0, .02, .06], hl: [.06, .03, 0], grain: .25, vignette: .35, bloom: .15, soft: 0, smooth: .2, white: .1 },
  { id: 'gr-neg', name: 'GR 負片', brand: '理光 Ricoh', flash: .5, reach: .5, bgDark: .35, flashTemp: .1, temp: -.02, tint: -.02, contrast: -.1, fade: .08, sat: -.25, vib: 0,
    split: .1, sh: [-.02, .04, .06], hl: [.05, .03, 0], grain: .3, vignette: .2, bloom: .1, soft: 0, smooth: .2, white: .1 },
  { id: 'gr-mono', name: 'GR 高對比黑白', brand: '理光 Ricoh', mono: true, flash: .7, reach: .4, bgDark: .7, flashTemp: 0, temp: 0, tint: 0, contrast: .9, fade: 0, sat: 0, vib: 0,
    split: 0, grain: .55, vignette: .6, bloom: .1, soft: 0, smooth: .15, white: 0 },
  { id: 'canon-ccd', name: 'CCD 冷白閃', brand: 'Canon IXUS 風', flash: .75, reach: .55, bgDark: .5, flashTemp: .5, temp: -.18, tint: .02, contrast: .25, fade: 0, sat: .2, vib: .2,
    mix: [[1.08, -.06, -.02], [-.02, 1.02, 0], [-.04, -.04, 1.12]], split: .05, sh: [0, 0, .05], hl: [.02, .02, .04], grain: .12, vignette: .1, bloom: .35, soft: .25, smooth: .35, white: .25, date: true },
  { id: 'canon-warm', name: '暖膚閃光', brand: 'Canon G7X 風', flash: .45, reach: .6, bgDark: .25, flashTemp: -.1, temp: .12, tint: .03, contrast: .15, fade: .02, sat: .05, vib: .1,
    split: .06, sh: [.02, 0, .02], hl: [.06, .03, .01], grain: .08, vignette: .15, bloom: .2, soft: .15, smooth: .5, white: .3 },
  { id: 'fuji-cc', name: 'Classic Chrome', brand: '富士 Fujifilm 風', flash: .45, reach: .5, bgDark: .45, flashTemp: .1, temp: .02, tint: -.02, contrast: .35, fade: .03, sat: -.35, vib: 0,
    mix: [[1, 0, 0], [.03, .92, .05], [0, .12, .82]], split: .1, sh: [-.02, .02, .03], hl: [.04, .03, 0], grain: .2, vignette: .25, bloom: .08, soft: 0, smooth: .2, white: .1 },
  { id: 'fuji-neg', name: 'Classic Neg', brand: '富士 Fujifilm 風', flash: .5, reach: .5, bgDark: .4, flashTemp: .15, temp: -.04, tint: .04, contrast: .5, fade: .06, sat: -.05, vib: 0,
    mix: [[1.02, -.04, .02], [.02, .9, .08], [-.02, .12, .9]], split: .14, sh: [-.03, .03, .05], hl: [.05, 0, .03], grain: .25, vignette: .25, bloom: .1, soft: 0, smooth: .2, white: .1 },
  { id: 'fuji-qs', name: '拋棄式相機', brand: '富士 QuickSnap 風', flash: .85, reach: .4, bgDark: .7, flashTemp: -.1, temp: .14, tint: -.08, contrast: .4, fade: .05, sat: .15, vib: .1,
    split: .1, sh: [0, .04, 0], hl: [.05, .03, 0], grain: .6, vignette: .55, bloom: .25, soft: .3, smooth: .15, white: .1, date: true },
  { id: 'sony-cyber', name: 'Y2K 數位藍調', brand: 'Sony Cyber-shot 風', flash: .7, reach: .5, bgDark: .55, flashTemp: .4, temp: -.25, tint: -.02, contrast: .3, fade: 0, sat: .3, vib: .2,
    mix: [[1.04, -.02, -.02], [0, 1.04, -.04], [-.06, 0, 1.1]], split: .06, sh: [0, .01, .06], hl: [0, .02, .04], grain: .1, vignette: .15, bloom: .3, soft: .2, smooth: .35, white: .3, date: true },
  { id: 'contax', name: 'T2 底片閃光', brand: 'Contax T2 風', flash: .5, reach: .55, bgDark: .4, flashTemp: -.05, temp: .1, tint: .02, contrast: .4, fade: .04, sat: .1, vib: .05,
    split: .08, sh: [.01, .02, .04], hl: [.07, .04, .01], grain: .3, vignette: .3, bloom: .12, soft: .05, smooth: .25, white: .15 },
];

/* user-adjustable controls (0..100 sliders mapped onto the preset's values) */
const CONTROLS = [
  ['amount', '濾鏡濃度', 100], ['flash', '閃光強度'], ['reach', '閃光範圍'], ['bgDark', '背景壓暗'],
  ['smooth', '美肌'], ['white', '美白'], ['bloom', '光暈'], ['grain', '顆粒'],
];

let current = null;         // selected preset
let values = {};            // slider values 0..1
let center = null;          // flash centre in 0..1 doc coords, null = auto
let previewCanvas = null, srcKey = '', srcSmall = null;
let queued = false;

/* ================= image processing ================= */
const sCurve = (v, k) => v < 0.5 ? 0.5 * Math.pow(2 * v, k) : 1 - 0.5 * Math.pow(2 * (1 - v), k);
function shoulder(v) { return v < 0.8 ? v : 0.8 + 0.2 * (1 - Math.exp(-(v - 0.8) / 0.2)); }

function skinRetouch(d, W, Hh, smooth, white) {
  if (smooth <= 0 && white <= 0) return;
  const n = W * Hh, skin = new Float32Array(n);
  let any = false;
  for (let i = 0, k = 0; i < n; i++, k += 4) {
    const r = d[k], g = d[k + 1], b = d[k + 2];
    const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
    const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;
    // soft membership around the classic YCbCr skin box (Cb 77–127, Cr 133–173)
    const m = clamp(Math.min(cb - 72, 132 - cb, cr - 128, 178 - cr) / 8, 0, 1) * clamp((r - 40) / 30, 0, 1);
    skin[i] = m; if (m > 0) any = true;
  }
  if (!any) return;
  if (smooth > 0) {
    const bl = new Uint8ClampedArray(d);
    D.gaussBlur(bl, W, Hh, Math.max(1.5, Math.max(W, Hh) / 260));
    for (let i = 0, k = 0; i < n; i++, k += 4) {
      if (!skin[i]) continue;
      // only smooth where the local difference is small: pores, not eyes or lips
      const diff = (Math.abs(d[k] - bl[k]) + Math.abs(d[k + 1] - bl[k + 1]) + Math.abs(d[k + 2] - bl[k + 2])) / 3;
      const w = skin[i] * smooth * clamp(1 - diff / 28, 0, 1) * 0.9;
      d[k] += (bl[k] - d[k]) * w; d[k + 1] += (bl[k + 1] - d[k + 1]) * w; d[k + 2] += (bl[k + 2] - d[k + 2]) * w;
    }
  }
  if (white > 0) {
    for (let i = 0, k = 0; i < n; i++, k += 4) {
      const w = skin[i] * white * 0.3;
      if (!w) continue;
      d[k] += (255 - d[k]) * w * 0.9; d[k + 1] += (255 - d[k + 1]) * w; d[k + 2] += (255 - d[k + 2]) * w;
    }
  }
}

function processLook(img, p, v, ctr) {
  const d = img.data, W = img.width, Hh = img.height, M = Math.max(W, Hh);
  const orig = v.amount < 1 ? new Uint8ClampedArray(d) : null;
  skinRetouch(d, W, Hh, v.smooth, v.white);

  const cx = ctr ? ctr.x : 0.5, cy = ctr ? ctr.y : 0.42;
  const r = 0.15 + v.reach * 0.35;
  const fl = v.flash, bg = v.bgDark;
  const ft = p.flashTemp || 0, fc = [1 - 0.05 * ft, 1, 1 + 0.07 * ft];
  const k = 1 + (p.contrast || 0);
  const fade = p.fade || 0, sat = 1 + (p.sat || 0), vib = p.vib || 0;
  const t = p.temp || 0, tn = p.tint || 0;
  const mix = p.mix, mono = !!p.mono;
  const split = p.split || 0, sh = p.sh || [0, 0, 0], hl = p.hl || [0, 0, 0];
  const vig = p.vignette || 0, grain = v.grain;
  const bloom = new Float32Array(v.bloom > 0 ? W * Hh : 0);

  for (let y = 0, i = 0; y < Hh; y++) {
    const ny = (y / Hh - cy) * Hh / M, vy = (y / Hh - 0.5) * Hh / M;
    for (let x = 0; x < W; x++, i++) {
      const q = i * 4;
      if (d[q + 3] === 0) continue;
      let R = d[q] / 255, G = d[q + 1] / 255, B = d[q + 2] / 255;
      // direct flash: inverse-square-ish light around the subject, ambient drops away behind
      const nx = (x / W - cx) * W / M;
      const dd = Math.hypot(nx, ny) / r;
      const L = 1 / Math.pow(1 + dd * dd, 2);
      const gain = (1 + fl * 0.45 * L) * (1 - bg * 0.85 * (1 - L));
      const fill = fl * 0.04 * L;
      R = R * gain * fc[0] + fill; G = G * gain * fc[1] + fill; B = B * gain * fc[2] + fill;
      R = shoulder(R); G = shoulder(G); B = shoulder(B);
      // white balance
      R += t * 0.07 + tn * 0.03; G -= tn * 0.05; B += -t * 0.07 + tn * 0.03;
      if (mix) { const r0 = R, g0 = G, b0 = B; R = mix[0][0] * r0 + mix[0][1] * g0 + mix[0][2] * b0; G = mix[1][0] * r0 + mix[1][1] * g0 + mix[1][2] * b0; B = mix[2][0] * r0 + mix[2][1] * g0 + mix[2][2] * b0; }
      let lum = 0.2126 * R + 0.7152 * G + 0.0722 * B;
      if (mono) { const m = 0.3 * R + 0.62 * G + 0.08 * B; R = G = B = m; }
      else {
        let f = sat;
        if (vib) { const mx = Math.max(R, G, B), mn = Math.min(R, G, B); f *= 1 + vib * (1 - clamp(mx - mn, 0, 1)); }
        R = lum + (R - lum) * f; G = lum + (G - lum) * f; B = lum + (B - lum) * f;
      }
      R = sCurve(clamp(R, 0, 1), k); G = sCurve(clamp(G, 0, 1), k); B = sCurve(clamp(B, 0, 1), k);
      R = fade + R * (1 - fade * 1.2); G = fade + G * (1 - fade * 1.2); B = fade + B * (1 - fade * 1.2);
      if (split && !mono) {
        lum = 0.2126 * R + 0.7152 * G + 0.0722 * B;
        const s = (1 - lum) * (1 - lum) * split * 6, h = lum * lum * split * 6;
        R += sh[0] * s + hl[0] * h; G += sh[1] * s + hl[1] * h; B += sh[2] * s + hl[2] * h;
      }
      if (vig) {
        const vd = Math.hypot((x / W - 0.5) * W / M, vy) / 0.62;
        const fv = 1 - vig * Math.pow(clamp((vd - 0.35) / 0.65, 0, 1), 1.5);
        R *= fv; G *= fv; B *= fv;
      }
      if (grain) { const g = (Math.random() - 0.5) * grain * 0.16; R += g; G += g; B += g; }
      if (bloom.length) { const l = 0.2126 * R + 0.7152 * G + 0.0722 * B; bloom[i] = Math.max(0, l - 0.72) / 0.28; }
      d[q] = R * 255; d[q + 1] = G * 255; d[q + 2] = B * 255;
    }
  }
  if (bloom.length) {
    // highlight halation: blur the bright parts and screen them back on (CCD / film glow)
    const glow = new Uint8ClampedArray(W * Hh * 4);
    for (let i = 0; i < bloom.length; i++) { const k4 = i * 4; glow[k4] = d[k4] * bloom[i]; glow[k4 + 1] = d[k4 + 1] * bloom[i]; glow[k4 + 2] = d[k4 + 2] * bloom[i]; glow[k4 + 3] = 255; }
    D.gaussBlur(glow, W, Hh, M * 0.018);
    const a = v.bloom * 1.1;
    for (let k4 = 0; k4 < d.length; k4 += 4) for (let c = 0; c < 3; c++) d[k4 + c] = 255 - (255 - d[k4 + c]) * (255 - glow[k4 + c] * a) / 255;
  }
  if (p.soft) {
    const bl = new Uint8ClampedArray(d);
    D.gaussBlur(bl, W, Hh, M / 900);
    for (let k4 = 0; k4 < d.length; k4 += 4) for (let c = 0; c < 3; c++) d[k4 + c] += (bl[k4 + c] - d[k4 + c]) * p.soft;
  }
  if (orig) for (let k4 = 0; k4 < d.length; k4 += 4) for (let c = 0; c < 3; c++) d[k4 + c] = orig[k4 + c] + (d[k4 + c] - orig[k4 + c]) * v.amount;
}

/* ---------- 7-segment date stamp, the way compact cameras printed it ---------- */
const SEG = { 0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc', 5: 'afgcd', 6: 'afgedc', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg', '-': 'g' };
function drawDate(ctx, W, Hh, text) {
  const h = Math.max(10, Math.min(W, Hh) * 0.045), w = h * 0.52, th = h * 0.12, gap = h * 0.22;
  let width = 0;
  for (const ch of text) width += ch === ' ' ? w * 0.7 : ch === "'" ? h * 0.18 : w + gap;
  let x = W - Math.min(W, Hh) * 0.06 - width, y = Hh - Math.min(W, Hh) * 0.06 - h;
  ctx.save();
  ctx.fillStyle = '#ffa23a';
  ctx.shadowColor = 'rgba(255,96,16,.95)'; ctx.shadowBlur = h * 0.35;
  ctx.globalAlpha = 0.92;
  const seg = (sx, sy, horiz) => {
    const L = horiz ? w : h / 2, t2 = th / 2;
    ctx.beginPath();
    if (horiz) { ctx.moveTo(sx + t2, sy); ctx.lineTo(sx + t2 * 2, sy - t2); ctx.lineTo(sx + L - t2 * 2, sy - t2); ctx.lineTo(sx + L - t2, sy); ctx.lineTo(sx + L - t2 * 2, sy + t2); ctx.lineTo(sx + t2 * 2, sy + t2); }
    else { ctx.moveTo(sx, sy + t2); ctx.lineTo(sx + t2, sy + t2 * 2); ctx.lineTo(sx + t2, sy + L - t2 * 2); ctx.lineTo(sx, sy + L - t2); ctx.lineTo(sx - t2, sy + L - t2 * 2); ctx.lineTo(sx - t2, sy + t2 * 2); }
    ctx.closePath(); ctx.fill();
  };
  for (const ch of text) {
    if (ch === ' ') { x += w * 0.7; continue; }
    if (ch === "'") { ctx.fillRect(x, y, th, h * 0.28); x += h * 0.18; continue; }
    const on = SEG[ch];
    if (on) {
      const sk = h * 0.05; // slight italic like the real LCD imprint
      const X = (xx, yy) => xx + sk * (1 - (yy - y) / h);
      if (on.includes('a')) seg(X(x, y), y, true);
      if (on.includes('g')) seg(X(x, y + h / 2), y + h / 2, true);
      if (on.includes('d')) seg(X(x, y + h), y + h, true);
      if (on.includes('f')) seg(X(x, y), y, false);
      if (on.includes('b')) seg(X(x + w, y), y, false);
      if (on.includes('e')) seg(X(x, y + h / 2), y + h / 2, false);
      if (on.includes('c')) seg(X(x + w, y + h / 2), y + h / 2, false);
    }
    x += w + gap;
  }
  ctx.restore();
}
function todayStamp() { const n = new Date(); return `'${String(n.getFullYear()).slice(2)} ${n.getMonth() + 1} ${String(n.getDate()).padStart(2, '0')}`; }

/* ================= preview / apply ================= */
function settings() {
  const v = {};
  CONTROLS.forEach(([k]) => { v[k] = values[k]; });
  return v;
}
function renderLook(srcCanvas, scale) {
  const W = Math.max(1, Math.round(srcCanvas.width * scale)), Hh = Math.max(1, Math.round(srcCanvas.height * scale));
  const c = D.makeCanvas(W, Hh), cx = c.getContext('2d', { willReadFrequently: true });
  cx.imageSmoothingQuality = 'high';
  cx.drawImage(srcCanvas, 0, 0, W, Hh);
  const img = cx.getImageData(0, 0, W, Hh);
  processLook(img, current, settings(), center);
  cx.putImageData(img, 0, 0);
  if ($('#flashDate').checked) drawDate(cx, W, Hh, $('#flashDateText').value || todayStamp());
  return c;
}
function queuePreview() { if (!queued) { queued = true; requestAnimationFrame(runPreview); } }
function runPreview() {
  queued = false;
  if (!current) return;
  const l = D.activeLayer();
  const scale = Math.min(1, 1400 / Math.max(l.canvas.width, l.canvas.height));
  const look = renderLook(l.canvas, scale);
  if (!previewCanvas || previewCanvas.width !== l.canvas.width || previewCanvas.height !== l.canvas.height) previewCanvas = D.makeCanvas(l.canvas.width, l.canvas.height);
  const pc = previewCanvas.getContext('2d');
  pc.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
  pc.imageSmoothingQuality = 'high';
  pc.drawImage(look, 0, 0, previewCanvas.width, previewCanvas.height);
  D.S.preview = previewCanvas;
  D.setPreviewOwner({ apply });
  D.render();
}
function cancel() {
  if (D.S.preview === previewCanvas) D.S.preview = null;
  D.setPreviewOwner(null);
  current = null;
  $$('#flashGrid button').forEach(b => b.classList.remove('on'));
  $('#flashCtl').hidden = true;
  D.render();
}
function apply() {
  if (!current) return;
  const l = D.activeLayer();
  const look = renderLook(l.canvas, 1);
  D.setPreviewOwner(null);
  if (D.S.preview === previewCanvas) D.S.preview = null;
  l.ctx.clearRect(0, 0, l.canvas.width, l.canvas.height);
  l.ctx.drawImage(look, 0, 0);
  const name = current.name;
  current = null;
  $$('#flashGrid button').forEach(b => b.classList.remove('on'));
  $('#flashCtl').hidden = true;
  D.touch(l); D.commit('閃光：' + name);
  thumbsKey = ''; requestAnimationFrame(buildThumbs);
  D.toast(`已套用「${name}」，可用復原撤銷`);
}

function choose(id) {
  // switching style keeps the user's position; sliders reset to the new style's defaults
  if (D.S.preview && D.S.preview !== previewCanvas) D.commitAdjustIfAny(); // bake a pending adjustment first
  current = PRESETS.find(p => p.id === id);
  values = { amount: 1, flash: current.flash, reach: current.reach, bgDark: current.bgDark, smooth: current.smooth, white: current.white, bloom: current.bloom, grain: current.grain };
  CONTROLS.forEach(([k]) => { const i = $('#fl-' + k); i.value = Math.round(values[k] * 100); $('#out-fl-' + k).textContent = i.value; });
  $('#flashDate').checked = !!current.date;
  $$('#flashGrid button').forEach(b => b.classList.toggle('on', b.dataset.id === id));
  $('#flashCtl').hidden = false;
  $('#flashName').textContent = `${current.name} · ${current.brand}`;
  queuePreview();
}

/* ================= UI ================= */
function buildUI() {
  const grid = $('#flashGrid');
  PRESETS.forEach(p => {
    const b = document.createElement('button');
    b.dataset.id = p.id;
    b.innerHTML = `<canvas width="120" height="120"></canvas><span>${p.name}</span><small>${p.brand}</small>`;
    b.addEventListener('click', () => choose(p.id));
    grid.appendChild(b);
  });
  const box = $('#flashSliders');
  CONTROLS.forEach(([k, label]) => {
    const row = document.createElement('label'); row.className = 'row';
    row.innerHTML = `<span>${label}</span><input type="range" id="fl-${k}" min="0" max="100" value="50"><output id="out-fl-${k}">50</output>`;
    box.appendChild(row);
    const inp = $('input', row);
    inp.addEventListener('input', () => { values[k] = +inp.value / 100; $('#out-fl-' + k).textContent = inp.value; queuePreview(); });
  });
  $('#flashDateText').value = todayStamp();
  $('#flashDate').addEventListener('change', queuePreview);
  $('#flashDateText').addEventListener('input', queuePreview);
  $('#flashApply').addEventListener('click', apply);
  $('#flashCancel').addEventListener('click', cancel);
  $('#flashPick').addEventListener('click', () => {
    D.toast('點一下照片上的主體（例如臉）');
    if (D.isTouch) document.getElementById('panel').classList.remove('open'), document.getElementById('scrim').hidden = true;
    D.pickPoint(p => {
      center = { x: clamp(p.x / D.S.w, 0, 1), y: clamp(p.y / D.S.h, 0, 1) };
      $('#flashPos').textContent = `指定（${Math.round(center.x * 100)}%, ${Math.round(center.y * 100)}%）`;
      queuePreview();
      D.toast('閃光位置已更新');
    });
  });
  $('#flashAuto').addEventListener('click', () => { center = null; $('#flashPos').textContent = '自動（畫面中央）'; queuePreview(); });
}
let thumbsKey = '';
function buildThumbs() {
  const l = D.activeLayer();
  if (!l) return;
  const key = l.id + ':' + l.ver;
  if (key === thumbsKey) return;
  thumbsKey = key;
  const t = D.makeCanvas(120, 120), tc = t.getContext('2d', { willReadFrequently: true });
  const s = Math.max(120 / l.canvas.width, 120 / l.canvas.height), sw = 120 / s, sh = 120 / s;
  tc.drawImage(l.canvas, (l.canvas.width - sw) / 2, (l.canvas.height - sh) / 2, sw, sh, 0, 0, 120, 120);
  const base = tc.getImageData(0, 0, 120, 120);
  $$('#flashGrid button').forEach(b => {
    const p = PRESETS.find(x => x.id === b.dataset.id);
    const img = new ImageData(new Uint8ClampedArray(base.data), 120, 120);
    processLook(img, p, { amount: 1, flash: p.flash, reach: p.reach, bgDark: p.bgDark, smooth: 0, white: 0, bloom: p.bloom, grain: p.grain }, null);
    b.querySelector('canvas').getContext('2d').putImageData(img, 0, 0);
  });
}

buildUI();
document.addEventListener('darkroom:tab', e => {
  if (e.detail === 'flash') requestAnimationFrame(buildThumbs);
  else if (current && D.S.preview === previewCanvas) apply();   // leaving the tab keeps the look
});
// keep the preview following the layer if the user switches layers or undoes
$('#layerList').addEventListener('click', () => { thumbsKey = ''; if (current) queuePreview(); });

// expose for the video editor and tests
D.flashLooks = { PRESETS, processLook, drawDate };
})();
