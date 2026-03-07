export interface ItineraryItem {
  id: string;
  type: string;
  status: string;
  title: string;
  subtitle: string;
  time: string;
  cost: number;
  currency: string;
  details: string | null;
  badge: string | null;
  per_night: boolean;
  nights: number | null;
  provider: string | null;
  approval_id: string | null;
}

export interface ItineraryDay {
  date: string;
  label: string;
  city: string;
  items: ItineraryItem[];
}

export interface BudgetBreakdown {
  total: number;
  allocated: number;
  remaining: number;
  by_category: Record<string, number>;
}

export interface TripItinerary {
  trip_id: string;
  title: string;
  subtitle: string;
  status: string;
  narrative: string | null;
  days: ItineraryDay[];
  budget: BudgetBreakdown;
  alerts: Record<string, unknown>[];
  preferences_applied: string[];
}

export interface ChatMessage {
  id: string;
  trip_id: string;
  role: "user" | "assistant";
  content: string;
  metadata_json: Record<string, unknown> | null;
  created_at: string | null;
}
