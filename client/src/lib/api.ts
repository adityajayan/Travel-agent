const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.token) {
      h["Authorization"] = `Bearer ${this.token}`;
    }
    return h;
  }

  async createTrip(goal: string) {
    const res = await fetch(`${API_URL}/trips`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ goal }),
    });
    if (!res.ok) throw new Error(`Create trip failed: ${res.status}`);
    return res.json();
  }

  async getTrips() {
    const res = await fetch(`${API_URL}/trips`, { headers: this.headers() });
    if (!res.ok) throw new Error(`Get trips failed: ${res.status}`);
    return res.json();
  }

  async getTrip(tripId: string) {
    const res = await fetch(`${API_URL}/trips/${tripId}`, {
      headers: this.headers(),
    });
    if (!res.ok) throw new Error(`Get trip failed: ${res.status}`);
    return res.json();
  }

  async submitApproval(approvalId: string, approved: boolean) {
    const res = await fetch(`${API_URL}/approvals/${approvalId}`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ approved }),
    });
    if (!res.ok) throw new Error(`Approval failed: ${res.status}`);
    return res.json();
  }
}

export const apiClient = new ApiClient();
