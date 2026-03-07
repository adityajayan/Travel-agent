"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import VoiceInputButton from "./VoiceInputButton";
import { CreateTripOptions, ParseTripResponse, ParsedTripParams, apiClient } from "@/lib/api";

interface TripFormProps {
  onSubmit: (options: CreateTripOptions) => void;
  disabled?: boolean;
}

const PLACEHOLDER_EXAMPLES = [
  "Plan a 5-day trip to Tokyo under $3000\u2026",
  "Find me business class flights to London next Tuesday\u2026",
  "Weekend getaway to wine country, boutique hotel, 2 people\u2026",
  "Family vacation to Italy in July, 2 adults 2 kids\u2026",
  "Book a hotel in SF near Union Square for 3 nights\u2026",
];

const DOMAIN_STYLES: Record<string, string> = {
  flight: "border-[rgba(59,130,246,0.3)] text-[#2563eb] bg-[rgba(59,130,246,0.06)]",
  hotel: "border-[rgba(147,51,234,0.3)] text-[#7c3aed] bg-[rgba(147,51,234,0.06)]",
  transport: "border-[rgba(234,88,12,0.3)] text-[#c2410c] bg-[rgba(234,88,12,0.06)]",
  activity: "border-[rgba(13,148,136,0.3)] text-[#0d9488] bg-[rgba(13,148,136,0.06)]",
};

const DOMAIN_LABELS: Record<string, string> = {
  flight: "Flights",
  hotel: "Hotels",
  transport: "Transport",
  activity: "Activities",
};

export default function TripForm({ onSubmit, disabled }: TripFormProps) {
  const [text, setText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseResult, setParseResult] = useState<ParseTripResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Rotate placeholder text
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
      // Confirm and create trip
      handleConfirm();
    } else {
      // First step: parse
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

  const handleConfirm = () => {
    if (!parseResult) return;
    const options: CreateTripOptions = {
      goal: parseResult.goal_text,
      parsed_params: parseResult.parsed,
    };
    if (parseResult.parsed.budget_total) {
      options.total_budget = parseResult.parsed.budget_total;
    }
    onSubmit(options);
    setText("");
    setParseResult(null);
    setParseError(null);
  };

  const handleAdjust = () => {
    setParseResult(null);
    setParseError(null);
    textareaRef.current?.focus();
  };

  const handleVoiceResult = (transcript: string) => {
    setText((prev) => (prev ? prev + " " + transcript : transcript));
  };

  return (
    <div className="bg-white border-2 border-border-heavy card-hover-bar">
      <form onSubmit={handleSubmit} className="p-4 lg:p-6">
        <p className="eyebrow mb-4">Plan Your Trip</p>

        {/* Freeform textarea */}
        <div className="relative mb-4">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              // Clear previous parse when text changes
              if (parseResult) {
                setParseResult(null);
                setParseError(null);
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder={PLACEHOLDER_EXAMPLES[placeholderIndex]}
            rows={3}
            disabled={disabled || parsing}
            className="w-full border-2 border-border-heavy bg-paper px-3 py-3 pr-14 text-sm font-body text-text-primary placeholder:text-text-ghost focus:outline-none focus:border-accent disabled:opacity-50 disabled:cursor-not-allowed resize-none"
          />
          <div className="absolute bottom-3 right-3">
            <VoiceInputButton onResult={handleVoiceResult} disabled={disabled || parsing} />
          </div>
        </div>

        {/* Parse error */}
        {parseError && (
          <div className="mb-4 p-3 border-[1.5px] border-accent-border bg-accent-soft">
            <p className="text-sm font-body text-accent">{parseError}</p>
          </div>
        )}

        {/* Submit / Parse button */}
        {!parseResult && (
          <div className="flex items-center justify-between gap-3 pt-3 border-t border-border-light">
            <p className="text-xs text-text-ghost font-body font-light hidden sm:block">
              Describe your trip in your own words. Our AI will handle the rest.
            </p>
            <button
              type="submit"
              disabled={disabled || !canSubmit || parsing}
              className="w-full sm:w-auto px-6 py-3 lg:py-2.5 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed btn-transition min-h-touch"
            >
              {parsing ? "Understanding\u2026" : "Plan Trip"}
            </button>
          </div>
        )}
      </form>

      {/* Parsed confirmation card */}
      {parseResult && (
        <div className="border-t-2 border-border-heavy p-4 lg:p-6">
          <p className="eyebrow mb-3">Here&apos;s What I Understood</p>

          {/* Parsed chips */}
          <div className="flex flex-wrap gap-2 mb-4">
            <ParsedChips parsed={parseResult.parsed} />
          </div>

          {/* Clarification notes */}
          {parseResult.clarification_needed.length > 0 && (
            <div className="mb-4 p-3 border-[1.5px] border-border-light bg-paper-elevated">
              {parseResult.clarification_needed.map((note, i) => (
                <p key={i} className="text-xs font-body text-text-muted font-light">
                  <span className="font-ui font-bold text-accent mr-1">&rarr;</span>
                  {note}
                </p>
              ))}
            </div>
          )}

          {/* Confidence indicator */}
          <div className="mb-4">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-paper-elevated">
                <div
                  className="h-full bg-success transition-all duration-500"
                  style={{ width: `${Math.round(parseResult.confidence * 100)}%` }}
                />
              </div>
              <span className="text-[0.62rem] font-body text-text-ghost">
                {Math.round(parseResult.confidence * 100)}% confident
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleConfirm}
              disabled={disabled}
              className="px-6 py-3 lg:py-2.5 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed btn-transition min-h-touch"
            >
              Looks Good &mdash; Plan It
            </button>
            <button
              onClick={handleAdjust}
              className="font-ui text-xs font-semibold uppercase tracking-[0.08em] text-text-muted hover:text-contrast btn-transition"
            >
              Let Me Adjust
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ParsedChips({ parsed }: { parsed: ParsedTripParams }) {
  const chips: { label: string; style: string }[] = [];

  // Destinations
  for (const dest of parsed.destinations) {
    chips.push({ label: dest, style: "border-border-heavy text-text-primary bg-paper" });
  }

  // Origin
  if (parsed.origin) {
    chips.push({ label: `from ${parsed.origin}`, style: "border-border-light text-text-mid bg-paper" });
  }

  // Dates
  if (parsed.departure_date && parsed.return_date) {
    chips.push({
      label: `${formatDate(parsed.departure_date)} \u2013 ${formatDate(parsed.return_date)}`,
      style: "border-border-light text-text-mid bg-paper",
    });
  } else if (parsed.departure_date) {
    chips.push({
      label: formatDate(parsed.departure_date),
      style: "border-border-light text-text-mid bg-paper",
    });
  }

  // Duration
  if (parsed.duration_days) {
    chips.push({
      label: `${parsed.duration_days} day${parsed.duration_days !== 1 ? "s" : ""}`,
      style: "border-border-light text-text-mid bg-paper",
    });
  }

  // Budget
  if (parsed.budget_total) {
    chips.push({
      label: `$${parsed.budget_total.toLocaleString()} budget`,
      style: "border-success-border text-success bg-success-soft",
    });
  }

  // Travelers
  const totalTravelers = parsed.travelers.adults + parsed.travelers.children;
  if (totalTravelers > 1) {
    const parts: string[] = [];
    if (parsed.travelers.adults > 0) parts.push(`${parsed.travelers.adults} adult${parsed.travelers.adults !== 1 ? "s" : ""}`);
    if (parsed.travelers.children > 0) parts.push(`${parsed.travelers.children} child${parsed.travelers.children !== 1 ? "ren" : ""}`);
    chips.push({
      label: parts.join(", "),
      style: "border-border-light text-text-mid bg-paper",
    });
  }

  // Domains
  for (const domain of parsed.domains) {
    chips.push({
      label: DOMAIN_LABELS[domain] ?? domain,
      style: DOMAIN_STYLES[domain] ?? "border-border-light text-text-mid bg-paper",
    });
  }

  // Flight preferences
  if (parsed.flight_preferences.cabin_class) {
    chips.push({
      label: parsed.flight_preferences.cabin_class.replace("_", " "),
      style: DOMAIN_STYLES.flight,
    });
  }
  if (parsed.flight_preferences.airline) {
    chips.push({
      label: parsed.flight_preferences.airline,
      style: DOMAIN_STYLES.flight,
    });
  }
  if (parsed.flight_preferences.nonstop) {
    chips.push({ label: "nonstop", style: DOMAIN_STYLES.flight });
  }

  // Hotel preferences
  if (parsed.hotel_preferences.type) {
    chips.push({
      label: parsed.hotel_preferences.type,
      style: DOMAIN_STYLES.hotel,
    });
  }
  if (parsed.hotel_preferences.location_notes) {
    chips.push({
      label: parsed.hotel_preferences.location_notes,
      style: DOMAIN_STYLES.hotel,
    });
  }

  return (
    <>
      {chips.map((chip, i) => (
        <span
          key={i}
          className={`px-2.5 py-1 border-[1.5px] font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] ${chip.style}`}
        >
          {chip.label}
        </span>
      ))}
    </>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}
