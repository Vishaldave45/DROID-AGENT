import { api } from './client';
import { Changeset, ApprovalRequest, RefactorPlan } from '../types';

export interface ChangesetsResponse {
  success: boolean;
  count: number;
  changesets: Changeset[];
}

export interface ApprovalsResponse {
  success: boolean;
  count: number;
  requests: ApprovalRequest[];
}

export interface RefactorPlanResponse {
  success: boolean;
  plan: RefactorPlan;
  changeset?: Changeset;
  error?: string;
}

export interface ApprovalResolutionResponse {
  success: boolean;
  status: string;
  resolved_at: string;
  resolved_by: string;
  error?: string;
}

export interface CommitChangesetResponse {
  success: boolean;
  commit_hash?: string;
  branch_name?: string;
  files_committed?: number;
  message?: string;
  error?: string;
}

export interface CreateChangesetParams {
  title: string;
  description: string;
  branch_name?: string;
}

export interface StageFileParams {
  changeset_id: string;
  file_path: string;
  new_content: string;
}

export interface ApplyChangesetParams {
  changeset_id: string;
  commit_message?: string;
  create_branch?: boolean;
}

export const orchestratorApi = {
  getChangesets: () => api.get<ChangesetsResponse>('/api/orchestrator/changesets'),

  getApprovals: (status?: string) => {
    const query = status && status !== 'ALL' ? `?status=${encodeURIComponent(status)}` : '';
    return api.get<ApprovalsResponse>(`/api/orchestrator/approvals${query}`);
  },

  planRefactor: (oldName: string, newName: string, targetScope: string = 'workspace') =>
    api.post<RefactorPlanResponse>('/api/orchestrator/refactor/plan', {
      oldName,
      newName,
      targetScope,
    }),

  createChangeset: (params: CreateChangesetParams) =>
    api.post<{ success: boolean; changeset: Changeset }>('/api/orchestrator/changesets', params),

  stageFile: (params: StageFileParams) =>
    api.post<{ success: boolean; changeset: Changeset }>('/api/orchestrator/changesets/stage', params),

  applyChangeset: (params: ApplyChangesetParams) =>
    api.post<CommitChangesetResponse>('/api/orchestrator/changesets/apply', params),

  resolveApproval: (requestId: string, approved: boolean, reason?: string) =>
    api.post<ApprovalResolutionResponse>('/api/orchestrator/approvals/decide', {
      requestId,
      decision: approved ? 'APPROVED' : 'REJECTED',
      reason: reason || 'Approved by system operator',
      approver: 'lead_security_architect',
    }),
};
