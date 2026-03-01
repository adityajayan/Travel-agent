"use client";

import { useState, useCallback } from "react";

const API_URL = "/api";

/**
 * M6 Item 5 — Push Notifications using Web Push API.
 * Registers service worker subscription and sends to backend.
 */
export function usePushNotifications() {
  const [subscribed, setSubscribed] = useState(false);
  const [supported] = useState(
    typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window
  );

  const subscribe = useCallback(async (vapidPublicKey: string) => {
    if (!supported) return;

    try {
      const registration = await navigator.serviceWorker.ready;

      const existing = await registration.pushManager.getSubscription();
      if (existing) {
        setSubscribed(true);
        return existing;
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
      });

      // Send subscription to backend
      await fetch(`${API_URL}/push/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(subscription.toJSON()),
      });

      setSubscribed(true);
      return subscription;
    } catch (err) {
      console.error("Push subscription failed:", err);
      return null;
    }
  }, [supported]);

  const unsubscribe = useCallback(async () => {
    if (!supported) return;

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();

        await fetch(`${API_URL}/push/unsubscribe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });
      }
      setSubscribed(false);
    } catch (err) {
      console.error("Push unsubscribe failed:", err);
    }
  }, [supported]);

  return { supported, subscribed, subscribe, unsubscribe };
}

function urlBase64ToUint8Array(base64String: string): BufferSource {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}
