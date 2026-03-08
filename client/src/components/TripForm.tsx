"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Plus, ChevronUp } from "lucide-react";
import VoiceInputButton from "./VoiceInputButton";
import { CreateTripOptions, ParseTripResponse, ParsedTripParams, DateSuggestion, apiClient } from "@/lib/api";
import { searchAirports, popularAirports, resolveAirport, Airport } from "@/lib/airports";
import { getSavedPreferences } from "./Settings";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

interface TripFormProps {
  onSubmit: (options: CreateTripOptions) => void;
  disabled?: boolean;
  activeTripSelected?: boolean;
}

const PLACEHOLDER_EXAMPLES = [
  "Plan a 5-day trip to Tokyo under $3000\u2026",
  "Find me business class flights to London next Tuesday\u2026",
  "Weekend getaway to wine country, boutique hotel, 2 people\u2026",
  "Family vacation to Italy in July, 2 adults 2 kids\u2026",
  "Book a hotel in SF near Union Square for 3 nights\u2026",
];

const DOMAIN_STYLES: Record<string, string> = {
  flight: "border-blue-200 text-blue-600 bg-blue-50",
  hotel: "border-purple-200 text-purple-600 bg-purple-50",
  transport: "border-orange-200 text-orange-600 bg-orange-50",
  activity: "border-teal-200 text-teal-600 bg-teal-50",
};

const DOMAIN_LABELS: Record<string, string> = {
  flight: "Flights",
  hotel: "Hotels",
  transport: "Transport",
  activity: "Activities",
};

export default function TripForm({ onSubmit, disabled, activeTripSelected }: TripFormProps) {
  const [text, setText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseResult, setParseResult] = useState<ParseTripResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [expanded, setExpanded] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-collapse on desktop when a trip is selected
  useEffect(() => {
    if (activeTripSelected && window.innerWidth >= 1024) setExpanded(false);
  }, [activeTripSelected]);

  // Re-expand if window shrinks below desktop breakpoint
  useEffect(() => {
    const handleResize = () => { if (window.innerWidth < 1024) setExpanded(true); };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((i) => (i + 1) % PLACEHOLDER_EXAMPLES.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const canSubmit = text.trim().length > 10;

  const handleParse = useCallback(async () => {
    if (!canSubmit || parsing) return;
    setParsing(true);
    setParseError(null);
    try {
      const result = await apiClient.parseTripGoal(text.trim());
      setParseResult(result);
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "Failed to parse your request");
    } finally {
      setParsing(false);
    }
  }, [text, canSubmit, parsing]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (parseResult) {
      handleConfirm();
    } else {
      handleParse();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (parseResult) {
        handleConfirm();
      } else if (canSubmit) {
        handleParse();
      }
    }
  };

  const handleConfirm = (editedParams?: ParsedTripParams) => {
    if (!parseResult) return;
    const params = editedParams ?? parseResult.parsed;
    const options: CreateTripOptions = {
      goal: parseResult.goal_text,
      parsed_params: params,
    };
    if (params.budget_total) {
      options.total_budget = params.budget_total;
    }
    onSubmit(options);
    setText("");
    setParseResult(null);
    setParseError(null);
    if (window.innerWidth >= 1024) setExpanded(false);
  };

  const handleAdjust = () => {
    setParseResult(null);
    setParseError(null);
    textareaRef.current?.focus();
  };

  const handleVoiceResult = (transcript: string) => {
    setText((prev) => (prev ? prev + " " + transcript : transcript));
  };

  if (!expanded) {
    return (
      <Card hover padding="none">
        <button onClick={() => setExpanded(true)} className="w-full flex items-center gap-3 p-4 lg:p-5 text-left btn-transition focus:outline-none focus:ring-2 focus:ring-gold/30 rounded-xl">
          <Plus className="h-4 w-4 text-navy" />
          <span className="font-sans text-sm text-slate">Plan a new trip...</span>
        </button>
      </Card>
    );
  }

  return (
    <Card hover padding="none">
      <form onSubmit={handleSubmit} className="p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4">
          <p className="eyebrow">Plan Your Trip</p>
          {activeTripSelected && (
            <Button variant="ghost" size="sm" onClick={() => setExpanded(false)} className="hidden lg:flex items-center gap-1">
              <ChevronUp className="h-3 w-3" /> Minimize
            </Button>
          )}
        </div>

        <div className="relative mb-4">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (parseResult) {
                setParseResult(null);
                setParseError(null);
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder={PLACEHOLDER_EXAMPLES[placeholderIndex]}
            rows={3}
            disabled={disabled || parsing}
            className="w-full border border-navy/20 bg-cream rounded-lg px-3 py-3 pr-14 text-sm font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold disabled:opacity-50 disabled:cursor-not-allowed resize-none"
          />
          <div className="absolute bottom-3 right-3">
            <VoiceInputButton onResult={handleVoiceResult} disabled={disabled || parsing} />
          </div>
        </div>

        {parseError && (
          <div className="mb-4 p-3 border border-error-border bg-error-soft rounded-lg">
            <p className="text-sm font-sans text-error">{parseError}</p>
          </div>
        )}

        {!parseResult && (
          <div className="flex items-center justify-between gap-3 pt-3 border-t border-gold-light/30">
            <p className="text-xs text-slate font-sans hidden sm:block">
              Describe your trip in your own words. Our AI will handle the rest.
            </p>
            <Button type="submit" variant="primary" size="md" disabled={disabled || !canSubmit || parsing} className="w-full sm:w-auto">
              {parsing ? "Understanding\u2026" : "Plan Trip"}
            </Button>
          </div>
        )}
      </form>

      {parseResult && (
        <TripConfirmation
          parseResult={parseResult}
          onConfirm={handleConfirm}
          onStartOver={handleAdjust}
          disabled={disabled}
          setParseResult={setParseResult}
        />
      )}
    </Card>
  );
}

const ALL_DOMAINS = ["flight", "hotel", "transport", "activity"] as const;

const CABIN_CLASSES = [
  { value: "", label: "Any" },
  { value: "economy", label: "Economy" },
  { value: "premium_economy", label: "Premium Economy" },
  { value: "business", label: "Business" },
  { value: "first", label: "First" },
];

const HOTEL_TYPES = [
  { value: "", label: "Any" },
  { value: "hotel", label: "Hotel" },
  { value: "boutique", label: "Boutique" },
  { value: "resort", label: "Resort" },
  { value: "hostel", label: "Hostel" },
  { value: "airbnb", label: "Airbnb" },
];

function TripConfirmation({
  parseResult,
  onConfirm,
  onStartOver,
  disabled,
}: {
  parseResult: ParseTripResponse;
  onConfirm: (params: ParsedTripParams) => void;
  onStartOver: () => void;
  disabled?: boolean;
  setParseResult: (r: ParseTripResponse | null) => void;
}) {
  const p = parseResult.parsed;

  const [destinations, setDestinations] = useState<string[]>(p.destinations);
  const [newDest, setNewDest] = useState("");
  const [origin, setOrigin] = useState(p.origin ?? "");
  const [departureDate, setDepartureDate] = useState(p.departure_date ?? "");
  const [returnDate, setReturnDate] = useState(p.return_date ?? "");
  const [durationDays, setDurationDays] = useState(p.duration_days ?? 5);
  const [budgetTotal, setBudgetTotal] = useState(p.budget_total ?? 0);
  const [adults, setAdults] = useState(p.travelers.adults);
  const [children, setChildren] = useState(p.travelers.children);
  const [domains, setDomains] = useState<string[]>(p.domains);
  const [cabinClass, setCabinClass] = useState(p.flight_preferences.cabin_class ?? "");
  const [airline, setAirline] = useState(p.flight_preferences.airline ?? "");
  const [nonstop, setNonstop] = useState(p.flight_preferences.nonstop ?? false);
  const [hotelType, setHotelType] = useState(p.hotel_preferences.type ?? "");
  const [starRating, setStarRating] = useState(p.hotel_preferences.star_rating ?? 0);
  const [locationNotes, setLocationNotes] = useState(p.hotel_preferences.location_notes ?? "");

  const [dateSuggestions, setDateSuggestions] = useState<DateSuggestion[]>([]);
  const [geoLoading, setGeoLoading] = useState(false);
  const [originSuggestions, setOriginSuggestions] = useState<Airport[]>([]);
  const [showOriginDropdown, setShowOriginDropdown] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const originDropdownRef = useRef<HTMLDivElement>(null);
  const [datesExpanded, setDatesExpanded] = useState(false);

  const hasFlights = domains.includes("flight");
  const originMissing = hasFlights && !origin.trim();

  // Auto-calc duration from dates
  useEffect(() => {
    if (departureDate && returnDate) {
      const dep = new Date(departureDate + "T00:00:00");
      const ret = new Date(returnDate + "T00:00:00");
      const diff = Math.round((ret.getTime() - dep.getTime()) / (1000 * 60 * 60 * 24));
      if (diff > 0) setDurationDays(diff);
    }
  }, [departureDate, returnDate]);

  // Fetch date suggestions when destination is known and dates are empty
  useEffect(() => {
    if (destinations.length > 0 && !departureDate && !returnDate) {
      apiClient
        .suggestDates(destinations[0], durationDays)
        .then((res) => setDateSuggestions(res.suggestions))
        .catch(() => {});
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Pre-fill origin: saved prefs > geolocation — resolve to airport format
  useEffect(() => {
    if (origin) return;

    const prefs = getSavedPreferences();
    if (prefs.departureCity) {
      const airport = resolveAirport(prefs.departureCity);
      setOrigin(airport ? `${airport.city} (${airport.code})` : prefs.departureCity);
      return;
    }

    if (!navigator.geolocation) return;
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const res = await apiClient.nearestCity(pos.coords.latitude, pos.coords.longitude);
          const airport = resolveAirport(res.city);
          setOrigin(airport ? `${airport.city} (${airport.code})` : res.city);
        } catch { /* ignore */ }
        setGeoLoading(false);
      },
      () => setGeoLoading(false),
      { timeout: 5000 }
    );
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleDomain = (d: string) => {
    setDomains((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));
  };

  const addDestination = () => {
    const trimmed = newDest.trim();
    if (trimmed && !destinations.includes(trimmed)) {
      setDestinations((prev) => [...prev, trimmed]);
      setNewDest("");
    }
  };

  const removeDestination = (dest: string) => {
    setDestinations((prev) => prev.filter((d) => d !== dest));
  };

  const applyDateSuggestion = (s: DateSuggestion) => {
    setDepartureDate(s.departure_date);
    setReturnDate(s.return_date);
    setDateSuggestions([]);
  };

  const handleOriginChange = (value: string) => {
    setOrigin(value);
    if (value.trim().length >= 1) {
      const results = searchAirports(value);
      setOriginSuggestions(results);
      setShowOriginDropdown(results.length > 0);
      setHighlightedIndex(-1);
    } else {
      // Show popular airports when field is cleared
      const popular = popularAirports();
      setOriginSuggestions(popular);
      setShowOriginDropdown(true);
      setHighlightedIndex(-1);
    }
  };

  const handleOriginFocus = () => {
    if (origin.trim().length >= 1) {
      const results = searchAirports(origin);
      if (results.length > 0) {
        setOriginSuggestions(results);
        setShowOriginDropdown(true);
      }
    } else {
      // Show popular airports on focus when empty
      const popular = popularAirports();
      setOriginSuggestions(popular);
      setShowOriginDropdown(true);
    }
  };

  const selectAirport = (airport: Airport) => {
    setOrigin(`${airport.city} (${airport.code})`);
    setShowOriginDropdown(false);
    setOriginSuggestions([]);
  };

  const handleOriginKeyDown = (e: React.KeyboardEvent) => {
    if (!showOriginDropdown || originSuggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((i) => Math.min(i + 1, originSuggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && highlightedIndex >= 0) {
      e.preventDefault();
      selectAirport(originSuggestions[highlightedIndex]);
    } else if (e.key === "Escape") {
      setShowOriginDropdown(false);
    }
  };

  const handleSubmit = () => {
    const params: ParsedTripParams = {
      destinations,
      origin: origin.trim().replace(/\s*\([A-Z]{3}\)$/, "") || null,
      departure_date: departureDate || null,
      return_date: returnDate || null,
      duration_days: durationDays || null,
      budget_total: budgetTotal || null,
      budget_currency: "USD",
      travelers: { adults, children },
      domains,
      flight_preferences: {
        cabin_class: cabinClass || null,
        airline: airline.trim() || null,
        nonstop: nonstop || null,
        seat_preference: p.flight_preferences.seat_preference,
      },
      hotel_preferences: {
        type: hotelType || null,
        star_rating: starRating || null,
        amenities: p.hotel_preferences.amenities,
        location_notes: locationNotes.trim() || null,
        budget_per_night: p.hotel_preferences.budget_per_night,
      },
      activity_preferences: p.activity_preferences,
      notes: p.notes,
    };
    onConfirm(params);
  };

  return (
    <div className="border-t border-gold-light/40 p-4 lg:p-6">
      <p className="eyebrow mb-3">Confirm &amp; Edit Your Trip</p>

      {(() => {
        const activeClarifications = parseResult.clarification_needed.filter((c) => {
          if (origin && /depart|origin|from where/i.test(c)) return false;
          return true;
        });
        return activeClarifications.length > 0 ? (
          <div className="mb-4 p-3 border border-gold-light/40 bg-cream-dark rounded-lg">
            {activeClarifications.map((note, i) => (
              <p key={i} className="text-xs font-sans text-slate">
                <span className="font-semibold text-gold mr-1">&rarr;</span>
                {note}
              </p>
            ))}
          </div>
        ) : null;
      })()}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Destinations */}
        <div>
          <label className="block text-xs font-sans font-semibold text-navy mb-1">Destinations</label>
          <div className="flex flex-wrap gap-1.5 mb-1.5">
            {destinations.map((d) => (
              <span key={d} className="inline-flex items-center gap-1 px-2.5 py-1 border border-navy/20 text-navy bg-cream rounded-md text-xs font-sans font-medium">
                {d}
                <button type="button" onClick={() => removeDestination(d)} className="text-slate hover:text-error ml-0.5" aria-label={`Remove ${d}`}>&times;</button>
              </span>
            ))}
          </div>
          <div className="flex gap-1.5">
            <input
              type="text"
              value={newDest}
              onChange={(e) => setNewDest(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addDestination(); } }}
              placeholder="Add city..."
              className="flex-1 border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30"
            />
            <button type="button" onClick={addDestination} className="px-2.5 py-1.5 bg-navy/10 text-navy rounded-md text-xs font-sans font-medium hover:bg-navy/20 btn-transition">Add</button>
          </div>
        </div>

        {/* Departure City */}
        <div className="relative" ref={originDropdownRef}>
          <label className="block text-xs font-sans font-semibold text-navy mb-1">
            Departure City {hasFlights && <span className="text-error">*</span>}
          </label>
          <input
            type="text"
            value={origin}
            onChange={(e) => handleOriginChange(e.target.value)}
            onKeyDown={handleOriginKeyDown}
            onFocus={handleOriginFocus}
            onBlur={() => { setTimeout(() => setShowOriginDropdown(false), 150); }}
            placeholder={geoLoading ? "Detecting location\u2026" : "City name or airport code (e.g. SFO)"}
            className={`w-full border rounded-md px-2.5 py-1.5 text-xs font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 bg-cream ${
              originMissing ? "border-error ring-1 ring-error/30" : "border-navy/20"
            }`}
            autoComplete="off"
          />
          {showOriginDropdown && originSuggestions.length > 0 && (
            <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-navy/20 rounded-md shadow-lg max-h-48 overflow-y-auto">
              {originSuggestions.map((airport, i) => (
                <button
                  key={`${airport.code}-${i}`}
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => selectAirport(airport)}
                  className={`w-full text-left px-3 py-2 text-xs font-sans flex items-center justify-between btn-transition ${
                    i === highlightedIndex ? "bg-gold/10 text-navy" : "text-navy hover:bg-cream-dark"
                  }`}
                >
                  <span>{airport.city}</span>
                  <span className="text-slate/60 font-medium">{airport.code}</span>
                </button>
              ))}
            </div>
          )}
          {originMissing && (
            <p className="text-xs font-sans text-error mt-0.5">Required for flight searches</p>
          )}
        </div>

      </div>

      {/* Travel Dates Section */}
      <div className="mb-4">
        <label className="block text-xs font-sans font-semibold text-navy mb-1.5">Travel Dates</label>

        {/* Suggested dates — prominent pills */}
        {dateSuggestions.length > 0 && (
          <div className="mb-2">
            <p className="text-[10px] font-sans text-slate/60 mb-1">Suggested dates</p>
            <div className="flex flex-wrap gap-2">
              {dateSuggestions.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => applyDateSuggestion(s)}
                  className="px-3 py-1.5 border border-gold-light/60 bg-cream rounded-md text-xs font-sans hover:bg-gold/10 hover:border-gold btn-transition text-left"
                >
                  <span className="font-semibold text-navy block">{s.label}</span>
                  <span className="text-slate/70">{s.reason}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Selected dates summary + expand toggle */}
        {departureDate && !datesExpanded && (
          <div className="flex items-center gap-2 mb-1.5 px-2.5 py-1.5 bg-cream-dark rounded-md border border-navy/10">
            <span className="text-xs font-sans text-navy font-medium">{departureDate}{returnDate ? ` \u2013 ${returnDate}` : ""}</span>
            <button type="button" onClick={() => setDatesExpanded(true)} className="text-xs font-sans text-gold hover:text-gold-dark btn-transition ml-auto">Edit</button>
          </div>
        )}

        {/* Collapsible date inputs */}
        {!departureDate && !datesExpanded && (
          <button
            type="button"
            onClick={() => setDatesExpanded(true)}
            className="text-xs font-sans font-medium text-gold hover:text-gold-dark btn-transition mb-1.5 flex items-center gap-1"
          >
            Set specific dates &darr;
          </button>
        )}

        {datesExpanded && (
          <div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-sans text-slate mb-0.5">Departure</label>
                <input
                  type="date"
                  value={departureDate}
                  onChange={(e) => setDepartureDate(e.target.value)}
                  className="w-full border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-gold/30"
                />
              </div>
              <div>
                <label className="block text-xs font-sans text-slate mb-0.5">Return</label>
                <input
                  type="date"
                  value={returnDate}
                  onChange={(e) => setReturnDate(e.target.value)}
                  min={departureDate || undefined}
                  className="w-full border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-gold/30"
                />
              </div>
            </div>
            <button
              type="button"
              onClick={() => setDatesExpanded(false)}
              className="text-xs font-sans font-medium text-slate/60 hover:text-navy btn-transition mt-1.5 flex items-center gap-1"
            >
              Collapse &uarr;
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Duration */}
        <div>
          <label className="block text-xs font-sans font-semibold text-navy mb-1">Duration (days)</label>
          <input
            type="number"
            value={durationDays}
            onChange={(e) => setDurationDays(Math.max(1, parseInt(e.target.value) || 1))}
            min={1}
            max={90}
            className="w-full border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-gold/30"
          />
        </div>

        {/* Budget */}
        <div>
          <label className="block text-xs font-sans font-semibold text-navy mb-1">Budget (USD)</label>
          <input
            type="number"
            value={budgetTotal || ""}
            onChange={(e) => setBudgetTotal(Math.max(0, parseFloat(e.target.value) || 0))}
            placeholder="No limit"
            min={0}
            className="w-full border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30"
          />
        </div>

        {/* Travelers */}
        <div>
          <label className="block text-xs font-sans font-semibold text-navy mb-1">Adults</label>
          <input
            type="number"
            value={adults}
            onChange={(e) => setAdults(Math.max(1, parseInt(e.target.value) || 1))}
            min={1}
            max={20}
            className="w-full border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-gold/30"
          />
        </div>
        <div>
          <label className="block text-xs font-sans font-semibold text-navy mb-1">Children</label>
          <input
            type="number"
            value={children}
            onChange={(e) => setChildren(Math.max(0, parseInt(e.target.value) || 0))}
            min={0}
            max={20}
            className="w-full border border-navy/20 bg-cream rounded-md px-2.5 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-gold/30"
          />
        </div>
      </div>

      {/* Domain toggles */}
      <div className="mb-4">
        <label className="block text-xs font-sans font-semibold text-navy mb-1.5">What to book</label>
        <div className="flex flex-wrap gap-2">
          {ALL_DOMAINS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => toggleDomain(d)}
              className={`px-3 py-1.5 border rounded-md text-xs font-sans font-medium btn-transition ${
                domains.includes(d)
                  ? DOMAIN_STYLES[d]
                  : "border-navy/10 text-slate/60 bg-cream-dark"
              }`}
            >
              {DOMAIN_LABELS[d] ?? d}
            </button>
          ))}
        </div>
      </div>

      {/* Flight preferences */}
      {hasFlights && (
        <div className="mb-4 p-3 border border-blue-100 bg-blue-50/30 rounded-lg">
          <p className="text-xs font-sans font-semibold text-blue-700 mb-2">Flight Preferences</p>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-sans text-blue-600 mb-0.5">Cabin Class</label>
              <select
                value={cabinClass}
                onChange={(e) => setCabinClass(e.target.value)}
                className="w-full border border-blue-200 bg-white rounded-md px-2 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-blue-200"
              >
                {CABIN_CLASSES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-sans text-blue-600 mb-0.5">Airline</label>
              <input
                type="text"
                value={airline}
                onChange={(e) => setAirline(e.target.value)}
                placeholder="Any"
                className="w-full border border-blue-200 bg-white rounded-md px-2 py-1.5 text-xs font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-1.5 text-xs font-sans text-blue-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={nonstop}
                  onChange={(e) => setNonstop(e.target.checked)}
                  className="rounded border-blue-200"
                />
                Nonstop only
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Hotel preferences */}
      {domains.includes("hotel") && (
        <div className="mb-4 p-3 border border-purple-100 bg-purple-50/30 rounded-lg">
          <p className="text-xs font-sans font-semibold text-purple-700 mb-2">Hotel Preferences</p>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-sans text-purple-600 mb-0.5">Type</label>
              <select
                value={hotelType}
                onChange={(e) => setHotelType(e.target.value)}
                className="w-full border border-purple-200 bg-white rounded-md px-2 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-purple-200"
              >
                {HOTEL_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-sans text-purple-600 mb-0.5">Star Rating</label>
              <select
                value={starRating}
                onChange={(e) => setStarRating(parseInt(e.target.value) || 0)}
                className="w-full border border-purple-200 bg-white rounded-md px-2 py-1.5 text-xs font-sans text-navy focus:outline-none focus:ring-2 focus:ring-purple-200"
              >
                <option value={0}>Any</option>
                <option value={3}>3+</option>
                <option value={4}>4+</option>
                <option value={5}>5</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-sans text-purple-600 mb-0.5">Location</label>
              <input
                type="text"
                value={locationNotes}
                onChange={(e) => setLocationNotes(e.target.value)}
                placeholder="e.g. near city center"
                className="w-full border border-purple-200 bg-white rounded-md px-2 py-1.5 text-xs font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-purple-200"
              />
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-3 border-t border-gold-light/30">
        <Button type="button" variant="primary" size="md" onClick={handleSubmit} disabled={disabled || originMissing}>
          Confirm &amp; Plan
        </Button>
        <Button type="button" variant="ghost" size="md" onClick={onStartOver}>
          Start Over
        </Button>
      </div>
    </div>
  );
}

