/* 暗房 Darkroom — photo & video clip editor.
   Clips play in sequence on one canvas; each clip can have a transition in, motion (photos),
   trim + speed + volume (videos), a colour filter and a caption. Export records the canvas
   and mixed audio in real time with MediaRecorder. */
(() => {
'use strict';
const D = window.Darkroom;
const { $, $$, clamp } = D;

const canvas = $('#vCanvas');
const ctx = canvas.getContext('2d');
const tl = $('#vTimeline');
const PPS = 34;          // timeline pixels per second
const MIN_W = 60;        // narrowest clip tile
let uid = 0;

const P = {               // project
  clips: [], sel: -1,
  aspect: '16:9', res: 720,
  music: null,           // { name, el, volume, fade }
};
let t = 0, playing = false, lastNow = 0, exporting = null;

const FILTERS = {
  none: ['無', ''], mono: ['黑白', 'grayscale(1)'], sepia: ['懷舊', 'sepia(.85)'],
  warm: ['暖陽', 'sepia(.25) saturate(1.35) hue-rotate(-8deg)'], cool: ['冷調', 'saturate(.85) hue-rotate(14deg) brightness(1.04)'],
  vivid: ['鮮豔', 'saturate(1.5) contrast(1.1)'], fade: ['褪色', 'contrast(.82) saturate(.7) brightness(1.08)'],
  noir: ['高反差黑白', 'grayscale(1) contrast(1.5)'],
};
const TRANSITIONS = { none: '無', fade: '交叉淡化', black: '黑場轉場', slide: '向左滑入', zoom: '縮放進入' };
const MOTIONS = { none: '靜止', zoomIn: '緩慢放大', zoomOut: '緩慢縮小', panL: '向左平移', panR: '向右平移' };

/* ================= helpers ================= */
const fmt = s => { s = Math.max(0, s); const m = Math.floor(s / 60); return `${m}:${(s - m * 60).toFixed(1).padStart(4, '0')}`; };
const clipDur = c => c.type === 'video' ? Math.max(0.1, (c.out - c.in) / c.speed) : c.dur;
const total = () => P.clips.reduce((a, c) => a + clipDur(c), 0);
function clipStart(i) { let s = 0; for (let j = 0; j < i; j++) s += clipDur(P.clips[j]); return s; }
function locate(time) {
  let s = 0;
  for (let i = 0; i < P.clips.length; i++) {
    const d = clipDur(P.clips[i]);
    if (time < s + d || i === P.clips.length - 1) return { i, local: clamp(time - s, 0, d), start: s };
    s += d;
  }
  return { i: -1, local: 0, start: 0 };
}
const ease = x => x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
const once = (el, ev) => new Promise(r => el.addEventListener(ev, r, { once: true }));

function sizeCanvas() {
  const [a, b] = P.aspect.split(':').map(Number);
  const short = P.res;
  let w, h;
  if (a >= b) { h = short; w = Math.round(short * a / b); } else { w = short; h = Math.round(short * b / a); }
  w -= w % 2; h -= h % 2;
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
}

/* ================= audio graph (needed for export and iOS volume) ================= */
let actx = null, master = null, recDest = null;
function ensureAudio() {
  if (actx) { if (actx.state === 'suspended') actx.resume(); return true; }
  try {
    actx = new (window.AudioContext || window.webkitAudioContext)();
    master = actx.createGain(); master.connect(actx.destination);
  } catch (_) { actx = null; return false; }
  P.clips.forEach(attachAudio);
  if (P.music) attachAudio(P.music);
  return true;
}
function attachAudio(item) {
  const el = item.video || item.el;
  if (!actx || !el || item.gain) return;
  try {
    const src = actx.createMediaElementSource(el);
    item.gain = actx.createGain(); item.gain.gain.value = 0;
    src.connect(item.gain).connect(master);
  } catch (_) { /* element volume stays as fallback */ }
}
function setVolume(item, v) {
  if (item.gain) item.gain.gain.value = v;
  else { const el = item.video || item.el; try { el.volume = clamp(v, 0, 1); } catch (_) {} }
}

/* ================= adding media ================= */
const hidden = document.createElement('div');
hidden.style.cssText = 'position:fixed;width:1px;height:1px;left:-10px;top:-10px;overflow:hidden;opacity:0;pointer-events:none';
document.body.appendChild(hidden);

function baseClip(type, name) {
  return {
    id: ++uid, type, name,
    transition: P.clips.length ? 'fade' : 'black', tdur: 0.6,
    filter: 'none', fit: 'cover',
    text: '', textPos: 'bottom', textSize: 6,
  };
}
function thumbFrom(src, sw, sh) {
  const h = 64, w = Math.max(1, Math.round(h * sw / sh));
  const c = D.makeCanvas(w, h); c.getContext('2d').drawImage(src, 0, 0, w, h);
  return c.toDataURL('image/jpeg', 0.7);
}
function addImageClip(src, name, opts = {}) {
  const c = Object.assign(baseClip('image', name), { src, w: src.width, h: src.height, dur: 3, motion: 'zoomIn' }, opts);
  c.thumb = thumbFrom(src, c.w, c.h);
  P.clips.push(c);
  return c;
}
async function addVideoClip(file) {
  const v = document.createElement('video');
  v.playsInline = true; v.setAttribute('playsinline', ''); v.preload = 'auto'; v.crossOrigin = 'anonymous';
  v.src = URL.createObjectURL(file);
  hidden.appendChild(v);
  await Promise.race([once(v, 'loadedmetadata'), once(v, 'error').then(() => { throw new Error('bad video'); })]);
  if (!isFinite(v.duration)) { v.currentTime = 1e7; await Promise.race([once(v, 'durationchange'), new Promise(r => setTimeout(r, 1500))]); v.currentTime = 0; }
  const duration = isFinite(v.duration) ? v.duration : 10;
  const c = Object.assign(baseClip('video', file.name.replace(/\.[^.]+$/, '')), {
    video: v, duration, in: 0, out: duration, speed: 1, volume: 1, w: v.videoWidth, h: v.videoHeight,
  });
  v.addEventListener('seeked', () => { if (!playing) drawAt(t); });
  attachAudio(c);
  v.currentTime = Math.min(0.5, duration / 2);
  await Promise.race([once(v, 'seeked'), new Promise(r => setTimeout(r, 1500))]);
  c.thumb = thumbFrom(v, c.w || 16, c.h || 9);
  P.clips.push(c);
  return c;
}
async function addFiles(files) {
  const list = [...files];
  if (!list.length) return;
  D.toast(`讀取 ${list.length} 個檔案…`);
  let added = 0;
  for (const f of list) {
    try {
      if (f.type.startsWith('video/')) { await addVideoClip(f); added++; }
      else if (f.type.startsWith('image/')) {
        const bmp = await createImageBitmap(f, { imageOrientation: 'from-image' }).catch(() => null) || await imgFromFile(f);
        addImageClip(bmp, f.name.replace(/\.[^.]+$/, '')); added++;
      }
    } catch (err) { console.error(err); D.toast('無法讀取：' + f.name); }
  }
  if (added) { P.sel = P.clips.length - 1; refresh(); D.toast(`已加入 ${added} 個素材`); }
}
function imgFromFile(f) {
  return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = URL.createObjectURL(f); });
}

/* ================= drawing ================= */
function drawSource(src, sw, sh, fit, scale = 1, panX = 0) {
  const W = canvas.width, H = canvas.height;
  if (!sw || !sh) return;
  if (fit === 'contain') {
    // blurred cover fill behind: downscale then upscale = cheap blur that works everywhere
    const tiny = drawSource.tiny || (drawSource.tiny = D.makeCanvas(24, 24));
    const tc = tiny.getContext('2d');
    const cs = Math.max(24 / sw, 24 / sh);
    tc.clearRect(0, 0, 24, 24);
    tc.drawImage(src, (24 - sw * cs) / 2, (24 - sh * cs) / 2, sw * cs, sh * cs);
    ctx.save(); ctx.imageSmoothingQuality = 'high'; ctx.globalAlpha *= 0.85; ctx.drawImage(tiny, 0, 0, W, H); ctx.restore();
    const s = Math.min(W / sw, H / sh) * scale;
    ctx.drawImage(src, (W - sw * s) / 2 + panX * W, (H - sh * s) / 2, sw * s, sh * s);
    return;
  }
  const s = Math.max(W / sw, H / sh) * scale;
  const dw = sw * s, dh = sh * s;
  const room = (dw - W) / 2;
  ctx.drawImage(src, (W - dw) / 2 + clamp(panX * W, -room, room), (H - dh) / 2, dw, dh);
}
function drawClip(c, local, alpha = 1, dx = 0, zoom = 1) {
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha = alpha;
  if (dx) ctx.translate(dx, 0);
  if (zoom !== 1) { ctx.translate(canvas.width / 2, canvas.height / 2); ctx.scale(zoom, zoom); ctx.translate(-canvas.width / 2, -canvas.height / 2); }
  ctx.filter = FILTERS[c.filter][1] || 'none';
  if (c.type === 'image') {
    const u = clamp(local / c.dur, 0, 1);
    let scale = 1, pan = 0;
    if (c.motion === 'zoomIn') scale = 1 + 0.14 * u;
    else if (c.motion === 'zoomOut') scale = 1.14 - 0.14 * u;
    else if (c.motion === 'panL') { scale = 1.15; pan = 0.07 - 0.14 * u; }
    else if (c.motion === 'panR') { scale = 1.15; pan = -0.07 + 0.14 * u; }
    drawSource(c.src, c.w, c.h, c.fit, scale, pan);
  } else if (c.video.readyState >= 2) {
    drawSource(c.video, c.video.videoWidth, c.video.videoHeight, c.fit);
  }
  ctx.filter = 'none';
  ctx.restore();
}
function drawCaption(c, local) {
  if (!c.text.trim()) return;
  const d = clipDur(c);
  const a = clamp(Math.min(local / 0.35, (d - local) / 0.35), 0, 1);
  if (a <= 0) return;
  const W = canvas.width, H = canvas.height, size = Math.round(Math.min(W, H) * c.textSize / 100);
  const lines = c.text.split('\n');
  ctx.save();
  ctx.globalAlpha = a;
  ctx.font = `700 ${size}px "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const lh = size * 1.3, block = lh * lines.length;
  const y0 = c.textPos === 'top' ? H * 0.1 + lh / 2 : c.textPos === 'center' ? H / 2 - block / 2 + lh / 2 : H * 0.9 - block + lh / 2;
  ctx.shadowColor = 'rgba(0,0,0,.65)'; ctx.shadowBlur = size * 0.25; ctx.shadowOffsetY = size * 0.05;
  ctx.fillStyle = '#fff';
  lines.forEach((ln, k) => ctx.fillText(ln, W / 2, y0 + k * lh + (1 - a) * size * 0.3));
  ctx.restore();
}
function drawAt(time) {
  sizeCanvas();
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  if (!P.clips.length) return;
  const { i, local } = locate(time);
  const c = P.clips[i], prev = P.clips[i - 1];
  const td = Math.min(c.tdur, clipDur(c) * 0.6);
  // at rest on 0:00 show the first frame instead of the black fade-in
  const intro = time === 0 && !playing;
  if (c.transition !== 'none' && local < td && !intro) {
    const p = ease(local / td);
    switch (c.transition) {
      case 'fade':
        if (prev) drawClip(prev, clipDur(prev));
        drawClip(c, local, p); break;
      case 'black':
        if (prev && p < 0.5) drawClip(prev, clipDur(prev), 1 - p * 2);
        else if (!prev || p >= 0.5) drawClip(c, local, prev ? p * 2 - 1 : p);
        break;
      case 'slide':
        if (prev) drawClip(prev, clipDur(prev), 1, -p * W);
        drawClip(c, local, 1, (1 - p) * W); break;
      case 'zoom':
        if (prev) drawClip(prev, clipDur(prev), 1 - p);
        drawClip(c, local, p, 0, 0.82 + 0.18 * p); break;
    }
  } else drawClip(c, local);
  drawCaption(c, intro ? Math.min(0.5, clipDur(c) / 2) : local);
}

/* ================= playback ================= */
function syncMedia() {
  const { i, local } = locate(t);
  const c = P.clips[i];
  P.clips.forEach(k => {
    if (k.type !== 'video') return;
    if (k !== c) {
      setVolume(k, 0);
      if (!k.video.paused) k.video.pause();
      // the previous clip must show its last frame during a transition
      if (!playing && k === P.clips[i - 1] && local < c.tdur) seek(k, k.out - 0.05);
    }
  });
  if (c && c.type === 'video') {
    const v = c.video, mt = c.in + local * c.speed;
    v.playbackRate = c.speed;
    setVolume(c, c.volume);
    if (playing) {
      if (v.paused && !c.pending && !c.failed && mt < c.out - 0.05) {
        if (Math.abs(v.currentTime - mt) > 0.12) v.currentTime = mt;
        c.pending = true;
        const pr = v.play();
        if (pr) pr.then(() => { c.pending = false; }).catch(() => { c.pending = false; c.failed = true; D.toast('影片無法播放，請再按一次 ▶'); });
        else c.pending = false;
      }
    } else seek(c, mt);
  }
  if (P.music) {
    const m = P.music, el = m.el;
    let vol = m.volume;
    if (m.fade) vol *= clamp((total() - t) / 2, 0, 1);
    setVolume(m, vol);
  }
}
function seek(c, mt) {
  const v = c.video;
  mt = clamp(mt, 0, c.duration - 0.01);
  if (!v.seeking && Math.abs(v.currentTime - mt) > 0.04) v.currentTime = mt;
}
function play() {
  if (!P.clips.length) return;
  ensureAudio();
  if (t >= total() - 0.05) t = 0;
  // unlock every video inside this tap so later play() calls are allowed (iOS)
  P.clips.forEach(c => {
    if (c.type === 'video' && !c.unlocked) {
      c.unlocked = true; setVolume(c, 0);
      const pr = c.video.play(); if (pr) pr.then(() => { if (!playing || P.clips[locate(t).i] !== c) c.video.pause(); }).catch(() => {});
    }
  });
  P.clips.forEach(c => { c.failed = false; });
  playing = true; lastNow = performance.now();
  if (P.music) { const el = P.music.el; try { el.currentTime = el.duration ? t % el.duration : 0; } catch (_) {} el.play().catch(() => {}); }
  setPlayIcon(); loop();
}
function pause() {
  playing = false;
  P.clips.forEach(c => { if (c.type === 'video') { c.video.pause(); c.pending = false; } });
  if (P.music) P.music.el.pause();
  setPlayIcon(); syncMedia(); drawAt(t); updateTime();
}
function loop() {
  if (!playing) return;
  const now = performance.now();
  const { i, start } = locate(t);
  const c = P.clips[i];
  const dt = Math.min(0.1, (now - lastNow) / 1000);
  lastNow = now;
  if (c.type === 'video' && c.pending) { /* wait for the video to actually start */ }
  else if (c.type === 'video' && !c.video.paused && !c.video.seeking) {
    const vt = start + (c.video.currentTime - c.in) / c.speed;
    t = c.video.currentTime >= c.out - 0.02 ? start + clipDur(c) + 0.0005 : Math.max(t, vt);
  } else t += dt;
  const T = total();
  if (t >= T) { t = T; playing = false; P.clips.forEach(k => k.type === 'video' && k.video.pause()); if (P.music) P.music.el.pause(); drawAt(T - 0.001); setPlayIcon(); updateTime(); if (exporting) exporting.finish(); return; }
  syncMedia(); drawAt(t); updateTime();
  if (exporting) exporting.progress(t / T);
  requestAnimationFrame(loop);
}
function setPlayIcon() {
  $('#vPlayIcon').innerHTML = playing ? '<path d="M7 4h4v16H7zM14 4h4v16h-4z"/>' : '<path d="M7 4v16l13-8z"/>';
  $('#vPlay').setAttribute('aria-label', playing ? '暫停' : '播放');
}
function seekTo(time) {
  t = clamp(time, 0, total());
  if (playing) { P.clips.forEach(c => { if (c.type === 'video') { c.video.pause(); c.pending = false; } }); lastNow = performance.now(); }
  syncMedia(); drawAt(t); updateTime();
}
function updateTime() {
  const T = total();
  $('#vTime').textContent = `${fmt(t)} / ${fmt(T)}`;
  $('#vSeek').value = T ? Math.round(t / T * 1000) : 0;
  placePlayhead();
}

/* ================= timeline ================= */
function tileWidth(c) { return Math.max(MIN_W, clipDur(c) * PPS); }
function renderTimeline() {
  tl.innerHTML = '';
  P.clips.forEach((c, i) => {
    const el = document.createElement('div');
    el.className = 'vclip' + (i === P.sel ? ' on' : '');
    el.style.width = tileWidth(c) + 'px';
    el.style.backgroundImage = `url(${c.thumb})`;
    el.dataset.i = i;
    el.innerHTML = `${i > 0 && c.transition !== 'none' ? '<span class="vtr" title="轉場"></span>' : ''}${c.text.trim() ? '<span class="vcap">T</span>' : ''}<span class="vlabel"><span>${c.type === 'video' ? '▶' : '▣'} ${i + 1}</span><span>${clipDur(c).toFixed(1)}s</span></span>`;
    tl.appendChild(el);
  });
  const add = document.createElement('button');
  add.className = 'vadd'; add.setAttribute('aria-label', '加入素材'); add.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>';
  add.addEventListener('click', () => $('#vFile').click());
  tl.appendChild(add);
  const ph = document.createElement('div'); ph.className = 'vplayhead'; ph.id = 'vPlayhead'; tl.appendChild(ph);
  placePlayhead();
}
function placePlayhead() {
  const ph = $('#vPlayhead');
  if (!ph) return;
  if (!P.clips.length) { ph.hidden = true; return; }
  ph.hidden = false;
  const { i, local } = locate(t);
  const el = tl.children[i];
  if (!el) return;
  ph.style.left = (el.offsetLeft + local / clipDur(P.clips[i]) * el.offsetWidth - 1) + 'px';
}
// click selects and seeks; mouse drag reorders
let drag = null;
tl.addEventListener('pointerdown', e => {
  const el = e.target.closest('.vclip');
  if (!el) return;
  const i = +el.dataset.i;
  drag = { i, x0: e.clientX, el, active: false, mouse: e.pointerType === 'mouse', to: i };
  if (drag.mouse) tl.setPointerCapture(e.pointerId);
});
tl.addEventListener('pointermove', e => {
  if (!drag || !drag.mouse) return;
  if (!drag.active && Math.abs(e.clientX - drag.x0) > 6) { drag.active = true; drag.el.classList.add('dragging'); }
  if (!drag.active) return;
  const tiles = [...tl.querySelectorAll('.vclip')];
  let to = tiles.length;
  for (let k = 0; k < tiles.length; k++) { const r = tiles[k].getBoundingClientRect(); if (e.clientX < r.left + r.width / 2) { to = k; break; } }
  drag.to = to;
  let mark = $('.vdrop', tl);
  if (!mark) { mark = document.createElement('div'); mark.className = 'vdrop'; tl.appendChild(mark); }
  const ref = tiles[to] || tl.querySelector('.vadd');
  mark.style.left = (ref.offsetLeft - 3) + 'px';
});
tl.addEventListener('pointerup', e => {
  if (!drag) return;
  const d = drag; drag = null;
  if (d.active) {
    let to = d.to; if (to > d.i) to--;
    if (to !== d.i) { const [c] = P.clips.splice(d.i, 1); P.clips.splice(to, 0, c); P.sel = to; seekTo(clipStart(to)); }
    refresh(); return;
  }
  const r = d.el.getBoundingClientRect();
  P.sel = d.i;
  seekTo(clipStart(d.i) + clamp((e.clientX - r.left) / r.width, 0, 0.999) * clipDur(P.clips[d.i]));
  renderTimeline(); renderProps();
});
tl.addEventListener('pointercancel', () => { drag = null; renderTimeline(); });

/* ================= properties panel ================= */
const opts = (map, cur) => Object.entries(map).map(([k, v]) => `<option value="${k}"${k === cur ? ' selected' : ''}>${Array.isArray(v) ? v[0] : v}</option>`).join('');
function esc(s) { return s.replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]); }
function renderProps() {
  const box = $('#vProps');
  const c = P.clips[P.sel];
  let html = '';
  if (c) {
    html += `<div class="clip-head"><span class="tag">${c.type === 'video' ? '影片' : '照片'}</span><b>${esc(c.name)}</b>
      <button class="ibtn" data-act="left" aria-label="往前移" title="往前移"${P.sel === 0 ? ' disabled' : ''}><svg viewBox="0 0 24 24"><path d="m15 6-6 6 6 6"/></svg></button>
      <button class="ibtn" data-act="right" aria-label="往後移" title="往後移"${P.sel === P.clips.length - 1 ? ' disabled' : ''}><svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg></button>
      <button class="ibtn" data-act="dup" aria-label="複製片段" title="複製片段"><svg viewBox="0 0 24 24"><rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></svg></button>
      <button class="ibtn danger" data-act="del" aria-label="刪除片段" title="刪除片段 (Delete)"><svg viewBox="0 0 24 24"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg></button></div>`;
    if (c.type === 'image') {
      html += `<h3>照片</h3>
        <label class="row"><span>長度</span><input type="range" data-k="dur" min="0.5" max="15" step="0.5" value="${c.dur}"><output>${c.dur.toFixed(1)}s</output></label>
        <label class="row"><span>動態效果</span><select data-k="motion">${opts(MOTIONS, c.motion)}</select></label>`;
    } else {
      html += `<h3>影片剪輯</h3>
        <label class="row"><span>起點</span><input type="range" data-k="in" min="0" max="${c.duration.toFixed(2)}" step="0.05" value="${c.in}"><output>${fmt(c.in)}</output></label>
        <label class="row"><span>終點</span><input type="range" data-k="out" min="0" max="${c.duration.toFixed(2)}" step="0.05" value="${c.out}"><output>${fmt(c.out)}</output></label>
        <label class="row"><span>速度</span><select data-k="speed">${opts({ 0.25: '0.25×', 0.5: '0.5× 慢動作', 1: '1×', 1.5: '1.5×', 2: '2×', 4: '4× 縮時' }, String(c.speed))}</select></label>
        <label class="row"><span>音量</span><input type="range" data-k="volume" min="0" max="1" step="0.05" value="${c.volume}"><output>${Math.round(c.volume * 100)}%</output></label>
        <button class="btn sm" data-act="split">在播放位置分割</button>`;
    }
    html += `<label class="row"><span>畫面</span><select data-k="fit">${opts({ cover: '填滿（裁切邊緣）', contain: '完整（模糊背景）' }, c.fit)}</select></label>
      <label class="row"><span>濾鏡</span><select data-k="filter">${opts(FILTERS, c.filter)}</select></label>
      <h3>轉場（進入此片段）</h3>
      <label class="row"><span>效果</span><select data-k="transition">${opts(TRANSITIONS, c.transition)}</select></label>
      <label class="row"><span>長度</span><input type="range" data-k="tdur" min="0.2" max="2" step="0.1" value="${c.tdur}"><output>${c.tdur.toFixed(1)}s</output></label>
      <h3>字幕</h3>
      <label class="row"><span>文字</span><input type="text" data-k="text" value="${esc(c.text)}" placeholder="輸入字幕（可留空）"></label>
      <label class="row"><span>位置</span><select data-k="textPos">${opts({ top: '上方', center: '中間', bottom: '下方' }, c.textPos)}</select></label>
      <label class="row"><span>大小</span><input type="range" data-k="textSize" min="3" max="16" step="0.5" value="${c.textSize}"><output>${c.textSize}</output></label>`;
  } else {
    html += `<p class="note">點選時間軸上的片段來編輯長度、轉場、濾鏡與字幕。</p>`;
  }
  html += `<h3>背景音樂</h3>`;
  if (P.music) {
    html += `<div class="clip-head"><span class="tag">音樂</span><b>${esc(P.music.name)}</b><button class="ibtn danger" data-act="musicDel" aria-label="移除音樂"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div>
      <label class="row"><span>音量</span><input type="range" data-m="volume" min="0" max="1" step="0.05" value="${P.music.volume}"><output>${Math.round(P.music.volume * 100)}%</output></label>
      <label class="row"><input type="checkbox" data-m="fade"${P.music.fade ? ' checked' : ''}><span>結尾 2 秒淡出</span></label>`;
  } else html += `<button class="btn sm" data-act="music">選擇音樂檔…</button>`;
  html += `<p class="note small">總長度 ${fmt(total())} · ${canvas.width}×${canvas.height}</p>`;
  box.innerHTML = html;
}
$('#vProps').addEventListener('input', e => {
  const k = e.target.dataset.k, m = e.target.dataset.m;
  const out = e.target.parentElement.querySelector('output');
  if (m) {
    P.music[m] = e.target.type === 'checkbox' ? e.target.checked : +e.target.value;
    if (out) out.textContent = Math.round(P.music.volume * 100) + '%';
    syncMedia(); return;
  }
  const c = P.clips[P.sel];
  if (!c || !k) return;
  let v = e.target.type === 'range' || k === 'speed' ? +e.target.value : e.target.value;
  if (k === 'in') { v = Math.min(v, c.out - 0.2); e.target.value = v; }
  if (k === 'out') { v = Math.max(v, c.in + 0.2); e.target.value = v; }
  c[k] = v;
  if (out) out.textContent = k === 'in' || k === 'out' ? fmt(v) : k === 'volume' ? Math.round(v * 100) + '%' : k === 'textSize' ? v : v.toFixed ? v.toFixed(1) + 's' : v;
  const start = clipStart(P.sel);
  if (k === 'in') t = start;
  else if (k === 'out') t = start + clipDur(c) - 0.01;
  else if (k === 'transition' || k === 'tdur') t = start + Math.min(c.tdur, clipDur(c)) * 0.5;
  else if (k === 'text' || k === 'textPos' || k === 'textSize') t = start + Math.min(clipDur(c) / 2, 1);
  else t = clamp(t, start, start + clipDur(c) - 0.01);
  renderTimeline(); syncMedia(); drawAt(t); updateTime();
});
$('#vProps').addEventListener('change', e => { if (e.target.dataset.k === 'speed' || e.target.dataset.k === 'transition') renderProps(); });
$('#vProps').addEventListener('click', e => {
  const b = e.target.closest('[data-act]');
  if (!b) return;
  const i = P.sel, c = P.clips[i];
  switch (b.dataset.act) {
    case 'left': if (i > 0) { [P.clips[i - 1], P.clips[i]] = [P.clips[i], P.clips[i - 1]]; P.sel--; } break;
    case 'right': if (i < P.clips.length - 1) { [P.clips[i + 1], P.clips[i]] = [P.clips[i], P.clips[i + 1]]; P.sel++; } break;
    case 'del': removeClip(i); break;
    case 'dup': {
      const copy = Object.assign({}, c, { id: ++uid, gain: null, unlocked: false, pending: false });
      if (c.type === 'video') {
        const v = document.createElement('video'); v.playsInline = true; v.preload = 'auto'; v.src = c.video.src; hidden.appendChild(v);
        v.addEventListener('seeked', () => { if (!playing) drawAt(t); });
        copy.video = v; attachAudio(copy);
      }
      P.clips.splice(i + 1, 0, copy); P.sel = i + 1; break;
    }
    case 'split': splitAtPlayhead(); return;
    case 'music': $('#vMusicFile').click(); return;
    case 'musicDel': if (P.music) { P.music.el.pause(); P.music = null; } break;
  }
  refresh();
});
function removeClip(i) {
  const c = P.clips[i];
  if (!c) return;
  if (c.type === 'video') { c.video.pause(); if (!P.clips.some(k => k !== c && k.video && k.video.src === c.video.src)) URL.revokeObjectURL(c.video.src); c.video.remove(); }
  P.clips.splice(i, 1);
  P.sel = Math.min(i, P.clips.length - 1);
  t = clamp(t, 0, total());
  refresh();
}
function splitAtPlayhead() {
  const { i, local } = locate(t);
  const c = P.clips[i];
  if (!c || c.type !== 'video' || local < 0.2 || clipDur(c) - local < 0.2) { D.toast('把播放位置移到這段影片中間再分割'); return; }
  const at = c.in + local * c.speed;
  const v = document.createElement('video'); v.playsInline = true; v.preload = 'auto'; v.src = c.video.src; hidden.appendChild(v);
  v.addEventListener('seeked', () => { if (!playing) drawAt(t); });
  const b = Object.assign({}, c, { id: ++uid, video: v, in: at, gain: null, unlocked: false, pending: false, transition: 'none' });
  attachAudio(b);
  c.out = at;
  P.clips.splice(i + 1, 0, b);
  P.sel = i + 1;
  refresh(); D.toast('已分割成兩段');
}

/* ================= export ================= */
function pickMime() {
  const list = ['video/mp4;codecs=avc1.42E01E,mp4a.40.2', 'video/mp4;codecs=avc1', 'video/mp4', 'video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm'];
  return list.find(m => window.MediaRecorder && MediaRecorder.isTypeSupported(m)) || '';
}
async function exportVideo() {
  if (!P.clips.length) { D.toast('先加入照片或影片'); return; }
  if (!window.MediaRecorder || !canvas.captureStream) { D.toast('這個瀏覽器不支援影片匯出，請改用 Chrome、Edge 或 Safari'); return; }
  pause();
  ensureAudio();
  const mime = pickMime();
  const ext = mime.includes('mp4') ? 'mp4' : 'webm';
  const vs = canvas.captureStream(30);
  const tracks = [...vs.getVideoTracks()];
  if (actx) {
    recDest = actx.createMediaStreamDestination();
    master.disconnect(); master.connect(recDest);   // record the mix silently
    tracks.push(...recDest.stream.getAudioTracks());
  }
  const rec = new MediaRecorder(new MediaStream(tracks), mime ? { mimeType: mime, videoBitsPerSecond: P.res >= 1080 ? 9e6 : 5e6 } : undefined);
  const chunks = [];
  rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
  let cancelled = false;
  const done = new Promise(res => { rec.onstop = res; });
  D.openModal('#dlgRender');
  $('#vRenderBar').style.width = '0%'; $('#vRenderStatus').textContent = '0%';
  const cleanup = () => {
    exporting = null;
    vs.getTracks().forEach(tr => tr.stop());
    if (actx) { master.disconnect(); master.connect(actx.destination); }
    D.closeModal();
  };
  exporting = {
    progress(p) { $('#vRenderBar').style.width = (p * 100).toFixed(1) + '%'; $('#vRenderStatus').textContent = Math.round(p * 100) + '%'; },
    finish() { setTimeout(() => rec.state !== 'inactive' && rec.stop(), 250); },
    cancel() { cancelled = true; pause(); if (rec.state !== 'inactive') rec.stop(); },
  };
  t = 0; syncMedia(); drawAt(0);
  // let video seeks settle on the first frame
  await new Promise(r => setTimeout(r, 300));
  rec.start(500);
  play();
  await done;
  cleanup();
  if (cancelled) { D.toast('已取消匯出'); return; }
  const blob = new Blob(chunks, { type: mime || 'video/webm' });
  await D.saveBlob(blob, `darkroom-video-${new Date().toISOString().slice(0, 10)}.${ext}`);
}
$('#vRenderCancel').addEventListener('click', () => exporting && exporting.cancel());

/* ================= mode switching & wiring ================= */
let sampleOffered = false;
function setMode(mode) {
  document.body.dataset.mode = mode;
  $$('#modeSeg button').forEach(b => b.classList.toggle('on', b.dataset.mode === mode));
  $('#videoView').hidden = mode !== 'video';
  if (mode === 'video') {
    if (!P.clips.length && !sampleOffered) { sampleOffered = true; buildSample(); }
    refresh();
  } else {
    if (playing) pause();
    requestAnimationFrame(() => D.render());
  }
}
function refresh() {
  sizeCanvas();
  $('#vEmpty').hidden = P.clips.length > 0;
  t = clamp(t, 0, total());
  renderTimeline(); renderProps(); syncMedia(); drawAt(t); updateTime();
}
function buildSample() {
  // three clips from the photo currently in the editor, so the first view shows what this mode does
  const base = D.flatten();
  addImageClip(base, '目前的照片', { motion: 'zoomIn', transition: 'black', text: '暗房 Darkroom', textPos: 'center', textSize: 9, dur: 3 });
  addImageClip(base, '目前的照片（暖色）', { motion: 'panL', filter: 'warm', transition: 'fade', text: '照片、影片都能剪', dur: 3 });
  addImageClip(base, '目前的照片（黑白）', { motion: 'zoomOut', filter: 'mono', transition: 'slide', text: '按「匯出影片」存成 MP4', dur: 3 });
  P.sel = 0; t = 0;
  D.toast('已用目前的照片建立範例，按 ▶ 預覽');
}

$$('#modeSeg button').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
$('#vAdd').addEventListener('click', () => $('#vFile').click());
$('#vFile').addEventListener('change', e => { addFiles(e.target.files); e.target.value = ''; });
$('#vFromPhoto').addEventListener('click', () => {
  const c = D.flatten(); addImageClip(c, '修圖影像'); P.sel = P.clips.length - 1; refresh(); D.toast('已加入目前修圖中的影像');
});
$('#vSample').addEventListener('click', () => { buildSample(); refresh(); });
$('#vAspect').addEventListener('change', e => { P.aspect = e.target.value; refresh(); });
$('#vRes').addEventListener('change', e => { P.res = +e.target.value; refresh(); });
$('#vMusic').addEventListener('click', () => $('#vMusicFile').click());
$('#vMusicFile').addEventListener('change', e => {
  const f = e.target.files[0]; e.target.value = '';
  if (!f) return;
  if (P.music) P.music.el.pause();
  const el = new Audio(); el.src = URL.createObjectURL(f); el.loop = true; el.preload = 'auto';
  P.music = { name: f.name.replace(/\.[^.]+$/, ''), el, volume: 0.7, fade: true };
  attachAudio(P.music);
  renderProps(); D.toast('已加入背景音樂');
});
$('#vExport').addEventListener('click', exportVideo);
$('#vPlay').addEventListener('click', () => (playing ? pause() : play()));
$('#vSeek').addEventListener('input', e => seekTo(+e.target.value / 1000 * total()));
$('#vGrab').addEventListener('click', () => {
  if (!P.clips.length) return;
  if (playing) pause();
  drawAt(t);
  const shot = D.copyCanvas(canvas);
  D.loadCanvasAsDocument(shot, '影片截圖 ' + fmt(t));
  setMode('photo');
  D.toast('已把畫面送到修圖');
});
window.addEventListener('keydown', e => {
  if (document.body.dataset.mode !== 'video' || e.target.matches('input, textarea, select')) return;
  if (e.key === ' ') { e.preventDefault(); playing ? pause() : play(); }
  else if ((e.key === 'Delete' || e.key === 'Backspace') && P.sel >= 0) { e.preventDefault(); removeClip(P.sel); }
  else if (e.key === 'ArrowLeft') seekTo(t - (e.shiftKey ? 5 : 1));
  else if (e.key === 'ArrowRight') seekTo(t + (e.shiftKey ? 5 : 1));
  else if (e.key.toLowerCase() === 's' && !e.ctrlKey && !e.metaKey) splitAtPlayhead();
});
// drop media straight onto the editor
$('#videoView').addEventListener('dragover', e => e.preventDefault());
$('#videoView').addEventListener('drop', e => { e.preventDefault(); addFiles(e.dataTransfer.files); });
document.fonts && document.fonts.ready.then(() => { if (document.body.dataset.mode === 'video') drawAt(t); });

document.body.dataset.mode = 'photo';
})();
