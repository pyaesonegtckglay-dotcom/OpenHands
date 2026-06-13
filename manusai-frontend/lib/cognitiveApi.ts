import { api } from "./api";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AnalyzeResponse {
  intent: string;
  intent_confidence: number;
  complexity: number;
  complexity_level: string;
  task_type: string;
  planning_required: boolean;
  plan_depth: string;
  goal: string;
  domain: string;
  desired_output: string;
  reason: string;
  keywords: string[];
}

export interface PlanStep {
  id: string;
  title: string;
  description: string;
  expected_output: string;
  dependencies: string[];
  status: string;
}

export interface CreatePlanResponse {
  plan_id: string;
  goal: string;
  steps: PlanStep[];
  plan_depth: string;
  provider_used: string;
  model_used: string;
  step_count: number;
  is_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
}

export interface PlanDetail {
  plan_id: string;
  goal: string;
  intent?: string;
  task_type?: string;
  complexity?: number;
  planning_required?: boolean;
  plan_depth?: string;
  provider_used?: string;
  model_used?: string;
  created_at?: string;
  steps: PlanStep[];
}

export interface PlanListItem {
  plan_id: string;
  goal: string;
  intent?: string;
  task_type?: string;
  complexity?: number;
  planning_required?: boolean;
  plan_depth?: string;
  provider_used?: string;
  status?: string;
  created_at?: string;
}

// ─── API Calls ────────────────────────────────────────────────────────────────

export const cognitiveAPI = {
  analyze: (message: string) =>
    api.post<AnalyzeResponse>("/api/v1/cognitive/analyze", { message }),

  createPlan: (goal: string, depth?: string) =>
    api.post<CreatePlanResponse>("/api/v1/planner/create", { goal, depth }),

  getPlan: (planId: string) =>
    api.get<PlanDetail>(`/api/v1/planner/${planId}`),

  listPlans: (limit = 20, offset = 0) =>
    api.get<{ plans: PlanListItem[]; total: number }>(
      `/api/v1/planner/list?limit=${limit}&offset=${offset}`
    ),
};
