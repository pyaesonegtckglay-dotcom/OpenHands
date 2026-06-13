import React from "react";
import { useNavigate } from "react-router";
import {
  MessageSquare,
  ListTodo,
  Brain,
  FolderOpen,
  Settings,
  Plus,
  X,
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

export function ShellMobileDrawer() {
  const navigate = useNavigate();
  const user = useGitUser();

  const {
    mobileDrawerOpen,
    setMobileDrawerOpen,
    activeSidebarSection,
    setActiveSidebarSection,
  } = useAppShellStore();

  const handleClose = () => setMobileDrawerOpen(false);

  const handleNavClick = (item: NavItem) => {
    setActiveSidebarSection(item.id);
    if (item.href) {
      navigate(item.href);
      handleClose();
    }
  };

  const handleNewConversation = () => {
    navigate("/");
    handleClose();
  };

  if (!mobileDrawerOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 md:hidden"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        data-testid="shell-mobile-drawer"
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 flex flex-col",
          "bg-[var(--surface-sidebar)] border-r border-[var(--surface-border)]",
          "shadow-2xl md:hidden",
          "animate-in slide-in-from-left duration-200",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between h-14 px-4 border-b border-[var(--surface-border)] flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-[var(--brand-primary)] flex items-center justify-center">
              <span className="text-[11px] font-bold text-black">M</span>
            </div>
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              ManusAI
            </span>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className={cn(
              "p-1.5 rounded-md",
              "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              "hover:bg-[var(--surface-sidebar-hover)] transition-colors",
            )}
            aria-label="Close navigation"
          >
            <X size={16} />
          </button>
        </div>

        {/* New Conversation Button */}
        <div className="px-3 pt-3 pb-1 flex-shrink-0">
          <button
            type="button"
            onClick={handleNewConversation}
            className={cn(
              "flex items-center gap-2 rounded-md transition-colors w-full px-3 py-2",
              "bg-[var(--brand-primary-muted)] hover:bg-[var(--surface-sidebar-hover)]",
              "text-[var(--brand-primary)] hover:text-[var(--text-primary)]",
              "border border-[var(--brand-primary)] border-opacity-30",
            )}
          >
            <Plus size={15} />
            <span className="text-xs font-medium">New Chat</span>
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
                  "flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors cursor-pointer w-full",
                  "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
                  "hover:bg-[var(--surface-sidebar-hover)]",
                  isActive &&
                    "bg-[var(--surface-sidebar-active)] text-[var(--text-primary)]",
                )}
              >
                <span
                  className={cn(
                    "flex-shrink-0 transition-colors",
                    isActive && "text-[var(--brand-primary)]",
                  )}
                >
                  {item.icon}
                </span>
                <span className="text-[13px] font-medium">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Conversation List (when Chat section active) */}
        {activeSidebarSection === "chat" && (
          <div className="flex-1 overflow-hidden mt-2 min-h-0">
            <ConversationPanel onClose={handleClose} />
          </div>
        )}

        {activeSidebarSection !== "chat" && <div className="flex-1" />}

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[var(--surface-border)] px-4 py-3 flex-shrink-0">
          <UserActions
            user={user.data ?? undefined}
            isLoading={user.isLoading}
          />
        </div>
      </div>
    </>
  );
}
