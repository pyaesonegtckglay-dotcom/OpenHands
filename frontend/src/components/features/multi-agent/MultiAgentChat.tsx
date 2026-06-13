/**
 * Multi-Agent Chat Interface
 * Main component for multi-agent conversations
 */

import React, { useState } from "react";
import { Card } from "#/ui/card";
import { CardTitle } from "#/ui/card-title";
import { Button } from "#/ui/button";
import { Badge } from "#/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "#/ui/tabs";
import { Textarea } from "#/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "#/ui/select";
import { AgentSelector } from "./AgentSelector";
import { TeamPanel } from "./TeamPanel";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { ActivityFeed } from "./ActivityFeed";
import { multiAgentService, type Execution, type ExecutionEvent } from "#/services/multi-agent-service";

type CollaborationMode = "sequential" | "parallel" | "hierarchical";

export const MultiAgentChat: React.FC = () => {
  const [goal, setGoal] = useState("");
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [collaborationMode, setCollaborationMode] = useState<CollaborationMode>("sequential");
  const [activeTab, setActiveTab] = useState("chat");
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleStartExecution = () => {
    if (!goal.trim()) return;
    setIsExecuting(true);
    setActiveTab("activity");
  };

  const handleExecutionComplete = (executionId: string) => {
    setIsExecuting(false);
    loadExecution(executionId);
  };

  const loadExecution = async (executionId: string) => {
    try {
      const exec = await multiAgentService.getExecution(executionId);
      setExecution(exec);
    } catch (err) {
      console.error("Failed to load execution:", err);
    }
  };

  const handleClear = () => {
    setGoal("");
    setSelectedAgents([]);
    setEvents([]);
    setExecution(null);
  };

  const canExecute = goal.trim().length > 0 && selectedAgents.length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b bg-background">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Multi-Agent Orchestration</h1>
            <p className="text-sm text-muted-foreground">
              Coordinate multiple AI agents to accomplish complex goals
            </p>
          </div>
          <Badge variant="outline" className="text-sm">
            {selectedAgents.length} agent{selectedAgents.length !== 1 ? "s" : ""} selected
          </Badge>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Configuration */}
        <div className="w-80 border-r bg-muted/30 flex-shrink-0 overflow-y-auto p-4 space-y-4">
          {/* Goal Input */}
          <Card className="p-4">
            <CardTitle className="text-base mb-2">Goal</CardTitle>
            <Textarea
              placeholder="Describe the goal for your agent team..."
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={4}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground mt-2">
              {goal.length}/500 characters
            </p>
          </Card>

          {/* Collaboration Mode */}
          <Card className="p-4">
            <CardTitle className="text-base mb-2">Collaboration Mode</CardTitle>
            <Select
              value={collaborationMode}
              onValueChange={(value) => setCollaborationMode(value as CollaborationMode)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sequential">
                  <div className="flex items-center gap-2">
                    <span>Sequential</span>
                    <div>
                      <p className="text-xs text-muted-foreground">Agents work one after another</p>
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="parallel">
                  <div className="flex items-center gap-2">
                    <span>Parallel</span>
                    <div>
                      <p className="text-xs text-muted-foreground">Multiple agents work simultaneously</p>
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="hierarchical">
                  <div className="flex items-center gap-2">
                    <span>Hierarchical</span>
                    <div>
                      <p className="text-xs text-muted-foreground">Supervisor coordinates sub-agents</p>
                    </div>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </Card>

          {/* Agent Selection */}
          <AgentSelector
            selected={selectedAgents}
            onChange={setSelectedAgents}
            maxAgents={5}
          />

          {/* Actions */}
          <div className="space-y-2">
            <Button
              className="w-full"
              size="lg"
              disabled={!canExecute || isExecuting}
              onClick={handleStartExecution}
            >
              {isExecuting ? "Executing..." : "Start Execution"}
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={handleClear}
            >
              Clear
            </Button>
          </div>
        </div>

        {/* Main Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="w-full justify-start rounded-none border-b px-4 h-12 bg-background">
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="teams">Teams</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 m-0 overflow-hidden">
              <div className="h-full flex flex-col p-4">
                <Card className="flex-1 flex flex-col p-4">
                  <CardTitle className="mb-4">Conversation</CardTitle>
                  <div className="flex-1 overflow-y-auto">
                    {events.length === 0 && !execution ? (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        <div className="text-center">
                          <p className="text-lg mb-2">No conversation yet</p>
                          <p className="text-sm">
                            Configure your goal and agents, then start an execution
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {/* Goal Message */}
                        <div className="flex gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-medium">
                            You
                          </div>
                          <div className="flex-1">
                            <p className="font-medium mb-1">Goal</p>
                            <p className="text-sm bg-muted rounded-lg p-3">{goal}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {selectedAgents.length} agents - {collaborationMode}
                            </p>
                          </div>
                        </div>

                        {/* Execution Response */}
                        {execution && (
                          <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-secondary-foreground text-sm">
                              Bot
                            </div>
                            <div className="flex-1">
                              <p className="font-medium mb-1">Multi-Agent Response</p>
                              <div className="bg-muted rounded-lg p-3 space-y-2">
                                <p className="text-sm">
                                  <strong>Execution ID:</strong> {execution.execution_id}
                                </p>
                                <p className="text-sm">
                                  <strong>Status:</strong>{" "}
                                  <Badge variant={execution.status === "completed" ? "default" : "secondary"}>
                                    {execution.status}
                                  </Badge>
                                </p>
                                <p className="text-sm">
                                  <strong>Duration:</strong> {execution.duration_ms}ms
                                </p>
                                {execution.results && (
                                  <div className="mt-2 pt-2 border-t">
                                    <p className="text-sm font-medium mb-1">Results:</p>
                                    <pre className="text-xs bg-background p-2 rounded overflow-x-auto">
                                      {JSON.stringify(execution.results, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="activity" className="flex-1 m-0 overflow-hidden p-4">
              <ActivityFeed
                goal={goal}
                agentTypes={selectedAgents}
                collaborationMode={collaborationMode}
                isActive={canExecute}
                onComplete={handleExecutionComplete}
              />
            </TabsContent>

            <TabsContent value="timeline" className="flex-1 m-0 overflow-hidden p-4">
              <ExecutionTimeline
                executionId={execution?.execution_id}
                events={events}
                execution={execution}
              />
            </TabsContent>

            <TabsContent value="teams" className="flex-1 m-0 overflow-y-auto p-4">
              <TeamPanel />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};