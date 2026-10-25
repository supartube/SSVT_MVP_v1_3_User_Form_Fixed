self.addEventListener("install", event => { self.skipWaiting(); });
self.addEventListener("activate", event => { event.waitUntil(self.clients.claim()); });
// Deliberately do not cache authenticated APIs, uploads, or video bytes.
