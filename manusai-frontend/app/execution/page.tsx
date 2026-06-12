"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Play,
  StopCircle,
  Zap,
  Activity,
  BarChart2,
  History,
  ChevronRight,
  Send,
  Sparkles,
} from "lucide-react";
import {
  executionAPI,
  streamExecutionEvents,
  ExecutionEvent,
  ExecutionReport,
} from "@/lib/api";
import { useExecutionStore } from "@/store/executionStore";
import ActivityPanel from "@/components/execution/ActivityPanel";
import ReportViewer from "@/components/execution/ReportViewer";

const EXAMPLE_GOALS = [
  "Research Tesla and generate a comprehensive report",
  "Create a CSV file containing the top 20 AI companies",
  "Analyze market trends for artificial intelligence in 2024",
  "Research SpaceX's latest missions and achievements",
  "Create a Python script to generate Fibonacci sequence",
  "Search for the best programming languages in 2025",
];

type Tab = "activity" | "report" | "history";

export default function ExecutionPage() {
  const router = useRouter();
  const {
    executionId,
    goal,
    status,
    events,
    report,
    isStreaming,
    setGoal,
    startExecution,
    addEvent,
    setReport,
    setStatus,
    stopStreaming,
    reset,
    history,
    setHistory,
  } = useExecutionStore();

  const [inputGoal, setInputGoal] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("activity");
  const [stopCleanup, setStopCleanup] = useState<(() => void) | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  // Auto-switch to report tab when report arrives
  useEffect(() => {
    if (report) {
      setActiveTab("report");
    }
  }, [report]);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await executionAPI.getHistory();
      setHistory(res.data.executions || []);
    } catch {
      /* ignore */
    }
    setLoadingHistory(false);
  };

  const handleStart = useCallback(async () => {
    const g = inputGoal.trim();
    if (!g || isStreaming) return;

    // Check auth
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    reset();
    setActiveTab("activity");
    setGoal(g);
    setInputGoal("");

    try {
      const res = await executionAPI.start(g);
      const { execution_id } = res.data;

      startExecution(execution_id, g);
      setStatus("running");

      // Subscribe to event stream
      const ac = new AbortController();
      abortRef.current = ac;

      const cleanup = streamExecutionEvents(
        execution_id,
        (event: ExecutionEvent) => {
          addEvent(event);

          // When execution is done, fetch report
          if (
            event.event_type === "report_complete" ||
            event.event_type === "execution_completed"
          ) {
            fetchReport(execution_id);
            setStatus("completed");
          }
        },
        () => {
          stopStreaming();
          if (status !== "completed") setStatus("completed");
          // Refresh history
          loadHistory();
        },
        ac.signal,
      );

      setStopCleanup(() => cleanup);
    } catch (err: unknown) {
      const e = err as { response?: { status?: number } };
      if (e?.response?.status === 401) {
        router.push("/login");
      } else {
        setStatus("failed");
        stopStreaming();
      }
    }
  }, [inputGoal, isStreaming]);

  const fetchReport = async (executionId: string) => {
    try {
      // Retry a few times as report may take a moment
      for (let i = 0; i < 5; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const res = await executionAPI.getReport(executionId);
        if (res.data) {
          setReport(res.data as ExecutionReport);
          return;
        }
      }
    } catch {
      /* report may not be available yet */
    }
  };

  const handleStop = useCallback(async () => {
    if (!executionId) return;
    try {
      await executionAPI.stop(executionId);
    } catch {
      /* ignore */
    }
    abortRef.current?.abort();
    stopCleanup?.();
    setStatus("cancelled");
    stopStreaming();
    loadHistory();
  }, [executionId, stopCleanup]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleStart();
    }
  };

  const statusConfig = {
    idle: { color: "text-gray-500", label: "Ready" },
    starting: { color: "text-blue-400", label: "Starting…" },
    running: { color: "text-yellow-400", label: "Running" },
    completed: { color: "text-green-400", label: "Completed" },
    failed: { color: "text-red-400", label: "Failed" },
    cancelled: { color: "text-gray-400", label: "Cancelled" },
  };
  const sc = statusConfig[status] || statusConfig.idle;

  return (
    <div className="flex flex-col h-full bg-[#0d0f13] overflow-hidden">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e2128] bg-[#111318] flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-violet-500/20 to-blue-600/20 rounded-lg flex items-center justify-center border border-[#252830]">
            <Zap className="w-4 h-4 text-violet-400" />
          </div>
          <div>
            <h1 className="text-white font-bold text-base">Execution Engine</h1>
            <p className="text-gray-600 text-[10px]">Phase 3 — Tool Orchestration · Real Actions</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${sc.color}`}>{sc.label}</span>
          {isStreaming && (
            <span className="relative flex h-2 w-2 ml-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500" />
            </span>
          )}
        </div>
      </div>

      {/* ── Input area ── */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-[#1e2128] bg-[#111318]">
        <div className="flex gap-3 items-end max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <div className="flex items-center gap-2 bg-[#1a1d24] border border-[#252830] focus-within:border-blue-600/50 rounded-xl px-4 py-3 transition-colors">
              <textarea
                value={inputGoal}
                onChange={(e) => setInputGoal(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  isStreaming
                    ? "Execution in progress…"
                    : "Enter your goal (e.g., Research Tesla and generate a report)…"
                }
                rows={1}
                disabled={isStreaming}
                className="flex-1 bg-transparent text-white text-sm resize-none focus:outline-none placeholder-gray-600 disabled:opacity-40"
                style={{ minHeight: "24px" }}
                onInput={(e) => {
                  const el = e.target as HTMLTextAreaElement;
                  el.style.height = "auto";
                  el.style.height = Math.min(el.scrollHeight, 96) + "px";
                }}
              />
            </div>
            {/* Example goals */}
            {!isStreaming && !inputGoal && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {EXAMPLE_GOALS.slice(0, 3).map((eg) => (
                  <button
                    key={eg}
                    onClick={() => setInputGoal(eg)}
                    className="text-[10px] text-gray-500 hover:text-gray-300 bg-[#1a1d24] hover:bg-[#252830] px-2 py-1 rounded-lg border border-[#252830] transition-all"
                  >
                    {eg.slice(0, 45)}…
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Action buttons */}
          {isStreaming ? (
            <button
              onClick={handleStop}
              className="flex items-center gap-2 px-4 py-3 bg-red-900/20 hover:bg-red-900/40 border border-red-600/40 hover:border-red-500/60 text-red-400 hover:text-red-300 rounded-xl text-sm font-medium transition-all flex-shrink-0"
            >
              <StopCircle className="w-4 h-4" />
              Stop
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={!inputGoal.trim()}
              className="flex items-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-all flex-shrink-0"
            >
              <Play className="w-4 h-4" />
              Execute
            </button>
          )}
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="flex-1 overflow-hidden flex gap-0">
        {/* Left: Chat/Goal area or Task Panel */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {status === "idle" && events.length === 0 ? (
            <WelcomeScreen onExample={(eg) => setInputGoal(eg)} />
          ) : (
            <TaskPanel />
          )}
        </div>

        {/* Right: Activity Panel + Report/History tabs */}
        <div className="w-80 flex-shrink-0 border-l border-[#1e2128] flex flex-col">
          {/* Tab bar */}
          <div className="flex border-b border-[#1e2128] bg-[#111318]">
            {([
              { id: "activity", label: "Activity", icon: Activity },
              { id: "report", label: "Report", icon: BarChart2 },
              { id: "history", label: "History", icon: History },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-1 py-2.5 text-xs font-medium transition-colors ${
                  activeTab === tab.id
                    ? "text-white border-b-2 border-blue-500"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
                {tab.id === "report" && report && (
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === "activity" && (
              <ActivityPanel className="border-0 rounded-none h-full" />
            )}
            {activeTab === "report" && (
              report ? (
                <ReportViewer report={report} className="border-0 rounded-none" />
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-center p-4">
                  <BarChart2 className="w-8 h-8 text-gray-700 mb-3" />
                  <p className="text-gray-600 text-xs">
                    {isStreaming ? "Generating report…" : "No report yet"}
                  </p>
                </div>
              )
            )}
            {activeTab === "history" && (
              <HistoryPanel
                history={history}
                loading={loadingHistory}
                onRefresh={loadHistory}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Task Panel (shows execution progress) ─────────────────────────────────────
function TaskPanel() {
  const { goal, events, status, executionId } = useExecutionStore();

  const taskEvents = events.filter(
    (e) => e.event_type === "task_started" || e.event_type === "task_completed" || e.event_type === "task_failed"
  );

  const taskMap = new Map<string, { started?: ExecutionEvent; completed?: ExecutionEvent; failed?: ExecutionEvent }>();
  for (const evt of taskEvents) {
    const taskId = (evt.data.task_id as string) || evt.message;
    if (!taskMap.has(taskId)) taskMap.set(taskId, {});
    const entry = taskMap.get(taskId)!;
    if (evt.event_type === "task_started") entry.started = evt;
    if (evt.event_type === "task_completed") entry.completed = evt;
    if (evt.event_type === "task_failed") entry.failed = evt;
  }

  const milestoneEvents = events.filter(
    (e) => [
      "intent_detected", "plan_generated", "task_graph_created",
      "execution_started", "execution_completed", "report_complete",
    ].includes(e.event_type)
  );

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Goal header */}
      <div className="bg-[#111318] border border-[#1e2128] rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-4 h-4 text-violet-400" />
          <h3 className="text-white font-semibold text-sm">Current Goal</h3>
        </div>
        <p className="text-gray-300 text-sm">{goal}</p>
        {executionId && (
          <p className="text-gray-600 text-[9px] mt-1 font-mono">ID: {executionId.slice(0, 16)}…</p>
        )}
      </div>

      {/* Milestone timeline */}
      {milestoneEvents.length > 0 && (
        <div className="bg-[#111318] border border-[#1e2128] rounded-xl p-4">
          <h3 className="text-gray-400 text-xs font-medium mb-3 uppercase tracking-wider">
            Execution Timeline
          </h3>
          <div className="space-y-2">
            {milestoneEvents.map((evt, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full flex-shrink-0" />
                <div className="flex-1 flex items-center justify-between">
                  <span className="text-gray-300 text-xs">{evt.message}</span>
                  <span className="text-gray-600 text-[10px] font-mono">{evt.timestamp_str}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks */}
      {taskMap.size > 0 && (
        <div className="bg-[#111318] border border-[#1e2128] rounded-xl p-4">
          <h3 className="text-gray-400 text-xs font-medium mb-3 uppercase tracking-wider">
            Tasks ({taskMap.size})
          </h3>
          <div className="space-y-2">
            {Array.from(taskMap.values()).map((entry, i) => {
              const evt = entry.completed || entry.failed || entry.started;
              if (!evt) return null;
              const taskTitle = (evt.data.task_title as string) || `Task ${i + 1}`;
              const toolId = (evt.data.tool as string) || "unknown";
              const isCompleted = !!entry.completed;
              const isFailed = !!entry.failed;
              const isRunning = !!(entry.started && !entry.completed && !entry.failed);

              return (
                <div
                  key={i}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-colors ${
                    isCompleted
                      ? "bg-green-900/10 border-green-900/30"
                      : isFailed
                      ? "bg-red-900/10 border-red-900/30"
                      : isRunning
                      ? "bg-blue-900/10 border-blue-900/30"
                      : "bg-[#0d0f13] border-[#1e2128]"
                  }`}
                >
                  <div className="flex-shrink-0">
                    {isCompleted ? (
                      <span className="text-green-400 text-sm">✅</span>
                    ) : isFailed ? (
                      <span className="text-red-400 text-sm">❌</span>
                    ) : isRunning ? (
                      <span className="text-blue-400 text-sm animate-pulse">⚡</span>
                    ) : (
                      <span className="text-gray-600 text-sm">⏳</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-200 text-xs truncate">{taskTitle}</p>
                    <p className="text-gray-600 text-[9px]">Tool: {toolId}</p>
                  </div>
                  {entry.completed?.data?.execution_time_ms ? (
                    <span className="text-gray-600 text-[9px]">
                      {Number(entry.completed.data.execution_time_ms)}ms
                    </span>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Welcome Screen ─────────────────────────────────────────────────────────────
function WelcomeScreen({ onExample }: { onExample: (eg: string) => void }) {
  return (
    <div className="max-w-2xl mx-auto py-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-gradient-to-br from-violet-500/20 to-blue-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-[#252830]">
          <Zap className="w-8 h-8 text-violet-400" />
        </div>
        <h2 className="text-white font-bold text-2xl mb-2">Execution Engine</h2>
        <p className="text-gray-400 text-sm max-w-md mx-auto">
          Phase 3 — Real tool execution. Give a goal, watch it execute with live activity streaming and a final report.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {EXAMPLE_GOALS.map((eg) => (
          <button
            key={eg}
            onClick={() => onExample(eg)}
            className="flex items-start gap-3 px-4 py-3 bg-[#111318] hover:bg-[#1a1d24] text-left rounded-xl border border-[#1e2128] hover:border-[#3a3d48] transition-all group"
          >
            <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 flex-shrink-0 mt-0.5 transition-colors" />
            <div>
              <p className="text-gray-300 text-xs group-hover:text-white transition-colors">{eg}</p>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-6 bg-[#111318] border border-[#1e2128] rounded-xl p-4">
        <h3 className="text-gray-400 text-xs font-medium mb-2 uppercase tracking-wider">How it works</h3>
        <div className="grid grid-cols-4 gap-3 text-center">
          {[
            { step: "1", label: "Classify Intent", icon: "🧠" },
            { step: "2", label: "Generate Plan", icon: "📋" },
            { step: "3", label: "Execute Tasks", icon: "⚡" },
            { step: "4", label: "Generate Report", icon: "📊" },
          ].map(({ step, label, icon }) => (
            <div key={step} className="flex flex-col items-center gap-1">
              <span className="text-2xl">{icon}</span>
              <p className="text-gray-500 text-[10px]">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── History Panel ─────────────────────────────────────────────────────────────
function HistoryPanel({
  history,
  loading,
  onRefresh,
}: {
  history: Array<{ id: string; goal: string; status: string; created_at: string }>;
  loading: boolean;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-24">
        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center p-4">
        <History className="w-8 h-8 text-gray-700 mb-3" />
        <p className="text-gray-600 text-xs">No executions yet</p>
        <button onClick={onRefresh} className="text-blue-400 text-xs mt-2 hover:underline">Refresh</button>
      </div>
    );
  }

  return (
    <div className="py-2">
      <div className="px-4 pb-2 flex items-center justify-between">
        <span className="text-gray-600 text-[10px]">{history.length} executions</span>
        <button onClick={onRefresh} className="text-blue-400 text-[10px] hover:underline">
          Refresh
        </button>
      </div>
      {history.map((item) => (
        <div
          key={item.id}
          className="px-4 py-2 border-b border-[#1e2128] hover:bg-[#1a1d24]/50 transition-colors"
        >
          <p className="text-gray-300 text-xs line-clamp-2">{item.goal}</p>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                item.status === "COMPLETED"
                  ? "bg-green-900/30 text-green-400"
                  : item.status === "FAILED"
                  ? "bg-red-900/30 text-red-400"
                  : "bg-gray-800 text-gray-500"
              }`}
            >
              {item.status}
            </span>
            <span className="text-gray-700 text-[9px]">
              {new Date(item.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
