"use client";
import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  MessageSquare, Brain, FolderOpen, Settings, LogOut, Zap,
  Cpu, Network, ChevronLeft, ChevronRight, Menu, X,
  Plus, Loader2, Activity, CheckSquare
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useAppShellStore } from "@/store/appShellStore";
import { useChatStore } from "@/store/chatStore";
import { Conversation } from "@/types";

// ─── Date formatter ───────────────────────────────────────────────────────────
function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

// ─── Nav items ────────────────────────────────────────────────────────────────
const PRIMARY_NAV = [
  { href: "/chat", icon: MessageSquare, label: "Chat", active: true },
  { href: "/execution", icon: Activity, label: "Execute", active: true, badge: "NEW" },
  { href: "/cognitive", icon: Cpu, label: "Cognitive", active: true, badge: "AI" },
  { href: "/taskgraph", icon: Network, label: "Task Graph", active: true, badge: "AI" },
];

const SECONDARY_NAV = [
  { href: "/tasks", icon: CheckSquare, label: "Tasks", active: false },
  { href: "/memory", icon: Brain, label: "Memory", active: false },
  { href: "/files", icon: FolderOpen, label: "Files", active: false },
  { href: "/settings", icon: Settings, label: "Settings", active: false },
];

// ─── Sidebar ──────────────────────────────────────────────────────────────────
function Sidebar({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { sidebarCollapsed, toggleSidebar } = useAppShellStore();
  const { conversations, currentConversationId, isLoading, loadConversations, loadMessages, newConversation } = useChatStore();

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const isChatActive = pathname.startsWith("/chat");

  const handleNewChat = () => {
    newConversation();
    if (!pathname.startsWith("/chat")) router.push("/chat");
    onClose?.();
  };

  const handleLoadConversation = (id: string) => {
    loadMessages(id);
    if (!pathname.startsWith("/chat")) router.push("/chat");
    onClose?.();
  };

  return (
    <div
      className={`flex flex-col h-full bg-[#111318] border-r border-[#1e2128] transition-all duration-300 ease-in-out ${
        sidebarCollapsed ? "w-14" : "w-64"
      }`}
    >
      {/* Logo + collapse toggle */}
      <div className={`flex items-center border-b border-[#1e2128] ${sidebarCollapsed ? "justify-center p-3" : "justify-between px-4 py-3"}`}>
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-violet-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-white font-semibold text-base tracking-tight">ManusAI</span>
          </div>
        )}
        {sidebarCollapsed && (
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-violet-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
        )}
        <button
          onClick={onClose ?? toggleSidebar}
          className={`p-1 text-gray-500 hover:text-gray-300 hover:bg-[#1e2128] rounded-md transition-colors ${sidebarCollapsed ? "hidden" : ""}`}
          title="Collapse sidebar"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat button */}
      <div className={`p-2 border-b border-[#1e2128] ${sidebarCollapsed ? "flex justify-center" : ""}`}>
        <button
          onClick={handleNewChat}
          className={`flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors ${
            sidebarCollapsed ? "w-9 h-9 justify-center" : "w-full px-3 py-2"
          }`}
          title="New Chat"
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          {!sidebarCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Primary nav */}
      <nav className={`p-2 space-y-0.5 ${sidebarCollapsed ? "flex flex-col items-center" : ""}`}>
        {PRIMARY_NAV.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.active ? item.href : "#"}
              onClick={onClose}
              title={sidebarCollapsed ? item.label : undefined}
              className={`flex items-center gap-3 rounded-lg text-sm transition-colors ${
                sidebarCollapsed ? "w-9 h-9 justify-center" : "px-3 py-2"
              } ${
                isActive && item.active
                  ? "bg-[#1e2128] text-white"
                  : item.active
                  ? "text-gray-400 hover:text-white hover:bg-[#1e2128]"
                  : "text-gray-600 cursor-not-allowed"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!sidebarCollapsed && (
                <>
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="text-[10px] bg-blue-600/20 text-blue-400 border border-blue-600/30 px-1.5 py-0.5 rounded-full font-medium">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Conversation history (only in expanded mode, when on chat) */}
      {!sidebarCollapsed && isChatActive && (
        <div className="flex-1 overflow-y-auto px-2 py-1 min-h-0">
          <p className="text-[10px] text-gray-600 uppercase tracking-widest px-3 py-1.5 font-medium">Recent Chats</p>
          {isLoading && conversations.length === 0 && (
            <div className="flex justify-center py-4">
              <Loader2 className="w-4 h-4 text-gray-600 animate-spin" />
            </div>
          )}
          {conversations.length === 0 && !isLoading && (
            <p className="text-xs text-gray-600 px-3 py-2">No conversations yet</p>
          )}
          <div className="space-y-0.5">
            {conversations.map((conv: Conversation) => (
              <button
                key={conv.id}
                onClick={() => handleLoadConversation(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors group text-xs ${
                  currentConversationId === conv.id
                    ? "bg-[#1e2128] text-white"
                    : "text-gray-500 hover:bg-[#1e2128] hover:text-gray-200"
                }`}
              >
                <p className="truncate font-medium">{conv.title}</p>
                <p className="text-gray-600 text-[10px] mt-0.5">{formatDate(conv.created_at)}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Spacer when not in chat or collapsed */}
      {(sidebarCollapsed || !isChatActive) && <div className="flex-1" />}

      {/* Secondary nav */}
      <div className={`p-2 border-t border-[#1e2128] space-y-0.5 ${sidebarCollapsed ? "flex flex-col items-center" : ""}`}>
        {SECONDARY_NAV.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.active ? item.href : "#"}
              onClick={onClose}
              title={sidebarCollapsed ? item.label : undefined}
              className={`flex items-center gap-3 rounded-lg text-sm transition-colors ${
                sidebarCollapsed ? "w-9 h-9 justify-center" : "px-3 py-2"
              } ${
                item.active
                  ? "text-gray-400 hover:text-white hover:bg-[#1e2128]"
                  : "text-gray-700 cursor-not-allowed"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!sidebarCollapsed && (
                <>
                  <span className="flex-1">{item.label}</span>
                  {!item.active && (
                    <span className="text-[10px] text-gray-700 bg-[#1e2128] px-1.5 py-0.5 rounded">
                      Soon
                    </span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </div>

      {/* User profile */}
      <div className={`border-t border-[#1e2128] p-2 ${sidebarCollapsed ? "flex flex-col items-center gap-2" : ""}`}>
        {!sidebarCollapsed ? (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#1e2128] group">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-violet-600 rounded-full flex items-center justify-center text-xs font-semibold text-white flex-shrink-0">
              {user?.username?.charAt(0).toUpperCase() || "M"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-medium truncate">{user?.username}</p>
              <p className="text-gray-600 text-[10px] truncate">{user?.email}</p>
            </div>
            <button
              onClick={logout}
              className="p-1 text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
              title="Logout"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <>
            <div
              className="w-7 h-7 bg-gradient-to-br from-blue-500 to-violet-600 rounded-full flex items-center justify-center text-xs font-semibold text-white cursor-default"
              title={user?.username || ""}
            >
              {user?.username?.charAt(0).toUpperCase() || "M"}
            </div>
            <button
              onClick={logout}
              className="w-9 h-9 flex items-center justify-center text-gray-600 hover:text-red-400 hover:bg-[#1e2128] rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Mobile Drawer ────────────────────────────────────────────────────────────
function MobileDrawer() {
  const { mobileMenuOpen, setMobileMenuOpen } = useAppShellStore();

  if (!mobileMenuOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={() => setMobileMenuOpen(false)}
      />
      {/* Drawer */}
      <div className="fixed inset-y-0 left-0 z-50 w-72 bg-[#111318] border-r border-[#1e2128] flex flex-col animate-in slide-in-from-left duration-200">
        <Sidebar onClose={() => setMobileMenuOpen(false)} />
      </div>
    </>
  );
}

// ─── Mobile Top Bar ───────────────────────────────────────────────────────────
function MobileTopBar({ title }: { title?: string }) {
  const { setMobileMenuOpen } = useAppShellStore();

  return (
    <div className="lg:hidden flex items-center justify-between px-4 py-3 bg-[#111318] border-b border-[#1e2128] flex-shrink-0">
      <button
        onClick={() => setMobileMenuOpen(true)}
        className="p-1.5 text-gray-400 hover:text-white hover:bg-[#1e2128] rounded-lg transition-colors"
      >
        <Menu className="w-5 h-5" />
      </button>
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-violet-600 rounded-md flex items-center justify-center">
          <Zap className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="text-white font-semibold text-sm">{title || "ManusAI"}</span>
      </div>
      <div className="w-8" />
    </div>
  );
}

// ─── Collapse toggle for expanded sidebar ────────────────────────────────────
function SidebarExpandButton() {
  const { sidebarCollapsed, toggleSidebar } = useAppShellStore();
  if (!sidebarCollapsed) return null;

  return (
    <button
      onClick={toggleSidebar}
      className="hidden lg:flex absolute left-14 top-1/2 -translate-y-1/2 z-10 w-5 h-10 bg-[#1e2128] border border-[#2e3138] rounded-r-md items-center justify-center text-gray-500 hover:text-white transition-colors"
      title="Expand sidebar"
    >
      <ChevronRight className="w-3 h-3" />
    </button>
  );
}

// ─── Main AppShell ────────────────────────────────────────────────────────────
interface AppShellProps {
  children: React.ReactNode;
  title?: string;
}

export default function AppShell({ children, title }: AppShellProps) {
  const { isAuthenticated, loadFromStorage } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (!isAuthenticated) {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      if (!token) {
        router.push("/login");
      }
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated && typeof window !== "undefined" && !localStorage.getItem("token")) {
    return null;
  }

  // Derive page title from pathname
  const pageTitle =
    title ||
    (pathname.startsWith("/chat") ? "Chat" :
     pathname.startsWith("/cognitive") ? "Cognitive Inspector" :
     pathname.startsWith("/taskgraph") ? "Task Graph" :
     pathname.startsWith("/settings") ? "Settings" :
     "ManusAI");

  return (
    <div className="flex h-screen w-screen bg-[#0d0f13] overflow-hidden">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex flex-shrink-0 relative">
        <Sidebar />
        <SidebarExpandButton />
      </div>

      {/* Mobile Drawer */}
      <MobileDrawer />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <MobileTopBar title={pageTitle} />

        {/* Page content */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
