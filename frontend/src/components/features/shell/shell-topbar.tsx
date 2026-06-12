import React from "react";
import { Menu, Activity } from "lucide-react";
import { cn } from "#/utils/utils";
import { useAppShellStore } from "./app-shell-store";
import { useAgentStore } from "#/stores/agent-store";
import { AgentState } from "#/types/agent-state";

function getStatusColor(state: AgentState): string {
  switch (state) {
    case AgentState.RUNNING:
      return "var(--status-active)";
    case AgentState.AWAITING_USER_INPUT:
    case AgentState.AWAITING_USER_CONFIRMATION:
      return "var(--status-warning)";
    case AgentState.ERROR:
    case AgentState.REJECTED:
      return "var(--status-error)";
    case AgentState.FINISHED:
      return "var(--status-success)";
    default:
      return "var(--status-idle)";
  }
}

interface ShellTopbarProps {
  title?: string;
}

export function ShellTopbar({ title = "ManusAI" }: ShellTopbarProps) {
  const { toggleMobileDrawer, toggleRightPanel, rightPanelOpen } =
    useAppShellStore();
  const { curAgentState } = useAgentStore();

  const statusColor = getStatusColor(curAgentState);
  const isActive = curAgentState === AgentState.RUNNING;

  return (
    <header
      data-testid="shell-topbar"
      className={cn(
        "flex items-center justify-between h-13 px-4",
        "bg-[var(--surface-sidebar)] border-b border-[var(--surface-border)]",
        "flex-shrink-0 md:hidden",
      )}
    >
      {/* Left: Menu button */}
      <button
        type="button"
        onClick={toggleMobileDrawer}
        className={cn(
          "p-2 rounded-md -ml-2",
          "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
          "hover:bg-[var(--surface-sidebar-hover)] transition-colors",
        )}
        aria-label="Open navigation"
      >
        <Menu size={18} />
      </button>

      {/* Center: Title */}
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-md bg-[var(--brand-primary)] flex items-center justify-center">
          <span className="text-[10px] font-bold text-black">M</span>
        </div>
        <span className="text-sm font-semibold text-[var(--text-primary)]">
          {title}
        </span>
      </div>

      {/* Right: Activity panel toggle */}
      <button
        type="button"
        onClick={toggleRightPanel}
        className={cn(
          "p-2 rounded-md -mr-2 relative",
          "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
          "hover:bg-[var(--surface-sidebar-hover)] transition-colors",
          rightPanelOpen && "text-[var(--brand-primary)]",
        )}
        aria-label="Toggle activity panel"
      >
        {/* Active indicator dot */}
        {isActive && (
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{ background: statusColor }}
          >
            <span
              className="absolute inset-0 rounded-full animate-ping"
              style={{ background: statusColor, opacity: 0.6 }}
            />
          </span>
        )}
        <Activity size={18} />
      </button>
    </header>
  );
}
