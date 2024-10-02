const CACHE_NAME = 'my-pwa-cache-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/cssmain.css',
  '/static/testicon.png',
  '/static/manifest.json',
  '/static/service-worker.js',
];

// Install event: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Return cached response if found, otherwise fetch from network
      return response || fetch(event.request).then((networkResponse) => {
        return caches.open(CACHE_NAME).then((cache) => {
          // Cache the new request if it's not already cached
          cache.put(event.request, networkResponse.clone());
          return networkResponse;
        });
      });
    }).catch(() => {
      // Optional: Return fallback page or asset if network fails (e.g., offline)
      return caches.match('/');
    })
  );
});
self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
