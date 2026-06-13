"use client";
import { create } from "zustand";
import { Message, Conversation } from "@/types";
import { chatAPI } from "@/lib/api";

interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  isSending: boolean;
  error: string | null;
  loadConversations: () => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  setCurrentConversation: (id: string | null) => void;
  newConversation: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  isLoading: false,
  isSending: false,
  error: null,

  loadConversations: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await chatAPI.getConversations();
      set({ conversations: res.data.conversations, isLoading: false });
    } catch (err: any) {
      set({ error: "Failed to load conversations", isLoading: false });
    }
  },

  loadMessages: async (conversationId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await chatAPI.getMessages(conversationId);
      set({ messages: res.data, currentConversationId: conversationId, isLoading: false });
    } catch (err: any) {
      set({ error: "Failed to load messages", isLoading: false });
    }
  },

  sendMessage: async (content) => {
    const { currentConversationId } = get();
    set({ isSending: true, error: null });
    try {
      const res = await chatAPI.sendMessage(content, currentConversationId ?? undefined);
      const newMessages: Message[] = res.data;
      const convId = newMessages[0]?.conversation_id;

      set((state) => ({
        messages: [...state.messages, ...newMessages],
        currentConversationId: convId || state.currentConversationId,
        isSending: false,
      }));

      // Refresh conversations list
      const convRes = await chatAPI.getConversations();
      set({ conversations: convRes.data.conversations });
    } catch (err: any) {
      set({ error: "Failed to send message", isSending: false });
    }
  },

  setCurrentConversation: (id) => {
    set({ currentConversationId: id, messages: [] });
  },

  newConversation: () => {
    set({ currentConversationId: null, messages: [] });
  },
}));
