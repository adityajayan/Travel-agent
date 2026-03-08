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
    <div className="max-w-md mx-auto mt-20 bg-white border border-gold-light/40 rounded-xl p-8 shadow-md">
      <h2 className="font-serif text-2xl text-navy mb-2">Sign In</h2>
      <p className="font-sans text-sm text-slate mb-6">
        Paste a JWT token to authenticate, or run the backend without <code className="bg-cream-dark px-1 rounded font-mono text-xs">AUTH_SECRET</code> to skip authentication.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={jwt}
          onChange={(e) => setJwt(e.target.value)}
          placeholder="Paste JWT token here"
          className="w-full border border-navy/20 bg-cream rounded-md px-4 py-2.5 text-sm font-sans text-navy placeholder:text-slate/50 focus:outline-none focus:ring-2 focus:ring-gold/30 focus:border-gold mb-4"
        />
        <button
          type="submit"
          disabled={!jwt.trim()}
          className="w-full px-5 py-3 bg-navy text-cream font-sans text-sm font-semibold rounded-md hover:bg-navy-light disabled:opacity-50 disabled:cursor-not-allowed btn-transition"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
