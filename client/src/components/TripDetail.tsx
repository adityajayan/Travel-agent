"use client";

import { ChevronLeft } from "lucide-react";

interface BookingData {
  domain: string;
  provider: string;
  details: Record<string, unknown>;
  amount: number;
}

interface TripDetailProps {
  trip: {
    id: string;
    goal: string;
    status: string;
    created_at?: string;
    total_spent?: number;
    total_budget?: number;
    summary_text?: string;
    bookings?: BookingData[];
  };
  onCancel?: (tripId: string) => void;
  onBack?: () => void;
}

const domainLabels: Record<string, string> = {
  flight: "Flight",
  hotel: "Hotel",
  transport: "Transport",
  activity: "Activity",
};

const statusConfig: Record<string, { label: string; style: string }> = {
  pending: { label: "Pending", style: "border-gold-light text-slate" },
  running: { label: "Running", style: "border-gold text-gold" },
  complete: { label: "Complete", style: "border-success-border text-success" },
  completed: { label: "Complete", style: "border-success-border text-success" },
  failed: { label: "Failed", style: "border-error text-error" },
  cancelled: { label: "Cancelled", style: "border-gold-light text-slate" },
};

export default function TripDetail({ trip, onCancel, onBack }: TripDetailProps) {
  const bookings = trip.bookings || [];
  const st = statusConfig[trip.status] || statusConfig.pending;

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const costByDomain: Record<string, number> = {};
  for (const b of bookings) {
    costByDomain[b.domain] = (costByDomain[b.domain] || 0) + b.amount;
  }

  const canCancel = trip.status === "pending" || trip.status === "running";

  return (
    <div className="bg-white border border-gold-light/40 rounded-xl overflow-hidden shadow-sm">
      <div className="p-6 border-b border-gold-light/30">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            {onBack && (
              <button
                onClick={onBack}
                className="font-sans text-xs font-medium text-slate hover:text-navy mb-3 flex items-center gap-1 min-h-touch btn-transition"
              >
                <ChevronLeft className="h-3 w-3" />
                Back to timeline
              </button>
            )}
            <h2 className="font-serif text-xl font-medium text-navy">{trip.goal}</h2>
            <p className="font-sans text-xs text-slate/60 mt-1">Created {formatDate(trip.created_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 border rounded-md font-sans text-xs font-medium ${st.style}`}>
              {st.label}
            </span>
            {canCancel && onCancel && (
              <button
                onClick={() => onCancel(trip.id)}
                className="font-sans text-xs font-medium text-slate border border-gold-light/40 px-3 py-2 rounded-md hover:border-navy/20 hover:text-navy btn-transition min-h-touch"
              >
                Cancel Trip
              </button>
            )}
          </div>
        </div>

        {trip.total_spent != null && trip.total_spent > 0 && (
          <div className="bg-navy rounded-lg p-4 -mx-6 -mb-6 mt-4 flex items-center gap-6">
            <div>
              <p className="font-sans text-xs font-medium text-white/50">Total Cost</p>
              <p className="font-serif text-2xl text-white">${trip.total_spent.toFixed(2)}</p>
            </div>
            {trip.total_budget != null && (
              <div>
                <p className="font-sans text-xs font-medium text-white/50">Budget</p>
                <p className="font-serif text-2xl text-white/40">${trip.total_budget.toFixed(0)}</p>
              </div>
            )}
            <div className="flex-1 flex flex-wrap gap-2 justify-end">
              {Object.entries(costByDomain).map(([domain, total]) => (
                <span key={domain} className="inline-flex items-center gap-1 px-2 py-1 border border-white/15 rounded text-xs">
                  <span className="font-sans text-xs font-medium text-white/70">{domainLabels[domain] || domain}</span>
                  <span className="text-white/50 font-sans">${total.toFixed(0)}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {trip.summary_text && (
        <div className="p-6 border-b border-gold-light/30">
          <p className="eyebrow mb-2">Trip Summary</p>
          <div className="font-sans text-sm text-slate whitespace-pre-wrap leading-relaxed">
            {trip.summary_text}
          </div>
        </div>
      )}

      {bookings.length > 0 && (
        <div className="p-6">
          <p className="eyebrow mb-3">Bookings ({bookings.length})</p>
          <div className="border border-gold-light/40 rounded-lg divide-y divide-gold-light/30">
            {bookings.map((booking, idx) => (
              <div key={idx} className="p-4 hover:bg-cream-dark btn-transition">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-sans text-xs font-semibold text-gold uppercase tracking-wide">
                    {domainLabels[booking.domain] || booking.domain}
                  </span>
                  <span className="font-serif text-lg text-navy">${booking.amount.toFixed(2)}</span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {Object.entries(booking.details).map(([key, value]) => (
                    <div key={key} className="text-xs font-sans">
                      <span className="text-slate capitalize">{key.replace(/_/g, " ")}: </span>
                      <span className="text-charcoal font-medium">{String(value)}</span>
                    </div>
                  ))}
                </div>
                {booking.provider && (
                  <p className="font-sans text-xs text-slate/60 mt-2">via {booking.provider}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!trip.summary_text && bookings.length === 0 && trip.status !== "running" && trip.status !== "pending" && (
        <div className="p-6 text-center text-slate font-sans text-sm">
          No booking details available for this trip.
        </div>
      )}
    </div>
  );
}
