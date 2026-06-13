"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppShellState {
  sidebarCollapsed: boolean;
  mobileMenuOpen: boolean;
  activityPanelOpen: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  toggleSidebar: () => void;
  setMobileMenuOpen: (v: boolean) => void;
  setActivityPanelOpen: (v: boolean) => void;
  toggleActivityPanel: () => void;
}

export const useAppShellStore = create<AppShellState>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      mobileMenuOpen: false,
      activityPanelOpen: false,

      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setMobileMenuOpen: (v) => set({ mobileMenuOpen: v }),
      setActivityPanelOpen: (v) => set({ activityPanelOpen: v }),
      toggleActivityPanel: () => set((s) => ({ activityPanelOpen: !s.activityPanelOpen })),
    }),
    { name: "manusai-shell" }
  )
);
