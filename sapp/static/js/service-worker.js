const CACHE_NAME = 'infinity-stock-v11-shell-16';
const STATIC_FALLBACKS = [
  '/static/manifest.webmanifest',
  '/static/img/logo.png',
];

const sameOriginRequest = rawUrl => {
  const url = new URL(rawUrl, self.location.origin);
  if (url.origin === self.location.origin) {
    return new Request(url.href, { credentials: 'include' });
  }
  return new Request(url.href, { mode: 'cors', credentials: 'omit' });
};

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_FALLBACKS).catch(() => null))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  // Mantemos caches anteriores enquanto pode haver fila criada por uma aba
  // antiga. O cliente solicita a limpeza quando não existem pendências.
  event.waitUntil(self.clients.claim());
});

self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type === 'CACHE_URLS' && Array.isArray(data.urls)) {
    event.waitUntil(caches.open(CACHE_NAME).then(async cache => {
      for (const rawUrl of [...new Set(data.urls.filter(Boolean))]) {
        try {
          const req = sameOriginRequest(rawUrl);
          const res = await fetch(req);
          if (res && (res.ok || res.type === 'opaque')) {
            await cache.put(req, res.clone());
            const url = new URL(req.url);
            if (url.origin === self.location.origin && !url.pathname.startsWith('/static/')) {
              const cleanReq = new Request(`${url.origin}${url.pathname}`, { credentials: 'include' });
              await cache.put(cleanReq, res.clone());
            }
          }
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

async function cachedNavigation(req) {
  const cache = await caches.open(CACHE_NAME);
  const url = new URL(req.url);
  const cleanReq = new Request(`${url.origin}${url.pathname}`, { credentials: 'include' });

  try {
    const fresh = await fetch(req);
    if (fresh && fresh.ok) {
      await cache.put(req, fresh.clone());
      await cache.put(cleanReq, fresh.clone());
    }
    return fresh;
  } catch (_) {
    const exact = await cache.match(req);
    if (exact) return exact;

    const clean = await cache.match(cleanReq);
    if (clean) return clean;

    // Prioriza telas operacionais que normalmente já foram pré-carregadas.
    for (const fallback of ['/solicitacoes/', '/estoque/', '/dashboard/', '/']) {
      const hit = await cache.match(new Request(`${self.location.origin}${fallback}`, { credentials: 'include' }));
      if (hit) return hit;
    }

    return new Response(
      `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>INFINITY STOCK Offline</title><style>body{margin:0;background:#f5f7f5;color:#24362b;font-family:Arial,sans-serif;display:grid;place-items:center;min-height:100vh;padding:20px}.card{max-width:460px;background:#fff;border:1px solid #dfe8e2;border-radius:18px;padding:24px;box-shadow:0 16px 45px rgba(31,77,46,.12);text-align:center}.dot{width:52px;height:52px;border-radius:16px;background:#111827;color:#fff;display:grid;place-items:center;margin:0 auto 14px;font-size:24px}.card h2{margin:0 0 8px;font-size:20px}.card p{margin:0;color:#64748b;font-size:14px;line-height:1.5}.card button{margin-top:16px;border:0;border-radius:10px;padding:10px 14px;background:#2f8f4e;color:#fff;font-weight:800}</style></head><body><div class="card"><div class="dot">●</div><h2>Sem conexão</h2><p>O modo offline está ativo, mas esta tela ainda não foi armazenada neste dispositivo. Quando a internet voltar, abra a tela uma vez para deixá-la disponível offline.</p><button onclick="location.reload()">Tentar novamente</button></div></body></html>`,
      { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', 'X-Infinity-Offline': 'fallback' } }
    );
  }
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Dados de API são tratados pelo snapshot IndexedDB por usuário no cliente.
  if (url.origin === self.location.origin && (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/'))) return;

  if (req.mode === 'navigate') {
    event.respondWith(cachedNavigation(req));
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(req);
    if (cached) return cached;

    try {
      const res = await fetch(req);
      if (res && (res.ok || res.type === 'opaque')) {
        await cache.put(req, res.clone());
      }
      return res;
    } catch (_) {
      return new Response('', { status: 504 });
    }
  })());
});
