"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient } from "@/lib/api";
import type { TripItinerary } from "@/lib/itinerary-types";
import { useWebSocket } from "@/hooks/useWebSocket";
import ItineraryHeader from "./ItineraryHeader";
import ItineraryTabBar from "./ItineraryTabBar";
import ItineraryDaySection from "./ItineraryDaySection";
import BudgetBar from "./BudgetBar";
import TripChat from "./TripChat";
import LoadingDots from "@/components/ui/LoadingDots";
import EmptyState from "@/components/ui/EmptyState";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import { Map, FileText, Clock, CreditCard } from "lucide-react";

interface ItineraryViewProps {
  tripId: string;
  onBack?: () => void;
  /** When true, hides the header (title/back/status) — parent handles it */
  embedded?: boolean;
}

export default function ItineraryView({ tripId, onBack, embedded }: ItineraryViewProps) {
  const [itinerary, setItinerary] = useState<TripItinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("itinerary");
  const [paymentStatus, setPaymentStatus] = useState<string>("unpaid");
  const [checkingOut, setCheckingOut] = useState(false);

  const fetchItinerary = useCallback(async () => {
    try {
      const [data, trip] = await Promise.all([
        apiClient.getTripItinerary(tripId),
        apiClient.getTrip(tripId),
      ]);
      setItinerary(data);
      setPaymentStatus(trip.payment_status ?? "unpaid");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load itinerary");
    } finally {
      setLoading(false);
    }
  }, [tripId]);

  useEffect(() => {
    setLoading(true);
    setItinerary(null);
    setError(null);
    setActiveTab("itinerary");
    fetchItinerary();
  }, [fetchItinerary]);

  useWebSocket(
    itinerary?.status === "review" || itinerary?.status === "planning" || itinerary?.status === "booking"
      ? tripId
      : null,
    (event) => {
      if (
        event.type === "approval_decided" ||
        event.type === "trip_completed" ||
        event.type === "trip_failed" ||
        event.type === "booking_progress"
      ) {
        fetchItinerary();
      }
    }
  );

  const handleItemAction = async (itemId: string, action: string) => {
    if (!itinerary) return;

    setItinerary((prev) => {
      if (!prev) return prev;
      const newStatus = action === "approve" ? "confirmed" : action === "reject" ? "rejected" : prev.status;
      return {
        ...prev,
        days: prev.days.map((day) => ({
          ...day,
          items: day.items.map((item) =>
            item.id === itemId ? { ...item, status: newStatus, approval_id: null } : item
          ),
        })),
      };
    });

    try {
      await apiClient.updateItineraryItem(tripId, itemId, action);
      fetchItinerary();
    } catch {
      fetchItinerary();
    }
  };

  const handleApproveAll = async () => {
    if (!itinerary) return;
    const pendingItems = itinerary.days
      .flatMap((d) => d.items)
      .filter((item) => item.status === "awaiting_approval");

    for (const item of pendingItems) {
      await handleItemAction(item.id, "approve");
    }
  };

  const handleCheckout = async () => {
    setCheckingOut(true);
    try {
      const { checkout_url } = await apiClient.createCheckoutSession(tripId);
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
      setCheckingOut(false);
    }
  };

  const pendingCount = itinerary
    ? itinerary.days.flatMap((d) => d.items).filter((i) => i.status === "awaiting_approval").length
    : 0;

  const totalCost = itinerary
    ? itinerary.days.flatMap((d) => d.items).reduce((sum, item) => sum + item.cost, 0)
    : 0;

  const showPayButton =
    itinerary?.status === "review" &&
    paymentStatus === "unpaid" &&
    pendingCount === 0 &&
    totalCost > 0;

  if (loading) {
    return <LoadingDots label="Loading itinerary..." />;
  }

  if (error || !itinerary) {
    return (
      <div className="bg-error/5 border border-error rounded-xl p-6 text-center">
        <p className="eyebrow justify-center mb-2">Error</p>
        <p className="font-sans text-sm text-charcoal">{error || "Itinerary not found"}</p>
        {onBack && (
          <Button variant="primary" size="md" onClick={onBack} className="mt-4">
            Back to Trips
          </Button>
        )}
      </div>
    );
  }

  return (
    <div>
      {!embedded && (
        <ItineraryHeader
          title={itinerary.title}
          subtitle={itinerary.subtitle}
          status={itinerary.status}
          pendingCount={pendingCount}
          onApproveAll={handleApproveAll}
        />
      )}

      {embedded && pendingCount > 0 && (
        <div className="flex items-center justify-end mb-3">
          <Button variant="primary" size="sm" onClick={handleApproveAll}>
            Approve All ({pendingCount})
          </Button>
        </div>
      )}

      {/* Pay & Book CTA */}
      {showPayButton && (
        <Card className="mb-6 border-gold bg-gold/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-sans text-sm font-semibold text-navy">Ready to book</p>
              <p className="font-sans text-xs text-slate mt-0.5">
                All items approved. Total: ${totalCost.toFixed(2)} + service fee
              </p>
            </div>
            <Button
              variant="primary"
              size="md"
              onClick={handleCheckout}
              disabled={checkingOut}
              className="flex items-center gap-2 whitespace-nowrap"
            >
              <CreditCard className="h-4 w-4" />
              {checkingOut ? "Redirecting..." : `Pay & Book — $${(totalCost + 9.99).toFixed(2)}`}
            </Button>
          </div>
        </Card>
      )}

      {/* Booking in progress banner */}
      {itinerary.status === "booking" && (
        <Card className="mb-6 border-blue-200 bg-blue-50">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <div>
              <p className="font-sans text-sm font-semibold text-blue-700">Booking in progress</p>
              <p className="font-sans text-xs text-blue-600/70">
                We&apos;re confirming your reservations with providers...
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Payment pending banner */}
      {itinerary.status === "payment_pending" && (
        <Card className="mb-6 border-gold bg-gold/5">
          <div className="flex items-center gap-3">
            <CreditCard className="h-5 w-5 text-gold" />
            <div>
              <p className="font-sans text-sm font-semibold text-navy">Awaiting payment</p>
              <p className="font-sans text-xs text-slate">
                Complete your payment to proceed with booking.
              </p>
            </div>
          </div>
        </Card>
      )}

      <div className={`grid grid-cols-1 ${embedded ? "gap-4" : "lg:grid-cols-[1fr_380px] gap-6"}`}>
        {/* Left panel */}
        <div>
          <ItineraryTabBar activeTab={activeTab} onTabChange={setActiveTab} />

          {activeTab === "itinerary" && (
            <>
              {itinerary.narrative && (
                <Card className="mb-6">
                  <p className="eyebrow mb-2">Trip Summary</p>
                  <div className="font-sans text-sm text-slate whitespace-pre-wrap leading-relaxed">
                    {itinerary.narrative}
                  </div>
                </Card>
              )}

              {itinerary.alerts.length > 0 && (
                <div className="space-y-2 mb-6">
                  {itinerary.alerts.map((alert, i) => (
                    <div
                      key={i}
                      className="bg-gold/8 border border-gold rounded-lg p-3 flex items-center gap-2 animate-slide-in-right"
                      style={{ animationDelay: `${i * 0.1}s` }}
                    >
                      <span className="font-sans text-xs font-semibold text-gold">
                        {String(alert.type || "Alert")}
                      </span>
                      <span className="font-sans text-xs text-charcoal">
                        {String(alert.message || "")}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {itinerary.days.length > 0 ? (
                itinerary.days.map((day, i) => (
                  <ItineraryDaySection
                    key={day.date}
                    day={day}
                    index={i}
                    tripId={tripId}
                    onItemAction={handleItemAction}
                  />
                ))
              ) : (
                <EmptyState title="Itinerary" subtitle="No itinerary items yet" />
              )}
            </>
          )}

          {activeTab === "map" && (
            <EmptyState icon={Map} title="Map View" subtitle="Coming soon" />
          )}

          {activeTab === "documents" && (
            <EmptyState icon={FileText} title="Documents" subtitle="Coming soon" />
          )}

          {activeTab === "history" && (
            <EmptyState icon={Clock} title="History" subtitle="Agent run history and tool calls will appear here" />
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          <BudgetBar budget={itinerary.budget} />
          <TripChat tripId={tripId} />
        </div>
      </div>
    </div>
  );
}
