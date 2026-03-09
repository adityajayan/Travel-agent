"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiClient, AuthUser } from "@/lib/api";

export type AppAuthStatus = "loading" | "ok" | "auth_required" | "unavailable";

interface AuthContextValue {
  user: AuthUser | null;
  status: AppAuthStatus;
  isAuthenticated: boolean;
  logout: () => void;
  refreshUser: () => Promise<void>;
  retryConnection: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  status: "loading",
  isAuthenticated: false,
  logout: () => {},
  refreshUser: async () => {},
  retryConnection: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AppAuthStatus>("loading");

  const refreshUser = useCallback(async () => {
    try {
      const data = await apiClient.getMe();
      if (!data.auth_configured) {
        // Auth not enabled on backend — allow access
        setUser(null);
        setStatus("ok");
      } else if (data.user) {
        setUser(data.user);
        setStatus("ok");
      } else {
        setUser(null);
        setStatus("auth_required");
      }
    } catch {
      // Backend unreachable
      setUser(null);
      setStatus("unavailable");
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    await apiClient.logout();
    setUser(null);
    setStatus("auth_required");
  }, []);

  const retryConnection = useCallback(() => {
    setStatus("loading");
    refreshUser();
  }, [refreshUser]);

  if (status === "loading") return null;

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        isAuthenticated: !!user,
        logout,
        refreshUser,
        retryConnection,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function InviteCodeForm({ userId, onApproved }: { userId: string; onApproved: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    try {
      await apiClient.validateInviteCode(code.trim(), userId);
      onApproved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid invite code");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20 bg-white border border-gold-light/40 rounded-xl p-8 shadow-md">
      <h2 className="font-serif text-2xl text-navy mb-2">You&apos;re on the list</h2>
      <p className="font-sans text-sm text-slate mb-6">
        We&apos;re rolling out access gradually. Enter your invite code to get started, or hang tight — we&apos;ll let you in soon.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Enter invite code"
          className="w-full border border-navy/20 bg-cream rounded-md px-4 py-2.5 text-sm font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold mb-3"
        />
        {error && (
          <p className="text-sm text-red-600 font-sans mb-3">{error}</p>
        )}
        <button
          type="submit"
          disabled={!code.trim() || loading}
          className="w-full px-5 py-3 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light disabled:opacity-50 disabled:cursor-not-allowed btn-transition"
        >
          {loading ? "Validating..." : "Activate Access"}
        </button>
      </form>
    </div>
  );
}

export function LoginForm() {
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      const url = await apiClient.getGoogleAuthUrl();
      window.location.href = url;
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20 bg-white border border-gold-light/40 rounded-xl p-8 shadow-md">
      <h2 className="font-serif text-2xl text-navy mb-2">Welcome to Concierge</h2>
      <p className="font-sans text-sm text-slate mb-6">
        Sign in to start planning your next trip with AI.
      </p>
      <button
        onClick={handleGoogleLogin}
        disabled={loading}
        className="w-full px-5 py-3 bg-white text-charcoal font-sans text-sm font-semibold rounded-md border border-navy/20 hover:bg-cream hover:border-navy/40 disabled:opacity-50 disabled:cursor-not-allowed btn-transition flex items-center justify-center gap-3"
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
        {loading ? "Redirecting..." : "Sign in with Google"}
      </button>
    </div>
  );
}
