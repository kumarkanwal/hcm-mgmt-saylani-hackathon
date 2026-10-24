"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken, USE_MOCKS } from "@/lib/api";
import { mockUserForRole } from "@/lib/mocks";
import type { LoginResponse, Role, User } from "@/lib/types";

type AuthContextValue = {
  user: User | null;
  role: Role | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  switchRole: (role: Role) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(USE_MOCKS ? mockUserForRole("hr") : null);
  const [isLoading, setIsLoading] = useState(!USE_MOCKS);

  const refreshUser = useCallback(async () => {
    if (!getToken() && !USE_MOCKS) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      setUser(await api.get<User>("/auth/me"));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
    const clear = () => setUser(null);
    window.addEventListener("hcm-auth-cleared", clear);
    return () => window.removeEventListener("hcm-auth-cleared", clear);
  }, [refreshUser]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    role: user?.role ?? null,
    isLoading,
    login: async (email, password) => {
      const response = await api.post<LoginResponse>("/auth/login", { email, password });
      setToken(response.access_token);
      setUser(response.user);
      return response.user;
    },
    logout: () => { setToken(null); setUser(null); window.location.assign("/login"); },
    refreshUser,
    switchRole: (role) => {
      if (!USE_MOCKS) return;
      setToken(`mock-token-${role}`);
      setUser(mockUserForRole(role));
    },
  }), [isLoading, refreshUser, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
