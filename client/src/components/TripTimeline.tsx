"use client";

import { useState } from "react";

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
    return (
      <div className="text-center py-8">
        <p className="font-body text-sm text-text-ghost">Waiting for agent events...</p>
        <div className="mt-3 flex justify-center gap-1.5">
          <span className="h-2 w-2 bg-border-heavy animate-pulse-dot" />
          <span className="h-2 w-2 bg-border-heavy animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
          <span className="h-2 w-2 bg-border-heavy animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
        </div>
      </div>
    );
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
  const icons: Record<string, string> = {
    flight: "M21 16v-2l-8-5V3.5a1.5 1.5 0 10-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z",
    hotel: "M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9a4 4 0 00-4-4z",
    transport: "M18.92 6.01A1.49 1.49 0 0017.5 5h-11c-.69 0-1.28.47-1.42 1.01L3 12v8a1 1 0 001 1h1a1 1 0 001-1v-1h12v1a1 1 0 001 1h1a1 1 0 001-1v-8l-2.08-5.99zM6.5 16A1.5 1.5 0 015 14.5 1.5 1.5 0 016.5 13 1.5 1.5 0 018 14.5 1.5 1.5 0 016.5 16zm11 0a1.5 1.5 0 01-1.5-1.5 1.5 1.5 0 011.5-1.5 1.5 1.5 0 011.5 1.5 1.5 1.5 0 01-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z",
    activity: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
  };
  return (
    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
      <path d={icons[domain] || icons.activity} />
    </svg>
  );
}

const domainLabels: Record<string, string> = {
  flight: "Flight",
  hotel: "Hotel",
  transport: "Transport",
  activity: "Activity",
};

function BookingCard({ booking }: { booking: BookingData }) {
  return (
    <div className="border-2 border-border-heavy p-3 card-hover-bar">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-accent">
            <DomainIcon domain={booking.domain} />
          </span>
          <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent">
            {domainLabels[booking.domain] || booking.domain}
          </span>
        </div>
        <span className="font-display text-lg text-contrast">${booking.amount.toFixed(2)}</span>
      </div>
      {booking.details && (
        <div className="font-body text-xs text-text-muted space-y-0.5">
          {Object.entries(booking.details).map(([key, value]) => (
            <div key={key} className="flex gap-1">
              <span className="text-text-ghost capitalize">{key.replace(/_/g, " ")}:</span>
              <span className="text-text-mid">{String(value)}</span>
            </div>
          ))}
        </div>
      )}
      {booking.provider && (
        <div className="mt-1.5 font-body text-[0.62rem] text-text-ghost">via {booking.provider}</div>
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
      <div className="flex items-start gap-3 p-4 bg-success-soft border-[1.5px] border-success-border">
        <span className="mt-0.5 h-5 w-5 bg-success flex items-center justify-center flex-shrink-0">
          <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </span>
        <p className="font-body text-sm text-success font-medium">Preferences submitted — agents are continuing...</p>
      </div>
    );
  }

  return (
    <div className="border-2 border-border-heavy p-4 bg-white">
      <div className="flex items-center gap-2 mb-3">
        <span className="h-5 w-5 bg-contrast flex items-center justify-center flex-shrink-0">
          <svg className="h-3 w-3 text-paper" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </span>
        <p className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-contrast">Quick Questions</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        {questions.map((q) => (
          <div key={q.key}>
            <label className="block font-body text-xs font-medium text-text-mid mb-1">{q.question}</label>
            <input
              type="text"
              value={answers[q.key] || ""}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))}
              placeholder={q.placeholder || "No preference"}
              className="w-full border-2 border-border-heavy bg-paper px-3 py-1.5 text-sm font-body text-text-primary placeholder:text-text-ghost focus:outline-none focus:border-accent"
            />
          </div>
        ))}
        <div className="flex gap-2">
          <button
            type="submit"
            className="px-4 py-2 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition"
          >
            Submit
          </button>
          <button
            type="button"
            onClick={() => {
              if (onSubmit && tripId && requestId) {
                onSubmit(tripId, requestId, {});
                setSubmitted(true);
              }
            }}
            className="px-4 py-2 text-text-mid font-ui text-xs font-bold uppercase tracking-[0.1em] border-2 border-border-heavy hover:bg-contrast hover:text-paper btn-transition"
          >
            Skip
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Smart Defaults Card ──────────────────────────────────────────────────────

function SmartDefaultsCard({ event }: { event: TripEvent }) {
  const [expanded, setExpanded] = useState(false);
  const stated = event.stated || {};
  const inferred = event.inferred || {};
  const tiers = event.budget_tiers;

  const statedEntries = Object.entries(stated);
  const inferredEntries = Object.entries(inferred);

  const formatLabel = (key: string) => key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="border-2 border-border-heavy bg-white overflow-hidden">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="h-5 w-5 bg-contrast flex items-center justify-center flex-shrink-0">
            <svg className="h-3 w-3 text-paper" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </span>
          <p className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-contrast">Smart Defaults</p>
        </div>

        {statedEntries.length > 0 && (
          <div className="mb-3">
            <p className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-muted mb-1.5">Your preferences</p>
            <div className="flex flex-wrap gap-2">
              {statedEntries.map(([key, value]) => (
                <span key={key} className="inline-flex items-center gap-1 px-2 py-1 bg-paper border border-border-light text-xs font-body">
                  <span className="text-text-ghost">{formatLabel(key)}:</span>
                  <span className="font-medium text-text-primary">{String(value)}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {inferredEntries.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <p className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-muted">We assumed</p>
              <button
                onClick={() => setExpanded(!expanded)}
                className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent hover:underline"
              >
                {expanded ? "hide" : "details"}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {inferredEntries.map(([key, param]) => (
                <span key={key} className="inline-flex items-center gap-1 px-2 py-1 bg-paper-elevated border border-border-light text-xs font-body">
                  <span className="text-text-ghost">{formatLabel(key)}:</span>
                  <span className="font-medium text-text-mid">{String(param.value)}</span>
                  {expanded && (
                    <span className="text-text-ghost ml-1">— {param.reason}</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {tiers && tiers.length > 0 && (
        <div className="border-t border-border-light p-4 bg-paper-elevated">
          <p className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-muted mb-3">Estimated budget range</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-0 border-2 border-border-heavy">
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
    <div className={`p-3 bg-white ${!isLast ? "border-b sm:border-b-0 sm:border-r border-border-light" : ""}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent">
          {tier.label}
        </span>
        <span className="font-display text-lg text-contrast">
          ~${tier.estimated_total.toLocaleString()}
        </span>
      </div>
      <div className="font-body text-xs text-text-muted space-y-1">
        <div className="flex items-start gap-1">
          <span className="text-accent font-ui font-bold">&rarr;</span>
          <span>{tier.flight_description}</span>
        </div>
        <div className="flex items-start gap-1">
          <span className="text-accent font-ui font-bold">&rarr;</span>
          <span>{tier.hotel_description}</span>
        </div>
      </div>
    </div>
  );
}

// ── Approval Card — the hero moment ─────────────────────────────────────────

function ApprovalCard({
  event,
  onApproval,
}: {
  event: TripEvent;
  onApproval: (id: string, approved: boolean) => void;
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
      <div className={`flex items-center gap-3 p-4 border-[1.5px] ${isApproved ? "bg-success-soft border-success-border" : "bg-accent-soft border-accent-border"}`}>
        <span className={`h-5 w-5 flex items-center justify-center flex-shrink-0 ${isApproved ? "bg-success" : "bg-accent"}`}>
          <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isApproved ? "M5 13l4 4L19 7" : "M6 18L18 6M6 6l12 12"} />
          </svg>
        </span>
        <p className={`font-body text-sm font-medium ${isApproved ? "text-success" : "text-accent"}`}>
          Booking {decided}: {actionLabel}
        </p>
      </div>
    );
  }

  return (
    <div className="border-2 border-border-heavy bg-white shadow-hard overflow-hidden">
      {/* Inverted header */}
      <div className="bg-contrast px-4 py-2.5 flex items-center gap-2">
        <svg className="h-4 w-4 text-paper" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        <span className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-paper">Approval Required</span>
      </div>

      <div className="p-4">
        {actionLabel && (
          <p className="font-body text-sm text-text-mid mb-3">
            Action: <span className="font-medium text-contrast capitalize">{actionLabel}</span>
            {domain && <span className="ml-2 font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent border-[1.5px] border-accent-border px-2 py-0.5">{domain}</span>}
          </p>
        )}

        {Object.keys(details).length > 0 && (
          <div className="mb-4 bg-paper-elevated border border-border-light p-3">
            <div className="font-body text-xs text-text-mid space-y-1">
              {Object.entries(details).map(([key, value]) => {
                if (key === "policy_violations_json" || key === "domain" || key === "action") return null;
                return (
                  <div key={key} className="flex gap-1">
                    <span className="text-text-ghost capitalize">{key.replace(/_/g, " ")}:</span>
                    <span className="font-medium text-text-primary">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {violations.length > 0 && (
          <div className="mb-4">
            <p className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent mb-1.5">Policy Flags</p>
            <div className="space-y-1">
              {violations.map((v, i) => (
                <div key={i} className="flex items-start gap-1.5 font-body text-xs">
                  <span className="text-accent font-ui font-bold mt-0.5">&rarr;</span>
                  <span className="text-text-mid">{String(v.message)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3 pt-3 border-t border-border-light">
          <button
            onClick={() => handleDecision(true)}
            className="px-5 py-2.5 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition min-h-touch"
          >
            Confirm Booking
          </button>
          <button
            onClick={() => handleDecision(false)}
            className="px-5 py-2.5 text-text-mid font-ui text-xs font-bold uppercase tracking-[0.1em] border-2 border-border-heavy hover:bg-contrast hover:text-paper btn-transition min-h-touch"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Timeline Event Router ──────────────────────────────────────────────

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
        <div className="border-2 border-border-heavy bg-white p-3">
          <div className="flex items-center gap-2 mb-1">
            {event.agent_type && (
              <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent">
                {event.agent_type}
              </span>
            )}
          </div>
          <p className="font-body text-sm text-text-mid font-light">{event.message}</p>
        </div>
      );

    case "tool_call":
      return (
        <div className="bg-paper-elevated border border-border-light p-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs bg-contrast text-paper px-2 py-0.5">{event.tool_name}</span>
            {event.status && (
              <span className="font-body text-xs text-text-ghost">{event.status}</span>
            )}
          </div>
          {event.status === "searching" && (
            <div className="mt-2 h-1.5 shimmer" />
          )}
        </div>
      );

    case "smart_defaults":
      return <SmartDefaultsCard event={event} />;

    case "approval_required":
      return <ApprovalCard event={event} onApproval={onApproval} />;

    case "clarification_needed":
      return (
        <ClarificationForm event={event} onSubmit={onClarification} tripId={tripId} />
      );

    case "trip_completed":
      return (
        <div className="space-y-4">
          {/* Success card */}
          <div className="bg-success-soft border-[1.5px] border-success-border p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="h-5 w-5 bg-success flex items-center justify-center flex-shrink-0">
                <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </span>
              <span className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-success">Trip Complete</span>
            </div>
            {event.summary?.narrative && (
              <div className="font-body text-sm text-text-mid font-light whitespace-pre-wrap leading-relaxed">
                {event.summary.narrative}
              </div>
            )}
            {event.summary?.total_spent != null && event.summary.total_spent > 0 && (
              <div className="mt-3 inline-flex items-center gap-1 px-3 py-1 bg-success-soft border-[1.5px] border-success-border">
                <span className="font-display text-lg text-success">
                  ${event.summary.total_spent.toFixed(2)}
                </span>
                <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-success ml-1">total</span>
              </div>
            )}
          </div>

          {/* Booking cards in magazine grid */}
          {event.summary?.bookings && event.summary.bookings.length > 0 && (
            <div className="border-2 border-border-heavy divide-y divide-border-light">
              {event.summary.bookings.map((booking, idx) => (
                <div key={idx} className="p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-accent"><DomainIcon domain={booking.domain} /></span>
                      <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-accent">{domainLabels[booking.domain] || booking.domain}</span>
                    </div>
                    <span className="font-display text-base text-contrast">${booking.amount.toFixed(2)}</span>
                  </div>
                  {booking.details && (
                    <div className="font-body text-xs text-text-muted space-y-0.5">
                      {Object.entries(booking.details).map(([key, value]) => (
                        <div key={key} className="flex gap-1">
                          <span className="text-text-ghost capitalize">{key.replace(/_/g, " ")}:</span>
                          <span className="text-text-mid">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {booking.provider && <div className="font-body text-[0.62rem] text-text-ghost mt-1">via {booking.provider}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "trip_failed":
      return (
        <div className="bg-accent-soft border-2 border-accent p-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="h-5 w-5 bg-accent flex items-center justify-center flex-shrink-0">
              <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </span>
            <span className="font-ui text-[0.72rem] font-bold uppercase tracking-[0.14em] text-accent">Trip Failed</span>
          </div>
          <p className="font-body text-sm text-text-mid font-light mt-1">{event.message}</p>
        </div>
      );

    default:
      return (
        <div className="p-3 bg-paper-elevated border border-border-light">
          <p className="font-mono text-xs text-text-ghost">{JSON.stringify(event)}</p>
        </div>
      );
  }
}
