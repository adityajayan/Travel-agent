"use client";

import { useState, useEffect, useCallback } from "react";

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
      <div className="bg-white border-2 border-border-heavy shadow-hard-sm p-4 flex items-start gap-3">
        <div className="h-10 w-10 bg-contrast flex items-center justify-center flex-shrink-0">
          <svg className="h-5 w-5 text-paper" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-ui text-sm font-bold uppercase tracking-[0.05em] text-contrast">Install App</p>
          {isIos ? (
            <p className="font-body text-xs text-text-muted font-light mt-0.5">
              Tap <span className="inline-flex items-center"><svg className="h-3.5 w-3.5 mx-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg></span> then &quot;Add to Home Screen&quot;
            </p>
          ) : (
            <p className="font-body text-xs text-text-muted font-light mt-0.5">
              Install for faster access and offline support
            </p>
          )}

          {deferredPrompt && (
            <button
              onClick={handleInstall}
              className="mt-2 px-4 py-2 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition min-h-touch"
            >
              Install
            </button>
          )}
        </div>

        <button
          onClick={handleDismiss}
          className="text-text-ghost hover:text-contrast p-1 -mt-1 -mr-1 min-h-touch min-w-touch flex items-center justify-center btn-transition"
          aria-label="Dismiss"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
