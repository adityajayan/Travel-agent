"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api";

export default function PaymentSuccessPage() {
  const searchParams = useSearchParams();
  const tripId = searchParams.get("trip_id");
  const [status, setStatus] = useState<"polling" | "paid" | "error">("polling");

  useEffect(() => {
    if (!tripId) {
      setStatus("error");
      return;
    }

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 30;

    const poll = async () => {
      while (!cancelled && attempts < maxAttempts) {
        try {
          const res = await apiClient.getPaymentStatus(tripId);
          if (res.payment_status === "paid") {
            setStatus("paid");
            return;
          }
        } catch {
          // ignore and retry
        }
        attempts++;
        await new Promise((r) => setTimeout(r, 2000));
      }
      if (!cancelled) setStatus("error");
    };

    poll();
    return () => { cancelled = true; };
  }, [tripId]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream">
      <div className="max-w-md w-full mx-auto bg-white border border-gold-light/40 rounded-xl p-8 shadow-md text-center">
        {status === "polling" && (
          <>
            <div className="w-12 h-12 border-4 border-gold border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h2 className="font-serif text-2xl text-navy mb-2">Processing Payment</h2>
            <p className="font-sans text-sm text-slate">
              Confirming your payment and booking your trip...
            </p>
          </>
        )}

        {status === "paid" && (
          <>
            <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="font-serif text-2xl text-navy mb-2">Payment Confirmed</h2>
            <p className="font-sans text-sm text-slate mb-6">
              Your trip is being booked with our providers. You&apos;ll receive confirmation shortly.
            </p>
            <a
              href={`/trips/${tripId}`}
              className="inline-block px-6 py-3 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light btn-transition"
            >
              View Trip
            </a>
          </>
        )}

        {status === "error" && (
          <>
            <div className="w-12 h-12 rounded-full bg-error/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="font-serif text-2xl text-navy mb-2">Something Went Wrong</h2>
            <p className="font-sans text-sm text-slate mb-6">
              We couldn&apos;t confirm your payment. Please check your trip for details.
            </p>
            <a
              href="/"
              className="inline-block px-6 py-3 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light btn-transition"
            >
              Back to Home
            </a>
          </>
        )}
      </div>
    </div>
  );
}
