/**
 * Multi-Agent Standalone Page
 * Standalone page for multi-agent orchestration - no conversation context required
 */

import React from "react";
import { Link } from "react-router";
import { ArrowLeft, Settings, Users } from "lucide-react";
import { MultiAgentChat } from "#/components/features/multi-agent";

export default function MultiAgentStandalonePage() {
  return (
    <div className="flex flex-col h-screen w-full bg-[#0F0F0F]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-[#26282D] bg-[#0A0A0A]">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 text-[#9CA3AF] hover:text-white transition-colors"
          >
            <ArrowLeft size={18} />
            <span className="text-sm">Back</span>
          </Link>
          <div className="flex items-center gap-2">
            <Users size={20} className="text-[#8B5CF6]" />
            <h1 className="text-lg font-semibold text-white">
              Multi-Agent Orchestration
            </h1>
          </div>
        </div>
        <Link
          to="/settings"
          className="p-2 rounded-lg text-[#9CA3AF] hover:text-white hover:bg-[#26282D] transition-colors"
        >
          <Settings size={18} />
        </Link>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <MultiAgentChat />
      </main>
    </div>
  );
}