"use client";

import { useState } from "react";
import Link from "next/link";
import { Plane, Hotel, Car, CheckCircle, AlertTriangle, X, Check, Lightbulb, HelpCircle, ChevronRight } from "lucide-react";
import Button from "@/components/ui/Button";
import LoadingDots from "@/components/ui/LoadingDots";
import { DOMAIN_CONFIG } from "@/lib/design-tokens";

interface BookingData {
  domain: string;
  provider: string;
  details: Record<string, unknown>;
  amount: number;
}

interface TripSummary {
  status?: string;
  narrative?: string;
  bookings?: BookingData[];
  total_spent?: number;
}

interface InferredParam {
  value: unknown;
  reason: string;
  confidence: number;
}

interface BudgetTier {
  name: string;
  label: string;
  flight_description: string;
  hotel_description: string;
  estimated_flight_cost: number;
  estimated_hotel_per_night: number;
  estimated_total: number;
}

interface TripEvent {
  type: string;
  message?: string;
  agent_type?: string;
  tool_name?: string;
  status?: string;
  summary?: TripSummary;
  approval_id?: string;
  context?: Record<string, unknown>;
  questions?: Array<{ key: string; question: string; placeholder?: string }>;
  request_id?: string;
  stated?: Record<string, unknown>;
  inferred?: Record<string, InferredParam>;
  budget_tiers?: BudgetTier[];
}

interface TripTimelineProps {
  events: TripEvent[];
  onApproval: (approvalId: string, approved: boolean) => void;
  onClarification?: (tripId: string, requestId: string, answers: Record<string, string>) => void;
  tripId?: string;
}

export default function TripTimeline({ events, onApproval, onClarification, tripId }: TripTimelineProps) {
  if (events.length === 0) {
    return <LoadingDots label="Waiting for agent events..." />;
  }

  return (
    <div className="timeline-thread space-y-4">
      {events.map((event, idx) => (
        <div key={idx} className="timeline-node stagger-fade-up" style={{ animationDelay: `${idx * 0.07}s` }}>
          <TimelineEvent event={event} onApproval={onApproval} onClarification={onClarification} tripId={tripId} />
        </div>
      ))}
    </div>
  );
}

function DomainIcon({ domain }: { domain: string }) {
  const iconMap: Record<string, React.ReactNode> = {
    flight: <Plane className="h-4 w-4" aria-hidden="true" />,
    hotel: <Hotel className="h-4 w-4" aria-hidden="true" />,
    transport: <Car className="h-4 w-4" aria-hidden="true" />,
    activity: <CheckCircle className="h-4 w-4" aria-hidden="true" />,
  };
  return <>{iconMap[domain] || iconMap.activity}</>;
}

function BookingCard({ booking }: { booking: BookingData }) {
  const config = DOMAIN_CONFIG[booking.domain];
  return (
    <div className="border border-gold-light/40 rounded-lg p-3 card-hover-bar">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-gold">
            <DomainIcon domain={booking.domain} />
          </span>
          <span className="font-sans text-xs font-semibold text-gold uppercase tracking-wide">
            {config?.label || booking.domain}
          </span>
        </div>
        <span className="font-serif text-lg text-navy">${booking.amount.toFixed(2)}</span>
      </div>
      {booking.details && (
        <div className="font-sans text-xs text-slate space-y-0.5">
          {Object.entries(booking.details).map(([key, value]) => (
            <div key={key} className="flex gap-1">
              <span className="text-slate/60 capitalize">{key.replace(/_/g, " ")}:</span>
              <span className="text-charcoal">{String(value)}</span>
            </div>
          ))}
        </div>
      )}
      {booking.provider && (
        <div className="mt-1.5 font-sans text-xs text-slate/60">via {booking.provider}</div>
      )}
    </div>
  );
}

function ClarificationForm({
  event,
  onSubmit,
  tripId,
}: {
  event: TripEvent;
  onSubmit?: (tripId: string, requestId: string, answers: Record<string, string>) => void;
  tripId?: string;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const questions = event.questions || [];
  const requestId = event.request_id || "";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSubmit && tripId && requestId) {
      onSubmit(tripId, requestId, answers);
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <div className="flex items-start gap-3 p-4 bg-success-soft border border-success-border rounded-lg">
        <span className="mt-0.5 h-5 w-5 bg-success rounded-full flex items-center justify-center flex-shrink-0">
          <Check className="h-3 w-3 text-white" aria-hidden="true" />
        </span>
        <p className="font-sans text-sm text-success font-medium">Preferences submitted — agents are continuing...</p>
      </div>
    );
  }

  return (
    <div className="border border-gold-light/40 rounded-lg p-4 bg-white">
      <div className="flex items-center gap-2 mb-3">
        <span className="h-5 w-5 bg-navy rounded-full flex items-center justify-center flex-shrink-0">
          <HelpCircle className="h-3 w-3 text-cream" aria-hidden="true" />
        </span>
        <p className="font-sans text-sm font-semibold text-navy">Quick Questions</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        {questions.map((q) => (
          <div key={q.key}>
            <label className="block font-sans text-xs font-medium text-charcoal mb-1">{q.question}</label>
            <input
              type="text"
              value={answers[q.key] || ""}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))}
              placeholder={q.placeholder || "No preference"}
              className="w-full border border-navy/20 bg-cream rounded-md px-3 py-1.5 text-sm font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold"
            />
          </div>
        ))}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" size="sm">
            Submit
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              if (onSubmit && tripId && requestId) {
                onSubmit(tripId, requestId, {});
                setSubmitted(true);
              }
            }}
          >
            Skip
          </Button>
        </div>
      </form>
    </div>
  );
}

function SmartDefaultsCard({ event }: { event: TripEvent }) {
  const [expanded, setExpanded] = useState(false);
  const stated = event.stated || {};
  const inferred = event.inferred || {};
  const tiers = event.budget_tiers;

  const statedEntries = Object.entries(stated);
  const inferredEntries = Object.entries(inferred);

  const formatLabel = (key: string) => key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="border border-gold-light/40 rounded-lg bg-white overflow-hidden shadow-sm">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="h-5 w-5 bg-navy rounded-full flex items-center justify-center flex-shrink-0">
            <Lightbulb className="h-3 w-3 text-cream" aria-hidden="true" />
          </span>
          <p className="font-sans text-sm font-semibold text-navy">Smart Defaults</p>
        </div>

        {statedEntries.length > 0 && (
          <div className="mb-3">
            <p className="font-sans text-xs font-medium text-slate mb-1.5">Your preferences</p>
            <div className="flex flex-wrap gap-2">
              {statedEntries.map(([key, value]) => (
                <span key={key} className="inline-flex items-center gap-1 px-2 py-1 bg-cream border border-gold-light/40 rounded-md text-xs font-sans">
                  <span className="text-slate/60">{formatLabel(key)}:</span>
                  <span className="font-medium text-navy">{String(value)}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {inferredEntries.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <p className="font-sans text-xs font-medium text-slate">We assumed</p>
              <button
                onClick={() => setExpanded(!expanded)}
                className="font-sans text-xs font-medium text-gold hover:text-gold-dark focus:outline-none focus:ring-2 focus:ring-gold/30 rounded-sm"
              >
                {expanded ? "hide" : "details"}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {inferredEntries.map(([key, param]) => (
                <span key={key} className="inline-flex items-center gap-1 px-2 py-1 bg-cream-dark border border-gold-light/40 rounded-md text-xs font-sans">
                  <span className="text-slate/60">{formatLabel(key)}:</span>
                  <span className="font-medium text-charcoal">{String(param.value)}</span>
                  {expanded && (
                    <span className="text-slate/60 ml-1">— {param.reason}</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {tiers && tiers.length > 0 && (
        <div className="border-t border-gold-light/30 p-4 bg-cream-dark">
          <p className="font-sans text-xs font-medium text-slate mb-3">Estimated budget range</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-0 border border-gold-light/40 rounded-lg overflow-hidden">
            {tiers.map((tier, i) => (
              <BudgetTierCard key={tier.name} tier={tier} isLast={i === tiers.length - 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BudgetTierCard({ tier, isLast }: { tier: BudgetTier; isLast: boolean }) {
  return (
    <div className={`p-3 bg-white ${!isLast ? "border-b sm:border-b-0 sm:border-r border-gold-light/30" : ""}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-sans text-xs font-semibold text-gold uppercase tracking-wide">
          {tier.label}
        </span>
        <span className="font-serif text-lg text-navy">
          ~${tier.estimated_total.toLocaleString()}
        </span>
      </div>
      <div className="font-sans text-xs text-slate space-y-1">
        <div className="flex items-start gap-1">
          <span className="text-gold font-semibold">&rarr;</span>
          <span>{tier.flight_description}</span>
        </div>
        <div className="flex items-start gap-1">
          <span className="text-gold font-semibold">&rarr;</span>
          <span>{tier.hotel_description}</span>
        </div>
      </div>
    </div>
  );
}

function ApprovalCard({
  event,
  onApproval,
  tripId,
}: {
  event: TripEvent;
  onApproval: (id: string, approved: boolean) => void;
  tripId?: string;
}) {
  const [decided, setDecided] = useState<"approved" | "rejected" | null>(null);
  const context = event.context || {};

  const domain = (context.domain as string) || "";
  const action = (context.action as string) || "";
  const details = (context.details as Record<string, unknown>) || context;
  const violations = (context.policy_violations_json as Array<Record<string, unknown>>) || [];

  const actionLabel = action.replace(/_/g, " ").replace(/:/g, " — ");

  const handleDecision = (approved: boolean) => {
    if (event.approval_id) {
      onApproval(event.approval_id, approved);
      setDecided(approved ? "approved" : "rejected");
    }
  };

  if (decided) {
    const isApproved = decided === "approved";
    return (
      <div className={`flex items-center gap-3 p-4 border rounded-lg ${isApproved ? "bg-success-soft border-success-border" : "bg-error-soft border-error-border"}`}>
        <span className={`h-5 w-5 rounded-full flex items-center justify-center flex-shrink-0 ${isApproved ? "bg-success" : "bg-error"}`}>
          {isApproved ? <Check className="h-3 w-3 text-white" aria-hidden="true" /> : <X className="h-3 w-3 text-white" aria-hidden="true" />}
        </span>
        <p className={`font-sans text-sm font-medium ${isApproved ? "text-success" : "text-error"}`}>
          Booking {decided}: {actionLabel}
        </p>
      </div>
    );
  }

  return (
    <div className="border border-gold-light/40 rounded-xl bg-white shadow-lg overflow-hidden">
      <div className="bg-navy px-4 py-2.5 flex items-center gap-2 rounded-t-xl">
        <AlertTriangle className="h-4 w-4 text-cream" aria-hidden="true" />
        <span className="font-sans text-sm font-semibold text-cream">Approval Required</span>
      </div>

      <div className="p-4">
        {actionLabel && (
          <p className="font-sans text-sm text-charcoal mb-3">
            Action: <span className="font-medium text-navy capitalize">{actionLabel}</span>
            {domain && <span className="ml-2 font-sans text-xs font-medium text-gold border border-gold-light rounded-md px-2 py-0.5">{domain}</span>}
          </p>
        )}

        {Object.keys(details).length > 0 && (
          <div className="mb-4 bg-cream-dark border border-gold-light/40 rounded-lg p-3">
            <div className="font-sans text-xs text-charcoal space-y-1">
              {Object.entries(details).map(([key, value]) => {
                if (key === "policy_violations_json" || key === "domain" || key === "action") return null;
                return (
                  <div key={key} className="flex gap-1">
                    <span className="text-slate capitalize">{key.replace(/_/g, " ")}:</span>
                    <span className="font-medium text-navy">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {violations.length > 0 && (
          <div className="mb-4">
            <p className="font-sans text-xs font-semibold text-error mb-1.5">Policy Flags</p>
            <div className="space-y-1">
              {violations.map((v, i) => (
                <div key={i} className="flex items-start gap-1.5 font-sans text-xs">
                  <span className="text-error font-semibold mt-0.5">&rarr;</span>
                  <span className="text-charcoal">{String(v.message)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3 pt-3 border-t border-gold-light/30">
          <Button variant="primary" size="sm" onClick={() => handleDecision(true)}>
            Confirm Booking
          </Button>
          <Button variant="secondary" size="sm" onClick={() => handleDecision(false)}>
            Reject
          </Button>
          {tripId && (
            <Link
              href={`/trips/${tripId}`}
              className="px-4 py-2.5 text-gold font-sans text-xs font-semibold hover:text-gold-dark btn-transition min-h-touch flex items-center gap-1 ml-auto focus:outline-none focus:ring-2 focus:ring-gold/30 rounded-md"
            >
              Review Full Itinerary
              <ChevronRight className="h-3 w-3" aria-hidden="true" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

function TimelineEvent({
  event,
  onApproval,
  onClarification,
  tripId,
}: {
  event: TripEvent;
  onApproval: (id: string, approved: boolean) => void;
  onClarification?: (tripId: string, requestId: string, answers: Record<string, string>) => void;
  tripId?: string;
}) {
  switch (event.type) {
    case "agent_progress":
      return (
        <div className="border border-gold-light/40 rounded-lg bg-white p-3">
          <div className="flex items-center gap-2 mb-1">
            {event.agent_type && (
              <span className="font-sans text-xs font-semibold text-gold uppercase tracking-wide">
                {event.agent_type}
              </span>
            )}
          </div>
          <p className="font-sans text-sm text-charcoal">{event.message}</p>
        </div>
      );

    case "tool_call":
      return (
        <div className="bg-cream-dark border border-gold-light/40 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs bg-navy text-cream px-2 py-0.5 rounded">{event.tool_name}</span>
            {event.status && (
              <span className="font-sans text-xs text-slate/60">{event.status}</span>
            )}
          </div>
          {event.status === "searching" && (
            <div className="mt-2 h-1.5 rounded-full shimmer" />
          )}
        </div>
      );

    case "smart_defaults":
      return <SmartDefaultsCard event={event} />;

    case "approval_required":
      return <ApprovalCard event={event} onApproval={onApproval} tripId={tripId} />;

    case "clarification_needed":
      return (
        <ClarificationForm event={event} onSubmit={onClarification} tripId={tripId} />
      );

    case "trip_completed":
      return (
        <div className="space-y-4">
          <div className="bg-success-soft border border-success-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="h-5 w-5 bg-success rounded-full flex items-center justify-center flex-shrink-0">
                <Check className="h-3 w-3 text-white" aria-hidden="true" />
              </span>
              <span className="font-sans text-sm font-semibold text-success">Trip Complete</span>
            </div>
            {event.summary?.narrative && (
              <div className="font-sans text-sm text-charcoal whitespace-pre-wrap leading-relaxed">
                {event.summary.narrative}
              </div>
            )}
            {event.summary?.total_spent != null && event.summary.total_spent > 0 && (
              <div className="mt-3 inline-flex items-center gap-1 px-3 py-1 bg-success-soft border border-success-border rounded-md">
                <span className="font-serif text-lg text-success">
                  ${event.summary.total_spent.toFixed(2)}
                </span>
                <span className="font-sans text-xs font-medium text-success ml-1">total</span>
              </div>
            )}
            {tripId && (
              <Link
                href={`/trips/${tripId}`}
                className="mt-3 inline-flex items-center gap-1 px-5 py-2.5 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light btn-transition focus:outline-none focus:ring-2 focus:ring-gold/30"
              >
                View Trip Plan
                <ChevronRight className="h-3 w-3 ml-1" aria-hidden="true" />
              </Link>
            )}
          </div>

          {event.summary?.bookings && event.summary.bookings.length > 0 && (
            <div className="border border-gold-light/40 rounded-lg divide-y divide-gold-light/30">
              {event.summary.bookings.map((booking, idx) => (
                <div key={idx} className="p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-gold"><DomainIcon domain={booking.domain} /></span>
                      <span className="font-sans text-xs font-semibold text-gold uppercase tracking-wide">{DOMAIN_CONFIG[booking.domain]?.label || booking.domain}</span>
                    </div>
                    <span className="font-serif text-base text-navy">${booking.amount.toFixed(2)}</span>
                  </div>
                  {booking.details && (
                    <div className="font-sans text-xs text-slate space-y-0.5">
                      {Object.entries(booking.details).map(([key, value]) => (
                        <div key={key} className="flex gap-1">
                          <span className="text-slate/60 capitalize">{key.replace(/_/g, " ")}:</span>
                          <span className="text-charcoal">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {booking.provider && <div className="font-sans text-xs text-slate/60 mt-1">via {booking.provider}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "trip_failed":
      return (
        <div className="bg-error-soft border border-error rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="h-5 w-5 bg-error rounded-full flex items-center justify-center flex-shrink-0">
              <X className="h-3 w-3 text-white" aria-hidden="true" />
            </span>
            <span className="font-sans text-sm font-semibold text-error">Trip Failed</span>
          </div>
          <p className="font-sans text-sm text-charcoal mt-1">{event.message}</p>
        </div>
      );

    default:
      return (
        <div className="p-3 bg-cream-dark border border-gold-light/40 rounded-lg">
          <p className="font-mono text-xs text-slate/60">{JSON.stringify(event)}</p>
        </div>
      );
  }
}
