"use client";
import { useEffect, useState } from "react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import TaskGraphViewer from "@/components/taskgraph/TaskGraphViewer";
import { useTaskGraphStore } from "@/store/taskGraphStore";
import { useAuthStore } from "@/store/authStore";
import { taskGraphAPI } from "@/lib/api";
import {
  Network, Plus, Loader2, RefreshCw, CheckCircle2,
  AlertCircle, Layers, Clock, ChevronRight, Zap
} from "lucide-react";
import { TaskGraph, GraphListItem } from "@/types";

function GraphListItemCard({
  item,
  isSelected,
  onClick,
}: {
  item: GraphListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 rounded-xl border transition-all mb-2 ${
        isSelected
          ? "bg-blue-900/20 border-blue-600 text-white"
          : "bg-gray-900 border-gray-800 hover:border-gray-600 text-gray-300"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium truncate">{item.goal}</p>
          <p className="text-xs text-gray-600 mt-0.5 font-mono">{item.graph_id.slice(0, 8)}…</p>
        </div>
        <span className="px-1.5 py-0.5 bg-gray-800 text-gray-500 text-xs rounded flex-shrink-0">
          {item.task_count} tasks
        </span>
      </div>
    </button>
  );
}

function CreateGraphPanel({
  onCreated,
}: {
  onCreated: (graphId: string) => void;
}) {
  const [planId, setPlanId] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!planId.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      const res = await taskGraphAPI.create(planId.trim());
      onCreated(res.data.graph_id);
      setPlanId("");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to create graph");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="p-4 border-b border-gray-800">
      <h3 className="text-white font-semibold text-sm mb-3 flex items-center gap-2">
        <Plus className="w-4 h-4 text-blue-400" />
        Create Task Graph
      </h3>
      <div className="space-y-2">
        <input
          value={planId}
          onChange={(e) => setPlanId(e.target.value)}
          placeholder="Enter Plan ID (UUID)"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-blue-500"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button
          onClick={handleCreate}
          disabled={!planId.trim() || isCreating}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs rounded-lg py-2 flex items-center justify-center gap-2 transition-colors"
        >
          {isCreating ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Creating…</>
          ) : (
            <><Zap className="w-3.5 h-3.5" /> Generate Graph</>
          )}
        </button>
        {error && (
          <p className="text-red-400 text-xs flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> {error}
          </p>
        )}
      </div>
      <p className="text-gray-700 text-xs mt-2">
        Create a plan first via <span className="text-gray-500">/api/v1/planner/create</span>, then paste the plan_id here.
      </p>
    </div>
  );
}

export default function TaskGraphPage() {
  const { loadFromStorage } = useAuthStore();
  const { graphs, currentGraph, isLoading, loadGraphs, loadGraph } = useTaskGraphStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);

  useEffect(() => {
    loadFromStorage();
    loadGraphs();
  }, []);

  const handleSelectGraph = async (graphId: string) => {
    setSelectedId(graphId);
    setLoadingGraph(true);
    await loadGraph(graphId);
    setLoadingGraph(false);
  };

  const handleCreated = async (graphId: string) => {
    await loadGraphs();
    await handleSelectGraph(graphId);
  };

  return (
    <DashboardLayout>
      <div className="flex h-full">
        {/* Left Sidebar */}
        <div className="w-72 flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden bg-gray-950">
          {/* Create panel */}
          <CreateGraphPanel onCreated={handleCreated} />

          {/* Graph list */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-gray-400 text-xs font-medium uppercase tracking-wider">
                Task Graphs
              </h3>
              <button
                onClick={loadGraphs}
                disabled={isLoading}
                className="text-gray-600 hover:text-gray-400 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              </button>
            </div>

            {isLoading && graphs.length === 0 ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-5 h-5 text-gray-600 animate-spin" />
              </div>
            ) : graphs.length === 0 ? (
              <div className="text-center py-8">
                <Network className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                <p className="text-gray-600 text-xs">No task graphs yet</p>
                <p className="text-gray-700 text-xs mt-1">
                  Create a plan first, then generate a graph
                </p>
              </div>
            ) : (
              graphs.map((g) => (
                <GraphListItemCard
                  key={g.graph_id}
                  item={g}
                  isSelected={selectedId === g.graph_id}
                  onClick={() => handleSelectGraph(g.graph_id)}
                />
              ))
            )}
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {loadingGraph ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Loading task graph…</p>
              </div>
            </div>
          ) : currentGraph && selectedId ? (
            <TaskGraphViewer graph={currentGraph} />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
              <div className="w-20 h-20 bg-gray-800/50 rounded-2xl flex items-center justify-center mb-6 border border-gray-700">
                <Network className="w-10 h-10 text-gray-600" />
              </div>
              <h2 className="text-white font-semibold text-lg mb-2">
                Task Graph Engine
              </h2>
              <p className="text-gray-500 text-sm max-w-md leading-relaxed mb-6">
                Phase 2 transforms validated plans into structured task graphs with
                dependency analysis, parallel execution detection, and wave-based execution planning.
              </p>
              <div className="grid grid-cols-3 gap-4 max-w-lg w-full">
                {[
                  { icon: <Layers className="w-5 h-5 text-blue-400" />, label: "Task Hierarchy", desc: "Parent-child task structure" },
                  { icon: <Zap className="w-5 h-5 text-yellow-400" />, label: "Parallel Detection", desc: "Identifies concurrent tasks" },
                  { icon: <Clock className="w-5 h-5 text-green-400" />, label: "Execution Waves", desc: "Ordered execution sequence" },
                ].map((f) => (
                  <div key={f.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                    <div className="flex justify-center mb-2">{f.icon}</div>
                    <p className="text-white text-xs font-medium">{f.label}</p>
                    <p className="text-gray-600 text-xs mt-1">{f.desc}</p>
                  </div>
                ))}
              </div>
              <p className="text-gray-700 text-xs mt-8">
                Select a graph from the sidebar or create one from a plan
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
