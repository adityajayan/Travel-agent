"use client";

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
  pending: { label: "Pending", style: "border-border-light text-text-ghost" },
  running: { label: "Running", style: "border-accent-border text-accent" },
  complete: { label: "Complete", style: "border-success-border text-success" },
  completed: { label: "Complete", style: "border-success-border text-success" },
  failed: { label: "Failed", style: "border-accent text-accent" },
  cancelled: { label: "Cancelled", style: "border-border-light text-text-ghost" },
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
    <div className="bg-white border-2 border-border-heavy overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-border-light">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            {onBack && (
              <button
                onClick={onBack}
                className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-muted hover:text-contrast mb-3 flex items-center gap-1 min-h-touch btn-transition"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back to timeline
              </button>
            )}
            <h2 className="font-display text-xl font-medium text-contrast">{trip.goal}</h2>
            <p className="font-body text-[0.62rem] text-text-ghost mt-1">Created {formatDate(trip.created_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 border-[1.5px] font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] ${st.style}`}>
              {st.label}
            </span>
            {canCancel && onCancel && (
              <button
                onClick={() => onCancel(trip.id)}
                className="font-ui text-xs font-bold uppercase tracking-[0.1em] text-text-muted border-2 border-border-light px-3 py-2 hover:border-border-heavy hover:text-contrast btn-transition min-h-touch"
              >
                Cancel Trip
              </button>
            )}
          </div>
        </div>

        {/* Cost summary — inverted bar */}
        {trip.total_spent != null && trip.total_spent > 0 && (
          <div className="bg-contrast p-4 -mx-6 -mb-6 mt-4 flex items-center gap-6">
            <div>
              <p className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-white/50">Total Cost</p>
              <p className="font-display text-2xl text-white">${trip.total_spent.toFixed(2)}</p>
            </div>
            {trip.total_budget != null && (
              <div>
                <p className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-white/50">Budget</p>
                <p className="font-display text-2xl text-white/40">${trip.total_budget.toFixed(0)}</p>
              </div>
            )}
            <div className="flex-1 flex flex-wrap gap-2 justify-end">
              {Object.entries(costByDomain).map(([domain, total]) => (
                <span key={domain} className="inline-flex items-center gap-1 px-2 py-1 border border-white/15 text-xs">
                  <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-white/70">{domainLabels[domain] || domain}</span>
                  <span className="text-white/50 font-body">${total.toFixed(0)}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Narrative */}
      {trip.summary_text && (
        <div className="p-6 border-b border-border-light">
          <p className="eyebrow mb-2">Trip Summary</p>
          <div className="font-body text-sm text-text-muted font-light whitespace-pre-wrap leading-relaxed">
            {trip.summary_text}
          </div>
        </div>
      )}

      {/* Bookings — magazine grid */}
      {bookings.length > 0 && (
        <div className="p-6">
          <p className="eyebrow mb-3">Bookings ({bookings.length})</p>
          <div className="border-2 border-border-heavy divide-y divide-border-light">
            {bookings.map((booking, idx) => (
              <div key={idx} className="p-4 hover:bg-paper-elevated btn-transition">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent">
                    {domainLabels[booking.domain] || booking.domain}
                  </span>
                  <span className="font-display text-lg text-contrast">${booking.amount.toFixed(2)}</span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {Object.entries(booking.details).map(([key, value]) => (
                    <div key={key} className="text-xs font-body">
                      <span className="text-text-muted capitalize">{key.replace(/_/g, " ")}: </span>
                      <span className="text-text-mid font-medium">{String(value)}</span>
                    </div>
                  ))}
                </div>
                {booking.provider && (
                  <p className="font-body text-[0.62rem] text-text-ghost mt-2">via {booking.provider}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!trip.summary_text && bookings.length === 0 && trip.status !== "running" && trip.status !== "pending" && (
        <div className="p-6 text-center text-text-ghost font-body text-sm">
          No booking details available for this trip.
        </div>
      )}
    </div>
  );
}
