/* 暗房 Darkroom — layer-based photo editor for phone and desktop.
   Plain JavaScript + Canvas 2D, no build step. */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const isTouch = matchMedia('(pointer: coarse)').matches;
const MAX_SIDE = isTouch ? 4096 : 8192;

const stage = $('#stage');
const view = $('#view');
const vctx = view.getContext('2d');

/* ================= state ================= */
let verSeq = 0, uidSeq = 0;
const S = {
  w: 0, h: 0, layers: [], active: 0,
  zoom: 1, panX: 0, panY: 0,
  tool: 'brush',
  color: '#f0a742', size: 24, opacity: 100, hardness: 80,
  shape: 'rect', shapeFill: false, tolerance: 32,
  crop: null, cropRatio: 'free',
  stroke: null,     // live stroke/shape canvas for the active layer
  preview: null,    // adjustment preview canvas for the active layer
  cursor: null,
};

const TOOL_NAMES = { move: '移動', hand: '平移', crop: '裁切', brush: '筆刷', eraser: '橡皮擦', shape: '形狀', fill: '油漆桶', text: '文字', eyedropper: '滴管' };
const BLENDS = [
  ['source-over', '正常'], ['multiply', '色彩增值'], ['screen', '濾色'], ['overlay', '覆蓋'],
  ['darken', '變暗'], ['lighten', '變亮'], ['color-dodge', '加亮顏色'], ['color-burn', '加深顏色'],
  ['hard-light', '實光'], ['soft-light', '柔光'], ['difference', '差異化'], ['exclusion', '排除'],
  ['hue', '色相'], ['saturation', '飽和度'], ['color', '顏色'], ['luminosity', '明度'],
];
const SWATCHES = ['#ffffff', '#000000', '#f0a742', '#e8645a', '#4fb38a', '#4c8ee8', '#b36fe0'];

function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function copyCanvas(src) { const c = makeCanvas(src.width, src.height); c.getContext('2d').drawImage(src, 0, 0); return c; }
function newLayer(name, w = S.w, h = S.h) {
  const c = makeCanvas(w, h);
  return { id: ++uidSeq, name, canvas: c, ctx: c.getContext('2d', { willReadFrequently: true }), visible: true, opacity: 1, blend: 'source-over', ver: ++verSeq };
}
function wrapLayer(meta, canvas) {
  return { id: meta.id, name: meta.name, canvas, ctx: canvas.getContext('2d', { willReadFrequently: true }), visible: meta.visible, opacity: meta.opacity, blend: meta.blend, ver: meta.ver };
}
const touch = l => { l.ver = ++verSeq; };
const activeLayer = () => S.layers[S.active];
function hexToRgb(hex) { const n = parseInt(hex.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function rgbToHex(r, g, b) { return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join(''); }

/* ================= history ================= */
const H = { stack: [], idx: -1, max: 30 };

function snapshot(label) {
  const prev = H.stack[H.idx];
  const prevMap = new Map(prev ? prev.layers.map(x => [x.id, x]) : []);
  return {
    label, w: S.w, h: S.h, active: S.active,
    layers: S.layers.map(l => {
      const p = prevMap.get(l.id);
      // unchanged pixels: share the previous snapshot's bitmap instead of copying again
      const canvas = (p && p.ver === l.ver) ? p.canvas : copyCanvas(l.canvas);
      return { id: l.id, name: l.name, visible: l.visible, opacity: l.opacity, blend: l.blend, ver: l.ver, canvas };
    }),
  };
}
function commit(label) {
  H.stack.length = H.idx + 1;
  H.stack.push(snapshot(label));
  if (H.stack.length > H.max) H.stack.shift();
  H.idx = H.stack.length - 1;
  afterChange();
}
function restore(snap) {
  S.w = snap.w; S.h = snap.h;
  S.layers = snap.layers.map(x => wrapLayer(x, copyCanvas(x.canvas)));
  S.active = clamp(snap.active, 0, S.layers.length - 1);
  S.crop = null; S.stroke = null;
  resetAdjust(false);
  afterChange();
}
function undo() {
  if (H.idx <= 0) return;
  const label = H.stack[H.idx].label;
  H.idx--; restore(H.stack[H.idx]); toast('復原：' + label);
}
function redo() {
  if (H.idx >= H.stack.length - 1) return;
  H.idx++; restore(H.stack[H.idx]); toast('重做：' + H.stack[H.idx].label);
}
function afterChange() {
  $('#btnUndo').disabled = H.idx <= 0;
  $('#btnRedo').disabled = H.idx >= H.stack.length - 1;
  refreshLayers(); refreshInfo(); render();
  filterThumbsDirty = true;
  if (currentTab === 'filters') buildFilterThumbs();
}

/* ================= document ================= */
function newDocument(w, h, bg = '#ffffff', name = '背景') {
  S.w = w; S.h = h;
  const l = newLayer(name);
  if (bg !== 'transparent') { l.ctx.fillStyle = bg; l.ctx.fillRect(0, 0, w, h); }
  S.layers = [l]; S.active = 0; S.crop = null;
  H.stack = []; H.idx = -1;
  resetAdjust(false);
  fitView();
  commit('新增');
}

function fitDims(w, h) {
  const s = Math.min(1, MAX_SIDE / Math.max(w, h));
  return [Math.max(1, Math.round(w * s)), Math.max(1, Math.round(h * s)), s < 1];
}

async function decodeImage(file) {
  if ('createImageBitmap' in window) {
    try { return await createImageBitmap(file, { imageOrientation: 'from-image' }); } catch (_) { /* fall through */ }
  }
  return new Promise((res, rej) => {
    const url = URL.createObjectURL(file); const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); res(img); };
    img.onerror = () => { URL.revokeObjectURL(url); rej(new Error('decode')); };
    img.src = url;
  });
}

async function openFile(file, asLayer = false) {
  if (!file || !file.type.startsWith('image/')) { toast('這不是影像檔'); return; }
  let img;
  try { img = await decodeImage(file); } catch (_) { toast('無法讀取這個影像格式'); return; }
  const iw = img.width, ih = img.height;
  const base = file.name.replace(/\.[^.]+$/, '') || '影像';
  if (asLayer && S.w) {
    const s = Math.min(1, S.w / iw, S.h / ih);
    const l = newLayer(base);
    const dw = iw * s, dh = ih * s;
    l.ctx.drawImage(img, (S.w - dw) / 2, (S.h - dh) / 2, dw, dh);
    S.layers.splice(S.active + 1, 0, l); S.active++;
    commit('置入影像');
    toast('已置入為新圖層');
    return;
  }
  const [w, h, scaled] = fitDims(iw, ih);
  S.w = w; S.h = h;
  const l = newLayer(base);
  l.ctx.imageSmoothingQuality = 'high';
  l.ctx.drawImage(img, 0, 0, w, h);
  S.layers = [l]; S.active = 0; S.crop = null;
  H.stack = []; H.idx = -1;
  resetAdjust(false);
  $('#expName').value = base + '-edit';
  fitView();
  commit('開啟');
  toast(scaled ? `已開啟，縮小為 ${w}×${h} 以節省記憶體` : `已開啟 ${w}×${h}`);
}

/* Sample photo so the editor opens in a working state: a dusk lake scene drawn procedurally. */
function makeSample() {
  const w = 1600, h = 1067;
  S.w = w; S.h = h;
  const l = newLayer('範例照片（湖畔黃昏）');
  const c = l.ctx;
  const sky = c.createLinearGradient(0, 0, 0, h * 0.62);
  sky.addColorStop(0, '#1f3157'); sky.addColorStop(0.45, '#8a5a7a'); sky.addColorStop(0.8, '#f09a5c'); sky.addColorStop(1, '#f7c27a');
  c.fillStyle = sky; c.fillRect(0, 0, w, h * 0.62);
  const sun = c.createRadialGradient(w * 0.62, h * 0.54, 0, w * 0.62, h * 0.54, 260);
  sun.addColorStop(0, 'rgba(255,240,200,1)'); sun.addColorStop(0.12, 'rgba(255,214,150,.95)'); sun.addColorStop(1, 'rgba(255,170,90,0)');
  c.fillStyle = sun; c.fillRect(0, 0, w, h * 0.62);
  const ridge = (base, amp, seed, color) => {
    c.beginPath(); c.moveTo(0, h * 0.62);
    for (let x = 0; x <= w; x += 8) {
      const y = base + Math.sin(x * 0.004 + seed) * amp + Math.sin(x * 0.011 + seed * 2.3) * amp * 0.45 + Math.sin(x * 0.031 + seed * 5) * amp * 0.12;
      c.lineTo(x, y);
    }
    c.lineTo(w, h * 0.62); c.closePath(); c.fillStyle = color; c.fill();
  };
  ridge(h * 0.47, 46, 1.2, '#6d4a6a');
  ridge(h * 0.52, 38, 3.7, '#4a3352');
  ridge(h * 0.575, 26, 6.1, '#2b2238');
  // lake: opaque base, then the mirrored sky on top (start 1px higher so no seam shows)
  c.fillStyle = '#1d1a2a'; c.fillRect(0, h * 0.62 - 1, w, h * 0.38 + 1);
  c.save(); c.translate(0, h * 1.24); c.scale(1, -1); c.globalAlpha = 0.7;
  c.drawImage(l.canvas, 0, 0, w, h * 0.62 - 2, 0, 2, w, h * 0.62 - 2);
  c.restore();
  const water = c.createLinearGradient(0, h * 0.62, 0, h);
  water.addColorStop(0, 'rgba(20,24,44,.15)'); water.addColorStop(1, 'rgba(10,12,24,.85)');
  c.fillStyle = water; c.fillRect(0, h * 0.62, w, h * 0.38);
  c.strokeStyle = 'rgba(255,220,170,.35)'; c.lineWidth = 2;
  for (let i = 0; i < 46; i++) {
    const y = h * 0.64 + i * i * 0.18, len = 30 + Math.random() * 120 * (1 - i / 50);
    const x = w * 0.62 + (Math.random() - 0.5) * (40 + i * 6);
    c.globalAlpha = 0.9 - i / 52; c.beginPath(); c.moveTo(x - len / 2, y); c.lineTo(x + len / 2, y); c.stroke();
  }
  c.globalAlpha = 1;
  c.fillStyle = '#120f1a'; c.fillRect(0, h * 0.86, w, h * 0.14);
  // film grain
  const img = c.getImageData(0, 0, w, h), d = img.data;
  for (let i = 0; i < d.length; i += 4) { const n = (Math.random() - 0.5) * 14; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
  c.putImageData(img, 0, 0);
  S.layers = [l]; S.active = 0;
  H.stack = []; H.idx = -1;
  fitView();
  commit('範例');
}

/* ================= compositing & view ================= */
const comp = makeCanvas(1, 1), cctx = comp.getContext('2d', { willReadFrequently: true });
const scratch = makeCanvas(1, 1), sctx = scratch.getContext('2d');
let checker = null;

function applyStroke(ctx) {
  const st = S.stroke;
  ctx.save(); ctx.globalAlpha = st.alpha; ctx.globalCompositeOperation = st.op; ctx.drawImage(st.canvas, 0, 0); ctx.restore();
}
function layerSource(l, i) {
  if (i !== S.active) return l.canvas;
  if (S.preview) return S.preview;
  if (S.stroke) {
    if (scratch.width !== l.canvas.width || scratch.height !== l.canvas.height) { scratch.width = l.canvas.width; scratch.height = l.canvas.height; }
    sctx.globalCompositeOperation = 'source-over'; sctx.globalAlpha = 1;
    sctx.clearRect(0, 0, scratch.width, scratch.height);
    sctx.drawImage(l.canvas, 0, 0); applyStroke(sctx);
    return scratch;
  }
  return l.canvas;
}
function composite(target, tctx, live = true) {
  if (target.width !== S.w || target.height !== S.h) { target.width = S.w; target.height = S.h; }
  tctx.save();
  tctx.globalCompositeOperation = 'source-over'; tctx.globalAlpha = 1;
  tctx.clearRect(0, 0, S.w, S.h);
  S.layers.forEach((l, i) => {
    if (!l.visible || l.opacity <= 0) return;
    tctx.globalAlpha = l.opacity; tctx.globalCompositeOperation = l.blend;
    tctx.drawImage(live ? layerSource(l, i) : l.canvas, 0, 0);
  });
  tctx.restore();
}

let rafPending = false;
function render() { if (!rafPending) { rafPending = true; requestAnimationFrame(draw); } }
function draw() {
  rafPending = false;
  const r = stage.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const W = Math.max(1, Math.round(r.width * dpr)), Hh = Math.max(1, Math.round(r.height * dpr));
  if (view.width !== W || view.height !== Hh) { view.width = W; view.height = Hh; }
  vctx.setTransform(1, 0, 0, 1, 0, 0);
  vctx.clearRect(0, 0, W, Hh);
  if (!S.w) return;
  composite(comp, cctx);

  vctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const x0 = S.panX, y0 = S.panY, dw = S.w * S.zoom, dh = S.h * S.zoom;
  vctx.shadowColor = 'rgba(0,0,0,.55)'; vctx.shadowBlur = 24;
  if (!checker) {
    const t = makeCanvas(16, 16), tc = t.getContext('2d');
    tc.fillStyle = '#3a3d42'; tc.fillRect(0, 0, 16, 16);
    tc.fillStyle = '#2b2e33'; tc.fillRect(0, 0, 8, 8); tc.fillRect(8, 8, 8, 8);
    checker = vctx.createPattern(t, 'repeat');
  }
  vctx.fillStyle = checker; vctx.fillRect(x0, y0, dw, dh);
  vctx.shadowBlur = 0; vctx.shadowColor = 'transparent';

  vctx.setTransform(dpr * S.zoom, 0, 0, dpr * S.zoom, dpr * S.panX, dpr * S.panY);
  vctx.imageSmoothingEnabled = S.zoom < 2;
  vctx.imageSmoothingQuality = 'high';
  vctx.drawImage(comp, 0, 0);

  vctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (S.crop) drawCropOverlay(x0, y0, dw, dh);
  if (S.cursor && (S.tool === 'brush' || S.tool === 'eraser') && !isTouch) {
    const cx = S.panX + S.cursor.x * S.zoom, cy = S.panY + S.cursor.y * S.zoom;
    const rr = Math.max(1, S.size / 2 * S.zoom);
    vctx.lineWidth = 1;
    vctx.strokeStyle = 'rgba(0,0,0,.7)'; vctx.beginPath(); vctx.arc(cx, cy, rr + 1, 0, Math.PI * 2); vctx.stroke();
    vctx.strokeStyle = 'rgba(255,255,255,.9)'; vctx.beginPath(); vctx.arc(cx, cy, rr, 0, Math.PI * 2); vctx.stroke();
  }
  updateHud();
}

function drawCropOverlay(x0, y0, dw, dh) {
  const c = S.crop;
  const cx = S.panX + c.x * S.zoom, cy = S.panY + c.y * S.zoom, cw = c.w * S.zoom, ch = c.h * S.zoom;
  vctx.fillStyle = 'rgba(8,9,12,.6)';
  vctx.beginPath(); vctx.rect(x0, y0, dw, dh); vctx.rect(cx, cy, cw, ch); vctx.fill('evenodd');
  vctx.strokeStyle = 'rgba(255,255,255,.35)'; vctx.lineWidth = 1;
  vctx.beginPath();
  for (let i = 1; i < 3; i++) {
    vctx.moveTo(cx + cw * i / 3, cy); vctx.lineTo(cx + cw * i / 3, cy + ch);
    vctx.moveTo(cx, cy + ch * i / 3); vctx.lineTo(cx + cw, cy + ch * i / 3);
  }
  vctx.stroke();
  vctx.strokeStyle = '#f0a742'; vctx.lineWidth = 2; vctx.strokeRect(cx, cy, cw, ch);
  vctx.fillStyle = '#f0a742';
  const hs = 8;
  [[cx, cy], [cx + cw, cy], [cx, cy + ch], [cx + cw, cy + ch]].forEach(([x, y]) => vctx.fillRect(x - hs / 2, y - hs / 2, hs, hs));
  vctx.font = '500 12px "IBM Plex Mono", monospace';
  const label = `${Math.round(c.w)} × ${Math.round(c.h)}`;
  const tw = vctx.measureText(label).width + 12;
  vctx.fillStyle = 'rgba(20,22,26,.9)'; vctx.fillRect(cx, cy - 24 > 0 ? cy - 24 : cy + 4, tw, 20);
  vctx.fillStyle = '#e7e4de'; vctx.fillText(label, cx + 6, (cy - 24 > 0 ? cy - 24 : cy + 4) + 14);
}

function updateHud() {
  const p = S.cursor;
  const pos = p && p.x >= 0 && p.y >= 0 && p.x < S.w && p.y < S.h ? `X <b>${Math.floor(p.x)}</b> Y <b>${Math.floor(p.y)}</b> · ` : '';
  $('#hud').innerHTML = `${pos}<b>${Math.round(S.zoom * 100)}%</b> · ${S.w}×${S.h} px`;
}

function fitView() {
  const r = stage.getBoundingClientRect();
  const pad = isTouch ? 16 : 40;
  const z = Math.min((r.width - pad) / S.w, (r.height - pad) / S.h, 4);
  S.zoom = z > 0 ? z : 1;
  S.panX = (r.width - S.w * S.zoom) / 2;
  S.panY = (r.height - S.h * S.zoom) / 2;
  render();
}
function zoomAt(factor, sx, sy) {
  const nz = clamp(S.zoom * factor, 0.02, 32);
  S.panX = sx - (sx - S.panX) * (nz / S.zoom);
  S.panY = sy - (sy - S.panY) * (nz / S.zoom);
  S.zoom = nz; render();
}
function stagePoint(e) { const r = view.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }
function toDoc(e) { const p = stagePoint(e); return { x: (p.x - S.panX) / S.zoom, y: (p.y - S.panY) / S.zoom }; }

/* ================= tools ================= */
function startPaint(e, erase) {
  const l = activeLayer();
  if (!l.visible) { toast('目前圖層已隱藏'); return null; }
  commitAdjustIfAny();
  const sc = makeCanvas(l.canvas.width, l.canvas.height);
  const c = sc.getContext('2d');
  S.stroke = { canvas: sc, alpha: S.opacity / 100, op: erase ? 'destination-out' : 'source-over' };
  const radius = Math.max(0.5, S.size / 2), hard = S.hardness / 100;
  const [r, g, b] = erase ? [0, 0, 0] : hexToRgb(S.color);
  const solid = `rgb(${r},${g},${b})`, clear = `rgba(${r},${g},${b},0)`;
  const spacing = Math.max(0.5, S.size * (hard > 0.9 ? 0.08 : 0.15));
  const pen = e.pointerType === 'pen';
  const dab = (x, y, pressure) => {
    const rr = pen ? radius * Math.max(0.15, pressure || 0.5) : radius;
    if (hard >= 0.98) { c.fillStyle = solid; c.beginPath(); c.arc(x, y, rr, 0, Math.PI * 2); c.fill(); return; }
    const gr = c.createRadialGradient(x, y, rr * hard, x, y, rr);
    gr.addColorStop(0, solid); gr.addColorStop(1, clear);
    c.fillStyle = gr; c.beginPath(); c.arc(x, y, rr, 0, Math.PI * 2); c.fill();
  };
  let last = toDoc(e), carry = 0;
  dab(last.x, last.y, e.pressure);
  render();
  return {
    move(ev) {
      const list = ev.getCoalescedEvents ? ev.getCoalescedEvents() : [];
      for (const ce of (list.length ? list : [ev])) {
        const q = toDoc(ce);
        const dx = q.x - last.x, dy = q.y - last.y, dist = Math.hypot(dx, dy);
        if (dist === 0) continue;
        let t = spacing - carry;
        while (t <= dist) { dab(last.x + dx * t / dist, last.y + dy * t / dist, ce.pressure); t += spacing; }
        carry = dist - (t - spacing);
        last = q;
      }
      render();
    },
    end() { applyStroke(l.ctx); S.stroke = null; touch(l); commit(erase ? '橡皮擦' : '筆刷'); },
    cancel() { S.stroke = null; render(); },
  };
}

function startShape(e) {
  const l = activeLayer();
  if (!l.visible) { toast('目前圖層已隱藏'); return null; }
  commitAdjustIfAny();
  const sc = makeCanvas(l.canvas.width, l.canvas.height), c = sc.getContext('2d');
  S.stroke = { canvas: sc, alpha: S.opacity / 100, op: 'source-over' };
  const p0 = toDoc(e); let moved = false;
  const drawShape = (p, square) => {
    c.clearRect(0, 0, sc.width, sc.height);
    let w = p.x - p0.x, h = p.y - p0.y;
    if (square && S.shape !== 'line') { const m = Math.max(Math.abs(w), Math.abs(h)); w = Math.sign(w || 1) * m; h = Math.sign(h || 1) * m; }
    c.strokeStyle = c.fillStyle = S.color; c.lineWidth = S.size; c.lineCap = 'round'; c.lineJoin = 'round';
    c.beginPath();
    if (S.shape === 'line') {
      let ex = p.x, ey = p.y;
      if (square) { const ang = Math.round(Math.atan2(h, w) / (Math.PI / 4)) * (Math.PI / 4), len = Math.hypot(w, h); ex = p0.x + Math.cos(ang) * len; ey = p0.y + Math.sin(ang) * len; }
      c.moveTo(p0.x, p0.y); c.lineTo(ex, ey); c.stroke(); return;
    }
    if (S.shape === 'rect') c.rect(p0.x, p0.y, w, h);
    else c.ellipse(p0.x + w / 2, p0.y + h / 2, Math.abs(w / 2), Math.abs(h / 2), 0, 0, Math.PI * 2);
    S.shapeFill ? c.fill() : c.stroke();
  };
  return {
    move(ev) { moved = true; drawShape(toDoc(ev), ev.shiftKey); render(); },
    end() { if (!moved) { S.stroke = null; render(); return; } applyStroke(l.ctx); S.stroke = null; touch(l); commit('形狀'); },
    cancel() { S.stroke = null; render(); },
  };
}

function startMove(e) {
  const l = activeLayer();
  commitAdjustIfAny();
  const backup = copyCanvas(l.canvas);
  const p0 = toDoc(e); let dx = 0, dy = 0;
  return {
    move(ev) {
      const p = toDoc(ev);
      dx = Math.round(p.x - p0.x); dy = Math.round(p.y - p0.y);
      l.ctx.clearRect(0, 0, l.canvas.width, l.canvas.height); l.ctx.drawImage(backup, dx, dy); render();
    },
    end() { if (dx || dy) { touch(l); commit('移動'); } },
    cancel() { l.ctx.clearRect(0, 0, l.canvas.width, l.canvas.height); l.ctx.drawImage(backup, 0, 0); render(); },
  };
}

function startHand(e) {
  const s0 = stagePoint(e), px = S.panX, py = S.panY;
  view.style.cursor = 'grabbing';
  return {
    move(ev) { const p = stagePoint(ev); S.panX = px + p.x - s0.x; S.panY = py + p.y - s0.y; render(); },
    end() { setCursor(); }, cancel() { setCursor(); },
  };
}

function pickColor(e) {
  const p = toDoc(e);
  const x = Math.floor(p.x), y = Math.floor(p.y);
  if (x < 0 || y < 0 || x >= S.w || y >= S.h) return false;
  composite(comp, cctx);
  const d = cctx.getImageData(x, y, 1, 1).data;
  if (d[3] === 0) return false;
  setColor(rgbToHex(d[0], d[1], d[2]));
  return true;
}
function startEyedropper(e) {
  pickColor(e);
  return { move(ev) { pickColor(ev); }, end() { toast('已取色 ' + S.color.toUpperCase()); }, cancel() {} };
}

function floodFill(e) {
  const l = activeLayer();
  commitAdjustIfAny();
  const p = toDoc(e);
  const sx = Math.floor(p.x), sy = Math.floor(p.y);
  const W = l.canvas.width, Hh = l.canvas.height;
  if (sx < 0 || sy < 0 || sx >= W || sy >= Hh) return;
  const img = l.ctx.getImageData(0, 0, W, Hh), d = img.data;
  const k0 = (sy * W + sx) * 4;
  const tr = d[k0], tg = d[k0 + 1], tb = d[k0 + 2], ta = d[k0 + 3];
  const T = S.tolerance * 2.55;
  const match = q => { const k = q * 4; return Math.abs(d[k] - tr) <= T && Math.abs(d[k + 1] - tg) <= T && Math.abs(d[k + 2] - tb) <= T && Math.abs(d[k + 3] - ta) <= T; };
  const mask = new Uint8Array(W * Hh);
  const stack = [sx, sy];
  while (stack.length) {
    const y = stack.pop(); let x = stack.pop();
    let q = y * W + x;
    while (x >= 0 && !mask[q] && match(q)) { x--; q--; }
    x++; q++;
    let up = false, down = false;
    while (x < W && !mask[q] && match(q)) {
      mask[q] = 1;
      if (y > 0) { const u = q - W; if (!mask[u] && match(u)) { if (!up) { stack.push(x, y - 1); up = true; } } else up = false; }
      if (y < Hh - 1) { const v = q + W; if (!mask[v] && match(v)) { if (!down) { stack.push(x, y + 1); down = true; } } else down = false; }
      x++; q++;
    }
  }
  const [fr, fg, fb] = hexToRgb(S.color), a = S.opacity / 100;
  for (let q = 0; q < mask.length; q++) {
    if (!mask[q]) continue;
    const k = q * 4, da = d[k + 3] / 255, oa = a + da * (1 - a);
    if (oa <= 0) continue;
    d[k] = (fr * a + d[k] * da * (1 - a)) / oa;
    d[k + 1] = (fg * a + d[k + 1] * da * (1 - a)) / oa;
    d[k + 2] = (fb * a + d[k + 2] * da * (1 - a)) / oa;
    d[k + 3] = oa * 255;
  }
  l.ctx.putImageData(img, 0, 0);
  touch(l); commit('油漆桶');
}

/* ----- crop ----- */
function normRect(a, b) {
  let x = Math.min(a.x, b.x), y = Math.min(a.y, b.y), w = Math.abs(b.x - a.x), h = Math.abs(b.y - a.y);
  return { x, y, w, h };
}
function constrainCrop(p0, p) {
  let w = p.x - p0.x, h = p.y - p0.y;
  if (S.cropRatio !== 'free') {
    const r = parseFloat(S.cropRatio);
    if (Math.abs(w) / r > Math.abs(h)) h = Math.sign(h || 1) * Math.abs(w) / r; else w = Math.sign(w || 1) * Math.abs(h) * r;
  }
  const rc = normRect(p0, { x: p0.x + w, y: p0.y + h });
  rc.x = clamp(rc.x, 0, S.w); rc.y = clamp(rc.y, 0, S.h);
  rc.w = Math.min(rc.w, S.w - rc.x); rc.h = Math.min(rc.h, S.h - rc.y);
  return rc;
}
function startCrop(e) {
  const p0 = toDoc(e);
  const c = S.crop;
  if (c && p0.x > c.x && p0.y > c.y && p0.x < c.x + c.w && p0.y < c.y + c.h) {
    const ox = c.x, oy = c.y;
    return {
      move(ev) { const p = toDoc(ev); c.x = clamp(ox + p.x - p0.x, 0, S.w - c.w); c.y = clamp(oy + p.y - p0.y, 0, S.h - c.h); render(); },
      end() {}, cancel() {},
    };
  }
  const start = { x: clamp(p0.x, 0, S.w), y: clamp(p0.y, 0, S.h) };
  S.crop = { x: start.x, y: start.y, w: 0, h: 0 };
  return {
    move(ev) { S.crop = constrainCrop(start, toDoc(ev)); render(); },
    end() { if (S.crop.w < 2 || S.crop.h < 2) { S.crop = null; render(); } },
    cancel() { S.crop = null; render(); },
  };
}
function applyCrop() {
  const c = S.crop;
  if (!c || c.w < 1 || c.h < 1) { toast('先在畫面上拖曳出裁切範圍'); return; }
  const x = Math.round(c.x), y = Math.round(c.y), w = Math.max(1, Math.round(c.w)), h = Math.max(1, Math.round(c.h));
  commitAdjustIfAny();
  S.layers.forEach(l => {
    const n = makeCanvas(w, h); n.getContext('2d').drawImage(l.canvas, -x, -y);
    l.canvas = n; l.ctx = n.getContext('2d', { willReadFrequently: true }); touch(l);
  });
  S.w = w; S.h = h; S.crop = null;
  fitView(); commit('裁切');
}

/* ----- text ----- */
let textPoint = null;
function startText(e) {
  textPoint = toDoc(e);
  openModal('#dlgText');
  setTimeout(() => { const t = $('#txtValue'); t.focus(); t.select(); }, 30);
  return null;
}
function applyText() {
  const txt = $('#txtValue').value;
  if (!txt.trim()) { closeModal(); return; }
  commitAdjustIfAny();
  const size = clamp(+$('#txtSize').value || 72, 6, 1000);
  const weight = $('#txtWeight').value, align = $('#txtAlign').value;
  const l = newLayer('文字：' + txt.split('\n')[0].slice(0, 12));
  const c = l.ctx;
  c.font = `${weight} ${size}px "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif`;
  c.fillStyle = S.color; c.textBaseline = 'top'; c.textAlign = align;
  if ($('#txtShadow').checked) { c.shadowColor = 'rgba(0,0,0,.55)'; c.shadowBlur = size * 0.18; c.shadowOffsetY = size * 0.06; }
  const p = textPoint || { x: S.w / 2, y: S.h / 2 };
  txt.split('\n').forEach((line, i) => c.fillText(line, p.x, p.y + i * size * 1.25));
  S.layers.splice(S.active + 1, 0, l); S.active++;
  closeModal(); commit('文字');
}

/* ----- pointer routing (with two-finger pinch on any tool) ----- */
const ptrs = new Map();
let action = null, pinch = null, spaceDown = false, blockUntilUp = false;

view.addEventListener('pointerdown', e => {
  if (!S.w) return;
  view.setPointerCapture(e.pointerId);
  ptrs.set(e.pointerId, stagePoint(e));
  if (ptrs.size === 2) {
    if (action && action.cancel) action.cancel();
    action = null;
    const [a, b] = [...ptrs.values()];
    pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, z: S.zoom, px: S.panX, py: S.panY };
    blockUntilUp = true;
    return;
  }
  if (ptrs.size > 2 || blockUntilUp) return;
  if (e.button === 2) return;
  const tool = (spaceDown || e.button === 1) ? 'hand' : S.tool;
  e.preventDefault();
  action = ({
    brush: () => startPaint(e, false), eraser: () => startPaint(e, true), shape: () => startShape(e),
    move: () => startMove(e), hand: () => startHand(e), eyedropper: () => startEyedropper(e),
    crop: () => startCrop(e), text: () => startText(e), fill: () => { floodFill(e); return null; },
  })[tool]() || null;
});
view.addEventListener('pointermove', e => {
  if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, stagePoint(e));
  if (pinch && ptrs.size >= 2) {
    const [a, b] = [...ptrs.values()];
    const d = Math.hypot(a.x - b.x, a.y - b.y) || 1, mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const nz = clamp(pinch.z * d / pinch.d, 0.02, 32);
    S.panX = mx - (pinch.mx - pinch.px) * (nz / pinch.z);
    S.panY = my - (pinch.my - pinch.py) * (nz / pinch.z);
    S.zoom = nz; render();
    return;
  }
  S.cursor = toDoc(e);
  if (action) action.move(e); else render();
});
const endPointer = e => {
  ptrs.delete(e.pointerId);
  if (ptrs.size < 2) pinch = null;
  if (ptrs.size === 0) blockUntilUp = false;
  if (action) { const a = action; action = null; e.type === 'pointercancel' ? a.cancel && a.cancel() : a.end(e); }
};
view.addEventListener('pointerup', endPointer);
view.addEventListener('pointercancel', endPointer);
view.addEventListener('pointerleave', () => { if (!action) { S.cursor = null; render(); } });
view.addEventListener('contextmenu', e => e.preventDefault());
view.addEventListener('wheel', e => {
  e.preventDefault();
  const p = stagePoint(e);
  // shift+wheel pans sideways; wheel and trackpad pinch (ctrl+wheel) zoom around the cursor
  if (e.shiftKey) { S.panX -= e.deltaY || e.deltaX; render(); return; }
  zoomAt(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015)), p.x, p.y);
}, { passive: false });

function setCursor() {
  view.style.cursor = ({ hand: 'grab', move: 'move', crop: 'crosshair', eyedropper: 'crosshair', text: 'text', fill: 'crosshair', shape: 'crosshair', brush: 'none', eraser: 'none' })[S.tool] || 'default';
  if (isTouch) view.style.cursor = 'default';
}

function setTool(t) {
  if (S.tool === 'crop' && t !== 'crop') S.crop = null;
  S.tool = t;
  $$('#toolbar button').forEach(b => b.classList.toggle('on', b.dataset.tool === t));
  $('#toolName').textContent = TOOL_NAMES[t];
  $$('#optbar [data-for]').forEach(el => { el.hidden = !el.dataset.for.split(' ').includes(t); });
  setCursor(); render();
}
function setColor(hex) {
  S.color = hex; $('#optColor').value = hex;
}

/* ================= adjustments ================= */
const ADJ = [
  ['光線'],
  ['exposure', '曝光', -100, 100], ['brightness', '亮度', -100, 100], ['contrast', '對比', -100, 100],
  ['highlights', '亮部', -100, 100], ['shadows', '陰影', -100, 100],
  ['色彩'],
  ['temperature', '色溫', -100, 100], ['tint', '色調', -100, 100], ['hue', '色相', -180, 180],
  ['saturation', '飽和度', -100, 100], ['vibrance', '自然飽和度', -100, 100],
  ['細節與效果'],
  ['sharpen', '銳利化', 0, 100], ['blur', '模糊', 0, 40], ['vignette', '暈影', 0, 100], ['grain', '顆粒', 0, 100],
];
const adj = {};
ADJ.forEach(a => { if (a.length > 1) adj[a[0]] = 0; });
let adjSrc = null; // {id, ver, data}
let adjQueued = false;

function buildAdjustUI() {
  const box = $('#adjList');
  ADJ.forEach(a => {
    if (a.length === 1) { const h = document.createElement('div'); h.className = 'adj-head'; h.textContent = a[0]; box.appendChild(h); return; }
    const [key, label, min, max] = a;
    const row = document.createElement('label'); row.className = 'row';
    row.innerHTML = `<span>${label}</span><input type="range" id="adj-${key}" min="${min}" max="${max}" value="0"><output id="out-${key}">0</output>`;
    box.appendChild(row);
    const inp = $('input', row), out = $('output', row);
    inp.addEventListener('input', () => { adj[key] = +inp.value; out.textContent = inp.value; out.classList.toggle('changed', +inp.value !== 0); queueAdjust(); });
    inp.addEventListener('dblclick', () => { inp.value = 0; inp.dispatchEvent(new Event('input')); });
  });
}
const adjActive = () => Object.values(adj).some(v => v !== 0);
function queueAdjust() { if (!adjQueued) { adjQueued = true; requestAnimationFrame(runAdjust); } }
function runAdjust() {
  adjQueued = false;
  const l = activeLayer(); if (!l) return;
  if (!adjActive()) { S.preview = null; render(); return; }
  if (!adjSrc || adjSrc.id !== l.id || adjSrc.ver !== l.ver) {
    adjSrc = { id: l.id, ver: l.ver, data: l.ctx.getImageData(0, 0, l.canvas.width, l.canvas.height) };
  }
  const src = adjSrc.data;
  const out = new ImageData(new Uint8ClampedArray(src.data), src.width, src.height);
  processAdjust(out, adj);
  if (!S.preview || S.preview.width !== out.width || S.preview.height !== out.height) S.preview = makeCanvas(out.width, out.height);
  S.preview.getContext('2d').putImageData(out, 0, 0);
  render();
}
function resetAdjust(rerender = true) {
  Object.keys(adj).forEach(k => {
    adj[k] = 0;
    const i = $('#adj-' + k), o = $('#out-' + k);
    if (i) { i.value = 0; o.textContent = '0'; o.classList.remove('changed'); }
  });
  S.preview = null; adjSrc = null;
  if (rerender) render();
}
function applyAdjust() {
  if (!adjActive()) { toast('尚未調整任何數值'); return; }
  if (adjQueued) runAdjust();
  const l = activeLayer();
  l.ctx.clearRect(0, 0, l.canvas.width, l.canvas.height);
  l.ctx.drawImage(S.preview, 0, 0);
  touch(l); resetAdjust(false); commit('調整');
  toast('已套用調整');
}
// Painting or editing while an adjustment preview is open bakes the preview first, so nothing is lost.
function commitAdjustIfAny() { if (S.preview && adjActive()) applyAdjust(); else if (S.preview) resetAdjust(false); }

function hueMatrix(deg) {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  return [
    0.213 + c * 0.787 - s * 0.213, 0.715 - c * 0.715 - s * 0.715, 0.072 - c * 0.072 + s * 0.928,
    0.213 - c * 0.213 + s * 0.143, 0.715 + c * 0.285 + s * 0.140, 0.072 - c * 0.072 - s * 0.283,
    0.213 - c * 0.213 - s * 0.787, 0.715 - c * 0.715 + s * 0.715, 0.072 + c * 0.928 + s * 0.072,
  ];
}

function processAdjust(img, a) {
  const d = img.data, W = img.width, Hh = img.height;
  // tone curve LUT: exposure → brightness → contrast → highlights/shadows
  const lut = new Float32Array(256);
  const ex = Math.pow(2, a.exposure / 50);
  const cc = a.contrast * 2.55, cf = (259 * (cc + 255)) / (255 * (259 - cc));
  for (let i = 0; i < 256; i++) {
    let v = i * ex + a.brightness * 1.2;
    v = cf * (v - 128) + 128;
    const t = clamp(v / 255, 0, 1);
    v += a.highlights * 0.9 * t * t * (t > 0.5 ? 1 : t * 2);
    v += a.shadows * 0.9 * (1 - t) * (1 - t) * (t < 0.5 ? 1 : (1 - t) * 2);
    lut[i] = v;
  }
  const doHue = a.hue !== 0, m = hueMatrix(a.hue);
  const sat = 1 + a.saturation / 100, vib = a.vibrance / 100;
  const tr = a.temperature * 0.45, tb = -a.temperature * 0.45, tg = -a.tint * 0.4, tm = a.tint * 0.2;
  const vig = a.vignette / 100, cx = W / 2, cy = Hh / 2, maxD = Math.hypot(cx, cy);
  const grain = a.grain * 0.6;
  const colorPass = doHue || sat !== 1 || vib !== 0 || tr !== 0 || tg !== 0;
  for (let y = 0, k = 0; y < Hh; y++) {
    for (let x = 0; x < W; x++, k += 4) {
      if (d[k + 3] === 0) continue;
      let r = lut[d[k]], g = lut[d[k + 1]], b = lut[d[k + 2]];
      if (colorPass) {
        r += tr + tm; b += tb + tm; g += tg;
        if (doHue) { const r0 = r, g0 = g, b0 = b; r = m[0] * r0 + m[1] * g0 + m[2] * b0; g = m[3] * r0 + m[4] * g0 + m[5] * b0; b = m[6] * r0 + m[7] * g0 + m[8] * b0; }
        let f = sat;
        if (vib !== 0) { const mx = Math.max(r, g, b), mn = Math.min(r, g, b); f *= 1 + vib * (1 - clamp((mx - mn) / 255, 0, 1)); }
        if (f !== 1) { const gray = 0.2126 * r + 0.7152 * g + 0.0722 * b; r = gray + (r - gray) * f; g = gray + (g - gray) * f; b = gray + (b - gray) * f; }
      }
      if (vig > 0) {
        const t = Math.hypot(x - cx, y - cy) / maxD;
        const v = 1 - vig * Math.pow(clamp((t - 0.35) / 0.65, 0, 1), 1.6);
        r *= v; g *= v; b *= v;
      }
      if (grain > 0) { const n = (Math.random() - 0.5) * grain; r += n; g += n; b += n; }
      d[k] = r; d[k + 1] = g; d[k + 2] = b;
    }
  }
  if (a.blur > 0) gaussBlur(d, W, Hh, a.blur);
  if (a.sharpen > 0) unsharp(d, W, Hh, a.sharpen / 100 * 1.6, 1.2);
}

function boxesForGauss(sigma, n) {
  const wIdeal = Math.sqrt((12 * sigma * sigma / n) + 1);
  let wl = Math.floor(wIdeal); if (wl % 2 === 0) wl--;
  const wu = wl + 2;
  const m = Math.round((12 * sigma * sigma - n * wl * wl - 4 * n * wl - 3 * n) / (-4 * wl - 4));
  return Array.from({ length: n }, (_, i) => (i < m ? wl : wu));
}
function boxPass(src, dst, W, Hh, r, horiz) {
  const iarr = 1 / (r + r + 1);
  const outer = horiz ? Hh : W, inner = horiz ? W : Hh;
  const step = horiz ? 4 : W * 4;
  for (let o = 0; o < outer; o++) {
    const base = horiz ? o * W * 4 : o * 4;
    for (let c = 0; c < 4; c++) {
      const at = i => src[base + clamp(i, 0, inner - 1) * step + c];
      let val = 0;
      for (let i = -r; i <= r; i++) val += at(i);
      for (let i = 0; i < inner; i++) {
        dst[base + i * step + c] = val * iarr;
        val += at(i + r + 1) - at(i - r);
      }
    }
  }
}
function gaussBlur(d, W, Hh, sigma) {
  const tmp = new Uint8ClampedArray(d.length);
  for (const box of boxesForGauss(sigma, 3)) {
    const r = (box - 1) / 2;
    if (r < 1) continue;
    boxPass(d, tmp, W, Hh, r, true);
    boxPass(tmp, d, W, Hh, r, false);
  }
}
function unsharp(d, W, Hh, amount, sigma) {
  const bl = new Uint8ClampedArray(d);
  gaussBlur(bl, W, Hh, sigma);
  for (let k = 0; k < d.length; k += 4) {
    d[k] = d[k] + (d[k] - bl[k]) * amount;
    d[k + 1] = d[k + 1] + (d[k + 1] - bl[k + 1]) * amount;
    d[k + 2] = d[k + 2] + (d[k + 2] - bl[k + 2]) * amount;
  }
}

/* ================= one-click filters ================= */
const FILTERS = [
  ['original', '原圖', null],
  ['mono', '黑白', d => { for (let k = 0; k < d.length; k += 4) { const g = 0.2126 * d[k] + 0.7152 * d[k + 1] + 0.0722 * d[k + 2]; d[k] = d[k + 1] = d[k + 2] = g; } }],
  ['noir', '高反差黑白', d => { for (let k = 0; k < d.length; k += 4) { let g = 0.3 * d[k] + 0.59 * d[k + 1] + 0.11 * d[k + 2]; g = 1.6 * (g - 128) + 118; d[k] = d[k + 1] = d[k + 2] = g; } }],
  ['sepia', '懷舊', d => { for (let k = 0; k < d.length; k += 4) { const r = d[k], g = d[k + 1], b = d[k + 2]; d[k] = r * .393 + g * .769 + b * .189; d[k + 1] = r * .349 + g * .686 + b * .168; d[k + 2] = r * .272 + g * .534 + b * .131; } }],
  ['warm', '暖陽', (d, img) => processAdjust(img, { ...zeroAdj(), temperature: 40, vibrance: 25, contrast: 8 })],
  ['cool', '冷調', (d, img) => processAdjust(img, { ...zeroAdj(), temperature: -40, tint: -8, saturation: -10, contrast: 6 })],
  ['fade', '褪色底片', (d, img) => { processAdjust(img, { ...zeroAdj(), contrast: -28, saturation: -25, shadows: 30, grain: 25 }); for (let k = 0; k < d.length; k += 4) { d[k] = d[k] * 0.9 + 22; d[k + 1] = d[k + 1] * 0.9 + 18; d[k + 2] = d[k + 2] * 0.88 + 26; } }],
  ['vivid', '鮮豔', (d, img) => processAdjust(img, { ...zeroAdj(), vibrance: 55, contrast: 18, saturation: 12 })],
  ['retro', '復古', (d, img) => { FILTERS[3][2](d); processAdjust(img, { ...zeroAdj(), contrast: 15, vignette: 55, grain: 20 }); }],
  ['invert', '負片', d => { for (let k = 0; k < d.length; k += 4) { d[k] = 255 - d[k]; d[k + 1] = 255 - d[k + 1]; d[k + 2] = 255 - d[k + 2]; } }],
  ['auto', '自動色階', d => autoLevels(d)],
  ['pixel', '馬賽克', (d, img) => pixelate(img, Math.max(4, Math.round(Math.max(img.width, img.height) / 80)))],
  ['emboss', '浮雕', (d, img) => convolve(img, [-2, -1, 0, -1, 1, 1, 0, 1, 2], 1, 0)],
  ['edges', '邊緣', (d, img) => { convolve(img, [-1, -1, -1, -1, 8, -1, -1, -1, -1], 1, 0); }],
  ['soft', '柔焦', (d, img) => softGlow(d, img)],
];
function zeroAdj() { const z = {}; Object.keys(adj).forEach(k => (z[k] = 0)); return z; }
function autoLevels(d) {
  const hist = [new Uint32Array(256), new Uint32Array(256), new Uint32Array(256)];
  let n = 0;
  for (let k = 0; k < d.length; k += 4) { if (!d[k + 3]) continue; hist[0][d[k]]++; hist[1][d[k + 1]]++; hist[2][d[k + 2]]++; n++; }
  const cut = n * 0.005;
  const ranges = hist.map(h => {
    let lo = 0, hi = 255, acc = 0;
    while (lo < 255 && (acc += h[lo]) < cut) lo++;
    acc = 0; while (hi > 0 && (acc += h[hi]) < cut) hi--;
    return hi > lo ? [lo, 255 / (hi - lo)] : [0, 1];
  });
  for (let k = 0; k < d.length; k += 4) for (let c = 0; c < 3; c++) d[k + c] = (d[k + c] - ranges[c][0]) * ranges[c][1];
}
function pixelate(img, size) {
  const d = img.data, W = img.width, Hh = img.height;
  for (let by = 0; by < Hh; by += size) for (let bx = 0; bx < W; bx += size) {
    let r = 0, g = 0, b = 0, a = 0, n = 0;
    const ey = Math.min(by + size, Hh), ex = Math.min(bx + size, W);
    for (let y = by; y < ey; y++) for (let x = bx; x < ex; x++) { const k = (y * W + x) * 4; r += d[k]; g += d[k + 1]; b += d[k + 2]; a += d[k + 3]; n++; }
    r /= n; g /= n; b /= n; a /= n;
    for (let y = by; y < ey; y++) for (let x = bx; x < ex; x++) { const k = (y * W + x) * 4; d[k] = r; d[k + 1] = g; d[k + 2] = b; d[k + 3] = a; }
  }
}
function convolve(img, kern, div, bias) {
  const W = img.width, Hh = img.height, d = img.data, src = new Uint8ClampedArray(d);
  for (let y = 0; y < Hh; y++) for (let x = 0; x < W; x++) {
    let r = 0, g = 0, b = 0, i = 0;
    for (let ky = -1; ky <= 1; ky++) for (let kx = -1; kx <= 1; kx++, i++) {
      const k = (clamp(y + ky, 0, Hh - 1) * W + clamp(x + kx, 0, W - 1)) * 4, w = kern[i];
      r += src[k] * w; g += src[k + 1] * w; b += src[k + 2] * w;
    }
    const k = (y * W + x) * 4;
    d[k] = r / div + bias; d[k + 1] = g / div + bias; d[k + 2] = b / div + bias;
  }
}
function softGlow(d, img) {
  // screen-blend a blurred copy over the original for a dreamy glow
  const o = new Uint8ClampedArray(d);
  gaussBlur(o, img.width, img.height, Math.max(2, Math.max(img.width, img.height) / 160));
  for (let k = 0; k < d.length; k += 4) for (let c = 0; c < 3; c++) {
    const a = d[k + c], b = o[k + c], screen = 255 - (255 - a) * (255 - b) / 255;
    d[k + c] = a * 0.45 + screen * 0.55;
  }
}

let filterThumbsDirty = true;
function buildFilterUI() {
  const grid = $('#filterGrid');
  FILTERS.forEach(([key, label]) => {
    const b = document.createElement('button');
    b.dataset.filter = key;
    b.innerHTML = `<canvas width="120" height="120"></canvas><span>${label}</span>`;
    b.addEventListener('click', () => applyFilter(key));
    grid.appendChild(b);
  });
}
function buildFilterThumbs() {
  if (!filterThumbsDirty || !S.w) return;
  filterThumbsDirty = false;
  const l = activeLayer();
  const t = makeCanvas(120, 120), tc = t.getContext('2d', { willReadFrequently: true });
  const s = Math.max(120 / l.canvas.width, 120 / l.canvas.height);
  const sw = 120 / s, sh = 120 / s;
  tc.drawImage(l.canvas, (l.canvas.width - sw) / 2, (l.canvas.height - sh) / 2, sw, sh, 0, 0, 120, 120);
  const base = tc.getImageData(0, 0, 120, 120);
  $$('#filterGrid button').forEach(b => {
    const f = FILTERS.find(x => x[0] === b.dataset.filter);
    const img = new ImageData(new Uint8ClampedArray(base.data), 120, 120);
    if (f[2]) f[2](img.data, img);
    b.querySelector('canvas').getContext('2d').putImageData(img, 0, 0);
  });
}
function applyFilter(key) {
  const f = FILTERS.find(x => x[0] === key);
  if (!f[2]) { toast('原圖：未變更（要回到先前狀態請用復原）'); return; }
  commitAdjustIfAny();
  const l = activeLayer();
  const img = l.ctx.getImageData(0, 0, l.canvas.width, l.canvas.height);
  f[2](img.data, img);
  l.ctx.putImageData(img, 0, 0);
  touch(l); commit('濾鏡：' + f[1]);
  toast('已套用「' + f[1] + '」');
}

/* ================= image operations ================= */
function transformAll(nw, nh, fn) {
  commitAdjustIfAny();
  S.layers.forEach(l => {
    const n = makeCanvas(nw, nh), c = n.getContext('2d');
    c.imageSmoothingQuality = 'high'; fn(c, l.canvas);
    l.canvas = n; l.ctx = n.getContext('2d', { willReadFrequently: true }); touch(l);
  });
  S.w = nw; S.h = nh; S.crop = null;
}
const imageOps = {
  rotL() { const w = S.w, h = S.h; transformAll(h, w, (c, src) => { c.translate(0, w); c.rotate(-Math.PI / 2); c.drawImage(src, 0, 0); }); fitView(); commit('向左旋轉'); },
  rotR() { const w = S.w, h = S.h; transformAll(h, w, (c, src) => { c.translate(h, 0); c.rotate(Math.PI / 2); c.drawImage(src, 0, 0); }); fitView(); commit('向右旋轉'); },
  flipH() { transformAll(S.w, S.h, (c, src) => { c.translate(S.w, 0); c.scale(-1, 1); c.drawImage(src, 0, 0); }); commit('水平翻轉'); },
  flipV() { transformAll(S.w, S.h, (c, src) => { c.translate(0, S.h); c.scale(1, -1); c.drawImage(src, 0, 0); }); commit('垂直翻轉'); },
  resize() { $('#rsW').value = S.w; $('#rsH').value = S.h; openModal('#dlgResize'); },
  new() { openModal('#dlgNew'); },
  placeLayer() { $('#fileLayer').click(); },
  flatten() {
    if (S.layers.length < 2) { toast('只有一個圖層'); return; }
    commitAdjustIfAny();
    const l = newLayer('平面化影像'); composite(l.canvas, l.ctx, false);
    S.layers = [l]; S.active = 0; commit('平面化');
  },
  clearLayer() { commitAdjustIfAny(); const l = activeLayer(); l.ctx.clearRect(0, 0, l.canvas.width, l.canvas.height); touch(l); commit('清除圖層'); },
  fillLayer() { commitAdjustIfAny(); const l = activeLayer(); l.ctx.save(); l.ctx.globalAlpha = S.opacity / 100; l.ctx.fillStyle = S.color; l.ctx.fillRect(0, 0, l.canvas.width, l.canvas.height); l.ctx.restore(); touch(l); commit('填滿'); },
};
function applyResize() {
  const w = clamp(Math.round(+$('#rsW').value), 1, 8192), h = clamp(Math.round(+$('#rsH').value), 1, 8192);
  const ow = S.w, oh = S.h;
  closeModal();
  if (w === ow && h === oh) return;
  transformAll(w, h, (c, src) => c.drawImage(src, 0, 0, ow, oh, 0, 0, w, h));
  fitView(); commit('影像尺寸');
}

/* ================= layers panel ================= */
function refreshLayers() {
  const ul = $('#layerList');
  ul.innerHTML = '';
  for (let i = S.layers.length - 1; i >= 0; i--) {
    const l = S.layers[i];
    const li = document.createElement('li');
    li.className = (i === S.active ? 'on ' : '') + (l.visible ? '' : 'hidden-layer');
    li.innerHTML = `<button class="eye" aria-label="${l.visible ? '隱藏' : '顯示'}圖層">${l.visible
      ? '<svg viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>'
      : '<svg viewBox="0 0 24 24"><path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.6 9.6 0 0 0 5.4-1.6"/></svg>'}</button>
      <canvas width="92" height="68"></canvas>
      <div class="lname"><span class="lt"></span><span class="lmeta">${Math.round(l.opacity * 100)}% · ${(BLENDS.find(b => b[0] === l.blend) || BLENDS[0])[1]}</span></div>`;
    $('.lt', li).textContent = l.name;
    const tc = $('canvas', li).getContext('2d');
    const s = Math.min(92 / l.canvas.width, 68 / l.canvas.height);
    tc.drawImage(l.canvas, (92 - l.canvas.width * s) / 2, (68 - l.canvas.height * s) / 2, l.canvas.width * s, l.canvas.height * s);
    li.addEventListener('click', ev => {
      if (ev.target.closest('.eye')) { l.visible = !l.visible; commit(l.visible ? '顯示圖層' : '隱藏圖層'); return; }
      if (S.active !== i) { commitAdjustIfAny(); S.active = i; refreshLayers(); render(); filterThumbsDirty = true; if (currentTab === 'filters') buildFilterThumbs(); }
    });
    $('.lname', li).addEventListener('dblclick', () => renameLayer(l, li));
    ul.appendChild(li);
  }
  const l = activeLayer();
  if (l) {
    $('#layerOpacity').value = Math.round(l.opacity * 100);
    $('#outLayerOpacity').textContent = Math.round(l.opacity * 100) + '%';
    $('#layerBlend').value = l.blend;
    $('#adjLayerName').textContent = l.name;
  }
  $('#lyDel').disabled = S.layers.length < 2;
  $('#lyMerge').disabled = S.active === 0;
  $('#lyUp').disabled = S.active >= S.layers.length - 1;
  $('#lyDown').disabled = S.active === 0;
}
function renameLayer(l, li) {
  const box = $('.lname', li);
  box.innerHTML = '<input type="text" aria-label="圖層名稱">';
  const inp = $('input', box); inp.value = l.name; inp.focus(); inp.select();
  const done = ok => { if (ok && inp.value.trim() && inp.value !== l.name) { l.name = inp.value.trim(); commit('重新命名'); } else refreshLayers(); };
  inp.addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Enter') done(true); if (e.key === 'Escape') done(false); });
  inp.addEventListener('blur', () => done(true), { once: true });
}
const layerOps = {
  lyAdd() { commitAdjustIfAny(); const l = newLayer('圖層 ' + (S.layers.length + 1)); S.layers.splice(S.active + 1, 0, l); S.active++; commit('新增圖層'); },
  lyDup() { commitAdjustIfAny(); const s = activeLayer(); const l = newLayer(s.name + ' 拷貝', s.canvas.width, s.canvas.height); l.ctx.drawImage(s.canvas, 0, 0); l.opacity = s.opacity; l.blend = s.blend; S.layers.splice(S.active + 1, 0, l); S.active++; commit('複製圖層'); },
  lyDel() { if (S.layers.length < 2) return; commitAdjustIfAny(); S.layers.splice(S.active, 1); S.active = Math.max(0, S.active - 1); commit('刪除圖層'); },
  lyUp() { const i = S.active; if (i >= S.layers.length - 1) return; [S.layers[i], S.layers[i + 1]] = [S.layers[i + 1], S.layers[i]]; S.active++; commit('上移圖層'); },
  lyDown() { const i = S.active; if (i <= 0) return; [S.layers[i], S.layers[i - 1]] = [S.layers[i - 1], S.layers[i]]; S.active--; commit('下移圖層'); },
  lyMerge() {
    const i = S.active; if (i <= 0) return;
    commitAdjustIfAny();
    const top = S.layers[i], below = S.layers[i - 1];
    below.ctx.save(); below.ctx.globalAlpha = top.visible ? top.opacity : 0; below.ctx.globalCompositeOperation = top.blend;
    below.ctx.drawImage(top.canvas, 0, 0); below.ctx.restore();
    touch(below); S.layers.splice(i, 1); S.active = i - 1; commit('向下合併');
  },
};

/* ================= export ================= */
let downloadsApi = null;
if (window.claude && typeof window.claude.use === 'function') {
  window.claude.use('downloads').then(d => { downloadsApi = d; }).catch(() => {});
}
let exportUrl = null;
function exportCanvas() {
  commitAdjustIfAny();
  const scale = +$('#expScale').value, fmt = $('#expFmt').value;
  const w = Math.max(1, Math.round(S.w * scale)), h = Math.max(1, Math.round(S.h * scale));
  const flat = makeCanvas(S.w, S.h); composite(flat, flat.getContext('2d'), false);
  const out = makeCanvas(w, h), c = out.getContext('2d');
  if (fmt === 'jpg') { c.fillStyle = '#ffffff'; c.fillRect(0, 0, w, h); }
  c.imageSmoothingQuality = 'high';
  c.drawImage(flat, 0, 0, w, h);
  return out;
}
function exportBlob() {
  const fmt = $('#expFmt').value, q = +$('#expQuality').value / 100;
  const mime = { png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp' }[fmt];
  return new Promise(res => exportCanvas().toBlob(b => res(b), mime, q));
}
let previewTimer = 0;
async function refreshExportPreview() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    const blob = await exportBlob();
    if (!blob) return;
    if (exportUrl) URL.revokeObjectURL(exportUrl);
    exportUrl = URL.createObjectURL(blob);
    $('#expPreview').src = exportUrl;
    const scale = +$('#expScale').value;
    $('#expInfo').textContent = `${Math.round(S.w * scale)} × ${Math.round(S.h * scale)} px · 約 ${(blob.size / 1024 / 1024).toFixed(2)} MB`;
  }, 120);
}
function openExport() {
  $('#expQualityRow').hidden = $('#expFmt').value === 'png';
  openModal('#dlgExport');
  refreshExportPreview();
}
async function saveExport() {
  const blob = await exportBlob();
  if (!blob) { toast('匯出失敗，請改用較小的縮放'); return; }
  const fmt = $('#expFmt').value;
  const name = ($('#expName').value.trim() || 'darkroom').replace(/[\\/:*?"<>|]/g, '_') + '.' + fmt;
  if (downloadsApi) {
    try { await downloadsApi.save({ filename: name, data: blob }); toast('已儲存 ' + name); }
    catch (err) { if (err && err.code !== 'declined') toast('無法儲存：可長按預覽圖另存'); }
    return;
  }
  const file = new File([blob], name, { type: blob.type });
  if (isTouch && navigator.canShare && navigator.canShare({ files: [file] })) {
    try { await navigator.share({ files: [file], title: name }); return; } catch (err) { if (err && err.name === 'AbortError') return; }
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  toast('已下載 ' + name);
}

/* ================= modals, tabs, toast ================= */
let openDlg = null;
function openModal(sel) { closeModal(); openDlg = $(sel); openDlg.hidden = false; $('#scrim').hidden = false; }
function closeModal() { if (openDlg) openDlg.hidden = true; openDlg = null; if (!$('#panel').classList.contains('open')) $('#scrim').hidden = true; }
$$('[data-close]').forEach(b => b.addEventListener('click', closeModal));
$('#scrim').addEventListener('click', () => { if (openDlg) closeModal(); else togglePanel(false); });

let currentTab = 'layers';
function setTab(t) {
  currentTab = t;
  $$('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === t));
  $$('.tab-body').forEach(b => { b.hidden = b.dataset.body !== t; });
  if (t === 'filters') requestAnimationFrame(buildFilterThumbs);
}
$$('.tabs button').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
function togglePanel(force) {
  const p = $('#panel'), open = force ?? !p.classList.contains('open');
  p.classList.toggle('open', open);
  $('#scrim').hidden = !open && !openDlg;
}
$('#btnPanel').addEventListener('click', () => togglePanel());
$('#sheetGrip').addEventListener('click', () => togglePanel(false));

let toastTimer = 0;
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 1800);
}
function refreshInfo() {
  const mp = (S.w * S.h / 1e6).toFixed(2);
  $('#docInfo').innerHTML = `<dt>尺寸</dt><dd>${S.w} × ${S.h} px</dd><dt>像素</dt><dd>${mp} MP</dd><dt>長寬比</dt><dd>${ratioLabel(S.w, S.h)}</dd><dt>圖層</dt><dd>${S.layers.length}</dd><dt>歷史紀錄</dt><dd>${H.idx + 1} / ${H.max}</dd>`;
}
function ratioLabel(w, h) { const g = (a, b) => (b ? g(b, a % b) : a); const k = g(w, h); const a = w / k, b = h / k; return a <= 50 && b <= 50 ? `${a}:${b}` : (w / h).toFixed(3) + ':1'; }

/* ================= wiring ================= */
function bindRange(id, outId, fmt, set) {
  const i = $(id), o = $(outId);
  i.addEventListener('input', () => { set(+i.value); o.textContent = fmt(+i.value); render(); });
}
bindRange('#optSize', '#outSize', v => v, v => (S.size = v));
bindRange('#optOpacity', '#outOpacity', v => v + '%', v => (S.opacity = v));
bindRange('#optHardness', '#outHardness', v => v + '%', v => (S.hardness = v));
bindRange('#optTolerance', '#outTolerance', v => v, v => (S.tolerance = v));
$('#optColor').addEventListener('input', e => (S.color = e.target.value));
$('#optShape').addEventListener('change', e => (S.shape = e.target.value));
$('#optShapeFill').addEventListener('change', e => (S.shapeFill = e.target.checked));
$('#optRatio').addEventListener('change', e => {
  S.cropRatio = e.target.value;
  if (S.crop && S.cropRatio !== 'free') { const c = S.crop; S.crop = constrainCrop({ x: c.x, y: c.y }, { x: c.x + c.w, y: c.y + c.h }); render(); }
});
$('#btnCropApply').addEventListener('click', applyCrop);
$('#btnCropCancel').addEventListener('click', () => { S.crop = null; render(); });
SWATCHES.forEach(c => {
  const b = document.createElement('button'); b.style.background = c; b.title = c; b.setAttribute('aria-label', '顏色 ' + c);
  b.addEventListener('click', () => setColor(c)); $('#swatches').appendChild(b);
});

$$('#toolbar button').forEach(b => b.addEventListener('click', () => setTool(b.dataset.tool)));
$('#btnUndo').addEventListener('click', undo);
$('#btnRedo').addEventListener('click', redo);
$('#btnFit').addEventListener('click', fitView);
$('#btnOpen').addEventListener('click', () => $('#fileOpen').click());
$('#btnNew').addEventListener('click', () => openModal('#dlgNew'));
$('#btnExport').addEventListener('click', openExport);
$('#fileOpen').addEventListener('change', e => { openFile(e.target.files[0]); e.target.value = ''; });
$('#fileLayer').addEventListener('change', e => { openFile(e.target.files[0], true); e.target.value = ''; });

const blendSel = $('#layerBlend');
BLENDS.forEach(([v, t]) => { const o = document.createElement('option'); o.value = v; o.textContent = t; blendSel.appendChild(o); });
blendSel.addEventListener('change', () => { activeLayer().blend = blendSel.value; commit('混合模式'); });
const lop = $('#layerOpacity');
lop.addEventListener('input', () => { activeLayer().opacity = +lop.value / 100; $('#outLayerOpacity').textContent = lop.value + '%'; render(); });
lop.addEventListener('change', () => commit('圖層不透明度'));
Object.keys(layerOps).forEach(id => $('#' + id).addEventListener('click', layerOps[id]));
$$('[data-img]').forEach(b => b.addEventListener('click', () => imageOps[b.dataset.img]()));

$('#adjApply').addEventListener('click', applyAdjust);
$('#adjReset').addEventListener('click', () => resetAdjust());
$('#txtApply').addEventListener('click', applyText);
$('#rsApply').addEventListener('click', applyResize);
$('#rsW').addEventListener('input', () => { if ($('#rsLock').checked) $('#rsH').value = Math.max(1, Math.round(+$('#rsW').value * S.h / S.w)); });
$('#rsH').addEventListener('input', () => { if ($('#rsLock').checked) $('#rsW').value = Math.max(1, Math.round(+$('#rsH').value * S.w / S.h)); });

const PRESETS = [['Full HD', 1920, 1080], ['4K', 3840, 2160], ['IG 方形', 1080, 1080], ['IG 限動', 1080, 1920], ['A4 150dpi', 1240, 1754], ['A3 150dpi', 1754, 2480]];
PRESETS.forEach(([n, w, h]) => {
  const b = document.createElement('button'); b.textContent = n;
  b.addEventListener('click', () => { $('#newW').value = w; $('#newH').value = h; });
  $('#newPresets').appendChild(b);
});
$('#newApply').addEventListener('click', () => {
  const w = clamp(Math.round(+$('#newW').value), 1, 8192), h = clamp(Math.round(+$('#newH').value), 1, 8192);
  closeModal(); newDocument(w, h, $('#newBg').value);
});

['#expFmt', '#expScale'].forEach(s => $(s).addEventListener('change', () => { $('#expQualityRow').hidden = $('#expFmt').value === 'png'; refreshExportPreview(); }));
$('#expQuality').addEventListener('input', e => { $('#outExpQuality').textContent = e.target.value; refreshExportPreview(); });
$('#expSave').addEventListener('click', saveExport);

// drag & drop, paste
let dragDepth = 0;
stage.addEventListener('dragenter', e => { e.preventDefault(); dragDepth++; $('#drop').hidden = false; });
stage.addEventListener('dragover', e => e.preventDefault());
stage.addEventListener('dragleave', () => { if (--dragDepth <= 0) { dragDepth = 0; $('#drop').hidden = true; } });
stage.addEventListener('drop', e => {
  e.preventDefault(); dragDepth = 0; $('#drop').hidden = true;
  const f = [...e.dataTransfer.files].find(x => x.type.startsWith('image/'));
  if (f) openFile(f, e.shiftKey);
});
window.addEventListener('paste', e => {
  const item = [...(e.clipboardData?.items || [])].find(i => i.type.startsWith('image/'));
  if (item) { e.preventDefault(); openFile(item.getAsFile(), true); }
});

// keyboard
const KEYS = { v: 'move', h: 'hand', c: 'crop', b: 'brush', e: 'eraser', u: 'shape', g: 'fill', t: 'text', i: 'eyedropper' };
window.addEventListener('keydown', e => {
  if (e.target.matches('input, textarea, select')) {
    if (openDlg && e.key === 'Escape') closeModal();
    if (openDlg === $('#dlgText') && e.key === 'Enter' && (e.ctrlKey || e.metaKey)) applyText();
    return;
  }
  const mod = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
  if (e.key === 'Escape') { if (openDlg) closeModal(); else if (S.crop) { S.crop = null; render(); } return; }
  if (openDlg) return;
  if (mod && k === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (mod && k === 'y') { e.preventDefault(); redo(); return; }
  if (mod && k === 's') { e.preventDefault(); openExport(); return; }
  if (mod && k === 'o') { e.preventDefault(); $('#fileOpen').click(); return; }
  if (mod && k === '0') { e.preventDefault(); fitView(); return; }
  if (mod && (k === '=' || k === '+')) { e.preventDefault(); const r = stage.getBoundingClientRect(); zoomAt(1.25, r.width / 2, r.height / 2); return; }
  if (mod && k === '-') { e.preventDefault(); const r = stage.getBoundingClientRect(); zoomAt(0.8, r.width / 2, r.height / 2); return; }
  if (mod && k === 'j') { e.preventDefault(); layerOps.lyDup(); return; }
  if (mod && k === 'e') { e.preventDefault(); layerOps.lyMerge(); return; }
  if (mod) return;
  if (e.key === ' ') { e.preventDefault(); if (!spaceDown) { spaceDown = true; view.style.cursor = 'grab'; } return; }
  if (e.key === 'Enter' && S.crop) { applyCrop(); return; }
  if (e.key === '1') { const r = stage.getBoundingClientRect(); zoomAt(1 / S.zoom, r.width / 2, r.height / 2); return; }
  if (e.key === '[') { S.size = Math.max(1, Math.round(S.size / 1.2)); $('#optSize').value = S.size; $('#outSize').textContent = S.size; render(); return; }
  if (e.key === ']') { S.size = Math.min(400, Math.round(S.size * 1.2) + 1); $('#optSize').value = S.size; $('#outSize').textContent = S.size; render(); return; }
  if ((e.key === 'Delete' || e.key === 'Backspace')) { imageOps.clearLayer(); return; }
  if (KEYS[k]) setTool(KEYS[k]);
});
window.addEventListener('keyup', e => { if (e.key === ' ') { spaceDown = false; setCursor(); } });

new ResizeObserver(() => render()).observe(stage);
window.addEventListener('beforeunload', e => { if (H.idx > 0) { e.preventDefault(); e.returnValue = ''; } });

/* ================= boot ================= */
buildAdjustUI();
buildFilterUI();
setTool('brush');
requestAnimationFrame(() => { makeSample(); toast('已載入範例照片，按「開啟」換成你的照片'); });

if ('serviceWorker' in navigator && !window.claude && /^https:|^http:\/\/localhost/.test(location.href)) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
})();
