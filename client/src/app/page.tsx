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

    if (dx > 80 && dy < dx * 0.5) {
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
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-contrast flex items-center justify-center">
              <span className="font-display text-white text-lg font-medium">C</span>
            </div>
            <span className="font-ui text-[0.9rem] font-bold uppercase tracking-[0.1em] text-contrast">Concierge</span>
          </div>
          <p className="text-text-muted mt-3 font-body text-sm font-light">Tell us what you want. We&apos;ll handle everything.</p>
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
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-contrast flex items-center justify-center">
              <span className="font-display text-white text-lg font-medium">C</span>
            </div>
            <span className="font-ui text-[0.9rem] font-bold uppercase tracking-[0.1em] text-contrast">Concierge</span>
          </div>
        </header>
        <div className="bg-accent-soft border-2 border-accent-border p-6 text-center">
          <p className="eyebrow justify-center mb-3">System Status</p>
          <h2 className="font-display text-xl text-contrast mb-2">Backend Not Running</h2>
          <p className="text-sm text-text-muted font-body font-light mb-4">
            The backend server is not reachable. Make sure it&apos;s running before using the app.
          </p>
          <pre className="bg-paper-elevated p-3 text-xs text-left text-text-mid overflow-x-auto mb-4 border border-border-light font-mono">
{`# In a separate terminal, from the project root:
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`}
          </pre>
          <button
            onClick={() => apiClient.checkAuth().then(setAuthStatus)}
            className="px-6 py-3 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition min-h-touch"
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
      {/* ── Navigation header ──────────────────────────────────────────────── */}
      <header className="mb-6 lg:mb-8 flex items-center justify-between border-b-2 border-border-heavy pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-contrast flex items-center justify-center">
            <span className="font-display text-paper text-lg font-medium">C</span>
          </div>
          <div>
            <span className="font-ui text-[0.9rem] font-bold uppercase tracking-[0.1em] text-contrast block leading-tight">Concierge</span>
            <span className="text-text-ghost font-body text-[0.62rem] block">Travel, handled for you</span>
          </div>
        </div>
        <div className="hidden lg:flex items-center gap-3">
          <button
            onClick={() => setView(view === "settings" ? "timeline" : "settings")}
            className={`font-ui text-xs font-semibold uppercase tracking-[0.08em] px-4 py-2 border-2 btn-transition ${
              view === "settings"
                ? "bg-contrast text-paper border-contrast"
                : "text-text-mid hover:text-contrast border-border-heavy hover:bg-contrast hover:text-paper"
            }`}
          >
            Settings
          </button>
          {isAuthenticated && (
            <button
              onClick={logout}
              className="font-ui text-xs font-semibold uppercase tracking-[0.08em] text-text-muted hover:text-contrast border-2 border-border-light hover:border-border-heavy px-4 py-2 btn-transition"
            >
              Sign Out
            </button>
          )}
        </div>
        {isAuthenticated && (
          <button
            onClick={logout}
            className="lg:hidden font-ui text-xs font-semibold uppercase tracking-[0.08em] text-text-muted border-2 border-border-light px-3 py-2 btn-transition min-h-touch flex items-center"
          >
            Sign Out
          </button>
        )}
      </header>

      {/* ── Desktop layout ──────────────────────────────────────────────────── */}
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
                <div className="bg-white border-2 border-border-heavy p-6 card-hover-bar">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-display text-xl font-medium">{activeTrip.goal}</h2>
                    <div className="flex items-center gap-2">
                      {(activeTrip.status === "complete" || activeTrip.status === "completed") && (
                        <button
                          onClick={() => setView("detail")}
                          className="font-ui text-xs font-bold uppercase tracking-[0.1em] text-accent border-2 border-accent-border px-3 py-1.5 hover:bg-accent-soft btn-transition"
                        >
                          View Details
                        </button>
                      )}
                      {(activeTrip.status === "pending" || activeTrip.status === "running") && (
                        <button
                          onClick={() => handleCancelTrip(activeTrip.id)}
                          className="font-ui text-xs font-bold uppercase tracking-[0.1em] text-text-muted border-2 border-border-light px-3 py-1.5 hover:border-border-heavy btn-transition"
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
        {mobileTab === "trips" && (
          <TripList
            trips={trips}
            activeTrip={activeTrip}
            onSelect={handleSelectTrip}
            onRefresh={refreshTrips}
          />
        )}

        {mobileTab === "plan" && (
          <TripForm onSubmit={handleCreateTrip} disabled={activeTrip?.status === "running"} />
        )}

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
              <div className="bg-white border-2 border-border-heavy p-4 card-hover-bar">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-display text-base font-medium truncate flex-1 mr-2">{activeTrip.goal}</h2>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {(activeTrip.status === "complete" || activeTrip.status === "completed") && (
                      <button
                        onClick={() => setView("detail")}
                        className="font-ui text-xs font-bold uppercase tracking-[0.1em] text-accent border-2 border-accent-border px-2 py-1.5 btn-transition min-h-touch flex items-center"
                      >
                        Details
                      </button>
                    )}
                    {(activeTrip.status === "pending" || activeTrip.status === "running") && (
                      <button
                        onClick={() => handleCancelTrip(activeTrip.id)}
                        className="font-ui text-xs font-bold uppercase tracking-[0.1em] text-text-muted border-2 border-border-light px-2 py-1.5 btn-transition min-h-touch flex items-center"
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
              <div className="bg-white border-2 border-border-heavy p-8 text-center">
                <p className="text-sm text-text-ghost font-body">No active trip</p>
                <button
                  onClick={() => setMobileTab("plan")}
                  className="mt-3 font-ui text-xs font-bold uppercase tracking-[0.1em] text-accent min-h-touch flex items-center justify-center mx-auto"
                >
                  Plan a new trip
                </button>
              </div>
            )}
          </>
        )}

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
  const styles: Record<string, string> = {
    pending: "border-border-light text-text-ghost",
    running: "border-accent-border text-accent",
    completed: "border-success-border text-success",
    complete: "border-success-border text-success",
    failed: "border-accent text-accent",
    cancelled: "border-border-light text-text-ghost",
  };

  return (
    <div className="flex items-center gap-2">
      {connected && status === "running" && (
        <span className="h-2 w-2 bg-accent animate-pulse-dot" />
      )}
      <span className={`px-2.5 py-0.5 border-[1.5px] font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] ${styles[status] ?? "border-border-light text-text-ghost"}`}>
        {status}
      </span>
    </div>
  );
}
