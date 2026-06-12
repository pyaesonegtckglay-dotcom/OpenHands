"use client";
import { useEffect, useState } from "react";
import { CheckCircle, XCircle, RefreshCw, Database, Radio, Box, Server } from "lucide-react";
import { statusAPI } from "@/lib/api";
import { SystemStatus } from "@/types";

const SERVICE_ICONS: Record<string, any> = {
  supabase_postgresql: Database,
  redis_upstash: Radio,
  e2b_sandbox: Box,
};

const SERVICE_LABELS: Record<string, string> = {
  supabase_postgresql: "Supabase PostgreSQL",
  redis_upstash: "Redis (Upstash)",
  e2b_sandbox: "E2B Sandbox",
};

export default function StatusDashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const [healthRes, servicesRes] = await Promise.all([
        statusAPI.health(),
        statusAPI.services(),
      ]);
      setBackendOk(healthRes.data.status === "ok");
      setStatus(servicesRes.data);
      setLastChecked(new Date());
    } catch {
      setBackendOk(false);
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const allServices = status
    ? Object.entries(status.services)
    : [
        ["supabase_postgresql", null],
        ["redis_upstash", null],
        ["e2b_sandbox", null],
      ];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-white text-xl font-semibold">System Status</h2>
          <p className="text-gray-500 text-sm mt-0.5">
            Live infrastructure health monitoring
            {lastChecked && (
              <span className="ml-2">· Last checked {lastChecked.toLocaleTimeString()}</span>
            )}
          </p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Overall status */}
      <div className={`mb-6 p-4 rounded-xl border ${
        backendOk === null
          ? "bg-gray-800/50 border-gray-700"
          : backendOk && status?.overall === "healthy"
          ? "bg-green-900/20 border-green-700/50"
          : "bg-red-900/20 border-red-700/50"
      }`}>
        <div className="flex items-center gap-3">
          {backendOk === null ? (
            <RefreshCw className="w-5 h-5 text-gray-400 animate-spin" />
          ) : backendOk && status?.overall === "healthy" ? (
            <CheckCircle className="w-5 h-5 text-green-400" />
          ) : (
            <XCircle className="w-5 h-5 text-red-400" />
          )}
          <div>
            <p className="text-white font-medium">
              {backendOk === null
                ? "Checking..."
                : backendOk && status?.overall === "healthy"
                ? "All Systems Operational"
                : "System Degraded"}
            </p>
            <p className="text-gray-400 text-sm">ManusAI Phase 0 Backend</p>
          </div>
        </div>
      </div>

      {/* Service grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Backend card */}
        <div className={`p-4 rounded-xl border ${
          backendOk === null
            ? "bg-gray-800/50 border-gray-700"
            : backendOk
            ? "bg-gray-800/50 border-gray-700"
            : "bg-red-900/20 border-red-700/50"
        }`}>
          <div className="flex items-start gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              backendOk ? "bg-green-900/40" : "bg-red-900/40"
            }`}>
              <Server className={`w-5 h-5 ${backendOk ? "text-green-400" : "text-red-400"}`} />
            </div>
            <div className="flex-1">
              <p className="text-white font-medium text-sm">Backend API</p>
              <p className="text-gray-500 text-xs">FastAPI + uvicorn</p>
            </div>
            {backendOk === null ? (
              <div className="w-2 h-2 bg-gray-500 rounded-full mt-1" />
            ) : backendOk ? (
              <CheckCircle className="w-4 h-4 text-green-400 mt-0.5" />
            ) : (
              <XCircle className="w-4 h-4 text-red-400 mt-0.5" />
            )}
          </div>
          <div className={`mt-3 text-xs font-medium px-2 py-0.5 rounded-full inline-block ${
            backendOk === null
              ? "bg-gray-700 text-gray-400"
              : backendOk
              ? "bg-green-900/50 text-green-400"
              : "bg-red-900/50 text-red-400"
          }`}>
            {backendOk === null ? "Checking" : backendOk ? "Connected" : "Disconnected"}
          </div>
        </div>

        {/* Infrastructure services */}
        {allServices.map(([key, svc]: any) => {
          const Icon = SERVICE_ICONS[key] || Server;
          const label = SERVICE_LABELS[key] || key;
          const connected = svc?.status === "connected";
          return (
            <div key={key} className={`p-4 rounded-xl border ${
              svc === null
                ? "bg-gray-800/50 border-gray-700"
                : connected
                ? "bg-gray-800/50 border-gray-700"
                : "bg-red-900/20 border-red-700/50"
            }`}>
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  svc === null ? "bg-gray-700/50" : connected ? "bg-green-900/40" : "bg-red-900/40"
                }`}>
                  <Icon className={`w-5 h-5 ${
                    svc === null ? "text-gray-500" : connected ? "text-green-400" : "text-red-400"
                  }`} />
                </div>
                <div className="flex-1">
                  <p className="text-white font-medium text-sm">{label}</p>
                  {svc?.error && (
                    <p className="text-red-400 text-xs mt-0.5">{svc.error.slice(0, 60)}</p>
                  )}
                </div>
                {svc === null ? (
                  <div className="w-2 h-2 bg-gray-500 rounded-full mt-1" />
                ) : connected ? (
                  <CheckCircle className="w-4 h-4 text-green-400 mt-0.5" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400 mt-0.5" />
                )}
              </div>
              <div className={`mt-3 text-xs font-medium px-2 py-0.5 rounded-full inline-block ${
                svc === null
                  ? "bg-gray-700 text-gray-400"
                  : connected
                  ? "bg-green-900/50 text-green-400"
                  : "bg-red-900/50 text-red-400"
              }`}>
                {svc === null ? "Checking" : connected ? "Connected" : "Disconnected"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
