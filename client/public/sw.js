/* Service Worker for Travel Agent PWA — push notifications */

self.addEventListener("push", (event) => {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: "Travel Agent", body: event.data.text() };
  }

  const options = {
    body: payload.body || "",
    icon: "/icon-192x192.png",
    badge: "/icon-192x192.png",
    data: { url: payload.url || "/" },
  };

  event.waitUntil(self.registration.showNotification(payload.title || "Travel Agent", options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";
  event.waitUntil(clients.openWindow(url));
});
