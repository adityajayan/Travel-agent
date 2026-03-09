// Centralized design tokens — single source of truth for status, domain, and budget colors

export const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  // Trip-level statuses
  planning: { label: "Planning", className: "border-gold text-gold" },
  review: { label: "In Review", className: "border-gold text-gold" },
  complete: { label: "Complete", className: "border-success-border text-success" },
  completed: { label: "Complete", className: "border-success-border text-success" },
  payment_pending: { label: "Awaiting Payment", className: "border-gold text-gold" },
  booking: { label: "Booking", className: "border-blue-200 text-blue-600" },
  failed: { label: "Failed", className: "border-error text-error" },
  cancelled: { label: "Cancelled", className: "border-gold-light text-slate" },
  // Item-level statuses
  awaiting_approval: { label: "Needs Approval", className: "border-gold text-gold" },
  confirmed: { label: "Confirmed", className: "border-success-border text-success" },
  rejected: { label: "Rejected", className: "border-error text-error" },
  suggested: { label: "Suggested", className: "border-blue-200 text-blue-600" },
};

export const DOMAIN_CONFIG: Record<
  string,
  { label: string; colors: { border: string; bg: string; text: string } }
> = {
  flight: { label: "Flight", colors: { border: "border-blue-200", bg: "bg-blue-50", text: "text-blue-600" } },
  hotel: { label: "Hotel", colors: { border: "border-purple-200", bg: "bg-purple-50", text: "text-purple-600" } },
  transport: { label: "Transport", colors: { border: "border-orange-200", bg: "bg-orange-50", text: "text-orange-600" } },
  activity: { label: "Activity", colors: { border: "border-teal-200", bg: "bg-teal-50", text: "text-teal-600" } },
};

export const BUDGET_CATEGORY_COLORS: Record<string, string> = {
  flight: "bg-blue-500",
  hotel: "bg-purple-500",
  transport: "bg-orange-500",
  activity: "bg-teal-500",
  food: "bg-amber-500",
  other: "bg-slate-400",
};

export const BUDGET_CATEGORY_LABELS: Record<string, string> = {
  flight: "Flights",
  hotel: "Hotels",
  transport: "Transport",
  activity: "Activities",
  food: "Food",
  other: "Other",
};
