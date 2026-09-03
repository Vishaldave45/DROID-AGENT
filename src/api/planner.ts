import { api } from './client';

export interface PlanStep {
  step_id: string;
  title: string;
  description: string;
  tool_name: string;
  arguments: Record<string, any>;
  dependencies: string[];
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'SKIPPED';
  verification: {
    command?: string;
    expected_outcome?: string;
  };
  retry_count: number;
}

export interface TaskPlan {
  task_id: string;
  requirement: string;
  steps: PlanStep[];
  status: string;
  created_at: string;
  estimated_complexity: string;
}

export interface PlanGenerationResponse {
  success: boolean;
  plan: TaskPlan;
  contextPackage?: {
    estimatedTokens: number;
    symbolCount: number;
    fileCount: number;
  };
}

export interface ReplanResponse {
  success: boolean;
  initialPlan: TaskPlan;
  remediatedPlan: TaskPlan;
}

export const plannerApi = {
  generate: (requirement: string, repo: string = '.', budget: number = 16000, taskId?: string) =>
    api.post<PlanGenerationResponse>('/api/planner/generate', {
      requirement,
      repo,
      budget,
      taskId,
    }),

  replan: (requirement: string, failedStepId: string, error: string) =>
    api.post<ReplanResponse>('/api/planner/replan', {
      requirement,
      failedStepId,
      error,
    }),
};
