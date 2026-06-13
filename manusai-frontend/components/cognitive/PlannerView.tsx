"use client";
import { useState } from "react";
import { cognitiveAPI, type CreatePlanResponse, type PlanListItem } from "@/lib/cognitiveApi";

const DEPTH_OPTIONS = [
  { value: "", label: "Auto-detect" },
  { value: "shallow", label: "Shallow (3-5 steps)" },
  { value: "medium", label: "Medium (5-10 steps)" },
  { value: "deep", label: "Deep (10-30 steps)" },
];

const STATUS_ICONS: Record<string, string> = {
  pending: "⏳",
  in_progress: "🔄",
  done: "✅",
  failed: "❌",
};

function StepCard({ step, index }: { step: CreatePlanResponse["steps"][0]; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-3 text-left hover:bg-gray-750 transition-colors"
      >
        <div className="flex-shrink-0 w-7 h-7 bg-purple-800 rounded-full flex items-center justify-center text-xs font-bold text-white">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white truncate">
              {step.title}
            </span>
            <span className="text-xs text-gray-500">{STATUS_ICONS[step.status] ?? "⏳"}</span>
          </div>
          {step.dependencies.length > 0 && (
            <div className="text-xs text-gray-500 mt-0.5">
              Depends on: {step.dependencies.join(", ")}
            </div>
          )}
        </div>
        <span className="text-gray-500 text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-0 border-t border-gray-700 space-y-2">
          <div>
            <div className="text-xs text-gray-400 mb-1">Description</div>
            <p className="text-sm text-gray-300">{step.description}</p>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Expected Output</div>
            <p className="text-sm text-green-300">{step.expected_output}</p>
          </div>
          {step.dependencies.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Dependencies</div>
              <div className="flex flex-wrap gap-1">
                {step.dependencies.map((dep) => (
                  <span key={dep} className="text-xs bg-gray-700 text-yellow-300 px-2 py-0.5 rounded">
                    {dep}
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

export default function PlannerView() {
  const [goal, setGoal] = useState("");
  const [depth, setDepth] = useState("");
  const [plan, setPlan] = useState<CreatePlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const createPlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await cognitiveAPI.createPlan(goal, depth || undefined);
      setPlan(res.data);
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : "Plan creation failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 p-6 w-full">
      <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
        📋 AI Planner
        <span className="text-xs font-normal bg-purple-800 text-purple-200 px-2 py-0.5 rounded-full">
          Phase 1
        </span>
      </h2>
      <p className="text-gray-400 text-sm mb-4">
        Generate structured step-by-step plans using AI. Plans are cognitive
        only — no execution.
      </p>

      <div className="space-y-3 mb-4">
        <textarea
          className="w-full bg-gray-800 border border-gray-600 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 resize-none"
          rows={3}
          placeholder="Describe your goal… e.g. Build a portfolio website with Next.js and deploy to Vercel"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
        />
        <div className="flex gap-3">
          <select
            className="bg-gray-800 border border-gray-600 text-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
            value={depth}
            onChange={(e) => setDepth(e.target.value)}
          >
            {DEPTH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            onClick={createPlan}
            disabled={loading || !goal.trim()}
            className="flex-1 bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Generating Plan…" : "Generate Plan"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg p-3 text-sm mb-4">
          {error}
        </div>
      )}

      {plan && (
        <div className="space-y-4">
          {/* Plan Header */}
          <div className="bg-purple-900/30 border border-purple-700 rounded-lg p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="text-xs text-purple-300 mb-1">Goal</div>
                <p className="text-sm text-white font-medium">{plan.goal}</p>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <span className="text-xs bg-purple-700 text-white px-2 py-0.5 rounded uppercase">
                  {plan.plan_depth}
                </span>
                <span className="text-xs text-gray-400">
                  {plan.step_count} steps
                </span>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
              <span>Provider: <span className="text-purple-300">{plan.provider_used}</span></span>
              <span>Model: <span className="text-purple-300">{plan.model_used}</span></span>
              <span
                className={`ml-auto px-2 py-0.5 rounded ${plan.is_valid ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}
              >
                {plan.is_valid ? "✓ Valid" : "⚠ Invalid"}
              </span>
            </div>
            {plan.validation_errors.length > 0 && (
              <div className="mt-2 text-xs text-red-400">
                {plan.validation_errors.map((e, i) => (
                  <div key={i}>⚠ {e}</div>
                ))}
              </div>
            )}
          </div>

          {/* Steps */}
          <div>
            <div className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">
              Plan Steps ({plan.steps.length})
            </div>
            <div className="space-y-2">
              {plan.steps.map((step, i) => (
                <StepCard key={step.id} step={step} index={i} />
              ))}
            </div>
          </div>

          <div className="text-xs text-gray-600 text-center pt-2 border-t border-gray-800">
            Plan ID: {plan.plan_id}
          </div>
        </div>
      )}
    </div>
  );
}
