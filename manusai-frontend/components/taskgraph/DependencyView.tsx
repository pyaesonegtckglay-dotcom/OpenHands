"use client";
import { AtomicTask, TaskDependency } from "@/types";
import { GitBranch, ArrowRight, Zap, AlertCircle } from "lucide-react";

function TaskNode({
  task,
  onHover,
  highlightedDeps,
}: {
  task: AtomicTask;
  onHover: (id: string | null) => void;
  highlightedDeps: Set<string>;
}) {
  const isHighlighted = highlightedDeps.has(task.id);

  return (
    <div
      onMouseEnter={() => onHover(task.id)}
      onMouseLeave={() => onHover(null)}
      className={`rounded-xl border p-3 cursor-pointer transition-all select-none ${
        isHighlighted
          ? "bg-blue-900/20 border-blue-600 shadow-lg shadow-blue-900/20"
          : task.is_blocking
          ? "bg-orange-950/20 border-orange-800/50 hover:border-orange-600"
          : task.parallelizable
          ? "bg-blue-950/20 border-blue-800/40 hover:border-blue-600"
          : "bg-gray-900 border-gray-800 hover:border-gray-600"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="font-mono text-gray-600 text-xs">{task.id}</span>
        <div className="flex gap-1 flex-shrink-0">
          {task.is_blocking && <AlertCircle className="w-3.5 h-3.5 text-orange-400" />}
          {task.parallelizable && !task.is_blocking && (
            <Zap className="w-3.5 h-3.5 text-blue-400" />
          )}
        </div>
      </div>
      <p className="text-white text-xs font-medium leading-snug">{task.title}</p>
      {task.dependencies.length > 0 && (
        <div className="mt-1.5 flex items-center gap-1 flex-wrap">
          <span className="text-gray-600 text-xs">←</span>
          {task.dependencies.map((d) => (
            <span
              key={d}
              className="text-xs px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded font-mono"
            >
              {d}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DependencyView({
  tasks,
  dependencies,
}: {
  tasks: AtomicTask[];
  dependencies: TaskDependency[];
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Find all tasks related to hovered task
  const highlightedDeps = new Set<string>();
  if (hoveredId) {
    highlightedDeps.add(hoveredId);
    // Find what hovered task depends on
    const task = tasks.find((t) => t.id === hoveredId);
    task?.dependencies.forEach((d) => highlightedDeps.add(d));
    // Find tasks that depend on hovered task
    tasks.forEach((t) => {
      if (t.dependencies.includes(hoveredId)) highlightedDeps.add(t.id);
    });
  }

  // Group tasks by their dependency depth
  const taskDepth: Record<string, number> = {};
  const computeDepth = (taskId: string, visited = new Set<string>()): number => {
    if (visited.has(taskId)) return 0;
    if (taskDepth[taskId] !== undefined) return taskDepth[taskId];
    visited.add(taskId);
    const task = tasks.find((t) => t.id === taskId);
    if (!task || task.dependencies.length === 0) {
      taskDepth[taskId] = 0;
      return 0;
    }
    const maxDep = Math.max(...task.dependencies.map((d) => computeDepth(d, new Set(visited))));
    taskDepth[taskId] = maxDep + 1;
    return taskDepth[taskId];
  };

  tasks.forEach((t) => computeDepth(t.id));
  const maxDepth = Math.max(...Object.values(taskDepth), 0);

  // Group by depth
  const byDepth: Record<number, AtomicTask[]> = {};
  tasks.forEach((t) => {
    const d = taskDepth[t.id] || 0;
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(t);
  });

  return (
    <div>
      <div className="flex items-center gap-4 mb-5 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <GitBranch className="w-4 h-4" />
          {dependencies.length} dependencies
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <span className="text-blue-400">Hover</span> a task to highlight its connections
        </div>
      </div>

      {/* Dependency chain visualization */}
      <div className="space-y-6">
        {Array.from({ length: maxDepth + 1 }, (_, i) => i).map((depth) => {
          const levelTasks = byDepth[depth] || [];
          if (levelTasks.length === 0) return null;

          return (
            <div key={depth}>
              <div className="flex items-center gap-3 mb-3">
                <div className="h-px flex-1 bg-gray-800" />
                <span className="text-gray-600 text-xs whitespace-nowrap">
                  Level {depth + 1}
                  {depth === 0 ? " — Start" : depth === maxDepth ? " — End" : ""}
                </span>
                <div className="h-px flex-1 bg-gray-800" />
              </div>

              <div
                className={`grid gap-3 ${
                  levelTasks.length === 1
                    ? "grid-cols-1 max-w-sm mx-auto"
                    : levelTasks.length === 2
                    ? "grid-cols-2"
                    : "grid-cols-2 lg:grid-cols-3"
                }`}
              >
                {levelTasks.map((task) => (
                  <TaskNode
                    key={task.id}
                    task={task}
                    onHover={setHoveredId}
                    highlightedDeps={highlightedDeps}
                  />
                ))}
              </div>

              {depth < maxDepth && (
                <div className="flex justify-center mt-4">
                  <ArrowRight className="w-5 h-5 text-gray-700 rotate-90" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Dependency list */}
      {dependencies.length > 0 && (
        <div className="mt-8 border-t border-gray-800 pt-6">
          <h4 className="text-gray-500 text-xs font-medium mb-3 uppercase tracking-wider">
            Dependency Edges
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {dependencies.map((dep) => {
              const source = tasks.find((t) => t.id === dep.source_task_id);
              const target = tasks.find((t) => t.id === dep.target_task_id);
              return (
                <div
                  key={dep.id}
                  className="flex items-center gap-2 p-2 bg-gray-900 rounded-lg border border-gray-800 text-xs"
                >
                  <span className="text-gray-400 font-mono truncate flex-1">
                    {source?.title || dep.source_task_id}
                  </span>
                  <ArrowRight className="w-3 h-3 text-gray-600 flex-shrink-0" />
                  <span className="text-gray-400 font-mono truncate flex-1">
                    {target?.title || dep.target_task_id}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
