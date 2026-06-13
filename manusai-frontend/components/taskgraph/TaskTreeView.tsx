"use client";
import { AtomicTask } from "@/types";
import {
  ChevronRight, ChevronDown, Zap, Clock, AlertCircle,
  GitBranch, Layers, CheckCircle2, Circle
} from "lucide-react";
import { useState } from "react";

function complexityColor(c: string) {
  switch (c) {
    case "high": return "text-red-400 bg-red-900/30 border-red-800";
    case "medium": return "text-yellow-400 bg-yellow-900/30 border-yellow-800";
    case "low": return "text-green-400 bg-green-900/30 border-green-800";
    default: return "text-gray-400 bg-gray-800 border-gray-700";
  }
}

function TaskCard({
  task,
  allTasks,
  depth = 0,
}: {
  task: AtomicTask;
  allTasks: AtomicTask[];
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const children = allTasks.filter((t) => t.dependencies.includes(task.id));
  const hasChildren = children.length > 0;

  return (
    <div className={`${depth > 0 ? "ml-6 border-l border-gray-800 pl-4" : ""}`}>
      <div
        className={`group relative bg-gray-900 border rounded-xl p-4 mb-3 transition-all hover:border-gray-600 ${
          task.is_blocking
            ? "border-orange-800/60 hover:border-orange-600"
            : task.parallelizable
            ? "border-blue-800/40 hover:border-blue-600"
            : "border-gray-800"
        }`}
      >
        {/* Connector line */}
        {depth > 0 && (
          <div className="absolute -left-4 top-6 w-4 h-px bg-gray-700" />
        )}

        <div className="flex items-start gap-3">
          {/* Expand toggle */}
          {hasChildren ? (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-0.5 text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
            >
              {expanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          ) : (
            <div className="mt-1.5 flex-shrink-0">
              <Circle className="w-3 h-3 text-gray-700" />
            </div>
          )}

          {/* Task content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-gray-600">{task.id}</span>
              <h4 className="text-white font-semibold text-sm">{task.title}</h4>

              {/* Badges */}
              {task.is_blocking && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-orange-900/40 text-orange-400 border border-orange-800/50 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Blocking
                </span>
              )}
              {task.parallelizable && !task.is_blocking && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-blue-900/30 text-blue-400 border border-blue-800/40 flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  Parallel
                </span>
              )}
              <span
                className={`px-2 py-0.5 text-xs rounded-full border ${complexityColor(
                  task.estimated_complexity
                )}`}
              >
                {task.estimated_complexity}
              </span>
            </div>

            <p className="text-gray-400 text-xs mt-1.5 leading-relaxed line-clamp-2">
              {task.description}
            </p>

            <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {task.estimated_duration}
              </span>
              {task.dependencies.length > 0 && (
                <span className="flex items-center gap-1">
                  <GitBranch className="w-3 h-3" />
                  Depends: {task.dependencies.join(", ")}
                </span>
              )}
              <span className="text-gray-700">Status: {task.status}</span>
            </div>

            {task.expected_output && (
              <div className="mt-2 px-3 py-1.5 bg-gray-800/60 rounded-lg border border-gray-700/50">
                <span className="text-gray-600 text-xs">Output: </span>
                <span className="text-gray-400 text-xs">{task.expected_output}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div>
          {children.map((child) => (
            <TaskCard
              key={child.id}
              task={child}
              allTasks={allTasks}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function TaskTreeView({ tasks }: { tasks: AtomicTask[] }) {
  // Find root tasks (no dependencies)
  const rootTasks = tasks.filter((t) => t.dependencies.length === 0);
  const otherTasks = tasks.filter(
    (t) => t.dependencies.length > 0 && !tasks.some((p) => p.id === t.parent_task && t.dependencies.includes(p.id))
  );

  const displayRoots = rootTasks.length > 0 ? rootTasks : tasks.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-4 px-1">
        <Layers className="w-4 h-4 text-gray-500" />
        <span className="text-gray-500 text-xs">
          {tasks.length} tasks — Root tasks shown at top, dependent tasks nested below
        </span>
      </div>
      {displayRoots.map((task) => (
        <TaskCard key={task.id} task={task} allTasks={tasks} depth={0} />
      ))}
    </div>
  );
}
