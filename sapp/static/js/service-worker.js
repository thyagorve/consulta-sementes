const CACHE_NAME = 'infinity-stock-v11-shell-2';
const STATIC_FALLBACKS = [
  '/static/manifest.webmanifest',
  '/static/img/logo.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_FALLBACKS).catch(() => null))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  // Não removemos o shell anterior automaticamente. Uma fila IndexedDB pode
  // conter operações criadas por uma versão ainda aberta no dispositivo.
  // O cliente só pede a limpeza quando não há nenhuma pendência/conflito.
  event.waitUntil(self.clients.claim());
});

self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type === 'CACHE_URLS' && Array.isArray(data.urls)) {
    event.waitUntil(caches.open(CACHE_NAME).then(async cache => {
      for (const url of data.urls) {
        try {
          const req = new Request(url, { credentials: 'include' });
          const res = await fetch(req);
          if (res.ok) await cache.put(req, res.clone());
        } catch (_) {}
      }
    }));
  }
  if (data.type === 'PRUNE_OLD_CACHES') {
    event.waitUntil(
      caches.keys().then(keys => Promise.all(
        keys.filter(k => k.startsWith('infinity-stock-') && k !== CACHE_NAME).map(k => caches.delete(k))
      ))
    );
  }
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/')) return;

  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        if (fresh.ok) {
          const cache = await caches.open(CACHE_NAME);
          await cache.put(req, fresh.clone());
        }
        return fresh;
      } catch (_) {
        const cached = await caches.match(req);
        if (cached) return cached;
        const cache = await caches.open(CACHE_NAME);
        const keys = await cache.keys();
        const html = keys.find(k => k.mode === 'navigate' || !new URL(k.url).pathname.startsWith('/static/'));
        return html ? cache.match(html) : new Response('Sem conexão. Abra uma tela que já tenha sido usada neste dispositivo.', { status:503, headers:{'Content-Type':'text/plain; charset=utf-8'} });
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cached = await caches.match(req);
    const network = fetch(req).then(async res => {
      if (res && (res.ok || res.type === 'opaque')) {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(req, res.clone());
      }
      return res;
    }).catch(() => null);
    return cached || await network || new Response('', {status:504});
  })());
});
