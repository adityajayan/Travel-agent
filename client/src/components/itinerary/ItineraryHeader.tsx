"use client";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";

interface ItineraryHeaderProps {
  title: string;
  subtitle: string;
  status: string;
  pendingCount: number;
  onApproveAll?: () => void;
}

const statusConfig: Record<string, { label: string; style: string }> = {
  pending: { label: "Pending", style: "border-gold-light text-slate" },
  running: { label: "Running", style: "border-gold text-gold" },
  complete: { label: "Complete", style: "border-success-border text-success" },
  completed: { label: "Complete", style: "border-success-border text-success" },
  awaiting_approval: { label: "Awaiting Approval", style: "border-gold text-gold" },
  failed: { label: "Failed", style: "border-error text-error" },
  cancelled: { label: "Cancelled", style: "border-gold-light text-slate" },
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
    <div className="border-b border-navy/20 pb-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Link
          href="/"
          className="font-sans text-xs font-semibold text-slate hover:text-navy flex items-center gap-1 btn-transition"
        >
          <ChevronLeft className="h-3 w-3" />
          Back
        </Link>
      </div>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h1 className="font-serif text-2xl lg:text-3xl font-medium text-navy leading-tight">
            {title}
          </h1>
          <p className="font-sans text-sm text-slate mt-1">{subtitle}</p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span
            className={`px-2.5 py-0.5 border rounded-md font-sans text-[0.65rem] font-medium ${st.style}`}
          >
            {st.label}
          </span>
          {pendingCount > 0 && onApproveAll && (
            <button
              onClick={onApproveAll}
              className="px-4 py-2 bg-navy text-cream font-sans text-xs font-semibold rounded-md hover:bg-navy-light btn-transition"
            >
              Approve All ({pendingCount})
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
