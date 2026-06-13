/**
 * Execution Timeline Component
 * Shows the progress and history of multi-agent executions
 */

import React from "react";
import { Card } from "#/ui/card";
import { Badge } from "#/ui/badge";
import { multiAgentService, type Execution, type ExecutionEvent } from "#/services/multi-agent-service";

interface ExecutionTimelineProps {
  executionId?: string;
  events?: ExecutionEvent[];
  execution?: Execution;
  compact?: boolean;
}

const eventIcons: Record<string, string> = {
  execution_started: "Start",
  agent_started: "Agent",
  agent_completed: "Done",
  execution_completed: "Complete",
  execution_failed: "Failed",
};

const eventLabels: Record<string, string> = {
  execution_started: "Execution Started",
  agent_started: "Agent Working",
  agent_completed: "Agent Completed",
  execution_completed: "Execution Complete",
  execution_failed: "Execution Failed",
};

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({
  executionId,
  events = [],
  execution,
  compact = false,
}) => {
  const [execDetails, setExecDetails] = React.useState<Execution | null>(execution || null);
  const [loading, setLoading] = React.useState(!execution && !!executionId);

  React.useEffect(() => {
    if (executionId && !execution) {
      loadExecution();
    }
  }, [executionId]);

  const loadExecution = async () => {
    if (!executionId) return;
    try {
      setLoading(true);
      const exec = await multiAgentService.getExecution(executionId);
      setExecDetails(exec);
    } catch (err) {
      console.error("Failed to load execution:", err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "failed":
        return "bg-red-500";
      case "running":
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  if (loading) {
    return (
      <Card className="p-4">
        <div className="space-y-4">
          <div className="h-6 w-32 bg-muted animate-pulse rounded" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3">
              <div className="w-8 h-8 bg-muted animate-pulse rounded-full" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-24 bg-muted animate-pulse rounded" />
                <div className="h-3 w-32 bg-muted animate-pulse rounded" />
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  const displayExecution = execDetails || execution;
  const displayEvents = events.length > 0 ? events : [];

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-lg">Execution Timeline</h2>
        {displayExecution && (
          <div className="flex items-center gap-2">
            <Badge className={getStatusColor(displayExecution.status)}>
              {displayExecution.status}
            </Badge>
            {displayExecution.duration_ms && (
              <span className="text-xs text-muted-foreground">
                {displayExecution.duration_ms}ms
              </span>
            )}
          </div>
        )}
      </div>
      
      {displayExecution?.execution_id && (
        <p className="text-xs text-muted-foreground font-mono mb-4">
          ID: {displayExecution.execution_id}
        </p>
      )}

      <div className={`space-y-3 ${compact ? "max-h-[300px] overflow-y-auto" : ""}`}>
        {!displayExecution && displayEvents.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No execution data</p>
            <p className="text-sm mt-1">Start an execution to see the timeline</p>
          </div>
        ) : (
          <>
            {displayEvents.map((event, index) => (
              <div key={index} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                    {eventIcons[event.type] || "?"}
                  </div>
                  {index < displayEvents.length - 1 && (
                    <div className="w-0.5 flex-1 bg-border mt-1 min-h-[20px]" />
                  )}
                </div>
                <div className="flex-1 pb-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">
                      {eventLabels[event.type] || event.type}
                    </span>
                    {event.step && (
                      <Badge variant="secondary" className="text-xs">
                        Step {event.step}
                      </Badge>
                    )}
                  </div>
                  {event.agent_id && (
                    <p className="text-xs text-muted-foreground font-mono mt-1">
                      Agent: {event.agent_id.slice(0, 8)}...
                    </p>
                  )}
                  {event.duration_ms && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Duration: {event.duration_ms}ms
                    </p>
                  )}
                  {event.error && (
                    <p className="text-xs text-red-500 mt-1">Error: {event.error}</p>
                  )}
                </div>
              </div>
            ))}

            {displayExecution?.results && displayEvents.length === 0 && (
              <div className="p-3 bg-muted rounded-lg">
                <h4 className="font-medium text-sm mb-2">Results</h4>
                <pre className="text-xs overflow-x-auto">
                  {JSON.stringify(displayExecution.results, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
};