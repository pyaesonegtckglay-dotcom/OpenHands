/**
 * Activity Feed Component
 * Real-time streaming display of multi-agent execution events
 */

import React, { useEffect, useRef } from "react";
import { Card } from "#/ui/card";
import { Badge } from "#/ui/badge";
import { multiAgentService, type ExecutionEvent } from "#/services/multi-agent-service";
import { ScrollArea } from "#/ui/scroll-area";

interface ActivityFeedProps {
  goal?: string;
  agentTypes?: string[];
  collaborationMode?: "sequential" | "parallel" | "hierarchical";
  isActive: boolean;
  onComplete?: (executionId: string) => void;
}

const eventConfig: Record<string, { icon: string; color: string; label: string }> = {
  execution_started: {
    icon: "🚀",
    color: "bg-blue-100 text-blue-800 border-blue-200",
    label: "Starting execution",
  },
  agent_started: {
    icon: "⚡",
    color: "bg-yellow-100 text-yellow-800 border-yellow-200",
    label: "Agent working",
  },
  agent_completed: {
    icon: "✅",
    color: "bg-green-100 text-green-800 border-green-200",
    label: "Agent completed",
  },
  execution_completed: {
    icon: "🎉",
    color: "bg-emerald-100 text-emerald-800 border-emerald-200",
    label: "Execution complete",
  },
  execution_failed: {
    icon: "❌",
    color: "bg-red-100 text-red-800 border-red-200",
    label: "Execution failed",
  },
  done: {
    icon: "✨",
    color: "bg-purple-100 text-purple-800 border-purple-200",
    label: "Done",
  },
  error: {
    icon: "⚠️",
    color: "bg-orange-100 text-orange-800 border-orange-200",
    label: "Error",
  },
};

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  goal,
  agentTypes,
  collaborationMode = "sequential",
  isActive,
  onComplete,
}) => {
  const [events, setEvents] = React.useState<ExecutionEvent[]>([]);
  const [status, setStatus] = React.useState<"idle" | "running" | "completed" | "error">("idle");
  const [currentExecutionId, setCurrentExecutionId] = React.useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const executionRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (executionRef.current) {
        executionRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const handleStartExecution = async () => {
    if (!goal?.trim()) return;

    setEvents([]);
    setStatus("running");
    setCurrentExecutionId(null);

    try {
      const execution = await multiAgentService.executeGoalStream(
        {
          goal,
          agent_types: agentTypes,
          collaboration_mode: collaborationMode,
        },
        (event) => {
          setEvents((prev) => [...prev, event]);

          if (event.execution_id) {
            setCurrentExecutionId(event.execution_id);
          }

          if (event.type === "execution_completed" || event.type === "done") {
            setStatus("completed");
            if (event.execution_id) {
              onComplete?.(event.execution_id);
            }
          }

          if (event.type === "execution_failed" || (event.type === "error" && event.error)) {
            setStatus("error");
          }
        }
      );

      setCurrentExecutionId(execution.execution_id);
      setStatus("completed");
      onComplete?.(execution.execution_id);
    } catch (err) {
      console.error("Execution failed:", err);
      setStatus("error");
      setEvents((prev) => [
        ...prev,
        { type: "error", error: err instanceof Error ? err.message : "Unknown error" },
      ]);
    }
  };

  const handleStopExecution = () => {
    if (executionRef.current) {
      executionRef.current.abort();
    }
    setStatus("idle");
  };

  const getEventConfig = (event: ExecutionEvent) => {
    return eventConfig[event.type] || { icon: "📋", color: "bg-gray-100", label: event.type };
  };

  return (
    <Card className="h-full flex flex-col">
      <div className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-lg">Activity Feed</h2>
          <Badge
            variant={status === "running" ? "default" : status === "completed" ? "secondary" : "outline"}
            className={status === "running" ? "animate-pulse" : ""}
          >
            {status === "idle" ? "Ready" : status === "running" ? "Running" : status === "completed" ? "Done" : "Error"}
          </Badge>
        </div>
        {currentExecutionId && (
          <p className="text-xs text-muted-foreground font-mono">
            {currentExecutionId}
          </p>
        )}
      </div>

      <div className="flex-1 flex flex-col min-h-0 p-0">
        <ScrollArea className="flex-1 px-4" ref={scrollRef}>
          <div className="space-y-2 pb-4">
            {events.length === 0 && status === "idle" && (
              <div className="text-center py-8 text-muted-foreground">
                <p>No activity yet</p>
                <p className="text-sm mt-1">Start an execution to see events</p>
              </div>
            )}

            {events.map((event, index) => {
              const config = getEventConfig(event);
              return (
                <div
                  key={index}
                  className={`flex items-start gap-2 p-2 rounded-lg border ${config.color}`}
                >
                  <span className="text-lg">{config.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{config.label}</p>
                    {event.step && (
                      <p className="text-xs opacity-80">Step {event.step}</p>
                    )}
                    {event.agent_id && (
                      <p className="text-xs opacity-80 font-mono truncate">
                        {event.agent_id.slice(0, 12)}...
                      </p>
                    )}
                    {event.duration_ms && (
                      <p className="text-xs opacity-80">{event.duration_ms}ms</p>
                    )}
                    {event.error && (
                      <p className="text-xs text-red-600 mt-1">{event.error}</p>
                    )}
                  </div>
                  <span className="text-xs opacity-60">
                    {new Date().toLocaleTimeString()}
                  </span>
                </div>
              );
            })}
          </div>
        </ScrollArea>

        <div className="p-4 border-t bg-muted/50 flex-shrink-0">
          {status === "idle" ? (
            <button
              onClick={handleStartExecution}
              disabled={!goal?.trim() || !isActive}
              className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
            >
              Start Execution
            </button>
          ) : status === "running" ? (
            <button
              onClick={handleStopExecution}
              className="w-full py-2 px-4 bg-destructive text-destructive-foreground rounded-lg font-medium hover:bg-destructive/90 transition-colors"
            >
              Stop Execution
            </button>
          ) : (
            <button
              onClick={() => setStatus("idle")}
              className="w-full py-2 px-4 border border-input bg-background rounded-lg font-medium hover:bg-muted transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>
    </Card>
  );
};