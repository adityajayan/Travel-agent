"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [isIos, setIsIos] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  useEffect(() => {
    const standalone = window.matchMedia("(display-mode: standalone)").matches
      || ("standalone" in window.navigator && (window.navigator as unknown as { standalone: boolean }).standalone);
    setIsStandalone(standalone);

    const dismissedAt = localStorage.getItem("pwa_install_dismissed");
    if (dismissedAt && Date.now() - Number(dismissedAt) < 86400000) {
      setDismissed(true);
    }

    const ua = navigator.userAgent;
    const iosDevice = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    setIsIos(iosDevice && !standalone);

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = useCallback(async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setDeferredPrompt(null);
    }
  }, [deferredPrompt]);

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem("pwa_install_dismissed", String(Date.now()));
    setDeferredPrompt(null);
  };

  if (isStandalone || dismissed) return null;
  if (!deferredPrompt && !isIos) return null;

  return (
    <div className="install-prompt fixed bottom-16 lg:bottom-4 left-4 right-4 mx-auto max-w-md z-40 animate-slide-up">
      <div className="bg-white border border-gold-light/40 shadow-lg rounded-xl p-4 flex items-start gap-3">
        <div className="h-10 w-10 bg-navy rounded-lg flex items-center justify-center flex-shrink-0">
          <Download className="h-5 w-5 text-cream" />
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-sans text-sm font-semibold text-navy">Install App</p>
          {isIos ? (
            <p className="font-sans text-xs text-slate mt-0.5">
              Tap the share button then &quot;Add to Home Screen&quot;
            </p>
          ) : (
            <p className="font-sans text-xs text-slate mt-0.5">
              Install for faster access and offline support
            </p>
          )}

          {deferredPrompt && (
            <button
              onClick={handleInstall}
              className="mt-2 px-4 py-2 bg-navy text-cream font-sans text-xs font-semibold rounded-md hover:bg-navy-light btn-transition min-h-touch"
            >
              Install
            </button>
          )}
        </div>

        <button
          onClick={handleDismiss}
          className="text-slate hover:text-navy p-1 -mt-1 -mr-1 min-h-touch min-w-touch flex items-center justify-center btn-transition"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
