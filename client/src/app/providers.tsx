"use client";

import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/components/AuthGate";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <AuthProvider>{children}</AuthProvider>
    </ToastProvider>
  );
}
