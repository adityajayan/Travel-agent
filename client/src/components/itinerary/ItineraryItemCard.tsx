"use client";

import { useState } from "react";
import { Plane, Hotel, Car, CheckCircle, ChevronDown } from "lucide-react";
import type { ItineraryItem } from "@/lib/itinerary-types";

interface ItineraryItemCardProps {
  item: ItineraryItem;
  tripId: string;
  onAction: (itemId: string, action: string) => void;
}

const domainIcons: Record<string, React.ElementType> = {
  flight: Plane,
  hotel: Hotel,
  transport: Car,
  activity: CheckCircle,
};

// Domain color system — matches TripTimeline and TripDetail
const domainColors: Record<string, { border: string; bg: string; text: string }> = {
  flight: { border: "border-blue-200", bg: "bg-blue-50", text: "text-blue-600" },
  hotel: { border: "border-purple-200", bg: "bg-purple-50", text: "text-purple-600" },
  transport: { border: "border-orange-200", bg: "bg-orange-50", text: "text-orange-600" },
  activity: { border: "border-teal-200", bg: "bg-teal-50", text: "text-teal-600" },
};

const domainLabels: Record<string, string> = {
  flight: "Flight",
  hotel: "Hotel",
  transport: "Transport",
  activity: "Activity",
};

const statusBadgeStyles: Record<string, string> = {
  confirmed: "border-success-border text-success",
  awaiting_approval: "border-gold text-gold",
  pending: "border-gold-light text-slate",
  suggested: "border-blue-200 text-blue-600",
  rejected: "border-error text-error",
};

export default function ItineraryItemCard({ item, tripId, onAction }: ItineraryItemCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const colors = domainColors[item.type] || domainColors.activity;
  const Icon = domainIcons[item.type] || domainIcons.activity;
  const badgeStyle = statusBadgeStyles[item.status] || statusBadgeStyles.pending;

  const handleAction = async (action: string) => {
    setActionLoading(action);
    try {
      onAction(item.id, action);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div
      className={`border border-gold-light/40 bg-white rounded-lg card-hover-bar cursor-pointer ${
        expanded ? "shadow-md" : ""
      }`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Collapsed view */}
      <div className="p-4 flex items-center gap-3">
        {/* Domain icon */}
        <span className={`flex-shrink-0 w-8 h-8 ${colors.bg} rounded-md flex items-center justify-center`}>
          <Icon className={`h-4 w-4 ${colors.text}`} />
        </span>

        {/* Title + subtitle */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-sans text-[0.65rem] font-semibold ${colors.text}`}>
              {domainLabels[item.type] || item.type}
            </span>
            {item.badge && (
              <span className="px-2 py-0.5 border border-gold rounded-md font-sans text-[0.6rem] font-medium text-gold">
                {item.badge}
              </span>
            )}
          </div>
          <p className="font-serif text-base font-medium text-navy truncate">{item.title}</p>
          <p className="font-sans text-xs text-slate truncate">{item.subtitle}</p>
        </div>

        {/* Time */}
        {item.time && (
          <span className="font-sans text-xs text-slate/60 flex-shrink-0">{item.time}</span>
        )}

        {/* Cost */}
        <div className="text-right flex-shrink-0">
          <span className="font-serif text-lg text-navy">${item.cost.toFixed(0)}</span>
          {item.per_night && item.nights && (
            <p className="font-sans text-[0.62rem] text-slate/60">
              {item.nights} night{item.nights > 1 ? "s" : ""}
            </p>
          )}
        </div>

        {/* Status badge */}
        <span
          className={`px-2 py-0.5 border rounded-md font-sans text-[0.6rem] font-medium flex-shrink-0 ${badgeStyle}`}
        >
          {item.status.replace(/_/g, " ")}
        </span>

        {/* Expand chevron */}
        <ChevronDown
          className={`h-4 w-4 text-slate/60 flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
        />
      </div>

      {/* Expanded view */}
      {expanded && (
        <div className="border-t border-gold-light/30 px-4 py-3" onClick={(e) => e.stopPropagation()}>
          {item.details && (
            <div className="font-sans text-xs text-slate mb-3 whitespace-pre-wrap">
              {item.details}
            </div>
          )}

          {item.provider && (
            <p className="font-sans text-[0.62rem] text-slate/60 mb-3">via {item.provider}</p>
          )}

          {/* Action buttons based on status */}
          <div className="flex gap-2 pt-2 border-t border-gold-light/30">
            {item.status === "awaiting_approval" && (
              <>
                <button
                  onClick={() => handleAction("approve")}
                  disabled={actionLoading === "approve"}
                  className="px-4 py-2 bg-navy text-cream font-sans text-xs font-semibold rounded-md hover:bg-navy-light btn-transition min-h-touch disabled:opacity-50"
                >
                  {actionLoading === "approve" ? "..." : "Approve"}
                </button>
                <button
                  onClick={() => handleAction("reject")}
                  disabled={actionLoading === "reject"}
                  className="px-4 py-2 text-charcoal font-sans text-xs font-semibold border border-navy/20 rounded-md hover:bg-navy hover:text-cream btn-transition min-h-touch disabled:opacity-50"
                >
                  {actionLoading === "reject" ? "..." : "Reject"}
                </button>
                <button
                  onClick={() => handleAction("request_alternatives")}
                  disabled={actionLoading === "request_alternatives"}
                  className="px-4 py-2 text-slate font-sans text-xs font-semibold rounded-md hover:text-navy btn-transition min-h-touch disabled:opacity-50"
                >
                  See Alternatives
                </button>
              </>
            )}
            {item.status === "confirmed" && (
              <button
                onClick={() => handleAction("reject")}
                className="px-4 py-2 text-error font-sans text-xs font-semibold border border-error rounded-md hover:bg-error/5 btn-transition min-h-touch"
              >
                Cancel Booking
              </button>
            )}
            {item.status === "suggested" && (
              <>
                <button
                  onClick={() => handleAction("approve")}
                  className="px-4 py-2 bg-navy text-cream font-sans text-xs font-semibold rounded-md hover:bg-navy-light btn-transition min-h-touch"
                >
                  Add to Trip
                </button>
                <button
                  onClick={() => handleAction("reject")}
                  className="px-4 py-2 text-slate font-sans text-xs font-semibold rounded-md hover:text-navy btn-transition min-h-touch"
                >
                  Skip
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
