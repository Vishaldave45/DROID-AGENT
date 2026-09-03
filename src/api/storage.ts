import { api } from './client';

export interface StorageStats {
  storage_type: string;
  db_path: string;
  db_size_bytes: number;
  db_size_kb: number;
  total_tasks: number;
  status_distribution: Record<string, number>;
  total_timeline_events: number;
  total_checkpoints: number;
  total_messages?: number;
}

export interface TaskItem {
  task_id: string;
  repository_id: string;
  requirement: string;
  status: string;
  iteration: number;
  current_step_index: number;
  files_read: string[];
  files_changed: string[];
  test_runs_count: number;
  test_failures_count: number;
  errors: string[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  event_id: string;
  task_id: string;
  iteration: number;
  event_type: string;
  payload: Record<string, any>;
  timestamp: string;
}

export interface CheckpointItem {
  checkpoint_id: string;
  task_id: string;
  iteration: number;
  state_snapshot: Record<string, any>;
  git_commit_hash: string | null;
  description: string;
  created_at: string;
}

export interface TaskDetailResponse {
  task: TaskItem;
  timeline: TimelineEvent[];
  checkpoints: CheckpointItem[];
  messages: any[];
}

export const storageApi = {
  getStats: () => api.get<StorageStats>('/api/storage/stats'),

  listTasks: (status?: string) =>
    api.get<{ tasks: TaskItem[]; total: number }>(
      status && status !== 'ALL' ? `/api/storage/tasks?status=${encodeURIComponent(status)}` : '/api/storage/tasks'
    ),

  getTask: (taskId: string) => api.get<TaskDetailResponse>(`/api/storage/tasks/${encodeURIComponent(taskId)}`),

  createTask: (requirement: string, repoId: string = 'repo_main') =>
    api.post<{ success: boolean; task: TaskItem }>('/api/storage/tasks', { requirement, repoId }),

  pauseTask: (taskId: string, reason: string = 'Manual user pause') =>
    api.post<{ success: boolean; status: string }>(`/api/storage/tasks/${encodeURIComponent(taskId)}/pause`, { reason }),

  resumeTask: (taskId: string) =>
    api.post<{ success: boolean; status: string }>(`/api/storage/tasks/${encodeURIComponent(taskId)}/resume`, {}),

  createCheckpoint: (taskId: string, description: string = 'Manual checkpoint snapshot') =>
    api.post<{ success: boolean; checkpoint_id: string }>(
      `/api/storage/tasks/${encodeURIComponent(taskId)}/checkpoint`,
      { description }
    ),

  restoreCheckpoint: (checkpointId: string) =>
    api.post<{ success: boolean; checkpoint_id: string; restored: boolean }>(
      `/api/storage/checkpoints/${encodeURIComponent(checkpointId)}/restore`,
      {}
    ),

  deleteTask: (taskId: string) =>
    api.delete<{ success: boolean; deleted_task_id: string }>(`/api/storage/tasks/${encodeURIComponent(taskId)}`),

  seedDemoData: () => api.post<{ success: boolean; seeded_tasks: number }>('/api/storage/seed', {}),
};
