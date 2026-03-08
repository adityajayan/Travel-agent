"use client";

import { STATUS_CONFIG } from "@/lib/design-tokens";

interface StatusBadgeProps {
  status: string;
  pulse?: boolean;
  className?: string;
}

export default function StatusBadge({ status, pulse, className = "" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.planning;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {pulse && (
        <span className="h-2 w-2 bg-gold rounded-full animate-pulse-dot" />
      )}
      <span
        className={`px-2 py-0.5 border rounded-md font-sans text-[10px] font-medium ${config.className}`}
      >
        {config.label}
      </span>
    </div>
  );
}
