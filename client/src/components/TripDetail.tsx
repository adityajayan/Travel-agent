"use client";

import { ChevronLeft } from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import { DOMAIN_CONFIG } from "@/lib/design-tokens";

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
    is_archived?: boolean;
    bookings?: BookingData[];
  };
  onCancel?: (tripId: string) => void;
  onRetry?: (tripId: string) => void;
  onArchive?: (tripId: string) => void;
  onBack?: () => void;
}

export default function TripDetail({ trip, onCancel, onRetry, onArchive, onBack }: TripDetailProps) {
  const bookings = trip.bookings || [];

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

  const canCancel = trip.status === "planning" || trip.status === "review";
  const canRetry = trip.status === "failed";
  const canArchive = trip.status === "complete" || trip.status === "cancelled" || trip.status === "failed";

  return (
    <Card padding="none">
      <div className="p-6 border-b border-gold-light/30">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            {onBack && (
              <button
                onClick={onBack}
                className="font-sans text-xs font-medium text-slate hover:text-navy mb-3 flex items-center gap-1 min-h-touch btn-transition focus:outline-none focus:ring-2 focus:ring-gold/30 rounded-md"
              >
                <ChevronLeft className="h-3 w-3" aria-hidden="true" />
                Back to timeline
              </button>
            )}
            <h2 className="font-serif text-xl font-medium text-navy">{trip.goal}</h2>
            <p className="font-sans text-xs text-slate/60 mt-1">Created {formatDate(trip.created_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={trip.status} />
            {canRetry && onRetry && (
              <Button variant="primary" size="sm" onClick={() => onRetry(trip.id)}>
                Retry
              </Button>
            )}
            {canCancel && onCancel && (
              <Button variant="secondary" size="sm" onClick={() => onCancel(trip.id)}>
                Cancel Trip
              </Button>
            )}
            {canArchive && onArchive && !trip.is_archived && (
              <Button variant="ghost" size="sm" onClick={() => onArchive(trip.id)}>
                Archive
              </Button>
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
                  <span className="font-sans text-xs font-medium text-cream/70">{DOMAIN_CONFIG[domain]?.label || domain}</span>
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
                    {DOMAIN_CONFIG[booking.domain]?.label || booking.domain}
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

      {!trip.summary_text && bookings.length === 0 && trip.status !== "planning" && trip.status !== "review" && (
        <div className="p-6 text-center text-slate font-sans text-sm">
          No booking details available for this trip.
        </div>
      )}
    </Card>
  );
}
