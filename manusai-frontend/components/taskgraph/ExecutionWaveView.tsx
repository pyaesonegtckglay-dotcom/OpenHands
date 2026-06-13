"use client";
import { ExecutionWave, AtomicTask } from "@/types";
import { Zap, AlertCircle, Play, Clock, ArrowDown } from "lucide-react";

function WaveCard({
  wave,
  tasks,
  isLast,
}: {
  wave: ExecutionWave;
  tasks: AtomicTask[];
  isLast: boolean;
}) {
  const waveTasks = tasks.filter((t) => wave.task_ids.includes(t.id));

  return (
    <div className="relative">
      {/* Wave header */}
      <div
        className={`rounded-xl border p-4 ${
          wave.all_blocking
            ? "bg-orange-950/20 border-orange-800/40"
            : wave.can_run_parallel
            ? "bg-blue-950/20 border-blue-800/40"
            : "bg-gray-900 border-gray-800"
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                wave.all_blocking
                  ? "bg-orange-900/40 text-orange-400"
                  : wave.can_run_parallel
                  ? "bg-blue-900/40 text-blue-400"
                  : "bg-gray-800 text-gray-400"
              }`}
            >
              {wave.wave_number}
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">
                Execution Wave {wave.wave_number}
              </h3>
              <p className="text-gray-500 text-xs">
                {wave.task_ids.length} task{wave.task_ids.length !== 1 ? "s" : ""}
                {wave.can_run_parallel ? " — can run in parallel" : " — sequential"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            {wave.can_run_parallel && (
              <span className="px-2 py-1 rounded-full bg-blue-900/30 text-blue-400 text-xs border border-blue-800/40 flex items-center gap-1">
                <Zap className="w-3 h-3" />
                Parallel
              </span>
            )}
            {wave.all_blocking && (
              <span className="px-2 py-1 rounded-full bg-orange-900/30 text-orange-400 text-xs border border-orange-800/40 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Blocking
              </span>
            )}
          </div>
        </div>

        {/* Task grid */}
        <div
          className={`grid gap-2 ${
            wave.task_ids.length > 2 ? "grid-cols-2 lg:grid-cols-3" : "grid-cols-1"
          }`}
        >
          {waveTasks.map((task) => (
            <div
              key={task.id}
              className={`rounded-lg p-3 border text-xs ${
                task.is_blocking
                  ? "bg-orange-950/30 border-orange-900/50"
                  : task.parallelizable
                  ? "bg-blue-950/30 border-blue-900/50"
                  : "bg-gray-800/60 border-gray-700/50"
              }`}
            >
              <div className="flex items-start justify-between gap-1 mb-1">
                <span className="font-mono text-gray-600">{task.id}</span>
                <div className="flex gap-1">
                  {task.is_blocking && (
                    <AlertCircle className="w-3 h-3 text-orange-400 flex-shrink-0" />
                  )}
                  {task.parallelizable && !task.is_blocking && (
                    <Zap className="w-3 h-3 text-blue-400 flex-shrink-0" />
                  )}
                </div>
              </div>
              <p className="text-white font-medium leading-tight">{task.title}</p>
              <div className="flex items-center gap-1 mt-1.5 text-gray-600">
                <Clock className="w-3 h-3" />
                <span>{task.estimated_duration}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Arrow connector */}
      {!isLast && (
        <div className="flex justify-center my-2">
          <div className="flex flex-col items-center">
            <div className="w-px h-4 bg-gray-700" />
            <ArrowDown className="w-4 h-4 text-gray-600" />
          </div>
        </div>
      )}
    </div>
  );
}

export default function ExecutionWaveView({
  waves,
  tasks,
}: {
  waves: ExecutionWave[];
  tasks: AtomicTask[];
}) {
  if (!waves || waves.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No execution waves generated
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-4 px-1 flex-wrap">
        <span className="px-2 py-1 bg-blue-900/30 text-blue-400 text-xs rounded-full border border-blue-800/40 flex items-center gap-1">
          <Zap className="w-3 h-3" />
          Parallel — runs simultaneously with other tasks in wave
        </span>
        <span className="px-2 py-1 bg-orange-900/30 text-orange-400 text-xs rounded-full border border-orange-800/40 flex items-center gap-1">
          <AlertCircle className="w-3 h-3" />
          Blocking — next wave waits for this
        </span>
      </div>

      {waves.map((wave, i) => (
        <WaveCard
          key={wave.wave_number}
          wave={wave}
          tasks={tasks}
          isLast={i === waves.length - 1}
        />
      ))}
    </div>
  );
}
