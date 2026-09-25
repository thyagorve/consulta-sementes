// Service Worker - GestorTLS
const CACHE_NAME = 'gestortls-v1.0.0';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('/admin/') ||
      event.request.url.includes('/webhook/')) {
    return;
  }
  
  event.respondWith(
    fetch(event.request).catch(() => {
      return new Response('Offline - Conecte-se à internet', {
        status: 200,
        headers: { 'Content-Type': 'text/plain' }
      });
    })
  );
});
