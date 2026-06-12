import React from "react";
import { cn } from "#/utils/utils";
import { ShellSidebar } from "./shell-sidebar";
import { ShellRightPanel } from "./shell-right-panel";
import { ShellTopbar } from "./shell-topbar";
import { ShellMobileDrawer } from "./shell-mobile-drawer";
import "./design-tokens.css";

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
}

/**
 * AppShell — Root layout wrapper for ManusAI
 *
 * Desktop (≥768px):
 *   ┌─────────────────────────────────────────────────────┐
 *   │ Sidebar (260px collapsible) │ Main (flex-1) │ Panel │
 *   └─────────────────────────────────────────────────────┘
 *
 * Mobile (<768px):
 *   ┌───────────────────────┐
 *   │ TopBar                │
 *   ├───────────────────────┤
 *   │ Main workspace        │
 *   └───────────────────────┘
 *   + Mobile Drawer (overlay)
 */
export function AppShell({ children, title }: AppShellProps) {
  return (
    <div
      data-testid="app-shell"
      className={cn(
        "flex h-screen w-full overflow-hidden",
        "bg-[var(--surface-bg)]",
      )}
    >
      {/* Desktop Sidebar — hidden on mobile */}
      <div className="hidden md:flex flex-shrink-0">
        <ShellSidebar />
      </div>

      {/* Mobile Top Bar — visible on mobile only */}
      <div className="flex flex-col w-full min-w-0 h-full overflow-hidden md:flex-row">
        <ShellTopbar title={title} />

        {/* Main Content */}
        <main
          className={cn(
            "flex-1 min-w-0 flex flex-col overflow-hidden",
            "bg-[var(--surface-bg)]",
          )}
        >
          {children}
        </main>
      </div>

      {/* Desktop Right Panel — rendered outside flex flow on mobile */}
      <div className="hidden md:flex flex-shrink-0">
        <ShellRightPanel />
      </div>

      {/* Mobile Drawer — portal overlay, mobile only */}
      <ShellMobileDrawer />
    </div>
  );
}
