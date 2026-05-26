const CACHE_NAME = 'sumo-consejo-v1';
const STATIC_ASSETS = [
  '/',
  '/login',
  '/static/manifest.json',
  '/static/icon-192.png',
];

// Install — cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener('fetch', event => {
  // Skip non-GET and cross-origin
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith(self.location.origin)) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cache successful responses
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Fallback to cache when offline
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          // Offline fallback page
          if (event.request.mode === 'navigate') {
            return new Response(
              `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
              <meta name="viewport" content="width=device-width,initial-scale=1">
              <title>Sin conexión</title>
              <style>body{font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#F5F4F0;color:#1A3A5C;text-align:center;padding:24px}
              h1{font-size:24px;margin-bottom:8px}p{color:#6B6B6B;font-size:15px}
              .btn{margin-top:20px;padding:12px 24px;background:#1A3A5C;color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block}
              </style></head><body>
              <div style="font-size:48px;margin-bottom:16px">⬡</div>
              <h1>Sin conexión</h1>
              <p>No hay conexión a internet.<br>Conéctate para continuar.</p>
              <a class="btn" onclick="location.reload()">Reintentar</a>
              </body></html>`,
              { headers: { 'Content-Type': 'text/html' } }
            );
          }
        });
      })
  );
});
