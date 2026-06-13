"use client";
import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare, CheckSquare, Brain, FolderOpen, Settings, LogOut, Zap, Cpu, Network
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";

const navItems: { href: string; icon: React.ElementType; label: string; active: boolean; badge?: string }[] = [
  { href: "/chat", icon: MessageSquare, label: "Chat", active: true },
  { href: "/cognitive", icon: Cpu, label: "Cognitive", active: true, badge: "P1" },
  { href: "/taskgraph", icon: Network, label: "Task Graph", active: true, badge: "P2" },
  { href: "/tasks", icon: CheckSquare, label: "Tasks", active: false },
  { href: "/memory", icon: Brain, label: "Memory", active: false },
  { href: "/files", icon: FolderOpen, label: "Files", active: false },
  { href: "/settings", icon: Settings, label: "Settings", active: false },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-white font-bold text-lg leading-none">ManusAI</h1>
            <p className="text-gray-500 text-xs">Phase 2</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.active ? item.href : "#"}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive && item.active
                  ? "bg-blue-600 text-white"
                  : item.active
                  ? "text-gray-400 hover:text-white hover:bg-gray-800"
                  : "text-gray-600 cursor-not-allowed"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
              {item.badge && (
                <span className="ml-auto text-xs bg-purple-800 text-purple-200 px-1.5 py-0.5 rounded">
                  {item.badge}
                </span>
              )}
              {!item.active && !item.badge && (
                <span className="ml-auto text-xs text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">
                  Soon
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User info + logout */}
      <div className="p-3 border-t border-gray-800">
        <div className="flex items-center justify-between px-3 py-2">
          <div className="min-w-0">
            <p className="text-white text-sm font-medium truncate">{user?.username}</p>
            <p className="text-gray-500 text-xs truncate">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-gray-800 rounded-lg transition-colors ml-2"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
