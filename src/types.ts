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
