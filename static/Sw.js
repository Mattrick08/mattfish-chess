const CACHE_NAME = 'mattfish-v1';

// Precache the app shell and static assets. Nothing under /api/ is ever cached:
// game state, moves and multiplayer polling must always hit the network.
const PRECACHE_URLS = [
  '/',
  '/play',
  '/multiplayer',
  '/static/theme.js',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/pieces/wP (1).png',
  '/static/pieces/wN (1).png',
  '/static/pieces/wB (1).png',
  '/static/pieces/wR (1).png',
  '/static/pieces/wQ (1).png',
  '/static/pieces/wK (1).png',
  '/static/pieces/bP (1).png',
  '/static/pieces/bN (1).png',
  '/static/pieces/bB (1).png',
  '/static/pieces/bR (1).png',
  '/static/pieces/bQ (1).png',
  '/static/pieces/bK (1).png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .catch(() => {}) // don't block install if one asset is missing
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never intercept API calls — game moves, clocks, chat, etc. must always be live.
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // Only handle GET requests from here on.
  if (event.request.method !== 'GET') {
    return;
  }

  // Page navigations: try the network first so content stays fresh,
  // fall back to cache when offline.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match('/')))
    );
    return;
  }

  // Static assets (css/js/images under /static/): cache-first for speed and offline use.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        });
      })
    );
  }
});
