import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SidebarSection = "chat" | "tasks" | "memory" | "files" | "settings";

interface AppShellState {
  // Sidebar
  sidebarCollapsed: boolean;
  activeSidebarSection: SidebarSection;

  // Right Panel
  rightPanelOpen: boolean;

  // Mobile Drawer
  mobileDrawerOpen: boolean;

  // Actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  setActiveSidebarSection: (section: SidebarSection) => void;
  setRightPanelOpen: (open: boolean) => void;
  toggleRightPanel: () => void;
  setMobileDrawerOpen: (open: boolean) => void;
  toggleMobileDrawer: () => void;
}

export const useAppShellStore = create<AppShellState>()(
  persist(
    (set) => ({
      // Defaults
      sidebarCollapsed: false,
      activeSidebarSection: "chat",
      rightPanelOpen: false,
      mobileDrawerOpen: false,

      // Sidebar actions
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      // Active section
      setActiveSidebarSection: (section) =>
        set({ activeSidebarSection: section }),

      // Right panel
      setRightPanelOpen: (open) => set({ rightPanelOpen: open }),
      toggleRightPanel: () =>
        set((state) => ({ rightPanelOpen: !state.rightPanelOpen })),

      // Mobile drawer
      setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
      toggleMobileDrawer: () =>
        set((state) => ({ mobileDrawerOpen: !state.mobileDrawerOpen })),
    }),
    {
      name: "manusai-shell-state",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        activeSidebarSection: state.activeSidebarSection,
        rightPanelOpen: state.rightPanelOpen,
      }),
    },
  ),
);
