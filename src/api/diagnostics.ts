import { api } from './client';

export interface ParsedFrame {
  file_path: string;
  line_number: number;
  function_name: string;
  code_line: string;
  locals: Record<string, any>;
  is_workspace_file: boolean;
}

export interface ParsedFailure {
  error_type: string;
  error_message: string;
  category: string;
  frames: ParsedFrame[];
  innermost_frame: ParsedFrame | null;
  raw_traceback: string;
}

export interface DiagnosticHypothesis {
  id: string;
  category: string;
  summary: string;
  root_cause: string;
  confidence: number;
  suggested_action: string;
  target_file: string;
  target_line: number;
  code_context: string | null;
  verification_cmd: string;
}

export interface DiagnosticLoopIteration {
  iteration: number;
  test_output_snippet: string;
  failures_count: number;
  hypothesis: DiagnosticHypothesis | null;
  patch_applied: boolean;
  rollback_performed: boolean;
}

export interface DiagnosticLoopResult {
  success: boolean;
  total_iterations: number;
  fixed: boolean;
  regressed: boolean;
  oscillated: boolean;
  final_status: string;
  timeline: DiagnosticLoopIteration[];
  summary: string;
}

export const diagnosticsApi = {
  parse: (text: string) =>
    api.post<{ success: boolean; count: number; failures: ParsedFailure[] }>('/api/diagnostics/parse', { text }),

  diagnose: (text: string, codeContext?: string, targetFile?: string) =>
    api.post<{ success: boolean; count: number; hypotheses: DiagnosticHypothesis[]; error?: string }>(
      '/api/diagnostics/diagnose',
      { text, codeContext, targetFile }
    ),

  runLoop: (cmd?: string, maxIterations: number = 4, autoRollback: boolean = true) =>
    api.post<{ success: boolean; result: DiagnosticLoopResult }>('/api/diagnostics/loop', {
      cmd,
      maxIterations,
      autoRollback,
    }),
};
