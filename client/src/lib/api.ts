export interface CreateTripOptions {
  goal: string;
  total_budget?: number;
  org_id?: string;
  policy_id?: string;
}

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
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Create trip failed: ${res.status}`);
    }
    return res.json();
  }

  async getTrips() {
    const res = await fetch("/api/trips", { headers: this.headers() });
    if (!res.ok) {
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

  async checkAuth(): Promise<boolean> {
    try {
      const res = await fetch("/api/trips", { headers: this.headers() });
      return res.ok;
    } catch {
      return false;
    }
  }
}

export const apiClient = new ApiClient();
