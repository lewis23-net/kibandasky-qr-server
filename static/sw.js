const CACHE = 'kibanda-v1';
const STATIC_ASSETS = [
    '/static/js/html5-qrcode.min.js',
    '/static/js/db.js',
    '/static/manifest.json'
];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(STATIC_ASSETS)));
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
    if (e.request.method !== 'GET') return;
    if (!e.request.url.startsWith(self.location.origin)) return;

    if (e.request.url.includes('/static/')) {
        e.respondWith(
            caches.match(e.request).then((hit) => {
                if (hit) return hit;
                return fetch(e.request).then((res) => {
                    const copy = res.clone();
                    caches.open(CACHE).then((c) => c.put(e.request, copy));
                    return res;
                });
            })
        );
        return;
    }

    e.respondWith(
        fetch(e.request)
            .then((res) => {
                if (res.ok && !res.redirected) {
                    const copy = res.clone();
                    caches.open(CACHE).then((c) => c.put(e.request, copy));
                }
                return res;
            })
            .catch(() => caches.match(e.request, { ignoreSearch: true }))
    );
});