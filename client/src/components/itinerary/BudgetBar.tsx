"use client";

import type { BudgetBreakdown } from "@/lib/itinerary-types";
import { BUDGET_CATEGORY_COLORS, BUDGET_CATEGORY_LABELS } from "@/lib/design-tokens";
import Card from "@/components/ui/Card";

interface BudgetBarProps {
  budget: BudgetBreakdown;
}

export default function BudgetBar({ budget }: BudgetBarProps) {
  const percentage = budget.total > 0 ? Math.min((budget.allocated / budget.total) * 100, 100) : 0;
  const isOverBudget = budget.total > 0 && budget.allocated > budget.total;

  return (
    <Card>
      <p className="eyebrow mb-3">Budget</p>

      {/* Main progress bar */}
      <div className="mb-3">
        <div className="h-3 bg-cream-dark border border-gold-light/30 rounded-full overflow-hidden">
          {budget.total > 0 ? (
            <div className="h-full flex rounded-full overflow-hidden">
              {Object.entries(budget.by_category).map(([category, amount]) => {
                const catPct = (amount / budget.total) * 100;
                return (
                  <div
                    key={category}
                    className={`h-full ${BUDGET_CATEGORY_COLORS[category] || "bg-gray-400"}`}
                    style={{ width: `${catPct}%` }}
                  />
                );
              })}
            </div>
          ) : (
            <div
              className="h-full bg-navy rounded-full"
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          )}
        </div>
      </div>

      {/* Amounts */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <span className="font-serif text-xl text-navy">${budget.allocated.toFixed(0)}</span>
          {budget.total > 0 && (
            <span className="font-sans text-xs text-slate/60 ml-1">
              of ${budget.total.toFixed(0)}
            </span>
          )}
        </div>
        {budget.total > 0 && (
          <div>
            <span
              className={`font-serif text-lg ${isOverBudget ? "text-error" : "text-success"}`}
            >
              ${budget.remaining.toFixed(0)}
            </span>
            <span className="font-sans text-xs font-medium text-slate/60 ml-1">
              remaining
            </span>
          </div>
        )}
      </div>

      {/* Category breakdown */}
      {Object.keys(budget.by_category).length > 0 && (
        <div className="border-t border-gold-light/30 pt-3 space-y-2">
          {Object.entries(budget.by_category).map(([category, amount]) => (
            <div key={category} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${BUDGET_CATEGORY_COLORS[category] || "bg-gray-400"}`} />
                <span className="font-sans text-xs font-medium text-slate">
                  {BUDGET_CATEGORY_LABELS[category] || category}
                </span>
              </div>
              <span className="font-sans text-sm text-charcoal">${amount.toFixed(0)}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
