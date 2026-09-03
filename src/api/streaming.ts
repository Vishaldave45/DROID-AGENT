import { api } from './client';
import { AgentStreamEvent } from '../types';

export interface DebuggerScenario {
  id: string;
  title: string;
  totalSteps: number;
}

export interface DebuggerScenariosResponse {
  success: boolean;
  count: number;
  scenarios: DebuggerScenario[];
}

export interface DebuggerSessionState {
  scenarioId: string;
  totalSteps: number;
  currentStepIndex: number;
  isPaused: boolean;
  isComplete: boolean;
  breakpoints: Record<string, boolean>;
}

export interface DebuggerStepResponse {
  success: boolean;
  done: boolean;
  step: number;
  total: number;
  event: any;
  rawEvent?: AgentStreamEvent;
  hitBreakpoint: boolean;
  scenarioId: string;
  error?: string;
}

export interface DebuggerResetResponse {
  success: boolean;
  scenarioId: string;
  session: DebuggerSessionState;
}

export interface DebuggerContinueResponse {
  success: boolean;
  hitBreakpoint: boolean;
  pausedAtStep: number;
  stepsExecuted: number;
  done: boolean;
  total: number;
  steps?: any[];
  events?: any[];
}

export const streamingApi = {
  getScenarios: () => api.get<DebuggerScenariosResponse>('/api/debugger/scenarios'),

  resetDebugger: (scenarioId: string) =>
    api.post<DebuggerResetResponse>('/api/debugger/reset', { scenarioId }),

  stepDebugger: () => api.post<DebuggerStepResponse>('/api/debugger/step', {}),

  continueDebugger: () => api.post<DebuggerContinueResponse>('/api/debugger/continue', {}),

  setBreakpoints: (eventTypes: string[]) =>
    api.post<{ success: boolean; breakpoints: Record<string, boolean> }>('/api/debugger/breakpoints', {
      eventTypes,
    }),

  createEventStreamUrl: (scenarioId?: string) => {
    const q = scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : '';
    return `/api/agent/stream-events${q}`;
  },
};
