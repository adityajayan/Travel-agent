"use client";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";
import Button from "@/components/ui/Button";

interface ItineraryHeaderProps {
  title: string;
  subtitle: string;
  status: string;
  pendingCount: number;
  onApproveAll?: () => void;
}

export default function ItineraryHeader({
  title,
  subtitle,
  status,
  pendingCount,
  onApproveAll,
}: ItineraryHeaderProps) {
  return (
    <div className="border-b border-navy/20 pb-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Link
          href="/"
          className="font-sans text-xs font-semibold text-slate hover:text-navy flex items-center gap-1 btn-transition focus:outline-none focus:ring-2 focus:ring-gold/30 rounded-md px-1"
        >
          <ChevronLeft className="h-3 w-3" aria-hidden="true" />
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
          <StatusBadge status={status} />
          {pendingCount > 0 && onApproveAll && (
            <Button variant="primary" size="sm" onClick={onApproveAll}>
              Approve All ({pendingCount})
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
