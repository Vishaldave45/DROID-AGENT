import { api } from './client';

export interface RepoSummary {
  root_path: string;
  languages: string[];
  total_files: number;
  total_lines_of_code: number;
  entry_points: string[];
  test_frameworks: string[];
  key_directories: string[];
  language_breakdown: Record<string, number>;
  frameworks: string[];
  manifests: Array<{
    manifest_file: string;
    manifest_type: string;
    packages: Record<string, string>;
    dev_packages: Record<string, string>;
  }>;
  files_sample: Array<{
    path: string;
    relative_path: string;
    language: string;
    size_bytes: number;
    lines_of_code: number;
    is_test: boolean;
    is_entry_point: boolean;
  }>;
}

export interface GraphNode {
  node_id: string;
  node_type: string;
  name: string;
  file_path: string;
  line_start: number;
  line_end: number;
  dependencies: string[];
  docstring: string | null;
  signature: string | null;
  async_function: boolean;
  decorators: string[];
  parent_id: string | null;
  complexity_score: number;
  metadata: Record<string, any>;
}

export interface GraphLink {
  source_id: string;
  target_id: string;
  edge_type: string;
  weight: number;
  metadata: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  stats: {
    total_nodes: number;
    total_edges: number;
    node_distribution: Record<string, number>;
    edge_distribution: Record<string, number>;
    total_files: number;
  };
}

export interface SymbolDetails {
  symbol: GraphNode;
  callers: GraphNode[];
  callees: Array<{
    target_id: string;
    target_name: string;
    target_node: GraphNode | null;
    resolved: boolean;
  }>;
  dependencies: Array<{
    edge_type: string;
    target_id: string;
    target_name: string;
    target_type: string;
  }>;
}

export interface ContextPackage {
  task_id: string;
  repository_summary: RepoSummary;
  relevant_files: Record<string, string>;
  symbols: GraphNode[];
  estimated_tokens: number;
  metadata: Record<string, any>;
}

export interface RepoStats {
  root_path: string;
  total_files: number;
  total_lines: number;
  languages: string[];
}

export const repoApi = {
  scan: (path: string = './nexforge-droid') =>
    api.get<RepoSummary>(`/api/repo/scan?path=${encodeURIComponent(path)}`),

  graph: (path: string = './nexforge-droid', maxNodes: number = 150) =>
    api.get<GraphData>(`/api/repo/graph?path=${encodeURIComponent(path)}&maxNodes=${maxNodes}`),

  searchSymbols: (query: string, path: string = './nexforge-droid') =>
    api.get<{ results: GraphNode[]; total: number }>(
      `/api/repo/symbols?path=${encodeURIComponent(path)}&query=${encodeURIComponent(query)}`
    ),

  symbolDetails: (symbol: string, path: string = './nexforge-droid') =>
    api.get<SymbolDetails>(
      `/api/repo/symbol-details?path=${encodeURIComponent(path)}&symbol=${encodeURIComponent(symbol)}`
    ),

  assembleContext: (requirement: string, path: string = './nexforge-droid') =>
    api.post<ContextPackage>('/api/repo/context', { requirement, path }),

  stats: (path: string = './nexforge-droid') =>
    api.get<RepoStats>(`/api/repo/stats?path=${encodeURIComponent(path)}`),
};
