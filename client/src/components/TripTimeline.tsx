"use client";

interface TripEvent {
  type: string;
  message?: string;
  agent_type?: string;
  tool_name?: string;
  status?: string;
  summary?: Record<string, unknown>;
  approval_id?: string;
  context?: Record<string, unknown>;
}

interface TripTimelineProps {
  events: TripEvent[];
  onApproval: (approvalId: string, approved: boolean) => void;
}

export default function TripTimeline({ events, onApproval }: TripTimelineProps) {
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
        <TimelineEvent key={idx} event={event} onApproval={onApproval} />
      ))}
    </div>
  );
}

function TimelineEvent({
  event,
  onApproval,
}: {
  event: TripEvent;
  onApproval: (id: string, approved: boolean) => void;
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

    case "trip_completed":
      return (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-green-50 border border-green-200">
          <span className="mt-0.5 h-5 w-5 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
            <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </span>
          <div>
            <p className="text-sm font-medium text-green-800">Trip planning complete!</p>
            {event.summary && (
              <pre className="text-xs bg-white rounded p-2 mt-2 overflow-auto border border-green-100">
                {JSON.stringify(event.summary, null, 2)}
              </pre>
            )}
          </div>
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
