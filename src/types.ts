export interface SubsystemInfo {
  id: string;
  name: string;
  category: 'core' | 'execution' | 'intelligence' | 'governance';
  status: 'ready' | 'in_progress' | 'planned';
  phase: number;
  description: string;
  keyFiles: string[];
  interfaces: string[];
  securityRole: string;
}

export interface TestCaseResult {
  name: string;
  module: string;
  status: 'passed' | 'failed' | 'skipped';
  durationMs: number;
  description: string;
}

export interface PhaseRoadmapItem {
  phase: number;
  title: string;
  status: 'completed' | 'active' | 'upcoming';
  objective: string;
  deliverables: string[];
}

export interface ChangesetFile {
  file_path: string;
  additions: number;
  deletions: number;
  is_new_file: boolean;
  is_deleted_file: boolean;
  syntax_valid: boolean;
  syntax_error: string | null;
  diff: string;
}

export interface Changeset {
  changeset_id: string;
  title: string;
  description: string;
  branch_name: string;
  status: 'DRAFT' | 'STAGED' | 'COMMITTED' | 'ROLLED_BACK';
  created_at: string;
  total_files: number;
  total_additions: number;
  total_deletions: number;
  commit_message: string | null;
  pr_body: string | null;
  affected_symbols: string[];
  files: ChangesetFile[];
}

export interface ApprovalRequest {
  request_id: string;
  action_type: string;
  description: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  payload: Record<string, any>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  reason: string | null;
}

export interface RefactorPlanFile {
  file_path: string;
  occurrences_found: number;
  syntax_valid: boolean;
}

export interface RefactorPlan {
  refactor_id: string;
  operation: string;
  details: string;
  total_modifications: number;
  all_syntax_valid: boolean;
  affected_files: RefactorPlanFile[];
}

export interface AgentStreamEvent {
  step: number;
  total: number;
  event: {
    type: 'THINKING' | 'TOOL_CALL' | 'TOOL_RESULT' | 'AST_VALIDATION' | 'PATCH_STAGE' | 'REGRESSION_TEST' | 'COMPLETION';
    text?: string;
    tool?: string;
    args?: Record<string, any>;
    success?: boolean;
    count?: number;
    status?: string;
    file?: string;
    diffLines?: string;
    suite?: string;
    testsPassed?: number;
    summary?: string;
  };
}
