import { api } from './client';

export interface DetailedTestCase {
  id: string;
  name: string;
  module: string;
  className: string;
  status: 'passed' | 'failed' | 'error' | 'skipped';
  durationMs: number;
  description: string;
  errorMessage?: string;
}

export interface DetailedTestRunResponse {
  success: boolean;
  total: number;
  passed: number;
  failed: number;
  errors: number;
  tests: DetailedTestCase[];
}

export interface TestSuiteRunResponse {
  success: boolean;
  total: number;
  failures: number;
  errors: number;
  passed: number;
  output: string;
}

export const testsApi = {
  getDetailed: (moduleFilter?: string) =>
    api.post<DetailedTestRunResponse>('/api/tests/detailed', { module: moduleFilter }),

  runQuickSuite: () => api.post<TestSuiteRunResponse>('/api/tests/run', {}),
};
