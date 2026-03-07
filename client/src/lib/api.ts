export interface CreateTripOptions {
  goal: string;
  total_budget?: number;
  org_id?: string;
  policy_id?: string;
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
