"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";
import Card from "@/components/ui/Card";

interface Trip {
  id: string;
  goal: string;
  status: string;
  created_at?: string;
  total_spent?: number;
  summary_text?: string;
}

interface TripListProps {
  trips: Trip[];
  activeTrip: Trip | null;
  onSelect: (trip: Trip) => void;
  onRefresh: () => void;
}

export default function TripList({ trips, activeTrip, onSelect, onRefresh }: TripListProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    onRefresh();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = trips.filter((trip) => {
    if (statusFilter !== "all" && trip.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return trip.goal.toLowerCase().includes(q) || trip.id.toLowerCase().includes(q);
    }
    return true;
  });

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <p className="eyebrow">Your Trips</p>
        <button
          onClick={onRefresh}
          className="font-sans text-xs font-medium text-gold hover:text-gold-dark btn-transition flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-gold/30 rounded-md px-1"
        >
          <RefreshCw className="h-3 w-3" aria-hidden="true" />
          Refresh
        </button>
      </div>

      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search trips..."
        className="w-full border border-navy/20 bg-cream rounded-md px-3 py-1.5 text-xs font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold mb-2"
      />

      <div className="flex gap-1 mb-3 overflow-x-auto">
        {["all", "running", "complete", "failed", "cancelled"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-2 lg:px-2 lg:py-1 font-sans text-xs font-medium whitespace-nowrap rounded-md btn-transition focus:outline-none focus:ring-2 focus:ring-gold/30 ${
              statusFilter === s
                ? "bg-navy text-cream"
                : "text-slate hover:text-navy hover:bg-cream-dark"
            }`}
          >
            {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-xs text-slate/60 text-center py-4 font-sans">
          {trips.length === 0 ? "No trips yet" : "No matching trips"}
        </p>
      ) : (
        <ul className="divide-y divide-gold-light/30">
          {filtered.map((trip) => (
            <li key={trip.id}>
              <button
                onClick={() => onSelect(trip)}
                className={`w-full text-left px-3 py-3 lg:py-2.5 text-sm btn-transition min-h-touch rounded-md focus:outline-none focus:ring-2 focus:ring-gold/30 ${
                  activeTrip?.id === trip.id
                    ? "bg-gold/8 border-l-[3px] border-gold"
                    : "hover:bg-cream-dark border-l-[3px] border-transparent"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="truncate flex-1 font-sans text-navy">{trip.goal}</span>
                  <StatusBadge status={trip.status} />
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {trip.created_at && (
                    <span className="font-sans text-[10px] text-slate/60">{formatDate(trip.created_at)}</span>
                  )}
                  {trip.total_spent != null && trip.total_spent > 0 && (
                    <span className="font-serif text-sm text-charcoal">${trip.total_spent.toFixed(0)}</span>
                  )}
                  {(trip.status === "complete" || trip.status === "completed" || trip.status === "awaiting_approval") && (
                    <Link
                      href={`/trips/${trip.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-sans text-xs font-medium text-gold hover:text-gold-dark hover:underline ml-auto"
                    >
                      View
                    </Link>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
