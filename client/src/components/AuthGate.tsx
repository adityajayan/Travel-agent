"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { useToast } from "./Toast";

interface AuthContextValue {
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue>({
  token: null,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("auth_token");
    if (stored) {
      setToken(stored);
      apiClient.setToken(stored);
    }
    setChecked(true);
  }, []);

  const login = useCallback((t: string) => {
    setToken(t);
    localStorage.setItem("auth_token", t);
    apiClient.setToken(t);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    localStorage.removeItem("auth_token");
    apiClient.clearToken();
  }, []);

  if (!checked) return null;

  return (
    <AuthContext.Provider value={{ token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function LoginForm() {
  const [jwt, setJwt] = useState("");
  const { login } = useAuth();
  const { toast } = useToast();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = jwt.trim();
    if (!trimmed) return;
    login(trimmed);
    toast("Logged in successfully", "success");
  };

  return (
    <div className="max-w-md mx-auto mt-20 bg-white border-2 border-border-heavy p-8">
      <h2 className="font-display text-2xl text-contrast mb-2">Sign In</h2>
      <p className="font-body text-sm text-text-muted font-light mb-6">
        Paste a JWT token to authenticate, or run the backend without <code className="bg-paper-elevated px-1 font-mono text-xs">AUTH_SECRET</code> to skip authentication.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={jwt}
          onChange={(e) => setJwt(e.target.value)}
          placeholder="Paste JWT token here"
          className="w-full border-2 border-border-heavy bg-paper px-4 py-2.5 text-sm font-body text-text-primary placeholder:text-text-ghost focus:outline-none focus:border-accent mb-4"
        />
        <button
          type="submit"
          disabled={!jwt.trim()}
          className="w-full px-5 py-3 bg-contrast text-paper font-ui text-xs font-bold uppercase tracking-[0.1em] hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed btn-transition"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
