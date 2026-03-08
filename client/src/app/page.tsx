"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Settings as SettingsIcon, LogOut } from "lucide-react";
import TripForm from "@/components/TripForm";
import TripTimeline from "@/components/TripTimeline";
import TripList from "@/components/TripList";
import TripDetail from "@/components/TripDetail";
import ItineraryView from "@/components/itinerary/ItineraryView";
import Settings, { getSavedPreferences } from "@/components/Settings";
import BottomNav from "@/components/BottomNav";
import InstallPrompt from "@/components/InstallPrompt";
import { useWebSocket } from "@/hooks/useWebSocket";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { apiClient, AuthStatus, CreateTripOptions } from "@/lib/api";
import { useAuth, LoginForm } from "@/components/AuthGate";
import { useToast } from "@/components/Toast";
import StatusBadge from "@/components/ui/StatusBadge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

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
  is_archived?: boolean;
  bookings?: Array<{
    domain: string;
    provider: string;
    details: Record<string, unknown>;
    amount: number;
  }>;
  result?: Record<string, unknown>;
}

type MobileTab = "trips" | "plan" | "settings";
type TripView = "list" | "timeline" | "detail";
type View = "timeline" | "detail" | "settings";

export default function Home() {
  const router = useRouter();
  const [activeTrip, setActiveTrip] = useState<Trip | null>(null);
  const [events, setEvents] = useState<TripEvent[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [view, setView] = useState<View>("timeline");
  const [mobileTab, setMobileTab] = useState<MobileTab>("plan");
  const [tripView, setTripView] = useState<TripView>("list");

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
          prev ? { ...prev, status: tripEvent.type === "trip_completed" ? "complete" : "failed" } : null
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
      if (options.parsed_params && !options.parsed_params.origin) {
        options.parsed_params.origin = prefs.departureCity;
      }
    }
    if (prefs.cabinClass && prefs.cabinClass !== "economy" && !options.goal.toLowerCase().includes("class")) {
      options.goal = `${options.goal}, ${prefs.cabinClass} class`;
    }

    try {
      const trip = await apiClient.createTrip(options);
      setActiveTrip(trip);
      setEvents([]);
      setView("timeline");
      setMobileTab("trips");
      setTripView("timeline");
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

  const handleRetryTrip = async (tripId: string) => {
    try {
      const updated = await apiClient.retryTrip(tripId);
      setActiveTrip(updated);
      setEvents([]);
      setView("timeline");
      setTripView("timeline");
      toast("Trip retrying — agents are replanning", "success");
      refreshTrips();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to retry trip");
    }
  };

  const handleArchiveTrip = async (tripId: string) => {
    try {
      await apiClient.archiveTrip(tripId);
      toast("Trip archived", "info");
      setActiveTrip(null);
      refreshTrips();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to archive trip");
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
      if (full.status === "complete" || full.status === "failed" || full.status === "cancelled") {
        setView("detail");
        setTripView("detail");
        setEvents([]);
      } else {
        setView("timeline");
        setTripView("timeline");
        setEvents([]);
      }
      setMobileTab("trips");
    } catch {
      setActiveTrip(trip);
      setEvents([]);
      setView("timeline");
      setTripView("timeline");
      setMobileTab("trips");
    }
  };

  const handleMobileTabChange = (tab: string) => {
    setMobileTab(tab as MobileTab);
    if (tab === "settings") setView("settings");
    else if (tab === "trips") {
      if (view === "settings") setView("timeline");
      // Keep tripView as-is so user returns to where they were
    } else if (tab === "plan") {
      if (view === "settings") setView("timeline");
    }
  };

  const handleBackToList = () => {
    setTripView("list");
    setActiveTrip(null);
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
      if (tripView === "detail" && mobileTab === "trips") {
        setTripView("timeline");
      } else if (tripView === "timeline" && mobileTab === "trips") {
        handleBackToList();
      } else if (view === "settings") {
        setView("timeline");
        setMobileTab("plan");
      }
    }
  }, [view, mobileTab, tripView]); // eslint-disable-line react-hooks/exhaustive-deps

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
          <Button variant="primary" size="md" onClick={() => apiClient.checkAuth().then(setAuthStatus)}>
            Retry Connection
          </Button>
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
            className={`font-sans text-sm font-medium px-4 py-2 border rounded-md btn-transition flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-gold/30 ${
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
              <TripForm onSubmit={handleCreateTrip} disabled={activeTrip?.status === "planning"} activeTripSelected={!!activeTrip} />

              {activeTrip && view === "detail" && (
                <ItineraryView
                  tripId={activeTrip.id}
                  onBack={() => setView("timeline")}
                />
              )}

              {activeTrip && view === "timeline" && (
                <Card hover padding="md">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-serif text-xl font-medium text-navy">{activeTrip.goal}</h2>
                    <div className="flex items-center gap-2">
                      {activeTrip.status === "complete" && (
                        <Button variant="ghost" size="sm" onClick={() => router.push(`/trips/${activeTrip.id}`)} className="text-gold border border-gold-light hover:bg-gold/8">
                          View Details
                        </Button>
                      )}
                      {activeTrip.status === "failed" && (
                        <Button variant="primary" size="sm" onClick={() => handleRetryTrip(activeTrip.id)}>
                          Retry
                        </Button>
                      )}
                      {(activeTrip.status === "planning" || activeTrip.status === "review") && (
                        <Button variant="secondary" size="sm" onClick={() => handleCancelTrip(activeTrip.id)}>
                          Cancel
                        </Button>
                      )}
                      <TripStatusBadge status={activeTrip.status} connected={connected} />
                    </div>
                  </div>
                  <TripTimeline
                    events={events}
                    onApproval={handleApproval}
                    onClarification={handleClarification}
                    tripId={activeTrip.id}
                  />
                </Card>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Mobile layout */}
      <div className="lg:hidden">
        {mobileTab === "trips" && (
          <>
            {tripView === "list" && (
              <TripList
                trips={trips}
                activeTrip={activeTrip}
                onSelect={handleSelectTrip}
                onRefresh={refreshTrips}
              />
            )}

            {tripView === "detail" && activeTrip && (
              <div>
                <button
                  onClick={handleBackToList}
                  className="font-sans text-sm font-medium text-gold hover:text-gold-dark btn-transition mb-3 flex items-center gap-1 min-h-touch"
                >
                  <span className="text-lg leading-none">&larr;</span> Back to Trips
                </button>
                <ItineraryView
                  tripId={activeTrip.id}
                  onBack={handleBackToList}
                />
              </div>
            )}

            {tripView === "timeline" && activeTrip && (
              <div>
                <button
                  onClick={handleBackToList}
                  className="font-sans text-sm font-medium text-gold hover:text-gold-dark btn-transition mb-3 flex items-center gap-1 min-h-touch"
                >
                  <span className="text-lg leading-none">&larr;</span> Back to Trips
                </button>
                <Card hover padding="sm">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="font-serif text-base font-medium text-navy truncate flex-1 mr-2">{activeTrip.goal}</h2>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {activeTrip.status === "complete" && (
                        <Button variant="ghost" size="sm" onClick={() => { setTripView("detail"); setView("detail"); }} className="text-gold border border-gold-light hover:bg-gold/8">
                          Details
                        </Button>
                      )}
                      {activeTrip.status === "failed" && (
                        <Button variant="primary" size="sm" onClick={() => handleRetryTrip(activeTrip.id)}>
                          Retry
                        </Button>
                      )}
                      {(activeTrip.status === "planning" || activeTrip.status === "review") && (
                        <Button variant="secondary" size="sm" onClick={() => handleCancelTrip(activeTrip.id)}>
                          Cancel
                        </Button>
                      )}
                      <TripStatusBadge status={activeTrip.status} connected={connected} />
                    </div>
                  </div>
                  <TripTimeline
                    events={events}
                    onApproval={handleApproval}
                    onClarification={handleClarification}
                    tripId={activeTrip.id}
                  />
                </Card>
              </div>
            )}

            {tripView !== "list" && !activeTrip && (
              <Card padding="md" className="text-center">
                <p className="text-sm text-slate font-sans">No active trip</p>
                <Button variant="ghost" size="sm" onClick={() => setMobileTab("plan")} className="mt-3 mx-auto">
                  Plan a new trip
                </Button>
              </Card>
            )}
          </>
        )}

        {mobileTab === "plan" && (
          <TripForm onSubmit={handleCreateTrip} disabled={activeTrip?.status === "planning"} />
        )}

        {mobileTab === "settings" && (
          <Settings onClose={() => { setView("timeline"); setMobileTab("plan"); }} />
        )}
      </div>

      <BottomNav
        activeTab={mobileTab}
        onTabChange={handleMobileTabChange}
        tripCount={trips.length}
        hasActiveTrip={activeTrip?.status === "planning"}
      />

      <InstallPrompt />
    </main>
  );
}

function TripStatusBadge({ status, connected }: { status: string; connected: boolean }) {
  return <StatusBadge status={status} pulse={connected && status === "planning"} />;
}
