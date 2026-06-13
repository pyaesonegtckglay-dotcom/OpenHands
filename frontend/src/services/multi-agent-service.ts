/**
 * Multi-Agent API Service
 * Handles all multi-agent orchestration API calls
 */

import { openHands } from "#/api/open-hands-axios";

export interface AgentType {
  type: string;
  name: string;
  description: string;
  capabilities: string[];
  tools: string[];
}

export interface Team {
  id: string;
  user_id: string;
  name: string;
  goal: string;
  collaboration_mode: "sequential" | "parallel" | "hierarchical";
  max_agents_parallel: number;
  shared_context: Record<string, any>;
  supervisor_id: string | null;
  status: string;
  results: Record<string, any>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Execution {
  execution_id: string;
  team_id: string | null;
  goal: string;
  agent_types: string[];
  collaboration_mode: string;
  status: "initializing" | "running" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  results: Record<string, any>;
  duration_ms: number;
  completed_agents: number;
}

export interface ExecutionEvent {
  type: "execution_started" | "agent_started" | "agent_completed" | "execution_completed" | "execution_failed" | "done" | "error";
  execution_id?: string;
  agent_id?: string;
  step?: number;
  result?: any;
  results?: any;
  duration_ms?: number;
  error?: string;
}

class MultiAgentService {
  private baseURL = "/api/v1";

  /**
   * Get available agent types
   */
  async getAgentTypes(): Promise<AgentType[]> {
    try {
      const { data } = await openHands.get<{ agent_types: AgentType[] }>(
        `${this.baseURL}/multi-agent/agents/types`
      );
      return data?.agent_types || [];
    } catch (err) {
      console.warn("Using fallback agent types due to API error:", err);
      // Return default agent types if API fails
      return [
        { type: "planner", name: "Planner Agent", description: "Breaks down complex goals into actionable steps", capabilities: ["planning", "goal_decomposition"], tools: ["reasoning"] },
        { type: "researcher", name: "Researcher Agent", description: "Gathers and synthesizes information", capabilities: ["web_search", "data_analysis"], tools: ["web_search"] },
        { type: "coder", name: "Coder Agent", description: "Writes, reviews, and refactors code", capabilities: ["coding", "debugging"], tools: ["code_editor"] },
        { type: "reviewer", name: "Reviewer Agent", description: "Reviews and provides feedback", capabilities: ["code_review", "quality_assurance"], tools: ["reasoning"] },
        { type: "executor", name: "Executor Agent", description: "Executes tasks and coordinates tools", capabilities: ["task_execution", "tool_use"], tools: ["python_executor"] },
        { type: "synthesizer", name: "Synthesizer Agent", description: "Combines outputs into cohesive results", capabilities: ["synthesis", "integration"], tools: ["reasoning"] },
        { type: "coordinator", name: "Coordinator Agent", description: "Orchestrates multiple agents", capabilities: ["coordination", "delegation"], tools: ["reasoning"] },
        { type: "generalist", name: "Generalist Agent", description: "Handles diverse tasks", capabilities: ["general_purpose", "adaptability"], tools: ["reasoning"] },
      ];
    }
  }

  /**
   * Create a team of agents
   */
  async createTeam(params: {
    goal: string;
    agent_types: string[];
    collaboration_mode?: "sequential" | "parallel" | "hierarchical";
    max_parallel?: number;
    team_name?: string;
  }): Promise<Team> {
    const { goal, agent_types, collaboration_mode = "sequential", max_parallel = 3, team_name } = params;
    const { data } = await openHands.post<Team>(
      `${this.baseURL}/multi-agent/teams/create`,
      null,
      {
        params: {
          goal,
          agent_types: agent_types.join(","),
          collaboration_mode,
          max_parallel,
          team_name,
        },
      }
    );
    return data;
  }

  /**
   * List all teams
   */
  async listTeams(): Promise<Team[]> {
    const { data } = await openHands.get<{ teams: Team[]; count: number }>(
      `${this.baseURL}/multi-agent/teams`
    );
    return data.teams;
  }

  /**
   * Get team details
   */
  async getTeam(teamId: string): Promise<Team> {
    const { data } = await openHands.get<Team>(
      `${this.baseURL}/multi-agent/teams/${teamId}`
    );
    return data;
  }

  /**
   * Execute a goal with agents
   */
  async executeGoal(params: {
    goal: string;
    agent_types?: string[];
    team_id?: string;
    collaboration_mode?: "sequential" | "parallel" | "hierarchical";
  }): Promise<Execution> {
    const { goal, agent_types, team_id, collaboration_mode = "sequential" } = params;
    const { data } = await openHands.post<Execution>(
      `${this.baseURL}/multi-agent/execute`,
      null,
      {
        params: {
          goal,
          agent_types: agent_types?.join(","),
          team_id,
          collaboration_mode,
        },
      }
    );
    return data;
  }

  /**
   * Execute goal with streaming
   */
  async executeGoalStream(
    params: {
      goal: string;
      agent_types?: string[];
      team_id?: string;
      collaboration_mode?: "sequential" | "parallel" | "hierarchical";
    },
    onEvent: (event: ExecutionEvent) => void
  ): Promise<Execution> {
    const { goal, agent_types, team_id, collaboration_mode = "sequential" } = params;
    
    const searchParams = new URLSearchParams({
      goal,
      collaboration_mode,
    });
    
    if (agent_types?.length) {
      searchParams.set("agent_types", agent_types.join(","));
    }
    if (team_id) {
      searchParams.set("team_id", team_id);
    }

    const baseURL = import.meta.env.VITE_BACKEND_BASE_URL || window?.location.host || "";
    const protocol = window?.location.protocol || "https:";
    const host = baseURL.startsWith("http") ? baseURL : `${protocol}//${baseURL}`;

    const response = await fetch(
      `${host}/api/v1/multi-agent/execute/stream?${searchParams}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          Accept: "text/event-stream",
        },
      }
    );

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    if (!reader) {
      throw new Error("No reader available");
    }

    let finalResult: Execution | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const event = JSON.parse(line.slice(6)) as ExecutionEvent;
            onEvent(event);
            
            if (event.type === "done" && event.result) {
              finalResult = event.result;
            }
          } catch (e) {
            console.error("Failed to parse event:", e);
          }
        }
      }
    }

    if (!finalResult) {
      throw new Error("Execution completed without result");
    }

    return finalResult;
  }

  /**
   * List executions
   */
  async listExecutions(limit = 20): Promise<Execution[]> {
    const { data } = await openHands.get<{ executions: Execution[]; count: number }>(
      `${this.baseURL}/multi-agent/executions`,
      { params: { limit } }
    );
    return data.executions;
  }

  /**
   * Get execution details
   */
  async getExecution(executionId: string): Promise<Execution> {
    const { data } = await openHands.get<Execution>(
      `${this.baseURL}/multi-agent/executions/${executionId}`
    );
    return data;
  }
}

export const multiAgentService = new MultiAgentService();