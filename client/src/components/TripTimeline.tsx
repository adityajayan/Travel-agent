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
      <div className="text-center text-gray-400 py-8">
        <p className="text-sm">Waiting for agent events...</p>
        <div className="mt-2 flex justify-center gap-1">
          <span className="h-2 w-2 rounded-full bg-gray-300 animate-pulse-dot" />
          <span className="h-2 w-2 rounded-full bg-gray-300 animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
          <span className="h-2 w-2 rounded-full bg-gray-300 animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event, idx) => (
        <TimelineEvent key={idx} event={event} onApproval={onApproval} onClarification={onClarification} tripId={tripId} />
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

function BookingCard({ booking }: { booking: BookingData }) {
  const domainLabels: Record<string, string> = {
    flight: "Flight",
    hotel: "Hotel",
    transport: "Transport",
    activity: "Activity",
  };

  const domainColors: Record<string, string> = {
    flight: "border-blue-200 bg-blue-50",
    hotel: "border-purple-200 bg-purple-50",
    transport: "border-orange-200 bg-orange-50",
    activity: "border-teal-200 bg-teal-50",
  };

  const iconColors: Record<string, string> = {
    flight: "text-blue-600",
    hotel: "text-purple-600",
    transport: "text-orange-600",
    activity: "text-teal-600",
  };

  return (
    <div className={`rounded-lg border p-3 ${domainColors[booking.domain] || "border-gray-200 bg-gray-50"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={iconColors[booking.domain] || "text-gray-600"}>
            <DomainIcon domain={booking.domain} />
          </span>
          <span className="text-sm font-medium text-gray-800">
            {domainLabels[booking.domain] || booking.domain}
          </span>
        </div>
        <span className="text-sm font-semibold text-gray-900">${booking.amount.toFixed(2)}</span>
      </div>
      {booking.details && (
        <div className="text-xs text-gray-600 space-y-0.5">
          {Object.entries(booking.details).map(([key, value]) => (
            <div key={key} className="flex gap-1">
              <span className="text-gray-500 capitalize">{key.replace(/_/g, " ")}:</span>
              <span>{String(value)}</span>
            </div>
          ))}
        </div>
      )}
      {booking.provider && (
        <div className="mt-1.5 text-xs text-gray-400">via {booking.provider}</div>
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
      <div className="flex items-start gap-3 p-4 rounded-lg bg-indigo-50 border border-indigo-200">
        <span className="mt-0.5 h-5 w-5 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
          <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </span>
        <p className="text-sm text-indigo-700">Preferences submitted — agents are continuing...</p>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-indigo-50 border border-indigo-200">
      <span className="mt-0.5 h-5 w-5 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
        <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </span>
      <div className="flex-1">
        <p className="text-sm font-medium text-indigo-800 mb-3">A few quick questions to plan your ideal trip:</p>
        <form onSubmit={handleSubmit} className="space-y-3">
          {questions.map((q) => (
            <div key={q.key}>
              <label className="block text-xs font-medium text-indigo-700 mb-1">{q.question}</label>
              <input
                type="text"
                value={answers[q.key] || ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))}
                placeholder={q.placeholder || "No preference"}
                className="w-full rounded-md border border-indigo-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent bg-white"
              />
            </div>
          ))}
          <button
            type="submit"
            className="px-4 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-md hover:bg-indigo-700 transition-colors"
          >
            Submit Preferences
          </button>
          <button
            type="button"
            onClick={() => {
              if (onSubmit && tripId && requestId) {
                onSubmit(tripId, requestId, {});
                setSubmitted(true);
              }
            }}
            className="ml-2 px-4 py-1.5 text-indigo-600 text-xs font-medium rounded-md border border-indigo-300 hover:bg-indigo-100 transition-colors"
          >
            Skip — Surprise Me
          </button>
        </form>
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
        <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 border border-blue-100">
          <span className="mt-0.5 h-5 w-5 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </span>
          <div>
            <p className="text-sm font-medium text-blue-800">
              {event.agent_type && <span className="text-blue-600">[{event.agent_type}] </span>}
              {event.message}
            </p>
          </div>
        </div>
      );

    case "tool_call":
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
          <span className="mt-0.5 h-5 w-5 rounded-full bg-gray-400 flex items-center justify-center flex-shrink-0">
            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </span>
          <div>
            <p className="text-sm text-gray-700">
              <span className="font-mono text-xs bg-gray-200 px-1.5 py-0.5 rounded">{event.tool_name}</span>
              <span className="ml-2 text-gray-500">{event.status}</span>
            </p>
          </div>
        </div>
      );

    case "approval_required":
      return (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200">
          <span className="mt-0.5 h-5 w-5 rounded-full bg-amber-500 flex items-center justify-center flex-shrink-0">
            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-800 mb-2">Approval Required</p>
            {event.context && (
              <pre className="text-xs bg-white rounded p-2 mb-3 overflow-auto border border-amber-100">
                {JSON.stringify(event.context, null, 2)}
              </pre>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => event.approval_id && onApproval(event.approval_id, true)}
                className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-md hover:bg-green-700 transition-colors"
              >
                Approve
              </button>
              <button
                onClick={() => event.approval_id && onApproval(event.approval_id, false)}
                className="px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-md hover:bg-red-700 transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      );

    case "clarification_needed":
      return (
        <ClarificationForm event={event} onSubmit={onClarification} tripId={tripId} />
      );

    case "trip_completed":
      return (
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-4 rounded-lg bg-green-50 border border-green-200">
            <span className="mt-0.5 h-5 w-5 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
              <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </span>
            <div className="flex-1">
              <p className="text-sm font-medium text-green-800 mb-2">Trip planning complete!</p>
              {event.summary?.narrative && (
                <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {event.summary.narrative}
                </div>
              )}
              {event.summary?.total_spent != null && event.summary.total_spent > 0 && (
                <div className="mt-3 inline-flex items-center gap-1 px-3 py-1 bg-green-100 rounded-full">
                  <span className="text-xs text-green-700 font-medium">
                    Total: ${event.summary.total_spent.toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          </div>

          {event.summary?.bookings && event.summary.bookings.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {event.summary.bookings.map((booking, idx) => (
                <BookingCard key={idx} booking={booking} />
              ))}
            </div>
          )}
        </div>
      );

    case "trip_failed":
      return (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 border border-red-200">
          <span className="mt-0.5 h-5 w-5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </span>
          <div>
            <p className="text-sm font-medium text-red-800">Trip planning failed</p>
            <p className="text-xs text-red-600 mt-1">{event.message}</p>
          </div>
        </div>
      );

    default:
      return (
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          <p className="text-xs text-gray-500 font-mono">{JSON.stringify(event)}</p>
        </div>
      );
  }
}
