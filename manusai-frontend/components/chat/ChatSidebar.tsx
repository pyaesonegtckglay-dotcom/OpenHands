"use client";
import { useEffect } from "react";
import { Plus, MessageSquare, Loader2 } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { Conversation } from "@/types";

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function ChatSidebar() {
  const { conversations, currentConversationId, isLoading, loadConversations, loadMessages, newConversation } = useChatStore();

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      <div className="p-3 border-b border-gray-800">
        <button
          onClick={newConversation}
          className="w-full flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {isLoading && conversations.length === 0 && (
          <div className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
          </div>
        )}

        {conversations.length === 0 && !isLoading && (
          <div className="text-center text-gray-600 text-sm py-8">
            No conversations yet
          </div>
        )}

        {conversations.map((conv: Conversation) => (
          <button
            key={conv.id}
            onClick={() => loadMessages(conv.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors group ${
              currentConversationId === conv.id
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <div className="flex items-start gap-2">
              <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium truncate">{conv.title}</p>
                <p className="text-xs text-gray-600 mt-0.5">{formatDate(conv.created_at)}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
