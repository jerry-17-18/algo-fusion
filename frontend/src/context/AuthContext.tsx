import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { apiClient } from "../lib/api";
import {
  clearAuthToken,
  clearStoredUser,
  getAuthToken,
  getStoredUser,
  setAuthToken,
  setStoredUser,
} from "../lib/storage";
import type { LoginResponse, User } from "../lib/types";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  loginDoctor: (username: string, password: string) => Promise<void>;
  loginPatient: (patientId: string, fullName: string, age: number) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [user, setUser] = useState<User | null>(getStoredUser<User>());

  useEffect(() => {
    apiClient.setToken(token);
  }, [token]);

  const value: AuthContextValue = {
    token,
    user,
    loginDoctor: async (username, password) => {
      const response: LoginResponse = await apiClient.login(username, password);
      setToken(response.access_token);
      setUser(response.user);
      setAuthToken(response.access_token);
      setStoredUser(response.user);
      apiClient.setToken(response.access_token);
    },
    loginPatient: async (patientId, fullName, age) => {
      const response: LoginResponse = await apiClient.patientLogin(patientId, fullName, age);
      setToken(response.access_token);
      setUser(response.user);
      setAuthToken(response.access_token);
      setStoredUser(response.user);
      apiClient.setToken(response.access_token);
    },
    logout: () => {
      setToken(null);
      setUser(null);
      clearAuthToken();
      clearStoredUser();
      apiClient.setToken(null);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
