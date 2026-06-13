"use client";
import { create } from "zustand";
import { User } from "@/types";
import { authAPI } from "@/lib/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  error: null,
  isAuthenticated: false,

  loadFromStorage: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        set({ token, user, isAuthenticated: true });
      } catch {}
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authAPI.login(email, password);
      const data = res.data;
      const user: User = { user_id: data.user_id, email: data.email, username: data.username };
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(user));
      set({ token: data.access_token, user, isAuthenticated: true, isLoading: false });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Login failed";
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  register: async (email, username, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authAPI.register(email, username, password);
      const data = res.data;
      const user: User = { user_id: data.user_id, email: data.email, username: data.username };
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(user));
      set({ token: data.access_token, user, isAuthenticated: true, isLoading: false });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Registration failed";
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ user: null, token: null, isAuthenticated: false });
    window.location.href = "/login";
  },

  clearError: () => set({ error: null }),
}));
