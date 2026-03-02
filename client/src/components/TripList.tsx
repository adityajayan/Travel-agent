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

  const statusColor: Record<string, string> = {
    pending: "bg-yellow-400",
    running: "bg-blue-400",
    complete: "bg-green-400",
    completed: "bg-green-400",
    failed: "bg-red-400",
    cancelled: "bg-gray-400",
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
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-700">Your Trips</h2>
        <button
          onClick={onRefresh}
          className="text-xs text-primary-600 hover:text-primary-700"
        >
          Refresh
        </button>
      </div>

      {/* Search */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search trips..."
        className="w-full rounded-md border border-gray-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent mb-2"
      />

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-3 overflow-x-auto">
        {["all", "running", "complete", "failed", "cancelled"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-2 lg:px-2 lg:py-1 rounded text-xs font-medium whitespace-nowrap transition-colors active:bg-gray-200 ${
              statusFilter === s
                ? "bg-primary-100 text-primary-700"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">
          {trips.length === 0 ? "No trips yet" : "No matching trips"}
        </p>
      ) : (
        <ul className="space-y-2">
          {filtered.map((trip) => (
            <li key={trip.id}>
              <button
                onClick={() => onSelect(trip)}
                className={`w-full text-left px-3 py-3 lg:py-2.5 rounded-lg text-sm transition-colors min-h-touch active:bg-gray-100 ${
                  activeTrip?.id === trip.id
                    ? "bg-primary-50 border border-primary-200"
                    : "hover:bg-gray-50 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full flex-shrink-0 ${statusColor[trip.status] ?? "bg-gray-300"}`} />
                  <span className="truncate flex-1">{trip.goal}</span>
                  {trip.created_at && (
                    <span className="text-xs text-gray-400 flex-shrink-0">{formatDate(trip.created_at)}</span>
                  )}
                </div>
                {trip.total_spent != null && trip.total_spent > 0 && (
                  <div className="ml-4 mt-0.5">
                    <span className="text-xs text-gray-500">${trip.total_spent.toFixed(0)}</span>
                  </div>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
