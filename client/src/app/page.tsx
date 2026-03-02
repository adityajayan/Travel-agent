"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import TripForm from "@/components/TripForm";
import TripTimeline from "@/components/TripTimeline";
import TripList from "@/components/TripList";
import TripDetail from "@/components/TripDetail";
import Settings, { getSavedPreferences } from "@/components/Settings";
import BottomNav from "@/components/BottomNav";
import InstallPrompt from "@/components/InstallPrompt";
import { useWebSocket } from "@/hooks/useWebSocket";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { apiClient, AuthStatus, CreateTripOptions } from "@/lib/api";
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
  total_spent?: number;
  total_budget?: number;
  summary_text?: string;
  bookings?: Array<{
    domain: string;
    provider: string;
    details: Record<string, unknown>;
    amount: number;
  }>;
  result?: Record<string, unknown>;
}

// Mobile tab maps to views: "trips" = list, "plan" = form, "timeline" = live, "settings" = settings
type MobileTab = "trips" | "plan" | "timeline" | "settings";
type View = "timeline" | "detail" | "settings";

export default function Home() {
  const [activeTrip, setActiveTrip] = useState<Trip | null>(null);
  const [events, setEvents] = useState<TripEvent[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [view, setView] = useState<View>("timeline");
  const [mobileTab, setMobileTab] = useState<MobileTab>("plan");

  // Swipe gesture state
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const mainRef = useRef<HTMLElement>(null);

  const { isAuthenticated, logout } = useAuth();
  const { toast } = useToast();
  const { supported: pushSupported, subscribed: pushSubscribed, subscribe: pushSubscribe } = usePushNotifications();

  // Check whether the backend requires auth
  useEffect(() => {
    apiClient.checkAuth().then((status) => {
      setAuthStatus(status);
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
    const prefs = getSavedPreferences();
    if (prefs.orgId && !options.org_id) options.org_id = prefs.orgId;
    if (prefs.policyId && !options.policy_id) options.policy_id = prefs.policyId;

    if (prefs.departureCity && !options.goal.toLowerCase().includes("from")) {
      options.goal = `${options.goal} from ${prefs.departureCity}`;
    }
    if (prefs.cabinClass && prefs.cabinClass !== "economy" && !options.goal.toLowerCase().includes("class")) {
      options.goal = `${options.goal}, ${prefs.cabinClass} class`;
    }

    try {
      const trip = await apiClient.createTrip(options);
      setActiveTrip(trip);
      setEvents([]);
      setView("timeline");
      setMobileTab("timeline");
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

  const handleCancelTrip = async (tripId: string) => {
    try {
      await apiClient.cancelTrip(tripId);
      toast("Trip cancelled", "info");
      setActiveTrip((prev) => prev ? { ...prev, status: "cancelled" } : null);
      refreshTrips();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to cancel trip");
    }
  };

  const handleSelectTrip = async (trip: Trip) => {
    try {
      const full = await apiClient.getTrip(trip.id);
      setActiveTrip(full);
      if (full.status === "complete" || full.status === "completed" || full.status === "failed" || full.status === "cancelled") {
        setView("detail");
        setMobileTab("timeline");
        setEvents([]);
      } else {
        setView("timeline");
        setMobileTab("timeline");
        setEvents([]);
      }
    } catch {
      setActiveTrip(trip);
      setEvents([]);
      setView("timeline");
      setMobileTab("timeline");
    }
  };

  const handleMobileTabChange = (tab: string) => {
    setMobileTab(tab as MobileTab);
    if (tab === "settings") setView("settings");
    else if (tab === "timeline") setView(activeTrip && (activeTrip.status === "complete" || activeTrip.status === "completed" || activeTrip.status === "failed" || activeTrip.status === "cancelled") ? "detail" : "timeline");
    else if (tab === "plan" || tab === "trips") {
      if (view === "settings") setView("timeline");
    }
  };

  // ── Swipe gesture: swipe right from left edge navigates back ─────────────
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    // Only register if starting near the left edge (<30px)
    if (touch.clientX < 30) {
      touchStartRef.current = { x: touch.clientX, y: touch.clientY };
    }
  }, []);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const touch = e.changedTouches[0];
    const dx = touch.clientX - touchStartRef.current.x;
    const dy = Math.abs(touch.clientY - touchStartRef.current.y);
    touchStartRef.current = null;

    // Swipe right at least 80px, mostly horizontal
    if (dx > 80 && dy < dx * 0.5) {
      // Navigate "back" depending on current view
      if (view === "detail") {
        setView("timeline");
      } else if (view === "settings") {
        setView("timeline");
        setMobileTab("plan");
      } else if (mobileTab === "timeline") {
        setMobileTab("trips");
      }
    }
  }, [view, mobileTab]);

  // Show login form only if backend explicitly returns 401
  if (authStatus === "auth_required" && !isAuthenticated) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 safe-area-x">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-primary-700">Travel Agent</h1>
          <p className="text-gray-500 mt-1">AI-powered travel planning assistant</p>
        </header>
        <LoginForm />
      </main>
    );
  }

  // Show backend unavailable banner
  if (authStatus === "unavailable") {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 safe-area-x">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-primary-700">Travel Agent</h1>
          <p className="text-gray-500 mt-1">AI-powered travel planning assistant</p>
        </header>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
          <div className="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
          <h2 className="text-lg font-semibold text-amber-800 mb-2">Backend Not Running</h2>
          <p className="text-sm text-amber-700 mb-4">
            The backend server is not reachable. Make sure it&apos;s running before using the app.
          </p>
          <pre className="bg-amber-100 rounded-lg p-3 text-xs text-left text-amber-900 overflow-x-auto mb-4">
{`# In a separate terminal, from the project root:
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`}
          </pre>
          <button
            onClick={() => apiClient.checkAuth().then(setAuthStatus)}
            className="px-4 py-2.5 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 active:bg-amber-800 transition-colors min-h-touch"
          >
            Retry Connection
          </button>
        </div>
      </main>
    );
  }

  return (
    <main
      ref={mainRef}
      className="max-w-5xl mx-auto px-4 py-6 lg:py-8 safe-area-x mobile-safe-bottom"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header — compact on mobile */}
      <header className="mb-6 lg:mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-primary-700">Travel Agent</h1>
          <p className="text-gray-500 mt-0.5 text-xs lg:text-sm">AI-powered travel planning assistant</p>
        </div>
        <div className="hidden lg:flex items-center gap-2">
          <button
            onClick={() => setView(view === "settings" ? "timeline" : "settings")}
            className={`text-xs border px-3 py-1.5 rounded-lg transition-colors ${
              view === "settings"
                ? "bg-primary-50 border-primary-200 text-primary-700"
                : "text-gray-500 hover:text-gray-700 border-gray-300"
            }`}
          >
            Settings
          </button>
          {isAuthenticated && (
            <button
              onClick={logout}
              className="text-xs text-gray-500 hover:text-gray-700 border border-gray-300 px-3 py-1.5 rounded-lg transition-colors"
            >
              Sign Out
            </button>
          )}
        </div>
        {/* Mobile: just sign out if authenticated */}
        {isAuthenticated && (
          <button
            onClick={logout}
            className="lg:hidden text-xs text-gray-500 hover:text-gray-700 border border-gray-300 px-3 py-1.5 rounded-lg transition-colors min-h-touch flex items-center"
          >
            Sign Out
          </button>
        )}
      </header>

      {/* ── Desktop layout (unchanged) ──────────────────────────────────────── */}
      <div className="hidden lg:block">
        {view === "settings" ? (
          <Settings onClose={() => setView("timeline")} />
        ) : (
          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-1">
              <TripList
                trips={trips}
                activeTrip={activeTrip}
                onSelect={handleSelectTrip}
                onRefresh={refreshTrips}
              />
            </div>
            <div className="col-span-2 space-y-6">
              <TripForm onSubmit={handleCreateTrip} disabled={activeTrip?.status === "running"} />

              {activeTrip && view === "detail" && (
                <TripDetail
                  trip={activeTrip}
                  onCancel={handleCancelTrip}
                  onBack={() => setView("timeline")}
                />
              )}

              {activeTrip && view === "timeline" && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">{activeTrip.goal}</h2>
                    <div className="flex items-center gap-2">
                      {(activeTrip.status === "complete" || activeTrip.status === "completed") && (
                        <button
                          onClick={() => setView("detail")}
                          className="text-xs text-primary-600 hover:text-primary-700 border border-primary-200 px-2 py-1 rounded-md"
                        >
                          View Details
                        </button>
                      )}
                      {(activeTrip.status === "pending" || activeTrip.status === "running") && (
                        <button
                          onClick={() => handleCancelTrip(activeTrip.id)}
                          className="text-xs text-red-500 hover:text-red-700 border border-red-200 px-2 py-1 rounded-md"
                        >
                          Cancel
                        </button>
                      )}
                      <StatusBadge status={activeTrip.status} connected={connected} />
                    </div>
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
        )}
      </div>

      {/* ── Mobile layout (tab-driven) ──────────────────────────────────────── */}
      <div className="lg:hidden">
        {/* Trips tab */}
        {mobileTab === "trips" && (
          <TripList
            trips={trips}
            activeTrip={activeTrip}
            onSelect={handleSelectTrip}
            onRefresh={refreshTrips}
          />
        )}

        {/* Plan tab */}
        {mobileTab === "plan" && (
          <TripForm onSubmit={handleCreateTrip} disabled={activeTrip?.status === "running"} />
        )}

        {/* Live / Timeline tab */}
        {mobileTab === "timeline" && (
          <>
            {activeTrip && view === "detail" && (
              <TripDetail
                trip={activeTrip}
                onCancel={handleCancelTrip}
                onBack={() => setView("timeline")}
              />
            )}

            {activeTrip && view === "timeline" && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-semibold truncate flex-1 mr-2">{activeTrip.goal}</h2>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {(activeTrip.status === "complete" || activeTrip.status === "completed") && (
                      <button
                        onClick={() => setView("detail")}
                        className="text-xs text-primary-600 hover:text-primary-700 border border-primary-200 px-2 py-1.5 rounded-md min-h-touch flex items-center"
                      >
                        Details
                      </button>
                    )}
                    {(activeTrip.status === "pending" || activeTrip.status === "running") && (
                      <button
                        onClick={() => handleCancelTrip(activeTrip.id)}
                        className="text-xs text-red-500 hover:text-red-700 border border-red-200 px-2 py-1.5 rounded-md min-h-touch flex items-center"
                      >
                        Cancel
                      </button>
                    )}
                    <StatusBadge status={activeTrip.status} connected={connected} />
                  </div>
                </div>
                <TripTimeline
                  events={events}
                  onApproval={handleApproval}
                  onClarification={handleClarification}
                  tripId={activeTrip.id}
                />
              </div>
            )}

            {!activeTrip && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
                <p className="text-sm text-gray-400">No active trip</p>
                <button
                  onClick={() => setMobileTab("plan")}
                  className="mt-3 text-xs text-primary-600 font-medium min-h-touch flex items-center justify-center mx-auto"
                >
                  Plan a new trip
                </button>
              </div>
            )}
          </>
        )}

        {/* Settings tab */}
        {mobileTab === "settings" && (
          <Settings onClose={() => { setView("timeline"); setMobileTab("plan"); }} />
        )}
      </div>

      {/* ── Bottom navigation (mobile only) ─────────────────────────────────── */}
      <BottomNav
        activeTab={mobileTab}
        onTabChange={handleMobileTabChange}
        tripCount={trips.length}
        hasActiveTrip={activeTrip?.status === "running"}
      />

      {/* ── Install prompt ──────────────────────────────────────────────────── */}
      <InstallPrompt />
    </main>
  );
}

function StatusBadge({ status, connected }: { status: string; connected: boolean }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    complete: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    cancelled: "bg-gray-100 text-gray-600",
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
