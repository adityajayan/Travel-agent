"use client";

import type { ItineraryDay } from "@/lib/itinerary-types";
import ItineraryItemCard from "./ItineraryItemCard";

interface ItineraryDaySectionProps {
  day: ItineraryDay;
  index: number;
  tripId: string;
  onItemAction: (itemId: string, action: string) => void;
}

export default function ItineraryDaySection({
  day,
  index,
  tripId,
  onItemAction,
}: ItineraryDaySectionProps) {
  const dayCost = day.items.reduce((sum, item) => sum + item.cost, 0);

  return (
    <div
      className="mb-6 stagger-fade-up"
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      {/* Day header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="font-sans text-xs font-semibold text-gold">
            {day.date}
          </span>
          <span className="font-sans text-sm text-charcoal">
            {day.label}
          </span>
          <span className="font-sans text-xs text-slate/60">{day.city}</span>
        </div>
        <span className="font-serif text-base text-navy">
          ${dayCost.toFixed(0)}
        </span>
      </div>

      {/* Divider */}
      <div className="h-px bg-navy/20 mb-4" />

      {/* Item cards */}
      <div className="space-y-3">
        {day.items.map((item) => (
          <ItineraryItemCard
            key={item.id}
            item={item}
            tripId={tripId}
            onAction={onItemAction}
          />
        ))}
      </div>
    </div>
  );
}
