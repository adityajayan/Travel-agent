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
    <div className="max-w-md mx-auto mt-20 bg-white rounded-xl shadow-sm border border-gray-200 p-8">
      <h2 className="text-xl font-bold text-gray-800 mb-2">Sign In</h2>
      <p className="text-sm text-gray-500 mb-6">
        Paste a JWT token to authenticate, or run the backend without <code className="bg-gray-100 px-1 rounded">AUTH_SECRET</code> to skip authentication.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={jwt}
          onChange={(e) => setJwt(e.target.value)}
          placeholder="Paste JWT token here"
          className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent mb-4"
        />
        <button
          type="submit"
          disabled={!jwt.trim()}
          className="w-full px-5 py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
