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
  shared_context: Record<string, unknown>;
  supervisor_id: string | null;
  status: string;
  results: Record<string, unknown>;
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
  results: Record<string, unknown>;
  duration_ms: number;
  completed_agents: number;
}

export interface ExecutionEvent {
  type: "execution_started" | "agent_started" | "agent_completed" | "execution_completed" | "execution_failed" | "done" | "error";
  execution_id?: string;
  agent_id?: string;
  step?: number;
  result?: unknown;
  results?: unknown;
  duration_ms?: number;
  error?: string;
}

class MultiAgentService {
  private baseURL = "/api/v1";
  private backendURL = "https://manusai-backend.onrender.com/api/v1";
  private accessToken: string | null = null;

  constructor() {
    // Get token from localStorage on init
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      
      // Listen for token updates
      window.addEventListener("storage", (e) => {
        if (e.key === "access_token") {
          this.accessToken = e.newValue;
        }
      });
      
      // Set backend URL from env if available
      const envBackend = import.meta.env.VITE_BACKEND_BASE_URL;
      if (envBackend) {
        const protocol = window.location.protocol || "https:";
        this.backendURL = `${protocol}//${envBackend}/api/v1`;
      }
    }
  }

  private getAuthHeaders(): Record<string, string> {
    if (!this.accessToken) {
      this.accessToken = localStorage.getItem("access_token");
    }
    return this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {};
  }

  private getRequestURL(path: string): string {
    // Use absolute URL for multi-agent service to ensure backend calls work
    return `${this.backendURL}${path}`;
  }

  /**
   * Set the access token (call after login)
   */
  setAccessToken(token: string) {
    this.accessToken = token;
  }

  /**
   * Get available agent types
   */
  async getAgentTypes(): Promise<AgentType[]> {
    try {
      const { data } = await openHands.get<{ agent_types: AgentType[] }>(
        this.getRequestURL("/multi-agent/agents/types"),
        { headers: this.getAuthHeaders() }
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
   * Login user and get token
   */
  async login(email: string, password: string): Promise<{ access_token: string; user_id: string }> {
    const { data } = await openHands.post<{ access_token: string; user_id: string }>(
      this.getRequestURL("/auth/login"),
      { email, password }
    );
    if (data.access_token) {
      this.accessToken = data.access_token;
      localStorage.setItem("access_token", data.access_token);
    }
    return data;
  }

  /**
   * Register new user
   */
  async register(email: string, password: string, username: string): Promise<{ access_token: string; user_id: string }> {
    const { data } = await openHands.post<{ access_token: string; user_id: string }>(
      this.getRequestURL("/auth/register"),
      { email, password, username }
    );
    if (data.access_token) {
      this.accessToken = data.access_token;
      localStorage.setItem("access_token", data.access_token);
    }
    return data;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    if (!this.accessToken) {
      this.accessToken = localStorage.getItem("access_token");
    }
    return !!this.accessToken;
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
      this.getRequestURL("/multi-agent/teams/create"),
      null,
      {
        params: {
          goal,
          agent_types: agent_types.join(","),
          collaboration_mode,
          max_parallel,
          team_name,
        },
        headers: this.getAuthHeaders(),
      }
    );
    return data;
  }

  /**
   * List all teams
   */
  async listTeams(): Promise<Team[]> {
    const { data } = await openHands.get<{ teams: Team[]; count: number }>(
      this.getRequestURL("/multi-agent/teams"),
      { headers: this.getAuthHeaders() }
    );
    return data.teams;
  }

  /**
   * Get team details
   */
  async getTeam(teamId: string): Promise<Team> {
    const { data } = await openHands.get<Team>(
      this.getRequestURL(`/multi-agent/teams/${teamId}`),
      { headers: this.getAuthHeaders() }
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
      this.getRequestURL("/multi-agent/execute"),
      null,
      {
        params: {
          goal,
          agent_types: agent_types?.join(","),
          team_id,
          collaboration_mode,
        },
        headers: this.getAuthHeaders(),
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

    const response = await fetch(
      `${this.backendURL}/multi-agent/execute/stream?${searchParams}`,
      {
        headers: {
          Authorization: `Bearer ${this.accessToken || localStorage.getItem("access_token")}`,
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
              finalResult = event.result as Execution;
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
      this.getRequestURL("/multi-agent/executions"),
      { params: { limit }, headers: this.getAuthHeaders() }
    );
    return data.executions;
  }

  /**
   * Get execution details
   */
  async getExecution(executionId: string): Promise<Execution> {
    const { data } = await openHands.get<Execution>(
      this.getRequestURL(`/multi-agent/executions/${executionId}`),
      { headers: this.getAuthHeaders() }
    );
    return data;
  }
}

export const multiAgentService = new MultiAgentService();