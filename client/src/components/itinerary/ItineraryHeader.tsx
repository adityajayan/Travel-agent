"use client";

import Link from "next/link";

interface ItineraryHeaderProps {
  title: string;
  subtitle: string;
  status: string;
  pendingCount: number;
  onApproveAll?: () => void;
}

const statusConfig: Record<string, { label: string; style: string }> = {
  pending: { label: "Pending", style: "border-border-light text-text-ghost" },
  running: { label: "Running", style: "border-accent-border text-accent" },
  complete: { label: "Complete", style: "border-success-border text-success" },
  completed: { label: "Complete", style: "border-success-border text-success" },
  awaiting_approval: { label: "Awaiting Approval", style: "border-accent-border text-accent" },
  failed: { label: "Failed", style: "border-accent text-accent" },
  cancelled: { label: "Cancelled", style: "border-border-light text-text-ghost" },
};

export default function ItineraryHeader({
  title,
  subtitle,
  status,
  pendingCount,
  onApproveAll,
}: ItineraryHeaderProps) {
  const st = statusConfig[status] || statusConfig.pending;

  return (
    <div className="border-b-2 border-border-heavy pb-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Link
          href="/"
          className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-muted hover:text-contrast flex items-center gap-1 btn-transition"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </Link>
      </div>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h1 className="font-display text-2xl lg:text-3xl font-medium text-contrast leading-tight">
            {title}
          </h1>
          <p className="font-body text-sm text-text-muted font-light mt-1">{subtitle}</p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span
            className={`px-2.5 py-0.5 border-[1.5px] font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] ${st.style}`}
          >
            {st.label}
          </span>
          {pendingCount > 0 && onApproveAll && (
            <button
              onClick={onApproveAll}
              className="px-4 py-2 bg-contrast text-paper font-ui text-[0.72rem] font-bold uppercase tracking-[0.1em] hover:bg-accent btn-transition"
            >
              Approve All ({pendingCount})
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
