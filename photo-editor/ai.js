/* 暗房 Darkroom — AI background removal (runs on-device) and colour-key removal.
   Model: U²-Net-p (Apache-2.0), 320×320 saliency mask, refined with a guided filter
   so edges follow the full-resolution photo. Runtime: onnxruntime-web (WASM). */
(() => {
'use strict';
const D = window.Darkroom;
const { $, clamp } = D;

const ORT_VERSION = '1.17.3';
const ORT_CDN = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
const MODEL_URL = 'models/u2netp.onnx';
const SIZE = 320;

let session = null, loading = null;
// cache of the last recognition, so slider tweaks re-apply instantly
let last = null; // { srcId, srcVer, raw: Float32Array(320*320), resultIds: [] }

function setProgress(pct, text) {
  $('#aiProgress').hidden = pct == null;
  if (pct != null) { $('#aiBar').style.width = Math.round(pct) + '%'; $('#aiStatus').textContent = text; }
}

function loadScript(src) {
  return new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = src; s.onload = res; s.onerror = () => rej(new Error('無法載入 AI 執行環境'));
    document.head.appendChild(s);
  });
}
async function exists(url) {
  try {
    const ctl = new AbortController();
    const r = await fetch(url, { signal: ctl.signal, cache: 'force-cache' });
    ctl.abort();
    return r.ok;
  } catch (_) { return false; }
}
async function fetchWithProgress(url, onPct) {
  const r = await fetch(url);
  if (!r.ok) throw new Error('模型下載失敗（' + r.status + '）');
  const total = +r.headers.get('content-length') || 0;
  if (!r.body || !total) return new Uint8Array(await r.arrayBuffer());
  const reader = r.body.getReader(), out = new Uint8Array(total);
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    out.set(value, got); got += value.length; onPct(got / total);
  }
  return out.subarray(0, got);
}

async function getSession() {
  if (session) return session;
  if (loading) return loading;
  loading = (async () => {
    setProgress(3, '載入 AI 執行環境…');
    if (!window.ort) await loadScript(ORT_CDN + 'ort.wasm.min.js');
    const ort = window.ort;
    ort.env.wasm.numThreads = 1;
    // use a copy shipped next to the page when there is one (offline / locked-down hosts), else the CDN
    const local = new URL('vendor/', document.baseURI).href;
    ort.env.wasm.wasmPaths = (await exists(local + 'ort-wasm-simd.wasm')) ? local : ORT_CDN;
    setProgress(8, '下載 AI 模型…');
    const bytes = await fetchWithProgress(MODEL_URL, p => setProgress(8 + p * 72, `下載 AI 模型 ${Math.round(p * 100)}%`));
    setProgress(82, '啟動模型…');
    session = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'], graphOptimizationLevel: 'all' });
    return session;
  })();
  try { return await loading; } finally { loading = null; }
}

/* Run U²-Net-p on a layer canvas → Float32Array mask 320×320 in 0..1 */
async function recognise(canvas) {
  const ses = await getSession();
  setProgress(88, '辨識主體…');
  await new Promise(r => setTimeout(r, 30));
  const t = D.makeCanvas(SIZE, SIZE), tc = t.getContext('2d', { willReadFrequently: true });
  tc.imageSmoothingQuality = 'high';
  tc.drawImage(canvas, 0, 0, SIZE, SIZE);
  const px = tc.getImageData(0, 0, SIZE, SIZE).data;
  let max = 1;
  for (let i = 0; i < px.length; i += 4) max = Math.max(max, px[i], px[i + 1], px[i + 2]);
  const mean = [0.485, 0.456, 0.406], std = [0.229, 0.224, 0.225];
  const n = SIZE * SIZE, input = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) for (let c = 0; c < 3; c++) input[c * n + i] = (px[i * 4 + c] / max - mean[c]) / std[c];
  const feeds = { [ses.inputNames[0]]: new window.ort.Tensor('float32', input, [1, 3, SIZE, SIZE]) };
  const out = await ses.run(feeds);
  const raw = Float32Array.from(out[ses.outputNames[0]].data);
  let lo = Infinity, hi = -Infinity;
  for (const v of raw) { if (v < lo) lo = v; if (v > hi) hi = v; }
  const span = hi - lo || 1;
  for (let i = 0; i < raw.length; i++) raw[i] = (raw[i] - lo) / span;
  return raw;
}

/* ---------- guided filter (He et al.) with integral-image box means ---------- */
function boxMean(src, W, H, r) {
  const I = new Float64Array((W + 1) * (H + 1));
  for (let y = 0; y < H; y++) {
    let row = 0;
    for (let x = 0; x < W; x++) { row += src[y * W + x]; I[(y + 1) * (W + 1) + x + 1] = I[y * (W + 1) + x + 1] + row; }
  }
  const out = new Float32Array(W * H);
  for (let y = 0; y < H; y++) {
    const y0 = Math.max(0, y - r), y1 = Math.min(H, y + r + 1);
    for (let x = 0; x < W; x++) {
      const x0 = Math.max(0, x - r), x1 = Math.min(W, x + r + 1);
      const s = I[y1 * (W + 1) + x1] - I[y0 * (W + 1) + x1] - I[y1 * (W + 1) + x0] + I[y0 * (W + 1) + x0];
      out[y * W + x] = s / ((x1 - x0) * (y1 - y0));
    }
  }
  return out;
}
function guidedFilter(I, p, W, H, r, eps) {
  const n = W * H;
  const Ip = new Float32Array(n), II = new Float32Array(n);
  for (let i = 0; i < n; i++) { Ip[i] = I[i] * p[i]; II[i] = I[i] * I[i]; }
  const mI = boxMean(I, W, H, r), mp = boxMean(p, W, H, r), mIp = boxMean(Ip, W, H, r), mII = boxMean(II, W, H, r);
  const a = new Float32Array(n), b = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const cov = mIp[i] - mI[i] * mp[i], v = mII[i] - mI[i] * mI[i];
    a[i] = cov / (v + eps); b[i] = mp[i] - a[i] * mI[i];
  }
  const ma = boxMean(a, W, H, r), mb = boxMean(b, W, H, r);
  const q = new Float32Array(n);
  for (let i = 0; i < n; i++) q[i] = ma[i] * I[i] + mb[i];
  return q;
}

/* Turn the 320×320 raw mask into a full-size alpha canvas, using the photo as the edge guide */
function buildMask(raw, srcCanvas) {
  const sw = srcCanvas.width, sh = srcCanvas.height;
  const k = Math.min(1, 1024 / Math.max(sw, sh));
  const W = Math.max(1, Math.round(sw * k)), H = Math.max(1, Math.round(sh * k));

  // upsample raw mask (bilinear via canvas)
  const small = D.makeCanvas(SIZE, SIZE), sc = small.getContext('2d');
  const sImg = sc.createImageData(SIZE, SIZE);
  for (let i = 0; i < raw.length; i++) { const v = raw[i] * 255; sImg.data[i * 4] = sImg.data[i * 4 + 1] = sImg.data[i * 4 + 2] = v; sImg.data[i * 4 + 3] = 255; }
  sc.putImageData(sImg, 0, 0);
  const work = D.makeCanvas(W, H), wc = work.getContext('2d', { willReadFrequently: true });
  wc.imageSmoothingQuality = 'high';
  wc.drawImage(small, 0, 0, W, H);
  const pm = wc.getImageData(0, 0, W, H).data;
  let p = new Float32Array(W * H);
  for (let i = 0; i < p.length; i++) p[i] = pm[i * 4] / 255;

  const refine = +$('#aiRefine').value / 100;
  if (refine > 0) {
    wc.clearRect(0, 0, W, H); wc.drawImage(srcCanvas, 0, 0, W, H);
    const g = wc.getImageData(0, 0, W, H).data, I = new Float32Array(W * H);
    for (let i = 0; i < I.length; i++) I[i] = (0.299 * g[i * 4] + 0.587 * g[i * 4 + 1] + 0.114 * g[i * 4 + 2]) / 255;
    const r = Math.max(2, Math.round(Math.max(W, H) * 0.008));
    const eps = Math.pow(10, -1.2 - 2.8 * refine);
    const q = guidedFilter(I, p, W, H, r, eps);
    for (let i = 0; i < p.length; i++) p[i] = p[i] * (1 - refine) + q[i] * refine;
  }
  const hard = +$('#aiHard').value / 100;
  const width = 1 - 0.92 * hard;
  const out = wc.createImageData(W, H), d = out.data;
  for (let i = 0; i < p.length; i++) d[i * 4 + 3] = clamp((p[i] - 0.5) / width + 0.5, 0, 1) * 255;
  const feather = +$('#aiFeather').value * k;
  if (feather > 0.3) D.gaussBlur(d, W, H, feather);
  wc.putImageData(out, 0, 0);

  const full = D.makeCanvas(sw, sh), fc = full.getContext('2d');
  fc.imageSmoothingQuality = 'high';
  fc.drawImage(work, 0, 0, sw, sh);
  // thumbnail for the panel
  const mv = $('#aiMask').getContext('2d');
  mv.fillStyle = '#000'; mv.fillRect(0, 0, 160, 160);
  const s = Math.min(160 / W, 160 / H);
  const thumb = D.makeCanvas(W, H), tcx = thumb.getContext('2d');
  tcx.fillStyle = '#fff'; tcx.fillRect(0, 0, W, H); tcx.globalCompositeOperation = 'destination-in'; tcx.drawImage(work, 0, 0);
  mv.drawImage(thumb, (160 - W * s) / 2, (160 - H * s) / 2, W * s, H * s);
  $('#aiMaskWrap').hidden = false;
  return full;
}

/* Build result layers: cut-out on top, optional new background below it, source hidden */
function compose(src, mask, label) {
  const S = D.S;
  const cut = D.newLayer(label + '：' + src.name.slice(0, 10), src.canvas.width, src.canvas.height);
  cut.ctx.drawImage(src.canvas, 0, 0);
  cut.ctx.globalCompositeOperation = 'destination-in'; cut.ctx.drawImage(mask, 0, 0);
  cut.ctx.globalCompositeOperation = 'source-over';
  const ids = [cut.id];
  const mode = $('#aiBg').value;
  let bg = null;
  if (mode !== 'transparent') {
    bg = D.newLayer('新背景', src.canvas.width, src.canvas.height);
    const c = bg.ctx;
    if (mode === 'color') { c.fillStyle = S.color; c.fillRect(0, 0, bg.canvas.width, bg.canvas.height); }
    else {
      c.drawImage(src.canvas, 0, 0);
      const img = c.getImageData(0, 0, bg.canvas.width, bg.canvas.height), d = img.data;
      if (mode === 'blur') D.gaussBlur(d, img.width, img.height, Math.max(4, Math.max(img.width, img.height) / 90));
      else for (let k = 0; k < d.length; k += 4) { const g = 0.2126 * d[k] + 0.7152 * d[k + 1] + 0.0722 * d[k + 2]; d[k] = d[k + 1] = d[k + 2] = g; }
      c.putImageData(img, 0, 0);
    }
    ids.push(bg.id);
  }
  const at = S.layers.indexOf(src);
  S.layers.splice(at + 1, 0, ...(bg ? [bg, cut] : [cut]));
  src.visible = false;
  S.active = S.layers.indexOf(cut);
  return ids;
}

/* If the active layer is a previous AI result, work from its original source instead */
function resolveSource() {
  const S = D.S;
  let src = D.activeLayer();
  if (last && last.resultIds.includes(src.id)) {
    const orig = S.layers.find(l => l.id === last.srcId);
    if (orig) {
      S.layers = S.layers.filter(l => !last.resultIds.includes(l.id));
      orig.visible = true;
      S.active = S.layers.indexOf(orig);
      src = orig;
    }
  }
  return src;
}

let busy = false;
async function runAI() {
  if (busy) return;
  busy = true; $('#aiRun').disabled = true;
  try {
    D.commitAdjustIfAny();
    const src = resolveSource();
    let raw;
    if (last && last.srcId === src.id && last.srcVer === src.ver) raw = last.raw;
    else raw = await recognise(src.canvas);
    setProgress(94, '精修邊緣…');
    await new Promise(r => setTimeout(r, 20));
    const mask = buildMask(raw, src.canvas);
    const ids = compose(src, mask, '去背');
    last = { srcId: src.id, srcVer: src.ver, raw, resultIds: ids };
    D.commit('AI 去背');
    setProgress(null);
    D.toast('完成！原圖已隱藏保留在下方圖層');
  } catch (err) {
    console.error(err);
    setProgress(null);
    const msg = String(err && err.message || err);
    D.toast(/wasm|WebAssembly|CompileError|Content Security/i.test(msg) ? '這個環境無法執行 AI 模型，可改用「純色背景去除」' : '去背失敗：' + msg.slice(0, 40));
  } finally {
    busy = false; $('#aiRun').disabled = false; updateLabel();
  }
}

/* ---------- colour key: remove a uniform background reached from the borders ---------- */
function runKey() {
  D.commitAdjustIfAny();
  const src = resolveSource();
  const W = src.canvas.width, H = src.canvas.height;
  const img = src.ctx.getImageData(0, 0, W, H), d = img.data;
  // background colour = median of border pixels
  const border = [];
  const push = (x, y) => { const k = (y * W + x) * 4; border.push([d[k], d[k + 1], d[k + 2]]); };
  const step = Math.max(1, Math.floor((W + H) / 400));
  for (let x = 0; x < W; x += step) { push(x, 0); push(x, H - 1); }
  for (let y = 0; y < H; y += step) { push(0, y); push(W - 1, y); }
  const med = [0, 1, 2].map(c => border.map(p => p[c]).sort((a, b) => a - b)[border.length >> 1]);
  const T = +$('#keyTol').value * 2.2;
  const dist = k => Math.max(Math.abs(d[k] - med[0]), Math.abs(d[k + 1] - med[1]), Math.abs(d[k + 2] - med[2]));
  const alpha = new Float32Array(W * H).fill(1);
  const soft = T * 0.6;
  const level = k => { const v = dist(k); return v <= T ? 0 : v >= T + soft ? 1 : (v - T) / soft; };
  if ($('#keyAll').checked) {
    for (let i = 0; i < W * H; i++) alpha[i] = level(i * 4);
  } else {
    const seen = new Uint8Array(W * H), queue = new Int32Array(W * H);
    let qh = 0, qt = 0;
    const seed = i => { if (!seen[i] && dist(i * 4) <= T + soft) { seen[i] = 1; queue[qt++] = i; } };
    for (let x = 0; x < W; x++) { seed(x); seed((H - 1) * W + x); }
    for (let y = 0; y < H; y++) { seed(y * W); seed(y * W + W - 1); }
    while (qh < qt) {
      const i = queue[qh++];
      const a = level(i * 4);
      alpha[i] = a;
      if (a >= 1) continue; // stop spreading at the subject's edge
      const x = i % W;
      if (x > 0) seed(i - 1);
      if (x < W - 1) seed(i + 1);
      if (i >= W) seed(i - W);
      if (i < W * (H - 1)) seed(i + W);
    }
  }
  const mask = D.makeCanvas(W, H), mc = mask.getContext('2d'), mi = mc.createImageData(W, H);
  for (let i = 0; i < alpha.length; i++) mi.data[i * 4 + 3] = alpha[i] * 255;
  mc.putImageData(mi, 0, 0);
  const ids = compose(src, mask, '去背景色');
  last = { srcId: src.id, srcVer: src.ver, raw: null, resultIds: ids };
  D.commit('去除背景色');
  D.toast(`已去除背景色 rgb(${med.join(', ')})`);
  updateLabel();
}

function updateLabel() {
  const l = D.activeLayer();
  if (!l) return;
  const again = last && (last.resultIds.includes(l.id) || (last.srcId === l.id && last.srcVer === l.ver && last.raw));
  $('#aiRun').textContent = again ? '重新套用' : 'AI 去背';
  const src = last && last.resultIds.includes(l.id) ? D.S.layers.find(x => x.id === last.srcId) : l;
  $('#aiLayerName').textContent = src ? src.name : l.name;
}

[['#aiRefine', '#outAiRefine'], ['#aiHard', '#outAiHard'], ['#aiFeather', '#outAiFeather'], ['#keyTol', '#outKeyTol']].forEach(([i, o]) => {
  $(i).addEventListener('input', () => { $(o).textContent = $(i).value; });
});
$('#aiRun').addEventListener('click', runAI);
$('#keyRun').addEventListener('click', runKey);
document.addEventListener('darkroom:tab', e => { if (e.detail === 'ai') updateLabel(); });
$('#layerList').addEventListener('click', () => setTimeout(updateLabel, 0));
})();
