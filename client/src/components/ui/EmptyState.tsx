"use client";

import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon: Icon, title, subtitle, action }: EmptyStateProps) {
  return (
    <div className="border border-gold-light/40 bg-white rounded-xl p-8 text-center shadow-sm">
      {Icon && (
        <div className="flex justify-center mb-3">
          <Icon className="h-8 w-8 text-slate/30" strokeWidth={1.5} />
        </div>
      )}
      <p className="eyebrow justify-center mb-1">{title}</p>
      {subtitle && (
        <p className="font-sans text-sm text-slate/60">{subtitle}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
