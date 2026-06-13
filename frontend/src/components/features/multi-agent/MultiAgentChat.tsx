/**
 * Multi-Agent Chat Interface
 * Main component for multi-agent conversations
 */

import React, { useState, useCallback, useEffect } from "react";
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

/**
 * Login Form Component
 */
const LoginForm: React.FC<{ onLogin: () => void }> = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegister) {
        await multiAgentService.register(email, password, username);
      } else {
        await multiAgentService.login(email, password);
      }
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full">
      <Card className="w-full max-w-md p-6">
        <CardTitle className="text-xl mb-4 text-center">
          {isRegister ? "Create Account" : "Sign In"}
        </CardTitle>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className="text-sm font-medium mb-1 block">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your_username"
                className="w-full px-3 py-2 border rounded-md bg-background"
                required
              />
            </div>
          )}
          
          <div>
            <label className="text-sm font-medium mb-1 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-3 py-2 border rounded-md bg-background"
              required
            />
          </div>
          
          <div>
            <label className="text-sm font-medium mb-1 block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 border rounded-md bg-background"
              required
            />
          </div>

          {error && (
            <div className="text-sm text-red-500 bg-red-50 dark:bg-red-950 rounded-lg p-2">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Please wait..." : isRegister ? "Create Account" : "Sign In"}
          </Button>
        </form>

        <div className="mt-4 text-center text-sm">
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="text-primary hover:underline"
          >
            {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
          </button>
        </div>
      </Card>
    </div>
  );
};

export const MultiAgentChat: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [goal, setGoal] = useState("");
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [collaborationMode, setCollaborationMode] = useState<CollaborationMode>("sequential");
  const [activeTab, setActiveTab] = useState("chat");
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check authentication on mount
  useEffect(() => {
    setIsAuthenticated(multiAgentService.isAuthenticated());
  }, []);

  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true);
  }, []);

  const handleStartExecution = useCallback(async () => {
    if (!goal.trim() || selectedAgents.length === 0) return;
    
    setIsExecuting(true);
    setError(null);
    setActiveTab("activity");
    setEvents([
      {
        type: "execution_started",
        message: "Starting multi-agent execution...",
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      const result = await multiAgentService.executeGoal({
        goal: goal.trim(),
        agent_types: selectedAgents,
        collaboration_mode: collaborationMode,
      });

      setExecution(result);
      setEvents((prev) => [
        ...prev,
        {
          type: "execution_completed",
          message: `Execution completed: ${result.execution_id}`,
          timestamp: new Date().toISOString(),
        },
      ]);

      // Add result events
      if (result.results && typeof result.results === 'object' && 'steps' in result.results) {
        const steps = (result.results as { steps?: { step: number; output: string }[] }).steps || [];
        steps.forEach((step: { step: number; output: string }, idx: number) => {
          setEvents((prev) => [
            ...prev,
            {
              type: "agent_output",
              message: `Agent ${idx + 1} output: ${step.output?.substring(0, 100)}...`,
              timestamp: new Date().toISOString(),
            },
          ]);
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Execution failed";
      setError(errorMessage);
      setEvents((prev) => [
        ...prev,
        {
          type: "error",
          message: `Error: ${errorMessage}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsExecuting(false);
    }
  }, [goal, selectedAgents, collaborationMode]);

  const handleExecutionComplete = useCallback((executionId: string) => {
    loadExecution(executionId);
  }, []);

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
    setError(null);
  };

  const canExecute = goal.trim().length > 0 && selectedAgents.length > 0;

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-shrink-0 p-4 border-b bg-background">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Multi-Agent Orchestration</h1>
              <p className="text-sm text-muted-foreground">
                Sign in to coordinate multiple AI agents
              </p>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <LoginForm onLogin={handleLoginSuccess} />
        </div>
      </div>
    );
  }

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
            {error && (
              <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-2">
                {error}
              </div>
            )}
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
                execution={execution ?? undefined}
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