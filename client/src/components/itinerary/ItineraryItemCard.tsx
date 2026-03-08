"use client";

import { useState } from "react";
import { Plane, Hotel, Car, CheckCircle, ChevronDown } from "lucide-react";
import type { ItineraryItem } from "@/lib/itinerary-types";
import StatusBadge from "@/components/ui/StatusBadge";
import Button from "@/components/ui/Button";
import { DOMAIN_CONFIG } from "@/lib/design-tokens";

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

export default function ItineraryItemCard({ item, tripId, onAction }: ItineraryItemCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const config = DOMAIN_CONFIG[item.type] || DOMAIN_CONFIG.activity;
  const Icon = domainIcons[item.type] || domainIcons.activity;

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
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      className={`border border-gold-light/40 bg-white rounded-lg card-hover-bar cursor-pointer focus:outline-none focus:ring-2 focus:ring-gold/30 ${
        expanded ? "shadow-md" : ""
      }`}
      onClick={() => setExpanded(!expanded)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setExpanded(!expanded);
        }
      }}
    >
      {/* Collapsed view */}
      <div className="p-4 flex items-center gap-3">
        <span className={`flex-shrink-0 w-8 h-8 ${config.colors.bg} rounded-md flex items-center justify-center`}>
          <Icon className={`h-4 w-4 ${config.colors.text}`} aria-hidden="true" />
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-sans text-xs font-semibold ${config.colors.text}`}>
              {config.label}
            </span>
            {item.badge && (
              <span className="px-2 py-0.5 border border-gold rounded-md font-sans text-[10px] font-medium text-gold">
                {item.badge}
              </span>
            )}
          </div>
          <p className="font-serif text-base font-medium text-navy truncate">{item.title}</p>
          <p className="font-sans text-xs text-slate truncate">{item.subtitle}</p>
        </div>

        {item.time && (
          <span className="font-sans text-xs text-slate/60 flex-shrink-0">{item.time}</span>
        )}

        <div className="text-right flex-shrink-0">
          <span className="font-serif text-lg text-navy">${item.cost.toFixed(0)}</span>
          {item.per_night && item.nights && (
            <p className="font-sans text-[10px] text-slate/60">
              {item.nights} night{item.nights > 1 ? "s" : ""}
            </p>
          )}
        </div>

        <StatusBadge status={item.status} />

        <ChevronDown
          className={`h-4 w-4 text-slate/60 flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
          aria-hidden="true"
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
            <p className="font-sans text-[10px] text-slate/60 mb-3">via {item.provider}</p>
          )}

          <div className="flex gap-2 pt-2 border-t border-gold-light/30">
            {item.status === "awaiting_approval" && (
              <>
                <Button variant="primary" size="sm" onClick={() => handleAction("approve")} disabled={actionLoading === "approve"}>
                  {actionLoading === "approve" ? "..." : "Approve"}
                </Button>
                <Button variant="secondary" size="sm" onClick={() => handleAction("reject")} disabled={actionLoading === "reject"}>
                  {actionLoading === "reject" ? "..." : "Reject"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => handleAction("request_alternatives")} disabled={actionLoading === "request_alternatives"}>
                  See Alternatives
                </Button>
              </>
            )}
            {item.status === "confirmed" && (
              <Button variant="danger" size="sm" onClick={() => handleAction("reject")}>
                Cancel Booking
              </Button>
            )}
            {item.status === "suggested" && (
              <>
                <Button variant="primary" size="sm" onClick={() => handleAction("approve")}>
                  Add to Trip
                </Button>
                <Button variant="ghost" size="sm" onClick={() => handleAction("reject")}>
                  Skip
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
