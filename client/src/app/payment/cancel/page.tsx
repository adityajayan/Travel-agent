"use client";

import { useSearchParams } from "next/navigation";

export default function PaymentCancelPage() {
  const searchParams = useSearchParams();
  const tripId = searchParams.get("trip_id");

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream">
      <div className="max-w-md w-full mx-auto bg-white border border-gold-light/40 rounded-xl p-8 shadow-md text-center">
        <div className="w-12 h-12 rounded-full bg-gold/10 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 className="font-serif text-2xl text-navy mb-2">Payment Cancelled</h2>
        <p className="font-sans text-sm text-slate mb-6">
          Your payment was not processed. Your trip is still saved and you can pay later.
        </p>
        <div className="flex gap-3 justify-center">
          {tripId && (
            <a
              href={`/trips/${tripId}`}
              className="px-6 py-3 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light btn-transition"
            >
              Back to Trip
            </a>
          )}
          <a
            href="/"
            className="px-6 py-3 bg-white text-navy font-sans text-sm font-semibold rounded-md border border-navy/20 hover:bg-cream btn-transition"
          >
            Home
          </a>
        </div>
      </div>
    </div>
  );
}
