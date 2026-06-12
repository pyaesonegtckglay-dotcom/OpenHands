"use client";
import { useState } from "react";
import { cognitiveAPI, type AnalyzeResponse } from "@/lib/cognitiveApi";

const INTENT_COLORS: Record<string, string> = {
  CHAT: "bg-gray-600 text-gray-100",
  QUESTION: "bg-blue-700 text-blue-100",
  TASK: "bg-yellow-700 text-yellow-100",
  PROJECT: "bg-purple-700 text-purple-100",
  WORKFLOW: "bg-orange-700 text-orange-100",
  COMMAND: "bg-red-700 text-red-100",
};

const TASK_TYPE_COLORS: Record<string, string> = {
  CHAT: "bg-gray-600",
  KNOWLEDGE: "bg-blue-600",
  RESEARCH: "bg-cyan-700",
  ANALYSIS: "bg-indigo-700",
  CODING: "bg-green-700",
  WRITING: "bg-teal-700",
  PROJECT: "bg-purple-700",
  WORKFLOW: "bg-orange-700",
  OTHER: "bg-gray-700",
};

function ComplexityBar({ value }: { value: number }) {
  const pct = (value / 10) * 100;
  const color =
    value <= 3 ? "bg-green-500" : value <= 6 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="mt-1">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>Complexity</span>
        <span className="font-bold text-white">{value}/10</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function CognitiveInspector() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const analyze = async () => {
    if (!message.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await cognitiveAPI.analyze(message);
      setResult(res.data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Analysis failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 p-6 w-full">
      <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
        🧠 Cognitive Inspector
        <span className="text-xs font-normal bg-purple-800 text-purple-200 px-2 py-0.5 rounded-full">
          Phase 1
        </span>
      </h2>
      <p className="text-gray-400 text-sm mb-4">
        Analyze user intent, complexity, and planning requirements without
        executing anything.
      </p>

      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 bg-gray-800 border border-gray-600 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500"
          placeholder="Enter a message to analyze…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && analyze()}
        />
        <button
          onClick={analyze}
          disabled={loading || !message.trim()}
          className="bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-3 text-sm mb-4">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Intent + Task Type Row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-xs text-gray-400 mb-1">Intent</div>
              <span
                className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${INTENT_COLORS[result.intent] ?? "bg-gray-600 text-white"}`}
              >
                {result.intent}
              </span>
              <div className="text-xs text-gray-500 mt-1">
                {Math.round(result.intent_confidence * 100)}% confidence
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-xs text-gray-400 mb-1">Task Type</div>
              <span
                className={`inline-block px-3 py-1 rounded-full text-xs font-bold text-white ${TASK_TYPE_COLORS[result.task_type] ?? "bg-gray-600"}`}
              >
                {result.task_type}
              </span>
              <div className="text-xs text-gray-500 mt-1">
                Domain: {result.domain}
              </div>
            </div>
          </div>

          {/* Complexity */}
          <div className="bg-gray-800 rounded-lg p-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-400">Complexity Level</span>
              <span className="text-xs text-gray-300 font-medium capitalize">
                {result.complexity_level}
              </span>
            </div>
            <ComplexityBar value={result.complexity} />
          </div>

          {/* Planning Decision */}
          <div
            className={`rounded-lg p-3 border ${result.planning_required ? "bg-purple-900/40 border-purple-600" : "bg-gray-800 border-gray-600"}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white">
                Planning Required
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold ${result.planning_required ? "bg-purple-600 text-white" : "bg-gray-600 text-gray-200"}`}
              >
                {result.planning_required ? "YES" : "NO"}
              </span>
            </div>
            {result.planning_required && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-gray-400">Plan Depth:</span>
                <span className="text-xs font-bold text-purple-300 uppercase">
                  {result.plan_depth}
                </span>
              </div>
            )}
            <p className="text-xs text-gray-400 mt-2 italic">{result.reason}</p>
          </div>

          {/* Goal + Output */}
          <div className="bg-gray-800 rounded-lg p-3">
            <div className="text-xs text-gray-400 mb-1">Extracted Goal</div>
            <p className="text-sm text-white">{result.goal}</p>
            <div className="text-xs text-gray-400 mt-2 mb-1">
              Desired Output
            </div>
            <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
              {result.desired_output}
            </span>
          </div>

          {/* Keywords */}
          {result.keywords.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-xs text-gray-400 mb-2">Keywords</div>
              <div className="flex flex-wrap gap-1">
                {result.keywords.slice(0, 12).map((kw) => (
                  <span
                    key={kw}
                    className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
