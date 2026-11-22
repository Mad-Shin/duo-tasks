const CACHE_NAME = "duotasks-shell-v32";
const SHELL_ASSETS = [
  "/",
  "/index.html",
  "/styles.css?v=32",
  "/app.js?v=32",
  "/manifest.json",
  "/icon.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.all(
        SHELL_ASSETS.map((url) =>
          fetch(new Request(url, { cache: "reload" }))
            .then((res) => (res.ok ? cache.put(url, res) : null))
            .catch(() => null)
        )
      )
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    return;
  }
  if (event.request.method !== "GET" || url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws")) {
    return;
  }
  event.respondWith(
    fetch(event.request, { cache: "no-store" })
      .then((res) => {
        if (res && res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
