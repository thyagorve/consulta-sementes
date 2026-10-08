const CACHE_NAME = 'imobcrm-pwa-v2';
const STATIC_PREFIX = '/static/';
const CORE = [
  '/static/pwa/icon-192.png',
  '/static/pwa/icon-512.png',
  '/static/pwa/icon-maskable-512.png',
  '/static/pwa/apple-touch-icon.png',
  '/static/pwa/manifest.webmanifest'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith(STATIC_PREFIX)) {
    const freshFirst = req.destination === 'style' || req.destination === 'script';
    if (freshFirst) {
      event.respondWith(
        fetch(req).then(res => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
          return res;
        }).catch(() => caches.match(req))
      );
    } else {
      event.respondWith(
        caches.match(req).then(cached => cached || fetch(req).then(res => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
          return res;
        }))
      );
    }
    return;
  }

  if (req.mode === 'navigate') {
    event.respondWith(fetch(req));
  }
});
