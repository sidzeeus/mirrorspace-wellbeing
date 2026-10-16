/*
 * Service worker: makes Support work with no connection (decision D7).
 *
 * What it caches:
 *   - the app shell pages needed for Support (HTML), and the scripts and styles they use
 *   - static assets under /_next/static (fingerprinted, safe to keep)
 *   - the public helplines page
 *
 * What it never caches: anything under /api/. No API response is ever stored here, so
 * check-ins, episodes, contacts and chats cannot end up in this cache. The safety plan
 * and helpline data for offline use are kept by the app itself (src/lib/offline.ts).
 *
 * Bump VERSION to release a new shell; old caches are deleted on activation.
 */
const VERSION = "v2";
const SHELL = `shell-${VERSION}`;
const ASSETS = `assets-${VERSION}`;
const OFFLINE_URL = "/offline";
const SHELL_PAGES = ["/offline", "/support", "/resources", "/plan", "/home"];
// Pages kept after a normal visit, so an exercise opened once opens again offline.
// Their HTML is an empty shell: the exercise text is shared content, not personal data.
const KEEP_AFTER_VISIT = ["/exercises"];

const keepable = (pathname) =>
  SHELL_PAGES.includes(pathname) ||
  KEEP_AFTER_VISIT.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));

async function cachePageWithAssets(cache, assets, url) {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok || response.redirected) return;
  await cache.put(url, response.clone());
  // Also keep the scripts, styles and fonts that page needs to run offline.
  const html = await response.text();
  const urls = new Set(html.match(/\/_next\/static\/[^"'\\)\s]+/g) || []);
  await Promise.all(
    [...urls].map(async (asset) => {
      try {
        if (!(await assets.match(asset))) await assets.add(asset);
      } catch {
        // A missing asset must not stop the rest from being cached.
      }
    }),
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const [cache, assets] = await Promise.all([caches.open(SHELL), caches.open(ASSETS)]);
      await Promise.all(
        SHELL_PAGES.map((url) => cachePageWithAssets(cache, assets, url).catch(() => undefined)),
      );
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(
        names.filter((name) => name !== SHELL && name !== ASSETS).map((name) => caches.delete(name)),
      );
      await self.clients.claim();
    })(),
  );
});

// The page asks the waiting worker to take over when the person chooses "Reload".
self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // Private data never goes through the cache. The browser handles it directly.
  if (url.pathname.startsWith("/api/")) return;

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      (async () => {
        const assets = await caches.open(ASSETS);
        const cached = await assets.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok) assets.put(request, response.clone());
        return response;
      })(),
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        const cache = await caches.open(SHELL);
        try {
          const response = await fetch(request);
          // Refresh the saved copy whenever one of these pages loads normally.
          if (response.ok && !response.redirected && keepable(url.pathname)) {
            cache.put(url.pathname, response.clone());
          }
          return response;
        } catch {
          return (
            (await cache.match(url.pathname)) ||
            (await cache.match(OFFLINE_URL)) ||
            new Response("You are offline.", { status: 503, headers: { "Content-Type": "text/plain" } })
          );
        }
      })(),
    );
  }
});
