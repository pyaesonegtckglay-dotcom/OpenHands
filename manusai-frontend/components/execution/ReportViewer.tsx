"use client";

import { ExecutionReport } from "@/lib/api";
import {
  FileText,
  CheckCircle,
  XCircle,
  BarChart2,
  Target,
  Zap,
  File,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ReportViewerProps {
  report: ExecutionReport;
  className?: string;
}

function StatCard({ label, value, className = "" }: { label: string; value: string | number; className?: string }) {
  return (
    <div className={`bg-[#0d0f13] border border-[#1e2128] rounded-lg px-3 py-2 text-center ${className}`}>
      <p className="text-white font-bold text-lg">{value}</p>
      <p className="text-gray-500 text-[10px]">{label}</p>
    </div>
  );
}

export default function ReportViewer({ report, className = "" }: ReportViewerProps) {
  const stats = report.execution_statistics;

  return (
    <div className={`bg-[#111318] border border-[#1e2128] rounded-xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#1e2128] bg-[#0d0f13]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-green-500/20 to-blue-600/20 rounded-lg flex items-center justify-center border border-[#252830]">
              {report.partial ? (
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
              ) : (
                <BarChart2 className="w-4 h-4 text-green-400" />
              )}
            </div>
            <div>
              <h2 className="text-white font-bold text-base">
                {report.partial ? "⚠️ Partial Report" : "✅ Execution Report"}
              </h2>
              <p className="text-gray-500 text-xs">{report.execution_id.slice(0, 8)}…</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-green-400 font-bold text-lg">{stats.success_rate}%</p>
            <p className="text-gray-600 text-[10px]">Success Rate</p>
          </div>
        </div>
      </div>

      {/* Goal */}
      <div className="px-6 py-3 border-b border-[#1e2128] bg-[#0d1117]">
        <div className="flex items-center gap-2 mb-1">
          <Target className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-gray-400 text-xs font-medium">Goal</span>
        </div>
        <p className="text-white text-sm">{report.goal}</p>
      </div>

      {/* Stats grid */}
      <div className="px-6 py-4 border-b border-[#1e2128]">
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Total Tasks" value={stats.total_tasks} />
          <StatCard label="Completed" value={stats.completed} className="!border-green-900/30" />
          <StatCard label="Failed" value={stats.failed} className={stats.failed > 0 ? "!border-red-900/30" : ""} />
          <StatCard label="Duration" value={`${stats.total_execution_time_s}s`} />
        </div>
      </div>

      {/* Tabs content */}
      <div className="flex-1 overflow-y-auto max-h-[500px]">
        {/* Actions */}
        <section className="px-6 py-4 border-b border-[#1e2128]">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-yellow-400" />
            <h3 className="text-white font-semibold text-sm">Actions Performed</h3>
            <span className="text-gray-600 text-xs">({report.actions_performed.length})</span>
          </div>
          <div className="space-y-1.5">
            {report.actions_performed.map((action, i) => (
              <div
                key={i}
                className="flex items-center gap-3 px-3 py-2 bg-[#0d0f13] rounded-lg border border-[#1e2128]"
              >
                {action.status === "COMPLETED" ? (
                  <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
                ) : action.status === "FAILED" ? (
                  <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-gray-200 text-xs truncate">{action.task}</p>
                  <p className="text-gray-600 text-[9px]">
                    {action.tool} · {action.duration_ms}ms
                    {action.retries > 0 ? ` · ${action.retries} retries` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Findings */}
        {report.findings.length > 0 && (
          <section className="px-6 py-4 border-b border-[#1e2128]">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <h3 className="text-white font-semibold text-sm">Findings</h3>
            </div>
            <div className="space-y-2">
              {report.findings.map((finding, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-blue-400 text-xs mt-0.5">•</span>
                  <p className="text-gray-300 text-xs">{finding}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Outputs */}
        {report.generated_outputs.length > 0 && (
          <section className="px-6 py-4 border-b border-[#1e2128]">
            <div className="flex items-center gap-2 mb-3">
              <File className="w-4 h-4 text-violet-400" />
              <h3 className="text-white font-semibold text-sm">Generated Outputs</h3>
            </div>
            <div className="space-y-2">
              {report.generated_outputs.map((out, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 px-3 py-2 bg-[#0d0f13] rounded-lg border border-[#1e2128]"
                >
                  <FileText className="w-3.5 h-3.5 text-violet-400 flex-shrink-0" />
                  <div>
                    <p className="text-gray-200 text-xs">{out.filename || "Output"}</p>
                    <p className="text-gray-600 text-[9px]">
                      {out.type} · {out.size_bytes ? `${out.size_bytes} bytes` : ""}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Errors */}
        {report.errors_encountered.length > 0 && (
          <section className="px-6 py-4 border-b border-[#1e2128]">
            <div className="flex items-center gap-2 mb-3">
              <XCircle className="w-4 h-4 text-red-400" />
              <h3 className="text-white font-semibold text-sm">Errors</h3>
            </div>
            <div className="space-y-2">
              {report.errors_encountered.map((err, i) => (
                <div
                  key={i}
                  className="px-3 py-2 bg-red-900/10 border border-red-900/30 rounded-lg"
                >
                  <p className="text-red-300 text-xs font-medium">{err.task}</p>
                  <p className="text-red-400/70 text-[10px] mt-0.5">{err.error.slice(0, 200)}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Full Markdown Report */}
        <section className="px-6 py-4">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-blue-400" />
            <h3 className="text-white font-semibold text-sm">Full Report</h3>
          </div>
          <div className="prose prose-invert prose-sm max-w-none text-gray-300 text-xs leading-relaxed bg-[#0d0f13] border border-[#1e2128] rounded-lg p-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.report_markdown}
            </ReactMarkdown>
          </div>
        </section>
      </div>
    </div>
  );
}
