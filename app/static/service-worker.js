const CACHE_NAME = 'firsat-ai-v8-static-1';
const STATIC_PREFIX = '/static/';

self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // HTML ve API cevapları hiçbir zaman service worker cache'inden verilmez.
  if (request.mode === 'navigate' || url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  if (!url.pathname.startsWith(STATIC_PREFIX)) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(async cache => {
      const cached = await cache.match(request);
      const networkPromise = fetch(request).then(response => {
        if (response.ok) cache.put(request, response.clone());
        return response;
      });
      return cached || networkPromise;
    })
  );
});
