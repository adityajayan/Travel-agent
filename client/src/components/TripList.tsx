"use client";

import { useEffect, useState } from "react";

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

  const statusStyles: Record<string, string> = {
    pending: "border-border-light text-text-ghost",
    running: "border-accent-border text-accent",
    complete: "border-success-border text-success",
    completed: "border-success-border text-success",
    failed: "border-accent text-accent",
    cancelled: "border-border-light text-text-ghost",
  };

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
    <div className="bg-white border-2 border-border-heavy p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="eyebrow">Your Trips</p>
        <button
          onClick={onRefresh}
          className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent hover:text-contrast btn-transition"
        >
          Refresh
        </button>
      </div>

      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search trips..."
        className="w-full border-2 border-border-heavy bg-paper px-3 py-1.5 text-xs font-body text-text-primary placeholder:text-text-ghost focus:outline-none focus:border-accent mb-2"
      />

      <div className="flex gap-1 mb-3 overflow-x-auto">
        {["all", "running", "complete", "failed", "cancelled"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-2 lg:px-2 lg:py-1 font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] whitespace-nowrap btn-transition ${
              statusFilter === s
                ? "bg-contrast text-paper"
                : "text-text-muted hover:text-contrast hover:bg-paper-elevated"
            }`}
          >
            {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-xs text-text-ghost text-center py-4 font-body">
          {trips.length === 0 ? "No trips yet" : "No matching trips"}
        </p>
      ) : (
        <ul className="divide-y divide-border-light">
          {filtered.map((trip) => (
            <li key={trip.id}>
              <button
                onClick={() => onSelect(trip)}
                className={`w-full text-left px-3 py-3 lg:py-2.5 text-sm btn-transition min-h-touch ${
                  activeTrip?.id === trip.id
                    ? "bg-accent-soft border-l-[3px] border-accent"
                    : "hover:bg-paper-elevated border-l-[3px] border-transparent"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="truncate flex-1 font-body text-text-primary">{trip.goal}</span>
                  <span className={`px-2 py-0.5 border-[1.5px] font-ui text-[0.6rem] font-bold uppercase tracking-[0.1em] flex-shrink-0 ${statusStyles[trip.status] ?? "border-border-light text-text-ghost"}`}>
                    {trip.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {trip.created_at && (
                    <span className="font-body text-[0.62rem] text-text-ghost">{formatDate(trip.created_at)}</span>
                  )}
                  {trip.total_spent != null && trip.total_spent > 0 && (
                    <span className="font-display text-sm text-text-mid">${trip.total_spent.toFixed(0)}</span>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
