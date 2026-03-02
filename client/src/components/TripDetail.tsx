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

const domainColors: Record<string, { bg: string; border: string; icon: string }> = {
  flight: { bg: "bg-blue-50", border: "border-blue-200", icon: "text-blue-600" },
  hotel: { bg: "bg-purple-50", border: "border-purple-200", icon: "text-purple-600" },
  transport: { bg: "bg-orange-50", border: "border-orange-200", icon: "text-orange-600" },
  activity: { bg: "bg-teal-50", border: "border-teal-200", icon: "text-teal-600" },
};

const statusConfig: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "bg-yellow-100 text-yellow-700" },
  running: { label: "Running", color: "bg-blue-100 text-blue-700" },
  complete: { label: "Complete", color: "bg-green-100 text-green-700" },
  completed: { label: "Complete", color: "bg-green-100 text-green-700" },
  failed: { label: "Failed", color: "bg-red-100 text-red-700" },
  cancelled: { label: "Cancelled", color: "bg-gray-100 text-gray-600" },
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

  // Group bookings by domain for cost breakdown
  const costByDomain: Record<string, number> = {};
  for (const b of bookings) {
    costByDomain[b.domain] = (costByDomain[b.domain] || 0) + b.amount;
  }

  const canCancel = trip.status === "pending" || trip.status === "running";

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            {onBack && (
              <button
                onClick={onBack}
                className="text-xs text-gray-500 hover:text-gray-700 mb-2 flex items-center gap-1 min-h-touch active:text-gray-900"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back to timeline
              </button>
            )}
            <h2 className="text-lg font-semibold text-gray-900">{trip.goal}</h2>
            <p className="text-xs text-gray-400 mt-1">Created {formatDate(trip.created_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${st.color}`}>
              {st.label}
            </span>
            {canCancel && onCancel && (
              <button
                onClick={() => onCancel(trip.id)}
                className="text-xs text-red-500 hover:text-red-700 border border-red-200 px-3 py-2 rounded-md hover:bg-red-50 active:bg-red-100 transition-colors min-h-touch"
              >
                Cancel Trip
              </button>
            )}
          </div>
        </div>

        {/* Cost summary bar */}
        {trip.total_spent != null && trip.total_spent > 0 && (
          <div className="flex items-center gap-4 mt-3">
            <div>
              <p className="text-xs text-gray-500">Total Cost</p>
              <p className="text-xl font-bold text-gray-900">${trip.total_spent.toFixed(2)}</p>
            </div>
            {trip.total_budget != null && (
              <div>
                <p className="text-xs text-gray-500">Budget</p>
                <p className="text-xl font-bold text-gray-400">${trip.total_budget.toFixed(0)}</p>
              </div>
            )}
            {/* Per-domain breakdown pills */}
            <div className="flex-1 flex flex-wrap gap-2 justify-end">
              {Object.entries(costByDomain).map(([domain, total]) => {
                const dc = domainColors[domain] || domainColors.activity;
                return (
                  <span key={domain} className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs ${dc.bg} ${dc.border} border`}>
                    <span className={`font-medium ${dc.icon}`}>{domainLabels[domain] || domain}</span>
                    <span className="text-gray-600">${total.toFixed(0)}</span>
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Narrative */}
      {trip.summary_text && (
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Trip Summary</h3>
          <div className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">
            {trip.summary_text}
          </div>
        </div>
      )}

      {/* Bookings */}
      {bookings.length > 0 && (
        <div className="p-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Bookings ({bookings.length})</h3>
          <div className="space-y-3">
            {bookings.map((booking, idx) => {
              const dc = domainColors[booking.domain] || domainColors.activity;
              return (
                <div key={idx} className={`rounded-lg border ${dc.border} ${dc.bg} p-4`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-sm font-medium ${dc.icon}`}>
                      {domainLabels[booking.domain] || booking.domain}
                    </span>
                    <span className="text-sm font-bold text-gray-900">${booking.amount.toFixed(2)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    {Object.entries(booking.details).map(([key, value]) => (
                      <div key={key} className="text-xs">
                        <span className="text-gray-500 capitalize">{key.replace(/_/g, " ")}: </span>
                        <span className="text-gray-700 font-medium">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                  {booking.provider && (
                    <p className="text-xs text-gray-400 mt-2">Provider: {booking.provider}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!trip.summary_text && bookings.length === 0 && trip.status !== "running" && trip.status !== "pending" && (
        <div className="p-6 text-center text-gray-400 text-sm">
          No booking details available for this trip.
        </div>
      )}
    </div>
  );
}
