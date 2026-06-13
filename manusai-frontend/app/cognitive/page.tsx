"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import DashboardLayout from "@/components/layout/DashboardLayout";
import CognitiveInspector from "@/components/cognitive/CognitiveInspector";
import PlannerView from "@/components/cognitive/PlannerView";

export default function CognitivePage() {
  const router = useRouter();
  const { loadFromStorage, token } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (token === null) {
      router.replace("/login");
    }
  }, [token, router]);

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full overflow-y-auto p-6 bg-gray-950">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-white">Cognitive Layer</h1>
            <span className="text-sm bg-purple-800 text-purple-200 px-3 py-1 rounded-full font-medium">
              Phase 1
            </span>
          </div>
          <p className="text-gray-400 text-sm max-w-2xl">
            Determine what users want, analyze task complexity, and generate
            structured plans. This layer classifies intent and creates plans —
            no execution happens here.
          </p>

          {/* Phase Info Bar */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Intent Types", value: "6", desc: "CHAT · QUESTION · TASK · PROJECT · WORKFLOW · COMMAND" },
              { label: "Task Types", value: "9", desc: "CHAT · KNOWLEDGE · RESEARCH · ANALYSIS · CODING · WRITING · PROJECT · WORKFLOW · OTHER" },
              { label: "Complexity Range", value: "1–10", desc: "Trivial → Simple → Moderate → Complex → Enterprise" },
              { label: "Providers", value: "3", desc: "Gemini → GitHub Models → SambaNova (fallback chain)" },
            ].map((item) => (
              <div key={item.label} className="bg-gray-900 border border-gray-700 rounded-lg p-3">
                <div className="text-xs text-gray-400">{item.label}</div>
                <div className="text-xl font-bold text-purple-300 my-1">{item.value}</div>
                <div className="text-xs text-gray-500 leading-tight">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CognitiveInspector />
          <PlannerView />
        </div>

        {/* Pipeline Diagram */}
        <div className="mt-6 bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h3 className="text-sm font-bold text-white mb-3">🔄 Cognitive Pipeline</h3>
          <div className="flex items-center gap-2 flex-wrap">
            {[
              "User Input",
              "Intent Classifier",
              "Goal Extractor",
              "Complexity Analyzer",
              "Task Classifier",
              "Planner Trigger",
              "Plan Generator",
              "Plan Validator",
              "Plan Storage",
            ].map((step, i, arr) => (
              <div key={step} className="flex items-center gap-2">
                <div className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5 text-xs text-gray-300 whitespace-nowrap">
                  {step}
                </div>
                {i < arr.length - 1 && (
                  <span className="text-gray-600 text-xs">→</span>
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            ⚠️ Phase 1 is cognitive only — no execution, no browser automation, no tool calls. Plans are generated and stored but not executed.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
