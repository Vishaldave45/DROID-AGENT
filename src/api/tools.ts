import { api } from './client';

export interface ToolDefinition {
  name: string;
  category?: 'filesystem' | 'search' | 'terminal' | 'git' | 'patcher' | 'diagnostics' | 'planner';
  description: string;
  input_schema: {
    type?: string;
    properties?: Record<string, any>;
    required?: string[];
  };
  requires_permission?: boolean;
  exampleArgs?: Record<string, any>;
}

export interface ToolExecutionResponse {
  success: boolean;
  output?: any;
  error?: string;
  exit_code?: number;
  metadata?: Record<string, any>;
}

export const toolsApi = {
  list: () => api.get<{ tools: ToolDefinition[]; total: number }>('/api/tools/list'),

  execute: (tool: string, args: Record<string, any>) =>
    api.post<ToolExecutionResponse>('/api/tools/execute', {
      tool,
      arguments: args,
    }),
};
