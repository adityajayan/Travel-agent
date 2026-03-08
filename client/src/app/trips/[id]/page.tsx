"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import ItineraryView from "@/components/itinerary/ItineraryView";

export default function TripArtifactPage() {
  const params = useParams();
  const tripId = params.id as string;

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
          <span className="text-slate/60 font-sans text-[10px] block">
            Travel, handled for you
          </span>
        </div>
        <Link
          href="/"
          className="ml-auto inline-flex items-center gap-1.5 px-4 py-2 border border-navy/20 text-charcoal font-sans text-xs font-medium rounded-md hover:bg-navy hover:text-cream btn-transition"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Back to Trips
        </Link>
      </div>

      <ItineraryView tripId={tripId} />
    </main>
  );
}
