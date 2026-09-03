import { api } from './client';

export interface SyntaxValidationResult {
  valid: boolean;
  language: string;
  error_message: string | null;
  line_number: number | null;
  column_number: number | null;
  syntax_tree_depth?: number;
}

export interface DiffResult {
  success: boolean;
  diff: string;
  originalLineCount: number;
  modifiedLineCount: number;
  hasChanges: boolean;
}

export interface SurgicalEditResult {
  success: boolean;
  error?: string;
  additions: number;
  deletions: number;
  preHash?: string;
  postHash?: string;
  syntaxValid: boolean;
  syntaxErrorLine?: number | null;
  finalContent: string;
}

export const patcherApi = {
  validate: (code: string, filePath?: string, language?: string) =>
    api.post<{ success: boolean; result: SyntaxValidationResult }>('/api/patcher/validate', {
      code,
      filePath,
      language,
    }),

  diff: (original: string, modified: string, fromFile?: string, toFile?: string) =>
    api.post<DiffResult>('/api/patcher/diff', {
      original,
      modified,
      fromFile,
      toFile,
    }),

  apply: (
    source: string,
    targetContent: string,
    replacementContent: string,
    allowFuzzy: boolean = false,
    validateSyntax: boolean = true
  ) =>
    api.post<SurgicalEditResult>('/api/patcher/apply', {
      source,
      targetContent,
      replacementContent,
      allowFuzzy,
      validateSyntax,
    }),
};
