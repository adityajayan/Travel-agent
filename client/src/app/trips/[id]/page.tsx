"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { TripItinerary } from "@/lib/itinerary-types";
import { useWebSocket } from "@/hooks/useWebSocket";
import ItineraryHeader from "@/components/itinerary/ItineraryHeader";
import ItineraryTabBar from "@/components/itinerary/ItineraryTabBar";
import ItineraryDaySection from "@/components/itinerary/ItineraryDaySection";
import BudgetBar from "@/components/itinerary/BudgetBar";
import TripChat from "@/components/itinerary/TripChat";

export default function TripArtifactPage() {
  const params = useParams();
  const tripId = params.id as string;

  const [itinerary, setItinerary] = useState<TripItinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("itinerary");

  const fetchItinerary = useCallback(async () => {
    try {
      const data = await apiClient.getTripItinerary(tripId);
      setItinerary(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load itinerary");
    } finally {
      setLoading(false);
    }
  }, [tripId]);

  // Initial fetch
  useEffect(() => {
    fetchItinerary();
  }, [fetchItinerary]);

  // SSE for live updates when trip is still active
  useWebSocket(
    itinerary?.status === "awaiting_approval" || itinerary?.status === "running"
      ? tripId
      : null,
    (event) => {
      if (
        event.type === "approval_decided" ||
        event.type === "trip_completed" ||
        event.type === "trip_failed"
      ) {
        // Refresh itinerary data on relevant events
        fetchItinerary();
      }
    }
  );

  const handleItemAction = async (itemId: string, action: string) => {
    if (!itinerary) return;

    // Optimistic update
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
      // Refresh to get authoritative data
      fetchItinerary();
    } catch {
      // Revert on error
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

  const pendingCount = itinerary
    ? itinerary.days.flatMap((d) => d.items).filter((i) => i.status === "awaiting_approval").length
    : 0;

  if (loading) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-6 lg:py-8 safe-area-x">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-navy rounded-lg flex items-center justify-center">
            <span className="font-serif text-cream text-lg font-medium">C</span>
          </div>
          <span className="font-sans text-sm font-semibold text-navy">
            Concierge
          </span>
        </div>
        <div className="text-center py-16">
          <div className="flex justify-center gap-1.5 mb-4">
            <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" />
            <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
            <span className="h-2 w-2 rounded-full bg-navy/20 animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
          </div>
          <p className="font-sans text-sm text-slate/60">Loading itinerary...</p>
        </div>
      </main>
    );
  }

  if (error || !itinerary) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-6 lg:py-8 safe-area-x">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-navy rounded-lg flex items-center justify-center">
            <span className="font-serif text-cream text-lg font-medium">C</span>
          </div>
          <span className="font-sans text-sm font-semibold text-navy">
            Concierge
          </span>
        </div>
        <div className="bg-error/5 border border-error rounded-xl p-6 text-center">
          <p className="eyebrow justify-center mb-2">Error</p>
          <p className="font-sans text-sm text-charcoal">{error || "Itinerary not found"}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 mt-4 px-6 py-3 bg-navy text-cream font-sans text-xs font-semibold rounded-md hover:bg-navy-light btn-transition"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Back to Trips
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-6 lg:py-8 safe-area-x">
      {/* Branding */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-navy rounded-lg flex items-center justify-center">
          <span className="font-serif text-cream text-lg font-medium">C</span>
        </div>
        <div>
          <span className="font-sans text-sm font-semibold text-navy block leading-tight">
            Concierge
          </span>
          <span className="text-slate/60 font-sans text-[0.62rem] block">
            Travel, handled for you
          </span>
        </div>
      </div>

      {/* Header */}
      <ItineraryHeader
        title={itinerary.title}
        subtitle={itinerary.subtitle}
        status={itinerary.status}
        pendingCount={pendingCount}
        onApproveAll={handleApproveAll}
      />

      {/* Two-panel layout: desktop side-by-side, mobile stacked */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        {/* Left panel — Itinerary */}
        <div>
          <ItineraryTabBar activeTab={activeTab} onTabChange={setActiveTab} />

          {activeTab === "itinerary" && (
            <>
              {/* Narrative */}
              {itinerary.narrative && (
                <div className="border border-gold-light/40 bg-white rounded-xl p-5 mb-6 shadow-sm">
                  <p className="eyebrow mb-2">Trip Summary</p>
                  <div className="font-sans text-sm text-slate whitespace-pre-wrap leading-relaxed">
                    {itinerary.narrative}
                  </div>
                </div>
              )}

              {/* Alert banners */}
              {itinerary.alerts.length > 0 && (
                <div className="space-y-2 mb-6">
                  {itinerary.alerts.map((alert, i) => (
                    <div
                      key={i}
                      className="bg-gold/8 border border-gold rounded-lg p-3 flex items-center gap-2 animate-slide-in-right"
                      style={{ animationDelay: `${i * 0.1}s` }}
                    >
                      <span className="font-sans text-[0.65rem] font-semibold text-gold">
                        {String(alert.type || "Alert")}
                      </span>
                      <span className="font-sans text-xs text-charcoal">
                        {String(alert.message || "")}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Day sections */}
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
                <div className="border border-gold-light/40 bg-white rounded-xl p-8 text-center shadow-sm">
                  <p className="font-sans text-sm text-slate/60">
                    No itinerary items yet
                  </p>
                </div>
              )}
            </>
          )}

          {activeTab === "map" && (
            <div className="border border-gold-light/40 bg-white rounded-xl p-8 text-center shadow-sm">
              <p className="eyebrow justify-center mb-2">Map View</p>
              <p className="font-sans text-sm text-slate/60">Coming soon</p>
            </div>
          )}

          {activeTab === "documents" && (
            <div className="border border-gold-light/40 bg-white rounded-xl p-8 text-center shadow-sm">
              <p className="eyebrow justify-center mb-2">Documents</p>
              <p className="font-sans text-sm text-slate/60">Coming soon</p>
            </div>
          )}

          {activeTab === "history" && (
            <div className="border border-gold-light/40 bg-white rounded-xl p-8 text-center shadow-sm">
              <p className="eyebrow justify-center mb-2">History</p>
              <p className="font-sans text-sm text-slate/60">
                Agent run history and tool calls will appear here
              </p>
            </div>
          )}
        </div>

        {/* Right sidebar — Budget + Chat */}
        <div className="space-y-6">
          <BudgetBar budget={itinerary.budget} />
          <TripChat tripId={tripId} />
        </div>
      </div>
    </main>
  );
}
