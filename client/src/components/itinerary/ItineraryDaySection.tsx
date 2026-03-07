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
          <span className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-accent">
            {day.date}
          </span>
          <span className="font-body text-sm text-text-mid font-light">
            {day.label}
          </span>
          <span className="font-body text-xs text-text-ghost">{day.city}</span>
        </div>
        <span className="font-display text-base text-contrast">
          ${dayCost.toFixed(0)}
        </span>
      </div>

      {/* Divider */}
      <div className="h-[2px] bg-border-heavy mb-4" />

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
