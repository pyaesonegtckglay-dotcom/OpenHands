"use client";
import { create } from "zustand";
import { TaskGraph, GraphListItem, CreateGraphResponse } from "@/types";
import { taskGraphAPI } from "@/lib/api";

interface TaskGraphState {
  graphs: GraphListItem[];
  currentGraph: TaskGraph | null;
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;
  viewMode: "tree" | "dependencies" | "waves";

  loadGraphs: () => Promise<void>;
  loadGraph: (graphId: string) => Promise<void>;
  createGraph: (planId: string) => Promise<CreateGraphResponse | null>;
  setViewMode: (mode: "tree" | "dependencies" | "waves") => void;
  clearError: () => void;
}

export const useTaskGraphStore = create<TaskGraphState>((set, get) => ({
  graphs: [],
  currentGraph: null,
  isLoading: false,
  isCreating: false,
  error: null,
  viewMode: "tree",

  loadGraphs: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await taskGraphAPI.list();
      set({ graphs: res.data.graphs, isLoading: false });
    } catch (err: any) {
      set({ error: "Failed to load task graphs", isLoading: false });
    }
  },

  loadGraph: async (graphId: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await taskGraphAPI.get(graphId);
      set({ currentGraph: res.data, isLoading: false });
    } catch (err: any) {
      set({ error: "Failed to load task graph", isLoading: false });
    }
  },

  createGraph: async (planId: string) => {
    set({ isCreating: true, error: null });
    try {
      const res = await taskGraphAPI.create(planId);
      const data: CreateGraphResponse = res.data;
      set({ isCreating: false });
      // Refresh list
      get().loadGraphs();
      return data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to create task graph";
      set({ error: msg, isCreating: false });
      return null;
    }
  },

  setViewMode: (mode) => set({ viewMode: mode }),
  clearError: () => set({ error: null }),
}));
