"use client";

import type { BudgetBreakdown } from "@/lib/itinerary-types";

interface BudgetBarProps {
  budget: BudgetBreakdown;
}

const categoryLabels: Record<string, string> = {
  flight: "Flights",
  hotel: "Hotels",
  transport: "Transport",
  activity: "Activities",
};

const categoryColors: Record<string, string> = {
  flight: "bg-blue-500",
  hotel: "bg-purple-500",
  transport: "bg-orange-500",
  activity: "bg-teal-500",
};

export default function BudgetBar({ budget }: BudgetBarProps) {
  const percentage = budget.total > 0 ? Math.min((budget.allocated / budget.total) * 100, 100) : 0;
  const isOverBudget = budget.total > 0 && budget.allocated > budget.total;

  return (
    <div className="border-2 border-border-heavy bg-white p-4">
      <p className="eyebrow mb-3">Budget</p>

      {/* Main progress bar */}
      <div className="mb-3">
        <div className="h-3 bg-paper-elevated border border-border-light overflow-hidden">
          {budget.total > 0 ? (
            <div className="h-full flex">
              {Object.entries(budget.by_category).map(([category, amount]) => {
                const catPct = (amount / budget.total) * 100;
                return (
                  <div
                    key={category}
                    className={`h-full ${categoryColors[category] || "bg-gray-400"}`}
                    style={{ width: `${catPct}%` }}
                  />
                );
              })}
            </div>
          ) : (
            <div
              className="h-full bg-contrast"
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          )}
        </div>
      </div>

      {/* Amounts */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <span className="font-display text-xl text-contrast">${budget.allocated.toFixed(0)}</span>
          {budget.total > 0 && (
            <span className="font-body text-xs text-text-ghost ml-1">
              of ${budget.total.toFixed(0)}
            </span>
          )}
        </div>
        {budget.total > 0 && (
          <div>
            <span
              className={`font-display text-lg ${isOverBudget ? "text-accent" : "text-success"}`}
            >
              ${budget.remaining.toFixed(0)}
            </span>
            <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-ghost ml-1">
              remaining
            </span>
          </div>
        )}
      </div>

      {/* Category breakdown */}
      {Object.keys(budget.by_category).length > 0 && (
        <div className="border-t border-border-light pt-3 space-y-2">
          {Object.entries(budget.by_category).map(([category, amount]) => (
            <div key={category} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 ${categoryColors[category] || "bg-gray-400"}`} />
                <span className="font-ui text-[0.65rem] font-bold uppercase tracking-[0.1em] text-text-muted">
                  {categoryLabels[category] || category}
                </span>
              </div>
              <span className="font-body text-sm text-text-mid">${amount.toFixed(0)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
