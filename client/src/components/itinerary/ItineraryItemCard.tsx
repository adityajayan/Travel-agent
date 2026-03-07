"use client";

import { useState } from "react";
import type { ItineraryItem } from "@/lib/itinerary-types";

interface ItineraryItemCardProps {
  item: ItineraryItem;
  tripId: string;
  onAction: (itemId: string, action: string) => void;
}

// Domain icon paths — same as TripTimeline.tsx DomainIcon
const domainIcons: Record<string, string> = {
  flight: "M21 16v-2l-8-5V3.5a1.5 1.5 0 10-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z",
  hotel: "M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9a4 4 0 00-4-4z",
  transport: "M18.92 6.01A1.49 1.49 0 0017.5 5h-11c-.69 0-1.28.47-1.42 1.01L3 12v8a1 1 0 001 1h1a1 1 0 001-1v-1h12v1a1 1 0 001 1h1a1 1 0 001-1v-8l-2.08-5.99zM6.5 16A1.5 1.5 0 015 14.5 1.5 1.5 0 016.5 13 1.5 1.5 0 018 14.5 1.5 1.5 0 016.5 16zm11 0a1.5 1.5 0 01-1.5-1.5 1.5 1.5 0 011.5-1.5 1.5 1.5 0 011.5 1.5 1.5 1.5 0 01-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z",
  activity: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
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
  awaiting_approval: "border-accent-border text-accent",
  pending: "border-border-light text-text-ghost",
  suggested: "border-blue-200 text-blue-600",
  rejected: "border-accent text-accent",
};

export default function ItineraryItemCard({ item, tripId, onAction }: ItineraryItemCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const colors = domainColors[item.type] || domainColors.activity;
  const iconPath = domainIcons[item.type] || domainIcons.activity;
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
      className={`border-2 border-border-heavy bg-white card-hover-bar cursor-pointer ${
        expanded ? "shadow-hard-sm" : ""
      }`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Collapsed view */}
      <div className="p-4 flex items-center gap-3">
        {/* Domain icon */}
        <span className={`flex-shrink-0 w-8 h-8 ${colors.bg} flex items-center justify-center`}>
          <svg className={`h-4 w-4 ${colors.text}`} fill="currentColor" viewBox="0 0 24 24">
            <path d={iconPath} />
          </svg>
        </span>

        {/* Title + subtitle */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] ${colors.text}`}>
              {domainLabels[item.type] || item.type}
            </span>
            {item.badge && (
              <span className="px-2 py-0.5 border-[1.5px] border-accent-border font-ui text-[0.6rem] font-bold uppercase tracking-[0.1em] text-accent">
                {item.badge}
              </span>
            )}
          </div>
          <p className="font-display text-base font-medium text-contrast truncate">{item.title}</p>
          <p className="font-body text-xs text-text-muted font-light truncate">{item.subtitle}</p>
        </div>

        {/* Time */}
        {item.time && (
          <span className="font-body text-xs text-text-ghost flex-shrink-0">{item.time}</span>
        )}

        {/* Cost */}
        <div className="text-right flex-shrink-0">
          <span className="font-display text-lg text-contrast">${item.cost.toFixed(0)}</span>
          {item.per_night && item.nights && (
            <p className="font-body text-[0.62rem] text-text-ghost">
              {item.nights} night{item.nights > 1 ? "s" : ""}
            </p>
          )}
        </div>

        {/* Status badge */}
        <span
          className={`px-2 py-0.5 border-[1.5px] font-ui text-[0.6rem] font-bold uppercase tracking-[0.1em] flex-shrink-0 ${badgeStyle}`}
        >
          {item.status.replace(/_/g, " ")}
        </span>

        {/* Expand chevron */}
        <svg
          className={`h-4 w-4 text-text-ghost flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expanded view */}
      {expanded && (
        <div className="border-t border-border-light px-4 py-3" onClick={(e) => e.stopPropagation()}>
          {item.details && (
            <div className="font-body text-xs text-text-muted font-light mb-3 whitespace-pre-wrap">
              {item.details}
            </div>
          )}

          {item.provider && (
            <p className="font-body text-[0.62rem] text-text-ghost mb-3">via {item.provider}</p>
          )}

          {/* Action buttons based on status */}
          <div className="flex gap-2 pt-2 border-t border-border-light">
            {item.status === "awaiting_approval" && (
              <>
                <button
                  onClick={() => handleAction("approve")}
                  disabled={actionLoading === "approve"}
                  className="px-4 py-2 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition min-h-touch disabled:opacity-50"
                >
                  {actionLoading === "approve" ? "..." : "Approve"}
                </button>
                <button
                  onClick={() => handleAction("reject")}
                  disabled={actionLoading === "reject"}
                  className="px-4 py-2 text-text-mid font-ui text-xs font-bold uppercase tracking-[0.1em] border-2 border-border-heavy hover:bg-contrast hover:text-paper btn-transition min-h-touch disabled:opacity-50"
                >
                  {actionLoading === "reject" ? "..." : "Reject"}
                </button>
                <button
                  onClick={() => handleAction("request_alternatives")}
                  disabled={actionLoading === "request_alternatives"}
                  className="px-4 py-2 text-text-ghost font-ui text-xs font-bold uppercase tracking-[0.1em] hover:text-contrast btn-transition min-h-touch disabled:opacity-50"
                >
                  See Alternatives
                </button>
              </>
            )}
            {item.status === "confirmed" && (
              <button
                onClick={() => handleAction("reject")}
                className="px-4 py-2 text-accent font-ui text-xs font-bold uppercase tracking-[0.1em] border-2 border-accent-border hover:bg-accent-soft btn-transition min-h-touch"
              >
                Cancel Booking
              </button>
            )}
            {item.status === "suggested" && (
              <>
                <button
                  onClick={() => handleAction("approve")}
                  className="px-4 py-2 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition min-h-touch"
                >
                  Add to Trip
                </button>
                <button
                  onClick={() => handleAction("reject")}
                  className="px-4 py-2 text-text-ghost font-ui text-xs font-bold uppercase tracking-[0.1em] hover:text-contrast btn-transition min-h-touch"
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
