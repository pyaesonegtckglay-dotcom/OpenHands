import React from "react";
import { NavLink, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import {
  MessageSquare,
  ListTodo,
  Brain,
  FolderOpen,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { useAppShellStore, SidebarSection } from "./app-shell-store";
import { ConversationPanel } from "../conversation-panel/conversation-panel";
import { UserActions } from "../sidebar/user-actions";
import { useGitUser } from "#/hooks/query/use-git-user";

interface NavItem {
  id: SidebarSection;
  icon: React.ReactNode;
  label: string;
  href?: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "chat",
    icon: <MessageSquare size={18} />,
    label: "Chat",
  },
  {
    id: "tasks",
    icon: <ListTodo size={18} />,
    label: "Tasks",
  },
  {
    id: "memory",
    icon: <Brain size={18} />,
    label: "Memory",
  },
  {
    id: "files",
    icon: <FolderOpen size={18} />,
    label: "Files",
  },
  {
    id: "settings",
    icon: <Settings size={18} />,
    label: "Settings",
    href: "/settings",
  },
];

export function ShellSidebar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useGitUser();

  const {
    sidebarCollapsed,
    toggleSidebar,
    activeSidebarSection,
    setActiveSidebarSection,
  } = useAppShellStore();

  const isCollapsed = sidebarCollapsed;

  const handleNavClick = (item: NavItem) => {
    setActiveSidebarSection(item.id);
    if (item.href) {
      navigate(item.href);
    }
  };

  const handleNewConversation = () => {
    navigate("/");
  };

  return (
    <aside
      data-testid="shell-sidebar"
      className={cn(
        "flex flex-col h-full bg-[var(--surface-sidebar)] border-r border-[var(--surface-border)]",
        "transition-all duration-300 ease-in-out overflow-hidden",
        isCollapsed ? "w-14" : "w-[260px]",
      )}
    >
      {/* Header */}
      <div
        className={cn(
          "flex items-center h-14 px-3 border-b border-[var(--surface-border)] flex-shrink-0",
          isCollapsed ? "justify-center" : "justify-between",
        )}
      >
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-[var(--brand-primary)] flex items-center justify-center">
              <span className="text-[11px] font-bold text-black">M</span>
            </div>
            <span className="text-sm font-semibold text-[var(--text-primary)] truncate">
              ManusAI
            </span>
          </div>
        )}
        {isCollapsed && (
          <div className="w-7 h-7 rounded-md bg-[var(--brand-primary)] flex items-center justify-center">
            <span className="text-[11px] font-bold text-black">M</span>
          </div>
        )}
        {!isCollapsed && (
          <button
            type="button"
            onClick={toggleSidebar}
            className="p-1.5 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-sidebar-hover)] transition-colors"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft size={15} />
          </button>
        )}
      </div>

      {/* New Conversation Button */}
      <div className={cn("px-2 pt-3 pb-1 flex-shrink-0")}>
        <button
          type="button"
          onClick={handleNewConversation}
          className={cn(
            "flex items-center gap-2 rounded-md transition-colors w-full",
            "bg-[var(--brand-primary-muted)] hover:bg-[var(--surface-sidebar-hover)]",
            "text-[var(--brand-primary)] hover:text-[var(--text-primary)]",
            "border border-[var(--brand-primary)] border-opacity-30",
            isCollapsed ? "justify-center p-2" : "px-3 py-2",
          )}
          aria-label="New conversation"
        >
          <Plus size={15} />
          {!isCollapsed && (
            <span className="text-xs font-medium">New Chat</span>
          )}
        </button>
      </div>

      {/* Nav Items */}
      <nav className="flex flex-col gap-0.5 px-2 pt-2 flex-shrink-0">
        {NAV_ITEMS.map((item) => {
          const isActive = activeSidebarSection === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNavClick(item)}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors cursor-pointer",
                "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
                "hover:bg-[var(--surface-sidebar-hover)]",
                isActive &&
                  "bg-[var(--surface-sidebar-active)] text-[var(--text-primary)]",
                isCollapsed && "justify-center px-2",
              )}
              aria-label={item.label}
              title={isCollapsed ? item.label : undefined}
            >
              <span
                className={cn(
                  "flex-shrink-0 transition-colors",
                  isActive && "text-[var(--brand-primary)]",
                )}
              >
                {item.icon}
              </span>
              {!isCollapsed && (
                <span className="text-[13px] font-medium truncate">
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Conversation List (when Chat section active and not collapsed) */}
      {!isCollapsed && activeSidebarSection === "chat" && (
        <div className="flex-1 overflow-hidden mt-2 min-h-0">
          <ConversationPanel onClose={() => {}} />
        </div>
      )}

      {/* Spacer when collapsed or non-chat section */}
      {(isCollapsed || activeSidebarSection !== "chat") && (
        <div className="flex-1" />
      )}

      {/* Footer */}
      <div
        className={cn(
          "flex items-center border-t border-[var(--surface-border)] px-2 py-3 flex-shrink-0",
          isCollapsed ? "justify-center flex-col gap-2" : "justify-between",
        )}
      >
        {/* Expand button when collapsed */}
        {isCollapsed && (
          <button
            type="button"
            onClick={toggleSidebar}
            className="p-1.5 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-sidebar-hover)] transition-colors"
            aria-label="Expand sidebar"
          >
            <ChevronRight size={15} />
          </button>
        )}

        {/* User Avatar */}
        <div className={cn(isCollapsed ? "w-full flex justify-center" : "")}>
          <UserActions user={user.data ?? undefined} isLoading={user.isLoading} />
        </div>
      </div>
    </aside>
  );
}
