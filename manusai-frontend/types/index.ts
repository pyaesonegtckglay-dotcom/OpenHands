export interface User {
  user_id: string;
  email: string;
  username: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  username: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  user_id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at?: string;
}

export interface ConversationList {
  conversations: Conversation[];
  total: number;
}

export interface ServiceStatus {
  status: "connected" | "disconnected";
  service: string;
  error?: string;
}

export interface SystemStatus {
  overall: "healthy" | "degraded";
  services: Record<string, ServiceStatus>;
}

// ── Phase 2: Task Graph Types ─────────────────────────────────────────────

export type TaskStatus = "PLANNED" | "READY" | "BLOCKED" | "WAITING" | "FAILED" | "COMPLETED";
export type TaskComplexity = "low" | "medium" | "high";

export interface AtomicTask {
  id: string;
  title: string;
  description: string;
  expected_output: string;
  estimated_complexity: TaskComplexity;
  estimated_duration: string;
  parent_task: string | null;
  child_tasks: string[];
  dependencies: string[];
  status: TaskStatus;
  order: number;
  parallelizable: boolean;
  is_blocking: boolean;
}

export interface TaskDependency {
  id: string;
  source_task_id: string;
  target_task_id: string;
}

export interface ExecutionWave {
  wave_number: number;
  task_ids: string[];
  task_titles: string[];
  can_run_parallel: boolean;
  all_blocking: boolean;
}

export interface TaskGraphStats {
  total_tasks: number;
  total_dependencies: number;
  total_waves: number;
  max_parallel: number;
  blocking_tasks: number;
  parallel_tasks: number;
  estimated_duration: string;
}

export interface TaskGraph {
  graph_id: string;
  plan_id: string;
  goal: string;
  tasks: AtomicTask[];
  dependencies: TaskDependency[];
  waves: ExecutionWave[];
  stats: TaskGraphStats;
  validation: {
    is_valid: boolean;
    errors: string[];
    warnings: string[];
    task_count: number;
    dependency_count: number;
  };
  provider_used?: string;
  regeneration_count?: number;
}

export interface CreateGraphResponse {
  graph_id: string;
  plan_id: string;
  goal: string;
  total_tasks: number;
  total_waves: number;
  max_parallel: number;
  estimated_duration: string;
  is_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
  regeneration_count: number;
}

export interface GraphListItem {
  graph_id: string;
  plan_id: string | null;
  goal: string;
  task_count: number;
  created_at: string;
}
