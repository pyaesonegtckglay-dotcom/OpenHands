"use client";
import { useState } from "react";
import { TaskGraph } from "@/types";
import TaskTreeView from "./TaskTreeView";
import ExecutionWaveView from "./ExecutionWaveView";
import DependencyView from "./DependencyView";
import {
  Network, Layers, GitBranch, Zap, AlertCircle,
  CheckCircle2, XCircle, Clock, ChevronDown, ChevronUp
} from "lucide-react";

type ViewMode = "tree" | "waves" | "dependencies";

function StatCard({
  label,
  value,
  icon,
  color = "gray",
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color?: "blue" | "orange" | "green" | "gray";
}) {
  const colors = {
    blue: "bg-blue-900/20 border-blue-800/50 text-blue-400",
    orange: "bg-orange-900/20 border-orange-800/50 text-orange-400",
    green: "bg-green-900/20 border-green-800/50 text-green-400",
    gray: "bg-gray-800/60 border-gray-700/50 text-gray-400",
  };

  return (
    <div className={`rounded-xl border p-3 ${colors[color]}`}>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs opacity-80">{label}</span>
      </div>
      <div className="text-lg font-bold text-white">{value}</div>
    </div>
  );
}

export default function TaskGraphViewer({ graph }: { graph: TaskGraph }) {
  const [view, setView] = useState<ViewMode>("tree");
  const [showValidation, setShowValidation] = useState(false);

  const { stats, validation, tasks, dependencies, waves, goal } = graph;

  const tabs = [
    { id: "tree" as ViewMode, label: "Task Tree", icon: <Layers className="w-4 h-4" /> },
    { id: "waves" as ViewMode, label: "Execution Waves", icon: <Zap className="w-4 h-4" /> },
    { id: "dependencies" as ViewMode, label: "Dependencies", icon: <GitBranch className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Graph Header */}
      <div className="px-6 py-4 border-b border-gray-800">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Network className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-gray-500 font-mono">
                {graph.graph_id.slice(0, 8)}…
              </span>
              {validation.is_valid ? (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <CheckCircle2 className="w-3 h-3" />
                  Valid
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-red-400">
                  <XCircle className="w-3 h-3" />
                  Invalid
                </span>
              )}
            </div>
            <h2 className="text-white font-semibold text-sm leading-snug">{goal}</h2>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
          <StatCard
            label="Tasks"
            value={stats.total_tasks}
            icon={<Layers className="w-3.5 h-3.5" />}
            color="blue"
          />
          <StatCard
            label="Waves"
            value={stats.total_waves}
            icon={<Zap className="w-3.5 h-3.5" />}
            color="green"
          />
          <StatCard
            label="Blocking"
            value={stats.blocking_tasks}
            icon={<AlertCircle className="w-3.5 h-3.5" />}
            color="orange"
          />
          <StatCard
            label="Duration"
            value={stats.estimated_duration}
            icon={<Clock className="w-3.5 h-3.5" />}
            color="gray"
          />
        </div>

        {/* Validation warnings */}
        {(validation.errors.length > 0 || validation.warnings.length > 0) && (
          <div className="mt-3">
            <button
              onClick={() => setShowValidation(!showValidation)}
              className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              {showValidation ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {validation.errors.length > 0
                ? `${validation.errors.length} validation error${validation.errors.length > 1 ? "s" : ""}`
                : `${validation.warnings.length} warning${validation.warnings.length > 1 ? "s" : ""}`}
            </button>
            {showValidation && (
              <div className="mt-2 space-y-1">
                {validation.errors.map((e, i) => (
                  <p key={i} className="text-xs text-red-400 flex items-center gap-1">
                    <XCircle className="w-3 h-3" /> {e}
                  </p>
                ))}
                {validation.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-yellow-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> {w}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* View Tabs */}
      <div className="px-6 border-b border-gray-800">
        <div className="flex gap-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setView(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-xs font-medium transition-colors border-b-2 -mb-px ${
                view === tab.id
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* View Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {view === "tree" && <TaskTreeView tasks={tasks} />}
        {view === "waves" && <ExecutionWaveView waves={waves} tasks={tasks} />}
        {view === "dependencies" && (
          <DependencyView tasks={tasks} dependencies={dependencies} />
        )}
      </div>
    </div>
  );
}
