import { api } from './client';
import { SubsystemInfo } from '../types';

export interface SystemManifest {
  system: string;
  version: string;
  phase: number;
  environment: string;
  subsystems: Record<string, string>;
}

export interface SystemManifestResponse {
  success: boolean;
  manifest: SystemManifest;
  pythonVersion: string;
  platform: string;
  toolCount: number;
  environment: string;
  defaultModel: string;
  maxContextTokens: number;
}

export interface SubsystemsResponse {
  success: boolean;
  count: number;
  registeredTools: string[];
  subsystems: SubsystemInfo[];
}

export interface ContextBudgetResponse {
  success: boolean;
  budget: {
    maxTotalTokens: number;
    systemPromptTokens: number;
    taskSpecTokens: number;
    repoSummaryTokens: number;
    relevantFilesTokens: number;
    symbolGraphTokens: number;
    conversationReserveTokens: number;
  };
  allocated: {
    estimatedTokens: number;
    symbolCount: number;
    fileCount: number;
  };
  symbols: Array<{
    name: string;
    file_path: string;
    node_type: string;
    complexity_score: number;
  }>;
}

export const systemApi = {
  getHealth: () => api.get<{ status: string; service: string; phase: number }>('/api/health'),

  getManifest: () => api.get<SystemManifestResponse>('/api/system/manifest'),

  getSubsystems: () => api.get<SubsystemsResponse>('/api/system/subsystems'),

  getContextBudget: (params?: { path?: string; requirement?: string; maxTokens?: number }) =>
    api.post<ContextBudgetResponse>('/api/context/budget', params || {}),
};
