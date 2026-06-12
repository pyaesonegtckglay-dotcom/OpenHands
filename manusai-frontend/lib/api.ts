import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to all requests
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  register: (email: string, username: string, password: string) =>
    api.post("/api/v1/auth/register", { email, username, password }),
  login: (email: string, password: string) =>
    api.post("/api/v1/auth/login", { email, password }),
  logout: () => api.post("/api/v1/auth/logout"),
  me: () => api.get("/api/v1/auth/me"),
};

// Chat
export const chatAPI = {
  sendMessage: (content: string, conversation_id?: string) =>
    api.post("/api/v1/chat/message", { content, conversation_id }),
  getConversations: () => api.get("/api/v1/chat/conversations"),
  getMessages: (conversationId: string) =>
    api.get(`/api/v1/chat/conversations/${conversationId}/messages`),
};

// Status
export const statusAPI = {
  health: () => api.get("/api/v1/status/health"),
  services: () => api.get("/api/v1/status/services"),
};

// Phase 2: Task Graph
export const taskGraphAPI = {
  create: (plan_id: string) =>
    api.post("/api/v1/taskgraph/create", { plan_id }),
  get: (graph_id: string) =>
    api.get(`/api/v1/taskgraph/${graph_id}`),
  getWaves: (graph_id: string) =>
    api.get(`/api/v1/taskgraph/${graph_id}/waves`),
  list: (limit = 20, offset = 0) =>
    api.get(`/api/v1/taskgraph/list?limit=${limit}&offset=${offset}`),
};

// Phase 2: Streaming Chat (SSE) with AbortSignal support
export const streamChat = async (
  content: string,
  conversationId: string | null,
  onToken: (token: string) => void,
  onDone: (convId: string, msgId: string) => void,
  onError: (err: string) => void,
  signal?: AbortSignal,
): Promise<void> => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/v1/stream/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        content,
        conversation_id: conversationId || undefined,
      }),
      signal,
    });
  } catch (err: unknown) {
    const e = err as { name?: string };
    if (e?.name === "AbortError") return;
    onError("Network error — please check your connection.");
    return;
  }

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
      return;
    }
    onError(`Server error: ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response stream available");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        reader.cancel();
        return;
      }

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;

        const raw = trimmed.slice(6).trim();
        if (!raw || raw === "[KEEPALIVE]") continue;

        try {
          const evt = JSON.parse(raw);

          if (evt.type === "token" && evt.text != null) {
            onToken(evt.text);
          } else if (evt.type === "done") {
            onDone(evt.conversation_id ?? "", evt.message_id ?? "");
            return;
          } else if (evt.type === "error") {
            onError(evt.message ?? "Stream error");
            return;
          }
        } catch {
          // Ignore malformed JSON lines in stream
        }
      }
    }
  } catch (err: unknown) {
    const e = err as { name?: string };
    if (e?.name === "AbortError") return;
    onError("Stream connection interrupted.");
  } finally {
    try { reader.cancel(); } catch { /* ignore */ }
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3: Execution API
// ─────────────────────────────────────────────────────────────────────────────

export const executionAPI = {
  start: (goal: string) =>
    api.post("/api/v1/execution/start", { goal }),
  stop: (execution_id: string) =>
    api.post("/api/v1/execution/stop", { execution_id }),
  get: (execution_id: string) =>
    api.get(`/api/v1/execution/${execution_id}`),
  getReport: (execution_id: string) =>
    api.get(`/api/v1/execution/${execution_id}/report`),
  getTasks: (execution_id: string) =>
    api.get(`/api/v1/execution/${execution_id}/tasks`),
  getEvidence: (execution_id: string) =>
    api.get(`/api/v1/execution/${execution_id}/evidence`),
  getArtifacts: (execution_id: string) =>
    api.get(`/api/v1/execution/${execution_id}/artifacts`),
  downloadFile: (execution_id: string, filename: string) =>
    `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/execution/${execution_id}/files/${filename}`,
  executeDirect: (goal: string) =>
    api.post("/api/v1/execution/execute-direct", { goal }),
  routeTest: (goal: string) =>
    api.post("/api/v1/execution/tools/route-test", { goal }),
  getWorkspaceFiles: () =>
    api.get("/api/v1/execution/workspace/files"),
  getHistory: (limit = 20, offset = 0) =>
    api.get(`/api/v1/execution/history?limit=${limit}&offset=${offset}`),
  getTools: () =>
    api.get("/api/v1/execution/tools/registry"),
  getMonitorStats: () =>
    api.get("/api/v1/execution/monitor/stats"),
};

// Phase 3: Subscribe to execution event stream (SSE)
export const streamExecutionEvents = (
  execution_id: string,
  onEvent: (event: ExecutionEvent) => void,
  onClose: () => void,
  signal?: AbortSignal,
): (() => void) => {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  let closed = false;

  const connect = async () => {
    try {
      const res = await fetch(
        `${BASE_URL}/api/v1/execution/${execution_id}/events`,
        {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            Accept: "text/event-stream",
          },
          signal,
        }
      );

      if (!res.ok || !res.body) {
        onClose();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!closed) {
        if (signal?.aborted) break;
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const raw = trimmed.slice(6).trim();
          if (!raw || raw === "[KEEPALIVE]") continue;

          try {
            const evt = JSON.parse(raw);
            if (evt.type === "stream_end") {
              onClose();
              return;
            }
            onEvent(evt as ExecutionEvent);
          } catch {
            // ignore malformed
          }
        }
      }
    } catch (err: unknown) {
      const e = err as { name?: string };
      if (e?.name !== "AbortError") {
        onClose();
      }
    }
    onClose();
  };

  connect();

  return () => { closed = true; };
};

// Types for Phase 3
export interface ExecutionEvent {
  id: string;
  execution_id: string;
  event_type: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: number;
  timestamp_str: string;
  level: "info" | "success" | "warning" | "error";
}

export interface ExecutionReport {
  execution_id: string;
  goal: string;
  objective: string;
  actions_performed: ActionItem[];
  findings: string[];
  generated_outputs: OutputItem[];
  errors_encountered: ErrorItem[];
  execution_statistics: ExecutionStats;
  final_result: string;
  report_markdown: string;
  created_at: number;
  partial: boolean;
}

export interface ActionItem {
  task: string;
  tool: string;
  status: string;
  duration_ms: number;
  retries: number;
}

export interface OutputItem {
  type: string;
  filename?: string;
  size_bytes?: number;
  task: string;
}

export interface ErrorItem {
  task: string;
  error: string;
  tool: string;
}

export interface ExecutionStats {
  total_tasks: number;
  completed: number;
  failed: number;
  cancelled: number;
  success_rate: number;
  total_execution_time_ms: number;
  total_execution_time_s: number;
  total_retries: number;
  tools_used: string[];
  partial: boolean;
}

