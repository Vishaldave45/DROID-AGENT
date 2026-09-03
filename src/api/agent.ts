import { api } from './client';

export interface AgentStepAction {
  tool: string;
  arguments: Record<string, any>;
  result?: any;
  error?: string;
}

export interface AgentStep {
  step: number;
  thought?: string;
  action?: AgentStepAction;
  observation?: string;
  timestamp?: string;
}

export interface AgentRunParams {
  requirement: string;
  provider?: 'gemini' | 'mock';
  mockScenario?: string;
  maxIterations?: number;
}

export interface AgentRunResponse {
  success: boolean;
  requirement: string;
  iterations: number;
  status: 'COMPLETED' | 'FAILED' | 'MAX_ITERATIONS_REACHED';
  steps: AgentStep[];
  filesRead: string[];
  filesModified: string[];
  finalSummary: string;
  error?: string;
}

export const agentApi = {
  run: (params: AgentRunParams) => api.post<AgentRunResponse>('/api/agent/run', params),
};
