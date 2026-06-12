import { create } from "zustand";
import { ExecutionEvent, ExecutionReport } from "@/lib/api";

export type ExecutionStatus =
  | "idle"
  | "starting"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface ExecutionState {
  // Current execution
  executionId: string | null;
  goal: string;
  status: ExecutionStatus;
  events: ExecutionEvent[];
  report: ExecutionReport | null;
  isStreaming: boolean;

  // History
  history: HistoryItem[];

  // Actions
  setGoal: (goal: string) => void;
  startExecution: (executionId: string, goal: string) => void;
  addEvent: (event: ExecutionEvent) => void;
  setReport: (report: ExecutionReport) => void;
  setStatus: (status: ExecutionStatus) => void;
  stopStreaming: () => void;
  reset: () => void;
  setHistory: (history: HistoryItem[]) => void;
}

export interface HistoryItem {
  id: string;
  goal: string;
  status: string;
  created_at: string;
  completed_at?: string;
}

export const useExecutionStore = create<ExecutionState>((set) => ({
  executionId: null,
  goal: "",
  status: "idle",
  events: [],
  report: null,
  isStreaming: false,
  history: [],

  setGoal: (goal) => set({ goal }),

  startExecution: (executionId, goal) =>
    set({
      executionId,
      goal,
      status: "starting",
      events: [],
      report: null,
      isStreaming: true,
    }),

  addEvent: (event) =>
    set((state) => ({
      events: [...state.events, event],
    })),

  setReport: (report) => set({ report }),

  setStatus: (status) => set({ status }),

  stopStreaming: () => set({ isStreaming: false }),

  reset: () =>
    set({
      executionId: null,
      goal: "",
      status: "idle",
      events: [],
      report: null,
      isStreaming: false,
    }),

  setHistory: (history) => set({ history }),
}));
