"use client";

import { ReactElement } from "react";
import { useExecutionStore } from "@/store/executionStore";
import { ExecutionEvent } from "@/lib/api";
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle,
  Info,
  Loader2,
  Zap,
  Brain,
  GitBranch,
  Play,
  FileText,
  BarChart2,
} from "lucide-react";

// Event type to icon map
function EventIcon({ eventType, level }: { eventType: string; level: string }) {
  const cls = "w-3.5 h-3.5 flex-shrink-0";
  if (level === "error") return <XCircle className={`${cls} text-red-400`} />;
  if (level === "success") return <CheckCircle className={`${cls} text-green-400`} />;
  if (level === "warning") return <AlertCircle className={`${cls} text-yellow-400`} />;

  const icons: Record<string, ReactElement> = {
    intent_detected: <Brain className={`${cls} text-violet-400`} />,
    planning_started: <Brain className={`${cls} text-blue-400`} />,
    plan_generated: <GitBranch className={`${cls} text-blue-400`} />,
    task_graph_created: <GitBranch className={`${cls} text-cyan-400`} />,
    execution_started: <Play className={`${cls} text-green-400`} />,
    wave_started: <Zap className={`${cls} text-yellow-400`} />,
    task_started: <Loader2 className={`${cls} text-blue-300 animate-spin`} />,
    tool_selected: <Zap className={`${cls} text-cyan-400`} />,
    task_completed: <CheckCircle className={`${cls} text-green-400`} />,
    task_failed: <XCircle className={`${cls} text-red-400`} />,
    wave_completed: <CheckCircle className={`${cls} text-green-300`} />,
    execution_completed: <CheckCircle className={`${cls} text-green-400`} />,
    report_generating: <FileText className={`${cls} text-violet-400`} />,
    report_complete: <BarChart2 className={`${cls} text-green-400`} />,
  };

  return icons[eventType] || <Info className={`${cls} text-gray-500`} />;
}

function EventLevelBadge({ level }: { level: string }) {
  const map: Record<string, string> = {
    info: "bg-gray-800 text-gray-400",
    success: "bg-green-900/30 text-green-400",
    warning: "bg-yellow-900/30 text-yellow-400",
    error: "bg-red-900/30 text-red-400",
  };
  return (
    <span className={`text-[9px] px-1 rounded font-mono ${map[level] || map.info}`}>
      {level}
    </span>
  );
}

function EmptyFeed() {
  return (
    <div className="flex flex-col items-center justify-center h-48 text-center">
      <Activity className="w-8 h-8 text-gray-700 mb-3" />
      <p className="text-gray-600 text-xs">Activity feed will appear here</p>
      <p className="text-gray-700 text-[10px] mt-1">Start an execution to see live events</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    idle: { cls: "bg-gray-800 text-gray-400", label: "Idle" },
    starting: { cls: "bg-blue-900/40 text-blue-400", label: "Starting…" },
    running: { cls: "bg-yellow-900/30 text-yellow-300", label: "Running" },
    completed: { cls: "bg-green-900/30 text-green-400", label: "Completed" },
    failed: { cls: "bg-red-900/30 text-red-400", label: "Failed" },
    cancelled: { cls: "bg-gray-800 text-gray-400", label: "Cancelled" },
  };
  const s = map[status] || map.idle;
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${s.cls}`}>
      {s.label}
    </span>
  );
}

interface ActivityPanelProps {
  className?: string;
}

export default function ActivityPanel({ className = "" }: ActivityPanelProps) {
  const { status, goal, events, executionId, isStreaming } = useExecutionStore();

  const completedTasks = events.filter((e) => e.event_type === "task_completed").length;
  const failedTasks = events.filter((e) => e.event_type === "task_failed").length;
  const totalTasks = (() => {
    const startEvt = events.find((e) => e.event_type === "execution_started");
    return (startEvt?.data?.total_tasks as number) || 0;
  })();

  const progress = totalTasks > 0
    ? Math.round(((completedTasks + failedTasks) / totalTasks) * 100)
    : 0;

  return (
    <div className={`flex flex-col bg-[#111318] border border-[#1e2128] rounded-xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e2128] bg-[#0d0f13]">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <span className="text-white font-semibold text-sm">Activity Stream</span>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
          )}
          <StatusPill status={status} />
        </div>
      </div>

      {/* Goal display */}
      {goal && (
        <div className="px-4 py-2 border-b border-[#1e2128] bg-[#0d1117]">
          <p className="text-gray-500 text-[9px] uppercase tracking-wider mb-0.5">Current Goal</p>
          <p className="text-gray-300 text-xs line-clamp-2">{goal}</p>
        </div>
      )}

      {/* Progress bar */}
      {totalTasks > 0 && (
        <div className="px-4 py-2 border-b border-[#1e2128]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-gray-500 text-[9px]">Progress</span>
            <span className="text-gray-400 text-[9px]">
              {completedTasks}/{totalTasks} tasks ({progress}%)
            </span>
          </div>
          <div className="h-1 bg-[#1e2128] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-violet-600 transition-all duration-500 rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Events feed */}
      <div className="flex-1 overflow-y-auto min-h-0 max-h-[420px]">
        {events.length === 0 ? (
          <EmptyFeed />
        ) : (
          <div className="py-2">
            {events.map((event, idx) => (
              <EventRow key={`${event.id}-${idx}`} event={event} />
            ))}
            {/* Live indicator */}
            {isStreaming && (
              <div className="flex items-center gap-2 px-4 py-2">
                <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                <span className="text-gray-600 text-xs">Processing…</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Stats footer */}
      {events.length > 0 && (
        <div className="px-4 py-2 border-t border-[#1e2128] flex items-center gap-4 bg-[#0d0f13]">
          <div className="text-center">
            <p className="text-green-400 text-xs font-bold">{completedTasks}</p>
            <p className="text-gray-600 text-[9px]">Done</p>
          </div>
          <div className="text-center">
            <p className="text-red-400 text-xs font-bold">{failedTasks}</p>
            <p className="text-gray-600 text-[9px]">Failed</p>
          </div>
          <div className="text-center">
            <p className="text-gray-400 text-xs font-bold">{events.length}</p>
            <p className="text-gray-600 text-[9px]">Events</p>
          </div>
        </div>
      )}
    </div>
  );
}

function EventRow({ event }: { event: ExecutionEvent }) {
  const isTask = event.event_type.startsWith("task_");
  const isWave = event.event_type.startsWith("wave_");
  const isMilestone = [
    "execution_started", "execution_completed",
    "plan_generated", "task_graph_created",
    "report_complete",
  ].includes(event.event_type);

  return (
    <div
      className={`flex items-start gap-2 px-4 py-1.5 hover:bg-[#1a1d24]/50 transition-colors ${
        isMilestone ? "bg-[#0d1117]" : ""
      }`}
    >
      <EventIcon eventType={event.event_type} level={event.level} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-gray-300 text-xs truncate flex-1">{event.message}</p>
          <EventLevelBadge level={event.level} />
        </div>
        <p className="text-gray-700 text-[9px] font-mono">{event.timestamp_str}</p>
      </div>
    </div>
  );
}
