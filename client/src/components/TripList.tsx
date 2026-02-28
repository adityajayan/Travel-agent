"use client";

import { useEffect } from "react";

interface Trip {
  id: string;
  goal: string;
  status: string;
  created_at?: string;
}

interface TripListProps {
  trips: Trip[];
  activeTrip: Trip | null;
  onSelect: (trip: Trip) => void;
  onRefresh: () => void;
}

export default function TripList({ trips, activeTrip, onSelect, onRefresh }: TripListProps) {
  useEffect(() => {
    onRefresh();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const statusColor: Record<string, string> = {
    pending: "bg-yellow-400",
    running: "bg-blue-400",
    completed: "bg-green-400",
    failed: "bg-red-400",
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

      {trips.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">No trips yet</p>
      ) : (
        <ul className="space-y-2">
          {trips.map((trip) => (
            <li key={trip.id}>
              <button
                onClick={() => onSelect(trip)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  activeTrip?.id === trip.id
                    ? "bg-primary-50 border border-primary-200"
                    : "hover:bg-gray-50 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full flex-shrink-0 ${statusColor[trip.status] ?? "bg-gray-300"}`} />
                  <span className="truncate">{trip.goal}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
