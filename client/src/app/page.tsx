"use client";

import { useEffect, useState } from "react";
import TripForm from "@/components/TripForm";
import TripTimeline from "@/components/TripTimeline";
import TripList from "@/components/TripList";
import { useWebSocket } from "@/hooks/useWebSocket";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { apiClient, CreateTripOptions } from "@/lib/api";
import { useAuth, LoginForm } from "@/components/AuthGate";
import { useToast } from "@/components/Toast";

export interface TripEvent {
  type: string;
  message?: string;
  agent_type?: string;
  tool_name?: string;
  status?: string;
  summary?: Record<string, unknown>;
  approval_id?: string;
  context?: Record<string, unknown>;
  questions?: Array<{ key: string; question: string; placeholder?: string }>;
  request_id?: string;
}

export interface Trip {
  id: string;
  goal: string;
  status: string;
  created_at?: string;
  result?: Record<string, unknown>;
}

export default function Home() {
  const [activeTrip, setActiveTrip] = useState<Trip | null>(null);
  const [events, setEvents] = useState<TripEvent[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [authRequired, setAuthRequired] = useState<boolean | null>(null);

  const { isAuthenticated, logout } = useAuth();
  const { toast } = useToast();
  const { supported: pushSupported, subscribed: pushSubscribed, subscribe: pushSubscribe } = usePushNotifications();

  // Check whether the backend requires auth
  useEffect(() => {
    apiClient.checkAuth().then((ok) => {
      setAuthRequired(!ok && !isAuthenticated);
    });
  }, [isAuthenticated]);

  // Auto-subscribe to push notifications when supported
  useEffect(() => {
    if (pushSupported && !pushSubscribed) {
      fetch("/api/push/vapid-key")
        .then((r) => r.json())
        .then((data) => {
          if (data.vapid_public_key) {
            pushSubscribe(data.vapid_public_key);
          }
        })
        .catch(() => {});
    }
  }, [pushSupported, pushSubscribed, pushSubscribe]);

  const { connected } = useWebSocket(
    activeTrip?.id ?? null,
    (event) => {
      const tripEvent = event as unknown as TripEvent;
      setEvents((prev) => [...prev, tripEvent]);

      if (tripEvent.type === "trip_completed" || tripEvent.type === "trip_failed") {
        setActiveTrip((prev) =>
          prev ? { ...prev, status: tripEvent.type === "trip_completed" ? "completed" : "failed" } : null
        );
        refreshTrips();
      }
    }
  );

  const refreshTrips = async () => {
    try {
      const data = await apiClient.getTrips();
      setTrips(data);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to load trips");
    }
  };

  const handleCreateTrip = async (options: CreateTripOptions) => {
    try {
      const trip = await apiClient.createTrip(options);
      setActiveTrip(trip);
      setEvents([]);
      toast("Trip created — agents are planning your trip", "success");
      refreshTrips();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create trip");
    }
  };

  const handleApproval = async (approvalId: string, approved: boolean) => {
    try {
      await apiClient.submitApproval(approvalId, approved);
      toast(approved ? "Booking approved" : "Booking rejected", "info");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to submit approval");
    }
  };

  const handleClarification = async (tripId: string, requestId: string, answers: Record<string, string>) => {
    try {
      await apiClient.submitClarification(tripId, requestId, answers);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to submit preferences");
    }
  };

  const handleSelectTrip = (trip: Trip) => {
    setActiveTrip(trip);
    setEvents([]);
  };

  // Show login form if backend requires auth and user isn't authenticated
  if (authRequired && !isAuthenticated) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-primary-700">Travel Agent</h1>
          <p className="text-gray-500 mt-1">AI-powered travel planning assistant</p>
        </header>
        <LoginForm />
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary-700">Travel Agent</h1>
          <p className="text-gray-500 mt-1">AI-powered travel planning assistant</p>
        </div>
        {isAuthenticated && (
          <button
            onClick={logout}
            className="text-xs text-gray-500 hover:text-gray-700 border border-gray-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            Sign Out
          </button>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel — trip list */}
        <div className="lg:col-span-1">
          <TripList
            trips={trips}
            activeTrip={activeTrip}
            onSelect={handleSelectTrip}
            onRefresh={refreshTrips}
          />
        </div>

        {/* Right panel — form + timeline */}
        <div className="lg:col-span-2 space-y-6">
          <TripForm onSubmit={handleCreateTrip} disabled={activeTrip?.status === "running"} />

          {activeTrip && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">{activeTrip.goal}</h2>
                <StatusBadge status={activeTrip.status} connected={connected} />
              </div>
              <TripTimeline
                events={events}
                onApproval={handleApproval}
                onClarification={handleClarification}
                tripId={activeTrip.id}
              />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function StatusBadge({ status, connected }: { status: string; connected: boolean }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <div className="flex items-center gap-2">
      {connected && status === "running" && (
        <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse-dot" />
      )}
      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
        {status}
      </span>
    </div>
  );
}
