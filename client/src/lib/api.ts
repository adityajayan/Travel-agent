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

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export interface PaymentStatusResponse {
  trip_id: string;
  payment_status: string;
  stripe_session_id: string | null;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  picture_url: string | null;
  is_approved: boolean;
}

export interface AuthMeResponse {
  user: AuthUser | null;
  auth_configured: boolean;
  expired?: boolean;
}

/** Result of the auth probe: "ok" = no auth needed, "auth_required" = need sign-in, "unavailable" = backend down */
export type AuthStatus = "ok" | "auth_required" | "unavailable";

class ApiClient {
  private headers(): Record<string, string> {
    return { "Content-Type": "application/json" };
  }

  private fetchOpts(extra?: RequestInit): RequestInit {
    return { credentials: "include" as RequestCredentials, ...extra };
  }

  // ── Auth ────────────────────────────────────────────────────────────────

  async getGoogleAuthUrl(): Promise<string> {
    const res = await fetch("/api/auth/google", this.fetchOpts());
    if (!res.ok) throw new Error("Failed to get Google auth URL");
    const data = await res.json();
    return data.url;
  }

  async getMe(): Promise<AuthMeResponse> {
    const res = await fetch("/api/auth/me", this.fetchOpts());
    if (!res.ok) throw new Error("Failed to get user info");
    return res.json();
  }

  async logout(): Promise<void> {
    await fetch("/api/auth/logout", this.fetchOpts({ method: "POST" }));
  }

  async joinWaitlist(email: string): Promise<{ status: string }> {
    const res = await fetch("/api/waitlist", this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ email }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? "Failed to join waitlist");
    }
    return res.json();
  }

  async validateInviteCode(code: string, userId: string): Promise<void> {
    const res = await fetch("/api/waitlist/validate-invite", this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ code, user_id: userId }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? "Invalid invite code");
    }
  }

  async checkAuth(): Promise<AuthStatus> {
    try {
      const res = await fetch("/api/auth/me", this.fetchOpts());
      if (res.status >= 502 && res.status <= 504) return "unavailable";
      if (!res.ok) return "unavailable";
      const data: AuthMeResponse = await res.json();
      if (!data.auth_configured) return "ok"; // auth not enabled
      if (data.user) return "ok";
      return "auth_required";
    } catch {
      return "unavailable";
    }
  }

  // ── Trips ───────────────────────────────────────────────────────────────

  async parseTripGoal(text: string): Promise<ParseTripResponse> {
    const res = await fetch("/api/trips/parse", this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ text }),
    }));
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
    const res = await fetch("/api/trips", this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(options),
    }));
    if (!res.ok) {
      if (res.status >= 502 && res.status <= 504) {
        throw new Error("Unable to reach the server. Please try again later.");
      }
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Create trip failed: ${res.status}`);
    }
    return res.json();
  }

  async getTrips(archived = false) {
    const url = archived ? "/api/trips?archived=true" : "/api/trips";
    const res = await fetch(url, this.fetchOpts({ headers: this.headers() }));
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
    const res = await fetch(`/api/trips/${tripId}`, this.fetchOpts({
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get trip failed: ${res.status}`);
    }
    return res.json();
  }

  async submitApproval(approvalId: string, approved: boolean) {
    const res = await fetch(`/api/approvals/${approvalId}`, this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ approved }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Approval failed: ${res.status}`);
    }
    return res.json();
  }

  async submitClarification(tripId: string, requestId: string, answers: Record<string, string>) {
    const res = await fetch(`/api/trips/${tripId}/clarify`, this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ request_id: requestId, answers }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Clarification failed: ${res.status}`);
    }
    return res.json();
  }

  async cancelTrip(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}`, this.fetchOpts({
      method: "PATCH",
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Cancel trip failed: ${res.status}`);
    }
    return res.json();
  }

  async getTripItinerary(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/itinerary`, this.fetchOpts({
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get itinerary failed: ${res.status}`);
    }
    return res.json();
  }

  async updateItineraryItem(tripId: string, itemId: string, action: string, notes = "") {
    const res = await fetch(`/api/trips/${tripId}/itinerary/items/${itemId}`, this.fetchOpts({
      method: "PATCH",
      headers: this.headers(),
      body: JSON.stringify({ action, notes }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Update item failed: ${res.status}`);
    }
    return res.json();
  }

  async getChatHistory(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/chat`, this.fetchOpts({
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get chat failed: ${res.status}`);
    }
    return res.json();
  }

  async sendChatMessage(tripId: string, message: string) {
    const res = await fetch(`/api/trips/${tripId}/chat`, this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ message }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Send chat failed: ${res.status}`);
    }
    return res.json();
  }

  async retryTrip(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/retry`, this.fetchOpts({
      method: "POST",
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Retry trip failed: ${res.status}`);
    }
    return res.json();
  }

  async archiveTrip(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/archive`, this.fetchOpts({
      method: "PATCH",
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Archive trip failed: ${res.status}`);
    }
    return res.json();
  }

  async unarchiveTrip(tripId: string) {
    const res = await fetch(`/api/trips/${tripId}/unarchive`, this.fetchOpts({
      method: "PATCH",
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Unarchive trip failed: ${res.status}`);
    }
    return res.json();
  }

  async getPolicies(orgId?: string) {
    const url = orgId
      ? `/api/policies?${new URLSearchParams({ org_id: orgId })}`
      : "/api/policies";
    const res = await fetch(url, this.fetchOpts({ headers: this.headers() }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Get policies failed: ${res.status}`);
    }
    return res.json();
  }

  async suggestDates(destination: string, durationDays: number): Promise<DateSuggestResponse> {
    const res = await fetch("/api/trips/parse/suggest-dates", this.fetchOpts({
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ destination, duration_days: durationDays }),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Suggest dates failed: ${res.status}`);
    }
    return res.json();
  }

  // ── Payments ─────────────────────────────────────────────────────────────

  async createCheckoutSession(tripId: string): Promise<CheckoutResponse> {
    const res = await fetch(`/api/trips/${tripId}/checkout`, this.fetchOpts({
      method: "POST",
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Checkout failed: ${res.status}`);
    }
    return res.json();
  }

  async getPaymentStatus(tripId: string): Promise<PaymentStatusResponse> {
    const res = await fetch(`/api/trips/${tripId}/payment-status`, this.fetchOpts({
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Payment status failed: ${res.status}`);
    }
    return res.json();
  }

  async cancelBooking(tripId: string, bookingId: string): Promise<{ status: string }> {
    const res = await fetch(`/api/trips/${tripId}/bookings/${bookingId}/cancel`, this.fetchOpts({
      method: "POST",
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Cancel booking failed: ${res.status}`);
    }
    return res.json();
  }

  async nearestCity(lat: number, lon: number): Promise<NearestCityResponse> {
    const res = await fetch(`/api/trips/parse/nearest-city?lat=${lat}&lon=${lon}`, this.fetchOpts({
      headers: this.headers(),
    }));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Nearest city failed: ${res.status}`);
    }
    return res.json();
  }
}

export const apiClient = new ApiClient();
