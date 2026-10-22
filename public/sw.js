// PWA Service Worker — Tier 1+2 範囲のみ
// 対象: 静的アセット（_astro/ の CSS/JS 等）のみ cache-first
// 対象外: HTML / 画像 / API / search-index.json（network 直通、SW キャッシュなし）
const CACHE_NAME = 'pwa-static-cache-v1';

self.addEventListener('install', (event) => {
  // 事前キャッシュなし: アセットはハッシュ付きでデプロイごとに URL が変わるため
  // cache.addAll() すると次回ビルドで 404 になり SW 更新が止まる
  event.waitUntil(caches.open(CACHE_NAME));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;
  // 静的アセット（_astro/ 配下のみ）を対象に限定
  if (!url.pathname.startsWith('/my-auto-blog/_astro/')) return;

  event.respondWith(
    caches.match(request)
      .then((cached) => (cached || fetch(request, { cache: 'no-store' })))
      .then((response) => {
        if (response && response.ok) {
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put(request, response.clone()));
        }
        return response;
      })
  );
});
