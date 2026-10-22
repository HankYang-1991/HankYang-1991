// Offline cache for the Darkroom PWA. Bump VERSION when files change.
const VERSION = 'darkroom-v2';
const FILES = ['./', 'index.html', 'style.css', 'app.js', 'ai.js', 'video.js', 'manifest.webmanifest', 'icon.svg'];
// the AI model and runtime are cached the first time they are used
const CACHE_HOSTS = [location.origin, 'https://cdn.jsdelivr.net', 'https://fonts.googleapis.com', 'https://fonts.gstatic.com'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  // network first so updates show up, cache as offline fallback
  e.respondWith(
    fetch(e.request).then(res => {
      if (res.ok && CACHE_HOSTS.includes(new URL(e.request.url).origin)) {
        const copy = res.clone(); caches.open(VERSION).then(c => c.put(e.request, copy));
      }
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
