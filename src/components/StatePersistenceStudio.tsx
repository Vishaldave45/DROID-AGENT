import React, { useState, useEffect } from "react";
import {
  Database,
  Layers,
  History,
  Bookmark,
  Play,
  Pause,
  RotateCcw,
  Plus,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileCode,
  ArrowRight,
  ShieldCheck,
  HardDrive,
  Clock,
  Terminal,
  ChevronRight,
  Sparkles,
} from "lucide-react";

interface StorageStats {
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

interface TaskItem {
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

interface TimelineEvent {
  event_id: string;
  task_id: string;
  iteration: number;
  event_type: string;
  payload: Record<string, any>;
  timestamp: string;
}

interface CheckpointItem {
  checkpoint_id: string;
  task_id: string;
  iteration: number;
  state_snapshot: Record<string, any>;
  git_commit_hash: string | null;
  description: string;
  created_at: string;
}

export const StatePersistenceStudio: React.FC = () => {
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTaskDetails, setSelectedTaskDetails] = useState<{
    task: TaskItem;
    timeline: TimelineEvent[];
    checkpoints: CheckpointItem[];
    messages: any[];
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [activeTab, setActiveTab] = useState<"timeline" | "checkpoints" | "state_json" | "schema">("timeline");

  // New task form state
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);
  const [newRequirement, setNewRequirement] = useState("");
  const [newRepoId, setNewRepoId] = useState("repo_core");

  // Checkpoint form
  const [checkpointDesc, setCheckpointDesc] = useState("");
  const [pauseReason, setPauseReason] = useState("");
  const [showPauseModal, setShowPauseModal] = useState(false);

  const [notification, setNotification] = useState<string | null>(null);

  const fetchStatsAndTasks = async () => {
    setLoading(true);
    try {
      const statsRes = await fetch("/api/storage/stats");
      const statsData = await statsRes.json();
      setStats(statsData);

      const tasksUrl = statusFilter !== "ALL" 
        ? `/api/storage/tasks?status=${statusFilter}` 
        : "/api/storage/tasks";
      const tasksRes = await fetch(tasksUrl);
      const tasksData = await tasksRes.json();
      setTasks(Array.isArray(tasksData) ? tasksData : []);

      if (selectedTaskId) {
        fetchTaskDetails(selectedTaskId);
      } else if (Array.isArray(tasksData) && tasksData.length > 0) {
        fetchTaskDetails(tasksData[0].task_id);
      }
    } catch (err: any) {
      console.error("Failed to load persistence data:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskDetails = async (taskId: string) => {
    setSelectedTaskId(taskId);
    try {
      const res = await fetch(`/api/storage/tasks/${encodeURIComponent(taskId)}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedTaskDetails(data);
      }
    } catch (err) {
      console.error("Failed to fetch task details:", err);
    }
  };

  useEffect(() => {
    fetchStatsAndTasks();
  }, [statusFilter]);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRequirement.trim()) return;
    try {
      const res = await fetch("/api/storage/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirement: newRequirement, repoId: newRepoId }),
      });
      const data = await res.json();
      setShowNewTaskModal(false);
      setNewRequirement("");
      showToast(`Task created: ${data.task_id}`);
      fetchStatsAndTasks();
      fetchTaskDetails(data.task_id);
    } catch (err) {
      showToast("Error creating task in SQLite.");
    }
  };

  const handlePauseTask = async () => {
    if (!selectedTaskId) return;
    try {
      const res = await fetch(`/api/storage/tasks/${encodeURIComponent(selectedTaskId)}/pause`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: pauseReason || "Manual user intervention" }),
      });
      if (res.ok) {
        showToast(`Task ${selectedTaskId} PAUSED.`);
        setShowPauseModal(false);
        setPauseReason("");
        fetchStatsAndTasks();
      }
    } catch (err) {
      showToast("Error pausing task.");
    }
  };

  const handleResumeTask = async () => {
    if (!selectedTaskId) return;
    try {
      const res = await fetch(`/api/storage/tasks/${encodeURIComponent(selectedTaskId)}/resume`, {
        method: "POST",
      });
      if (res.ok) {
        showToast(`Task ${selectedTaskId} RESUMED.`);
        fetchStatsAndTasks();
      }
    } catch (err) {
      showToast("Error resuming task.");
    }
  };

  const handleCreateCheckpoint = async () => {
    if (!selectedTaskId) return;
    try {
      const res = await fetch(`/api/storage/tasks/${encodeURIComponent(selectedTaskId)}/checkpoint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: checkpointDesc || "Manual point-in-time snapshot" }),
      });
      if (res.ok) {
        setCheckpointDesc("");
        showToast("State snapshot checkpoint created in SQLite!");
        fetchStatsAndTasks();
      }
    } catch (err) {
      showToast("Error creating checkpoint.");
    }
  };

  const handleRestoreCheckpoint = async (checkpointId: string) => {
    if (!confirm("Are you sure you want to rollback task state to this checkpoint?")) return;
    try {
      const res = await fetch(`/api/storage/checkpoints/${encodeURIComponent(checkpointId)}/restore`, {
        method: "POST",
      });
      if (res.ok) {
        showToast("Task state successfully restored from checkpoint!");
        fetchStatsAndTasks();
      }
    } catch (err) {
      showToast("Error restoring checkpoint.");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm(`Delete task ${taskId} and all related checkpoints/events from SQLite?`)) return;
    try {
      const res = await fetch(`/api/storage/tasks/${encodeURIComponent(taskId)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast(`Task ${taskId} deleted.`);
        setSelectedTaskId(null);
        setSelectedTaskDetails(null);
        fetchStatsAndTasks();
      }
    } catch (err) {
      showToast("Error deleting task.");
    }
  };

  const handleSeedDemo = async () => {
    try {
      const res = await fetch("/api/storage/seed", { method: "POST" });
      if (res.ok) {
        showToast("Seeded SQLite database with real tasks and events!");
        fetchStatsAndTasks();
      }
    } catch (err) {
      showToast("Error seeding storage.");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
      case "EXECUTING":
        return "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20";
      case "PLANNING":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      case "PAUSED":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "FAILED":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20";
      default:
        return "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20";
    }
  };

  const getEventBadge = (type: string) => {
    switch (type) {
      case "STEP_START":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400";
      case "TOOL_INVOCATION":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400";
      case "TOOL_RESULT":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
      case "CHECKPOINT_SAVED":
      case "CHECKPOINT_RESTORED":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400";
      case "STATE_PAUSED":
      case "STATE_RESUMED":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400";
      case "TASK_COMPLETED":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400";
      case "TASK_FAILED":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400";
      default:
        return "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400";
    }
  };

  return (
    <div id="state-persistence-studio" className="space-y-6">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 px-5 py-3 rounded-xl shadow-2xl border border-zinc-700/50 animate-fade-in text-sm font-medium">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 dark:text-emerald-600 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Header & Stats Banner */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-xs font-semibold uppercase tracking-wider rounded-full">
                Phase 4 Engine
              </span>
              <span className="text-xs text-zinc-500 font-mono flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5" />
                SQLite ACID Persistence
              </span>
            </div>
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">
              Droid State & Execution Timeline Persistence
            </h2>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
              Production SQLite storage layer tracking full TaskState snapshots, immutable execution timelines, state rollback checkpoints, and pause/resume lifecycle.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleSeedDemo}
              className="px-3.5 py-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2 border border-zinc-300 dark:border-zinc-700"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Seed Demo State
            </button>
            <button
              onClick={() => setShowNewTaskModal(true)}
              className="px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors flex items-center gap-2 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              New Task
            </button>
            <button
              onClick={fetchStatsAndTasks}
              disabled={loading}
              className="p-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-200 dark:border-zinc-700"
              title="Refresh database state"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Database Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-zinc-100 dark:border-zinc-800">
          <div className="bg-zinc-50 dark:bg-zinc-800/50 p-3.5 rounded-xl border border-zinc-200/70 dark:border-zinc-800">
            <div className="text-xs text-zinc-500 font-medium">Database File</div>
            <div className="text-sm font-semibold text-zinc-900 dark:text-white mt-1 truncate" title={stats?.db_path || ".nexforge/droid_state.db"}>
              {stats?.db_size_kb ? `${stats.db_size_kb} KB` : "0 KB"} (SQLite)
            </div>
            <div className="text-[11px] text-zinc-400 truncate mt-0.5">
              {stats?.db_path?.split("/").pop() || "droid_state.db"}
            </div>
          </div>

          <div className="bg-zinc-50 dark:bg-zinc-800/50 p-3.5 rounded-xl border border-zinc-200/70 dark:border-zinc-800">
            <div className="text-xs text-zinc-500 font-medium">Total Persisted Tasks</div>
            <div className="text-xl font-bold text-zinc-900 dark:text-white mt-1">
              {stats?.total_tasks || 0}
            </div>
            <div className="text-[11px] text-zinc-500 mt-0.5">
              {stats?.status_distribution?.COMPLETED || 0} resolved, {stats?.status_distribution?.EXECUTING || 0} active
            </div>
          </div>

          <div className="bg-zinc-50 dark:bg-zinc-800/50 p-3.5 rounded-xl border border-zinc-200/70 dark:border-zinc-800">
            <div className="text-xs text-zinc-500 font-medium">Timeline Events</div>
            <div className="text-xl font-bold text-zinc-900 dark:text-white mt-1">
              {stats?.total_timeline_events || 0}
            </div>
            <div className="text-[11px] text-zinc-500 mt-0.5">
              Immutable execution trace
            </div>
          </div>

          <div className="bg-zinc-50 dark:bg-zinc-800/50 p-3.5 rounded-xl border border-zinc-200/70 dark:border-zinc-800">
            <div className="text-xs text-zinc-500 font-medium">State Checkpoints</div>
            <div className="text-xl font-bold text-zinc-900 dark:text-white mt-1">
              {stats?.total_checkpoints || 0}
            </div>
            <div className="text-[11px] text-zinc-500 mt-0.5">
              Rollback snapshots
            </div>
          </div>
        </div>
      </div>

      {/* Main Studio Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Task List (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3 mb-3">
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-500" />
                Persisted Tasks ({tasks.length})
              </h3>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs bg-zinc-50 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 rounded-lg px-2.5 py-1.5 focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="PENDING">PENDING</option>
                <option value="PLANNING">PLANNING</option>
                <option value="EXECUTING">EXECUTING</option>
                <option value="PAUSED">PAUSED</option>
                <option value="COMPLETED">COMPLETED</option>
                <option value="FAILED">FAILED</option>
              </select>
            </div>

            {tasks.length === 0 ? (
              <div className="text-center py-12 px-4 border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl">
                <Database className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
                <div className="text-sm font-medium text-zinc-700 dark:text-zinc-300">No tasks found</div>
                <p className="text-xs text-zinc-500 mt-1 max-w-xs mx-auto">
                  Create a new task or click "Seed Demo State" to populate SQLite.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
                {tasks.map((t) => {
                  const isSelected = selectedTaskId === t.task_id;
                  return (
                    <div
                      key={t.task_id}
                      onClick={() => fetchTaskDetails(t.task_id)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-indigo-500/5 dark:bg-indigo-500/10 border-indigo-500/50 shadow-sm"
                          : "bg-zinc-50/50 dark:bg-zinc-850 hover:bg-zinc-100/70 dark:hover:bg-zinc-800 border-zinc-200/80 dark:border-zinc-800"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-xs font-bold text-zinc-900 dark:text-white truncate">
                              {t.task_id}
                            </span>
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${getStatusBadge(
                                t.status
                              )}`}
                            >
                              {t.status}
                            </span>
                          </div>
                          <div className="text-xs text-zinc-700 dark:text-zinc-300 line-clamp-2">
                            {t.requirement}
                          </div>
                        </div>
                        <ChevronRight
                          className={`w-4 h-4 shrink-0 text-zinc-400 transition-transform ${
                            isSelected ? "translate-x-0.5 text-indigo-500" : ""
                          }`}
                        />
                      </div>

                      <div className="flex items-center gap-4 mt-2.5 pt-2 border-t border-zinc-200/60 dark:border-zinc-800/80 text-[11px] text-zinc-500">
                        <span>Iter: {t.iteration}</span>
                        <span>Read: {t.files_read?.length || 0}</span>
                        <span>Changed: {t.files_changed?.length || 0}</span>
                        <span className="ml-auto text-[10px] text-zinc-400">
                          {new Date(t.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Selected Task Inspector (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {selectedTaskDetails ? (
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm space-y-5">
              {/* Task Header & Controls */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-bold text-zinc-900 dark:text-white">
                      {selectedTaskDetails.task.task_id}
                    </span>
                    <span
                      className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${getStatusBadge(
                        selectedTaskDetails.task.status
                      )}`}
                    >
                      {selectedTaskDetails.task.status}
                    </span>
                    <span className="text-xs text-zinc-500 font-mono">
                      Repo: {selectedTaskDetails.task.repository_id}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-700 dark:text-zinc-300 mt-1 font-medium">
                    {selectedTaskDetails.task.requirement}
                  </p>
                </div>

                {/* State Control Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  {selectedTaskDetails.task.status === "PAUSED" ? (
                    <button
                      onClick={handleResumeTask}
                      className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Resume
                    </button>
                  ) : selectedTaskDetails.task.status !== "COMPLETED" && selectedTaskDetails.task.status !== "FAILED" ? (
                    <button
                      onClick={() => setShowPauseModal(true)}
                      className="px-3 py-1.5 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
                    >
                      <Pause className="w-3.5 h-3.5" />
                      Pause
                    </button>
                  ) : null}

                  <button
                    onClick={() => handleDeleteTask(selectedTaskDetails.task.task_id)}
                    className="p-1.5 text-zinc-400 hover:text-rose-500 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                    title="Delete task from SQLite"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Inspector Navigation Tabs */}
              <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-2">
                <button
                  onClick={() => setActiveTab("timeline")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
                    activeTab === "timeline"
                      ? "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
                      : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
                  }`}
                >
                  <History className="w-3.5 h-3.5" />
                  Execution Timeline ({selectedTaskDetails.timeline?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("checkpoints")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
                    activeTab === "checkpoints"
                      ? "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
                      : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
                  }`}
                >
                  <Bookmark className="w-3.5 h-3.5" />
                  Checkpoints ({selectedTaskDetails.checkpoints?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("state_json")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
                    activeTab === "state_json"
                      ? "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
                      : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5" />
                  State Snapshot
                </button>
                <button
                  onClick={() => setActiveTab("schema")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
                    activeTab === "schema"
                      ? "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
                      : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
                  }`}
                >
                  <Database className="w-3.5 h-3.5" />
                  SQL Schema
                </button>
              </div>

              {/* Tab 1: Execution Timeline */}
              {activeTab === "timeline" && (
                <div className="space-y-3">
                  <div className="text-xs text-zinc-500 font-medium flex items-center justify-between">
                    <span>Chronological event stream recorded during reasoning loop</span>
                    <span className="font-mono text-[11px]">{selectedTaskDetails.timeline?.length} events</span>
                  </div>

                  {selectedTaskDetails.timeline?.length === 0 ? (
                    <div className="text-center py-8 text-xs text-zinc-500 border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl">
                      No timeline events recorded yet.
                    </div>
                  ) : (
                    <div className="space-y-2.5 max-h-[450px] overflow-y-auto pr-1">
                      {selectedTaskDetails.timeline.map((evt, idx) => (
                        <div
                          key={evt.event_id || idx}
                          className="p-3 bg-zinc-50 dark:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${getEventBadge(
                                  evt.event_type
                                )}`}
                              >
                                {evt.event_type}
                              </span>
                              <span className="text-[11px] text-zinc-500 font-mono">
                                Iter #{evt.iteration}
                              </span>
                            </div>
                            <span className="text-[10px] text-zinc-400 font-mono">
                              {new Date(evt.timestamp).toLocaleTimeString()}
                            </span>
                          </div>

                          {/* Payload rendering */}
                          {evt.payload && Object.keys(evt.payload).length > 0 && (
                            <pre className="mt-1 p-2 bg-zinc-950 text-zinc-300 dark:bg-black font-mono text-[11px] rounded-lg overflow-x-auto">
                              {JSON.stringify(evt.payload, null, 2)}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Checkpoints & Rollback */}
              {activeTab === "checkpoints" && (
                <div className="space-y-4">
                  {/* Create Checkpoint Box */}
                  <div className="p-3.5 bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center gap-3">
                    <input
                      type="text"
                      placeholder="Snapshot description (e.g., Pre-refactor checkpoint)"
                      value={checkpointDesc}
                      onChange={(e) => setCheckpointDesc(e.target.value)}
                      className="flex-1 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-white focus:outline-none"
                    />
                    <button
                      onClick={handleCreateCheckpoint}
                      className="px-3.5 py-2 text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors shrink-0 shadow-sm flex items-center gap-1.5"
                    >
                      <Bookmark className="w-3.5 h-3.5" />
                      Save Checkpoint
                    </button>
                  </div>

                  {selectedTaskDetails.checkpoints?.length === 0 ? (
                    <div className="text-center py-8 text-xs text-zinc-500 border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl">
                      No checkpoints created for this task yet.
                    </div>
                  ) : (
                    <div className="space-y-2.5 max-h-[400px] overflow-y-auto pr-1">
                      {selectedTaskDetails.checkpoints.map((chk) => (
                        <div
                          key={chk.checkpoint_id}
                          className="p-3.5 bg-zinc-50 dark:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs space-y-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <div className="font-semibold text-zinc-900 dark:text-white flex items-center gap-2">
                                <Bookmark className="w-3.5 h-3.5 text-purple-500" />
                                {chk.description || "Point-in-time Snapshot"}
                              </div>
                              <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                                ID: {chk.checkpoint_id} • Iter #{chk.iteration}
                              </div>
                            </div>

                            <button
                              onClick={() => handleRestoreCheckpoint(chk.checkpoint_id)}
                              className="px-2.5 py-1 text-xs font-medium text-purple-600 dark:text-purple-400 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg transition-colors flex items-center gap-1"
                            >
                              <RotateCcw className="w-3 h-3" />
                              Restore State
                            </button>
                          </div>

                          <div className="text-[11px] text-zinc-500 flex items-center gap-3">
                            <span>Created: {new Date(chk.created_at).toLocaleString()}</span>
                            {chk.git_commit_hash && (
                              <span className="font-mono">Git: {chk.git_commit_hash}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: State JSON Snapshot */}
              {activeTab === "state_json" && (
                <div className="space-y-2">
                  <div className="text-xs text-zinc-500 font-medium">
                    Live serialized TaskState record in SQLite:
                  </div>
                  <pre className="p-3.5 bg-zinc-950 text-zinc-200 dark:bg-black font-mono text-xs rounded-xl overflow-x-auto max-h-[450px]">
                    {JSON.stringify(selectedTaskDetails.task, null, 2)}
                  </pre>
                </div>
              )}

              {/* Tab 4: SQL Schema */}
              {activeTab === "schema" && (
                <div className="space-y-3 text-xs">
                  <div className="text-zinc-500 font-medium">
                    Active SQLite DDL definitions with foreign keys and cascade deletions:
                  </div>
                  <div className="bg-zinc-950 text-emerald-400 dark:bg-black font-mono p-3.5 rounded-xl text-[11px] overflow-x-auto max-h-[450px]">
{`-- Tasks Table
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    requirement TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    current_step_index INTEGER NOT NULL DEFAULT 0,
    iteration INTEGER NOT NULL DEFAULT 0,
    plan_json TEXT NOT NULL DEFAULT '[]',
    files_read_json TEXT NOT NULL DEFAULT '[]',
    files_changed_json TEXT NOT NULL DEFAULT '[]',
    test_runs_count INTEGER NOT NULL DEFAULT 0,
    test_failures_count INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Timeline Events
CREATE TABLE task_timeline_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    timestamp TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

-- Checkpoints Table
CREATE TABLE task_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 0,
    state_snapshot_json TEXT NOT NULL,
    git_commit_hash TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);`}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-12 text-center shadow-sm">
              <Database className="w-10 h-10 text-zinc-400 mx-auto mb-3" />
              <div className="text-base font-semibold text-zinc-900 dark:text-white">
                Select a Task to Inspect
              </div>
              <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
                Choose any persisted task from the list on the left to inspect its real SQLite timeline events, rollback checkpoints, and serialized state.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* New Task Modal */}
      {showNewTaskModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Plus className="w-5 h-5 text-indigo-500" />
              Create New Task
            </h3>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Target Repository ID
                </label>
                <input
                  type="text"
                  value={newRepoId}
                  onChange={(e) => setNewRepoId(e.target.value)}
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Engineering Requirement / Objective
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Implement resilient exponential backoff for HTTP 429 errors..."
                  value={newRequirement}
                  onChange={(e) => setNewRequirement(e.target.value)}
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-white focus:outline-none resize-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewTaskModal(false)}
                  className="px-4 py-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors shadow-sm"
                >
                  Create & Persist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Pause Task Modal */}
      {showPauseModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Pause className="w-5 h-5 text-amber-500" />
              Pause Task Execution
            </h3>
            <div className="space-y-3">
              <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                Reason for Pause (recorded in SQLite timeline):
              </label>
              <input
                type="text"
                placeholder="e.g., Awaiting security policy review or manual code inspection"
                value={pauseReason}
                onChange={(e) => setPauseReason(e.target.value)}
                className="w-full text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-white focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowPauseModal(false)}
                className="px-4 py-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePauseTask}
                className="px-4 py-2 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors shadow-sm"
              >
                Confirm Pause
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
