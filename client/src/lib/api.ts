export interface TravelerCount {
  adults: number;
  children: number;
}

export interface FlightPreferences {
  cabin_class: string | null;
  airline: string | null;
  nonstop: boolean | null;
  seat_preference: string | null;
}

export interface HotelPreferences {
  type: string | null;
  star_rating: number | null;
  amenities: string[];
  location_notes: string | null;
  budget_per_night: number | null;
}

export interface ParsedTripParams {
  destinations: string[];
  origin: string | null;
  departure_date: string | null;
  return_date: string | null;
  duration_days: number | null;
  budget_total: number | null;
  budget_currency: string;
  travelers: TravelerCount;
  domains: string[];
  flight_preferences: FlightPreferences;
  hotel_preferences: HotelPreferences;
  activity_preferences: string[];
  notes: string | null;
}

export interface ParseTripResponse {
  parsed: ParsedTripParams;
  goal_text: string;
  confidence: number;
  clarification_needed: string[];
  raw_input: string;
}

export interface CreateTripOptions {
  goal: string;
  total_budget?: number;
  org_id?: string;
  policy_id?: string;
  parsed_params?: ParsedTripParams;
}

export interface DateSuggestion {
  label: string;
  reason: string;
  departure_date: string;
  return_date: string;
}

export interface DateSuggestResponse {
  suggestions: DateSuggestion[];
}

export interface NearestCityResponse {
  city: string;
  country: string;
}

/** Result of the auth probe: "ok" = no auth needed, "auth_required" = need JWT, "unavailable" = backend down */
export type AuthStatus = "ok" | "auth_required" | "unavailable";

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.token) {
      h["Authorization"] = `Bearer ${this.token}`;
    }
    return h;
  }

  async parseTripGoal(text: string): Promise<ParseTripResponse> {
    const res = await fetch("/api/trips/parse", {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      if (res.status >= 502 && res.status <= 504) {
        throw new Error("Unable to reach the server. Please try again later.");
      }
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Parse failed: ${res.status}`);
    }
    return res.json();
  }

  async createTrip(options: CreateTripOptions) {
    const res = await fetch("/api/trips", {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(options),
    });
    if (!res.ok) {
      if (res.status >= 502 && res.status <= 504) {
        throw new Error("Unable to reach the server. Please try again later.");
      }
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Create trip failed: ${res.status}`);
    }
    return res.json();
  }

  async getTrips() {
    const res = await fetch("/api/trips", { headers: this.headers() });
    if (!res.ok) {
      if (res.status >= 502 && res.status <= 504) {
        throw new Error("Unable to reach the server. Please try again later.");
      }
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get trips failed: ${res.status}`);
    }
    return res.json();
  }

  async getTrip(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}`, {
      headers: this.headers(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get trip failed: ${res.status}`);
    }
    return res.json();
  }

  async submitApproval(approvalId: string, approved: boolean) {
    const res = await fetch(`/api/approvals/${approvalId}`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ approved }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Approval failed: ${res.status}`);
    }
    return res.json();
  }

  async submitClarification(tripId: string, requestId: string, answers: Record<string, string>) {
    const res = await fetch(`/api/trips/${tripId}/clarify`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ request_id: requestId, answers }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Clarification failed: ${res.status}`);
    }
    return res.json();
  }

  async cancelTrip(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}`, {
      method: "PATCH",
      headers: this.headers(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Cancel trip failed: ${res.status}`);
    }
    return res.json();
  }

  async getTripItinerary(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/itinerary`, {
      headers: this.headers(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get itinerary failed: ${res.status}`);
    }
    return res.json();
  }

  async updateItineraryItem(tripId: string, itemId: string, action: string, notes = "") {
    const res = await fetch(`/api/trips/${tripId}/itinerary/items/${itemId}`, {
      method: "PATCH",
      headers: this.headers(),
      body: JSON.stringify({ action, notes }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Update item failed: ${res.status}`);
    }
    return res.json();
  }

  async getChatHistory(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/chat`, {
      headers: this.headers(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get chat failed: ${res.status}`);
    }
    return res.json();
  }

  async sendChatMessage(tripId: string, message: string) {
    const res = await fetch(`/api/trips/${tripId}/chat`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ message }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Send chat failed: ${res.status}`);
    }
    return res.json();
  }

  async getPolicies(orgId?: string) {
    const url = orgId
      ? `/api/policies?${new URLSearchParams({ org_id: orgId })}`
      : "/api/policies";
    const res = await fetch(url, { headers: this.headers() });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get policies failed: ${res.status}`);
    }
    return res.json();
  }

  async suggestDates(destination: string, durationDays: number): Promise<DateSuggestResponse> {
    const res = await fetch("/api/trips/parse/suggest-dates", {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ destination, duration_days: durationDays }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Suggest dates failed: ${res.status}`);
    }
    return res.json();
  }

  async nearestCity(lat: number, lon: number): Promise<NearestCityResponse> {
    const res = await fetch(`/api/trips/parse/nearest-city?lat=${lat}&lon=${lon}`, {
      headers: this.headers(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Nearest city failed: ${res.status}`);
    }
    return res.json();
  }

  async checkAuth(): Promise<AuthStatus> {
    try {
      const res = await fetch("/api/health");
      if (res.status === 401) return "auth_required";
      if (res.ok) return "ok";
      // 502/503/504 = Next.js proxy couldn't reach backend
      if (res.status >= 500) return "unavailable";
      return "ok";
    } catch {
      // Network error — backend or proxy completely unreachable
      return "unavailable";
    }
  }
}

export const apiClient = new ApiClient();
