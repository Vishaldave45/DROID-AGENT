"""Explicit Task Planner data models, DAG dependency validation, and step lifecycle (Phase 8)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Set, Tuple


class PlanStepType(str, Enum):
    """Categorical archetype of engineering plan steps."""

    DISCOVERY = "DISCOVERY"             # Repository and dependency exploration
    INVESTIGATION = "INVESTIGATION"     # Symbol call graph and root cause analysis
    IMPLEMENTATION = "IMPLEMENTATION"   # Code modification or creation
    VERIFICATION = "VERIFICATION"       # Unit/integration test and lint execution
    REFACTOR = "REFACTOR"               # Cleanup or structural improvement
    DOCUMENTATION = "DOCUMENTATION"     # Docs, comments, and schemas update


class StepStatus(str, Enum):
    """Execution state of an individual step."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


@dataclass
class PlanStep:
    """A discrete, verifiable unit of work within an ExecutionPlan."""

    step_id: str
    title: str
    description: str
    step_type: PlanStepType
    dependencies: List[str] = field(default_factory=list)  # List of prerequisite step_ids
    target_files: List[str] = field(default_factory=list)
    target_symbols: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    acceptance_criteria: str = ""
    status: StepStatus = StepStatus.PENDING
    evidence: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_in_progress(self) -> None:
        self.status = StepStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self, evidence: Optional[str] = None, duration_ms: Optional[float] = None) -> None:
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        if evidence:
            self.evidence = evidence
        if duration_ms is not None:
            self.duration_ms = duration_ms

    def mark_failed(self, error: Optional[str] = None) -> None:
        self.status = StepStatus.FAILED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        if error:
            self.evidence = f"FAILED: {error}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "step_type": self.step_type.value if isinstance(self.step_type, PlanStepType) else str(self.step_type),
            "dependencies": self.dependencies,
            "target_files": self.target_files,
            "target_symbols": self.target_symbols,
            "required_tools": self.required_tools,
            "acceptance_criteria": self.acceptance_criteria,
            "status": self.status.value if isinstance(self.status, StepStatus) else str(self.status),
            "evidence": self.evidence,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        step_type_str = data.get("step_type", "IMPLEMENTATION")
        step_type = PlanStepType(step_type_str) if step_type_str in PlanStepType._value2member_map_ else PlanStepType.IMPLEMENTATION

        status_str = data.get("status", "PENDING")
        status = StepStatus(status_str) if status_str in StepStatus._value2member_map_ else StepStatus.PENDING

        return cls(
            step_id=data["step_id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            step_type=step_type,
            dependencies=data.get("dependencies", []),
            target_files=data.get("target_files", []),
            target_symbols=data.get("target_symbols", []),
            required_tools=data.get("required_tools", []),
            acceptance_criteria=data.get("acceptance_criteria", ""),
            status=status,
            evidence=data.get("evidence"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms"),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExecutionPlan:
    """Directed Acyclic Graph (DAG) of sequential and parallel plan steps."""

    plan_id: str
    task_id: str
    title: str
    objective: str
    steps: List[PlanStep] = field(default_factory=list)
    current_step_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def is_valid_dag(self) -> Tuple[bool, Optional[str]]:
        """Validates that all dependencies exist and that there are no circular dependency cycles."""
        step_map = {s.step_id: s for s in self.steps}

        # 1. Check missing dependencies
        for step in self.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_map:
                    return False, f"Step '{step.step_id}' depends on non-existent step '{dep_id}'."
                if dep_id == step.step_id:
                    return False, f"Step '{step.step_id}' cannot depend on itself."

        # 2. Check for cycles via DFS
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(curr_id: str) -> bool:
            visited[curr_id] = 1
            for dep_id in step_map[curr_id].dependencies:
                state = visited.get(dep_id, 0)
                if state == 1:
                    return True  # Cycle detected
                if state == 0:
                    if dfs(dep_id):
                        return True
            visited[curr_id] = 2
            return False

        for step in self.steps:
            if visited.get(step.step_id, 0) == 0:
                if dfs(step.step_id):
                    return False, "Circular dependency cycle detected in plan DAG."

        return True, None

    def get_next_runnable_steps(self) -> List[PlanStep]:
        """Returns pending steps whose prerequisite dependencies are all marked COMPLETED."""
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        runnable: List[PlanStep] = []

        for step in self.steps:
            if step.status == StepStatus.PENDING:
                # Check if all dependencies are completed
                if all(dep_id in completed_ids for dep_id in step.dependencies):
                    runnable.append(step)

        return runnable

    def progress_percentage(self) -> float:
        """Calculates total completion percentage of the plan."""
        if not self.steps:
            return 0.0
        completed_count = sum(1 for s in self.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
        return round((completed_count / len(self.steps)) * 100.0, 1)

    def is_completed(self) -> bool:
        """Returns true if all steps in the plan are either COMPLETED or SKIPPED."""
        if not self.steps:
            return False
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    def has_failures(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "title": self.title,
            "objective": self.objective,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_id": self.current_step_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress_percentage": self.progress_percentage(),
            "is_completed": self.is_completed(),
            "has_failures": self.has_failures(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        steps = [PlanStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            plan_id=data["plan_id"],
            task_id=data.get("task_id", "task-default"),
            title=data.get("title", "Execution Plan"),
            objective=data.get("objective", ""),
            steps=steps,
            current_step_id=data.get("current_step_id"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            metadata=data.get("metadata", {}),
        )
