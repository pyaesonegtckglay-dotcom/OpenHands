import React from "react";
import { PanelRightClose, PanelRightOpen, Activity } from "lucide-react";
import { cn } from "#/utils/utils";
import { useAppShellStore } from "./app-shell-store";
import { useAgentStore } from "#/stores/agent-store";
import { AgentState } from "#/types/agent-state";
import { ConversationTabs } from "../conversation/conversation-tabs/conversation-tabs";
import { ConversationTabContent } from "../conversation/conversation-tabs/conversation-tab-content/conversation-tab-content";

function getStatusLabel(state: AgentState): string {
  switch (state) {
    case AgentState.RUNNING:
      return "Running";
    case AgentState.AWAITING_USER_INPUT:
      return "Waiting";
    case AgentState.PAUSED:
      return "Paused";
    case AgentState.STOPPED:
      return "Stopped";
    case AgentState.FINISHED:
      return "Done";
    case AgentState.ERROR:
      return "Error";
    case AgentState.RATE_LIMITED:
      return "Rate Limited";
    case AgentState.LOADING:
    case AgentState.INIT:
      return "Loading";
    default:
      return "Idle";
  }
}

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

export function ShellRightPanel() {
  const { rightPanelOpen, toggleRightPanel } = useAppShellStore();
  const { curAgentState } = useAgentStore();

  const statusLabel = getStatusLabel(curAgentState);
  const statusColor = getStatusColor(curAgentState);
  const isActive = curAgentState === AgentState.RUNNING;

  return (
    <div className="relative flex items-stretch">
      {/* Toggle button — always visible */}
      <div className="flex flex-col items-center justify-start pt-4 px-1 border-l border-[var(--surface-border)] bg-[var(--surface-sidebar)]">
        <button
          type="button"
          onClick={toggleRightPanel}
          className={cn(
            "p-1.5 rounded-md transition-colors group",
            "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
            "hover:bg-[var(--surface-sidebar-hover)]",
          )}
          aria-label={rightPanelOpen ? "Close activity panel" : "Open activity panel"}
          title={rightPanelOpen ? "Close activity panel" : "Open activity panel"}
        >
          {/* Activity indicator dot */}
          <span className="relative flex items-center justify-center">
            {isActive && (
              <span
                className="absolute inset-0 rounded-full animate-ping opacity-60"
                style={{ background: statusColor }}
              />
            )}
            <span
              className="relative w-2 h-2 rounded-full mb-1 block"
              style={{ background: statusColor }}
            />
          </span>
          {rightPanelOpen ? (
            <PanelRightClose size={16} />
          ) : (
            <PanelRightOpen size={16} />
          )}
        </button>

        {/* Status label rotated */}
        {!rightPanelOpen && (
          <span
            className="text-[10px] font-medium mt-2 rotate-90 whitespace-nowrap origin-center"
            style={{ color: statusColor }}
          >
            {statusLabel}
          </span>
        )}
      </div>

      {/* Panel content */}
      <div
        className={cn(
          "flex flex-col overflow-hidden transition-all duration-300 ease-in-out",
          "bg-[var(--surface-sidebar)] border-l border-[var(--surface-border)]",
          rightPanelOpen ? "w-80 opacity-100" : "w-0 opacity-0 pointer-events-none",
        )}
      >
        {/* Panel Header */}
        <div className="flex items-center justify-between px-4 h-14 border-b border-[var(--surface-border)] flex-shrink-0">
          <div className="flex items-center gap-2">
            <Activity size={15} className="text-[var(--text-secondary)]" />
            <span className="text-[13px] font-semibold text-[var(--text-primary)]">
              Activity
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="text-[11px] font-medium px-2 py-0.5 rounded-full"
              style={{
                color: statusColor,
                background: `${statusColor}1a`,
              }}
            >
              {statusLabel}
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-3 pt-3 flex-shrink-0">
          <ConversationTabs />
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden px-3 pb-3">
          <ConversationTabContent />
        </div>
      </div>
    </div>
  );
}
