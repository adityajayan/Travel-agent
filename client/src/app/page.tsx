"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Settings as SettingsIcon, LogOut } from "lucide-react";
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

type MobileTab = "trips" | "plan" | "timeline" | "settings";
type View = "timeline" | "detail" | "settings";

export default function Home() {
  const router = useRouter();
  const [activeTrip, setActiveTrip] = useState<Trip | null>(null);
  const [events, setEvents] = useState<TripEvent[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [view, setView] = useState<View>("timeline");
  const [mobileTab, setMobileTab] = useState<MobileTab>("plan");

  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const mainRef = useRef<HTMLElement>(null);

  const { isAuthenticated, logout } = useAuth();
  const { toast } = useToast();
  const { supported: pushSupported, subscribed: pushSubscribed, subscribe: pushSubscribe } = usePushNotifications();

  useEffect(() => {
    apiClient.checkAuth().then((status) => {
      setAuthStatus(status);
    });
  }, [isAuthenticated]);

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

  if (authStatus === "auth_required" && !isAuthenticated) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 safe-area-x">
        <header className="mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-navy rounded-lg flex items-center justify-center">
              <span className="font-serif text-white text-lg font-medium">C</span>
            </div>
            <span className="font-sans text-lg font-semibold text-navy">Concierge</span>
          </div>
          <p className="text-slate mt-3 font-sans text-sm">Tell us what you want. We&apos;ll handle everything.</p>
        </header>
        <LoginForm />
      </main>
    );
  }

  if (authStatus === "unavailable") {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 safe-area-x">
        <header className="mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-navy rounded-lg flex items-center justify-center">
              <span className="font-serif text-white text-lg font-medium">C</span>
            </div>
            <span className="font-sans text-lg font-semibold text-navy">Concierge</span>
          </div>
        </header>
        <div className="bg-gold/8 border border-gold-light rounded-xl p-6 text-center">
          <p className="eyebrow justify-center mb-3">System Status</p>
          <h2 className="font-serif text-xl text-navy mb-2">Backend Not Running</h2>
          <p className="text-sm text-slate font-sans mb-4">
            The backend server is not reachable. Make sure it&apos;s running before using the app.
          </p>
          <pre className="bg-cream-dark p-3 text-xs text-left text-charcoal overflow-x-auto mb-4 border border-gold-light/40 rounded-lg font-mono">
{`# In a separate terminal, from the project root:
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`}
          </pre>
          <button
            onClick={() => apiClient.checkAuth().then(setAuthStatus)}
            className="px-6 py-3 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light btn-transition min-h-touch"
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
      <header className="mb-6 lg:mb-8 flex items-center justify-between border-b border-gold-light/40 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-navy rounded-lg flex items-center justify-center">
            <span className="font-serif text-cream text-lg font-medium">C</span>
          </div>
          <div>
            <span className="font-sans text-lg font-semibold text-navy block leading-tight">Concierge</span>
            <span className="text-slate/60 font-sans text-xs block">Travel, handled for you</span>
          </div>
        </div>
        <div className="hidden lg:flex items-center gap-3">
          <button
            onClick={() => setView(view === "settings" ? "timeline" : "settings")}
            className={`font-sans text-sm font-medium px-4 py-2 border rounded-md btn-transition flex items-center gap-1.5 ${
              view === "settings"
                ? "bg-navy text-cream border-navy"
                : "text-charcoal hover:text-navy border-navy/20 hover:bg-navy hover:text-cream"
            }`}
          >
            <SettingsIcon className="h-4 w-4" />
            Settings
          </button>
          {isAuthenticated && (
            <button
              onClick={logout}
              className="font-sans text-sm font-medium text-slate hover:text-navy border border-gold-light/40 hover:border-navy/20 px-4 py-2 rounded-md btn-transition flex items-center gap-1.5"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          )}
        </div>
        {isAuthenticated && (
          <button
            onClick={logout}
            className="lg:hidden font-sans text-xs font-medium text-slate border border-gold-light/40 px-3 py-2 rounded-md btn-transition min-h-touch flex items-center gap-1"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
        )}
      </header>

      {/* Desktop layout */}
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
                <div className="bg-white border border-gold-light/40 rounded-xl p-6 shadow-sm card-hover-bar">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-serif text-xl font-medium text-navy">{activeTrip.goal}</h2>
                    <div className="flex items-center gap-2">
                      {(activeTrip.status === "complete" || activeTrip.status === "completed") && (
                        <button
                          onClick={() => router.push(`/trips/${activeTrip.id}`)}
                          className="font-sans text-xs font-semibold text-gold border border-gold-light px-3 py-1.5 rounded-md hover:bg-gold/8 btn-transition"
                        >
                          View Details
                        </button>
                      )}
                      {(activeTrip.status === "pending" || activeTrip.status === "running") && (
                        <button
                          onClick={() => handleCancelTrip(activeTrip.id)}
                          className="font-sans text-xs font-medium text-slate border border-gold-light/40 px-3 py-1.5 rounded-md hover:border-navy/20 btn-transition"
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

      {/* Mobile layout */}
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
              <div className="bg-white border border-gold-light/40 rounded-xl p-4 shadow-sm card-hover-bar">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-serif text-base font-medium text-navy truncate flex-1 mr-2">{activeTrip.goal}</h2>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {(activeTrip.status === "complete" || activeTrip.status === "completed") && (
                      <button
                        onClick={() => router.push(`/trips/${activeTrip.id}`)}
                        className="font-sans text-xs font-semibold text-gold border border-gold-light px-2 py-1.5 rounded-md btn-transition min-h-touch flex items-center"
                      >
                        Details
                      </button>
                    )}
                    {(activeTrip.status === "pending" || activeTrip.status === "running") && (
                      <button
                        onClick={() => handleCancelTrip(activeTrip.id)}
                        className="font-sans text-xs font-medium text-slate border border-gold-light/40 px-2 py-1.5 rounded-md btn-transition min-h-touch flex items-center"
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
              <div className="bg-white border border-gold-light/40 rounded-xl p-8 text-center shadow-sm">
                <p className="text-sm text-slate font-sans">No active trip</p>
                <button
                  onClick={() => setMobileTab("plan")}
                  className="mt-3 font-sans text-sm font-medium text-gold min-h-touch flex items-center justify-center mx-auto"
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

      <BottomNav
        activeTab={mobileTab}
        onTabChange={handleMobileTabChange}
        tripCount={trips.length}
        hasActiveTrip={activeTrip?.status === "running"}
      />

      <InstallPrompt />
    </main>
  );
}

function StatusBadge({ status, connected }: { status: string; connected: boolean }) {
  const styles: Record<string, string> = {
    pending: "border-gold-light text-slate",
    running: "border-gold text-gold",
    completed: "border-success-border text-success",
    complete: "border-success-border text-success",
    failed: "border-error text-error",
    cancelled: "border-gold-light text-slate",
  };

  return (
    <div className="flex items-center gap-2">
      {connected && status === "running" && (
        <span className="h-2 w-2 bg-gold rounded-full animate-pulse-dot" />
      )}
      <span className={`px-2.5 py-0.5 border rounded-md font-sans text-xs font-medium ${styles[status] ?? "border-gold-light text-slate"}`}>
        {status}
      </span>
    </div>
  );
}
