"""Diagnostic Loop Controller: autonomous test failure consumption, root-cause diagnosis, targeted patch, and re-test loop with oscillation and regression termination guards."""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.diagnostics.diagnostic_reasoner import (
    DiagnosisHypothesis,
    DiagnosticReasoner,
)
from app.diagnostics.test_runner import TestRunner
from app.diagnostics.traceback_parser import TestExecutionReport
from app.observability.logger import get_logger
from app.patcher.safe_modifier import SafeCodeModifier
from app.patcher.snapshot_auditor import FileSnapshotAuditor

logger = get_logger("nexforge.diagnostics.loop")


class TerminationGuardReason(str, Enum):
    """Reason for termination of the autonomous diagnostic fix loop."""

    RESOLVED = "RESOLVED"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    OSCILLATION_DETECTED = "OSCILLATION_DETECTED"
    REGRESSION_ABORT = "REGRESSION_ABORT"
    NO_PROGRESS_LIMIT = "NO_PROGRESS_LIMIT"
    SYNTAX_ERROR_ABORT = "SYNTAX_ERROR_ABORT"
    EXECUTION_ERROR = "EXECUTION_ERROR"


@dataclass
class IterationStep:
    """Detailed record of one iteration of the Test-Observe-Diagnose-Fix-ReTest loop."""

    iteration: int
    test_report: TestExecutionReport
    hypotheses: List[DiagnosisHypothesis] = field(default_factory=list)
    patch_attempted: Optional[Dict[str, Any]] = None
    snapshot_version: Optional[int] = None
    rollback_occurred: bool = False
    duration_ms: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "test_report": self.test_report.to_dict(),
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "patch_attempted": self.patch_attempted,
            "snapshot_version": self.snapshot_version,
            "rollback_occurred": self.rollback_occurred,
            "duration_ms": round(self.duration_ms, 2),
            "notes": self.notes,
        }


@dataclass
class DiagnosticLoopResult:
    """Final summary of the diagnostic fix loop execution."""

    success: bool
    termination_reason: TerminationGuardReason
    initial_failures_count: int
    final_failures_count: int
    total_iterations: int
    steps: List[IterationStep] = field(default_factory=list)
    snapshots_taken: int = 0
    rollbacks_triggered: int = 0
    summary: str = ""
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "termination_reason": self.termination_reason.value,
            "initial_failures_count": self.initial_failures_count,
            "final_failures_count": self.final_failures_count,
            "total_iterations": self.total_iterations,
            "snapshots_taken": self.snapshots_taken,
            "rollbacks_triggered": self.rollbacks_triggered,
            "summary": self.summary,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "steps": [s.to_dict() for s in self.steps],
        }


class DiagnosticLoopController:
    """Executes the closed-loop Test -> Observe -> Diagnose -> Patch -> Re-verify cycle."""

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        test_runner: Optional[TestRunner] = None,
        reasoner: Optional[DiagnosticReasoner] = None,
        modifier: Optional[SafeCodeModifier] = None,
        auditor: Optional[FileSnapshotAuditor] = None,
    ) -> None:
        self.workspace_root = workspace_root or os.getcwd()
        self.test_runner = test_runner or TestRunner(self.workspace_root)
        self.reasoner = reasoner or DiagnosticReasoner(self.workspace_root)
        self.modifier = modifier or SafeCodeModifier(self.workspace_root)
        self.auditor = auditor or FileSnapshotAuditor(self.workspace_root)

    def _extract_failure_fingerprint(self, report: TestExecutionReport) -> str:
        """Computes a deterministic signature of current failures to detect oscillation."""
        signatures = []
        for f in report.failures:
            innermost_line = f.innermost_frame.line_number if f.innermost_frame else 0
            innermost_file = os.path.basename(f.innermost_frame.file_path) if f.innermost_frame else ""
            signatures.append(f"{f.test_name}:{f.error_type}:{innermost_file}:{innermost_line}")
        return "|".join(sorted(signatures))

    def _detect_oscillation(self, fingerprint_history: List[str]) -> bool:
        """Detects ping-pong oscillation: e.g. [A, B, A] or [A, B, C, A]."""
        if len(fingerprint_history) < 3:
            return False
        current = fingerprint_history[-1]
        # Check if current signature appeared previously
        prior = fingerprint_history[:-1]
        return current in prior

    def execute_loop(
        self,
        test_command: str,
        max_iterations: int = 4,
        auto_rollback_on_regression: bool = True,
        custom_patch_provider: Optional[Callable[[DiagnosisHypothesis], Optional[Dict[str, str]]]] = None,
    ) -> DiagnosticLoopResult:
        """Executes the diagnostic loop until resolution, oscillation, regression, or max iterations."""
        start_time = time.time()
        steps: List[IterationStep] = []
        fingerprint_history: List[str] = []
        snapshots_taken = 0
        rollbacks_triggered = 0

        logger.info(f"Starting Diagnostic Fix Loop with max_iterations={max_iterations}")

        initial_report = self.test_runner.run_command(test_command)
        initial_failures = initial_report.failed_count + initial_report.error_count

        if initial_report.all_passed:
            total_dur = (time.time() - start_time) * 1000
            return DiagnosticLoopResult(
                success=True,
                termination_reason=TerminationGuardReason.RESOLVED,
                initial_failures_count=0,
                final_failures_count=0,
                total_iterations=1,
                steps=[
                    IterationStep(
                        iteration=1,
                        test_report=initial_report,
                        notes="All tests passed on initial execution.",
                        duration_ms=total_dur,
                    )
                ],
                summary="All tests passed on initial run. No diagnostic patching required.",
                total_duration_ms=total_dur,
            )

        current_report = initial_report
        previous_passed_count = initial_report.passed_count

        for iteration in range(1, max_iterations + 1):
            step_start = time.time()
            curr_fail_count = current_report.failed_count + current_report.error_count

            # 1. Check if all resolved
            if current_report.all_passed or curr_fail_count == 0:
                step_dur = (time.time() - step_start) * 1000
                steps.append(
                    IterationStep(
                        iteration=iteration,
                        test_report=current_report,
                        notes="All failures resolved successfully.",
                        duration_ms=step_dur,
                    )
                )
                total_dur = (time.time() - start_time) * 1000
                return DiagnosticLoopResult(
                    success=True,
                    termination_reason=TerminationGuardReason.RESOLVED,
                    initial_failures_count=initial_failures,
                    final_failures_count=0,
                    total_iterations=iteration,
                    steps=steps,
                    snapshots_taken=snapshots_taken,
                    rollbacks_triggered=rollbacks_triggered,
                    summary=f"Diagnostic loop successfully resolved all {initial_failures} failures in {iteration} iterations.",
                    total_duration_ms=total_dur,
                )

            # 2. Check for Oscillation
            fp = self._extract_failure_fingerprint(current_report)
            fingerprint_history.append(fp)
            if self._detect_oscillation(fingerprint_history):
                step_dur = (time.time() - step_start) * 1000
                steps.append(
                    IterationStep(
                        iteration=iteration,
                        test_report=current_report,
                        notes=f"Oscillation detected: failure state signature {fp} previously observed. Guard triggered.",
                        duration_ms=step_dur,
                    )
                )
                total_dur = (time.time() - start_time) * 1000
                return DiagnosticLoopResult(
                    success=False,
                    termination_reason=TerminationGuardReason.OSCILLATION_DETECTED,
                    initial_failures_count=initial_failures,
                    final_failures_count=curr_fail_count,
                    total_iterations=iteration,
                    steps=steps,
                    snapshots_taken=snapshots_taken,
                    rollbacks_triggered=rollbacks_triggered,
                    summary="Termination Guard Triggered: Oscillation detected between cyclic error signatures.",
                    total_duration_ms=total_dur,
                )

            # 3. Diagnose failures
            hypotheses: List[DiagnosisHypothesis] = []
            for failure in current_report.failures:
                hyp = self.reasoner.analyze_failure(failure)
                hypotheses.append(hyp)

            # Select highest confidence hypothesis
            best_hyp = max(hypotheses, key=lambda h: h.confidence_score) if hypotheses else None
            if not best_hyp or not best_hyp.primary_file or best_hyp.primary_file == "<unknown_file>":
                step_dur = (time.time() - step_start) * 1000
                steps.append(
                    IterationStep(
                        iteration=iteration,
                        test_report=current_report,
                        hypotheses=hypotheses,
                        notes="No actionable stack frame found in workspace source code to patch.",
                        duration_ms=step_dur,
                    )
                )
                total_dur = (time.time() - start_time) * 1000
                return DiagnosticLoopResult(
                    success=False,
                    termination_reason=TerminationGuardReason.NO_PROGRESS_LIMIT,
                    initial_failures_count=initial_failures,
                    final_failures_count=curr_fail_count,
                    total_iterations=iteration,
                    steps=steps,
                    snapshots_taken=snapshots_taken,
                    rollbacks_triggered=rollbacks_triggered,
                    summary="Loop aborted: Unable to identify target workspace source file from failure traceback.",
                    total_duration_ms=total_dur,
                )

            # 4. Generate & apply patch
            patch_target: Optional[str] = None
            patch_replacement: Optional[str] = None

            if custom_patch_provider:
                custom_patch = custom_patch_provider(best_hyp)
                if custom_patch:
                    patch_target = custom_patch.get("target_content")
                    patch_replacement = custom_patch.get("replacement_content")

            if not patch_target:
                patch_target = best_hyp.proposed_target_content
                patch_replacement = best_hyp.proposed_replacement_content

            if not patch_target or patch_replacement is None:
                step_dur = (time.time() - step_start) * 1000
                steps.append(
                    IterationStep(
                        iteration=iteration,
                        test_report=current_report,
                        hypotheses=hypotheses,
                        notes=f"No concrete patch replacement synthesized for hypothesis {best_hyp.failure_id}.",
                        duration_ms=step_dur,
                    )
                )
                total_dur = (time.time() - start_time) * 1000
                return DiagnosticLoopResult(
                    success=False,
                    termination_reason=TerminationGuardReason.NO_PROGRESS_LIMIT,
                    initial_failures_count=initial_failures,
                    final_failures_count=curr_fail_count,
                    total_iterations=iteration,
                    steps=steps,
                    snapshots_taken=snapshots_taken,
                    rollbacks_triggered=rollbacks_triggered,
                    summary=f"Loop halted: No surgical patch generated for {best_hyp.failure_id}.",
                    total_duration_ms=total_dur,
                )

            # 5. Capture Snapshot before modification
            file_to_patch = best_hyp.primary_file
            snap = self.auditor.take_snapshot(file_to_patch, reason=f"diagnostic-loop-iter-{iteration}")
            snap_ver = snap.version if snap else None
            if snap:
                snapshots_taken += 1

            # 6. Apply surgical edit via SafeCodeModifier (includes AST validation)
            edit_res = self.modifier.apply_surgical_edit(
                file_path=file_to_patch,
                target_content=patch_target,
                replacement_content=patch_replacement,
                validate_syntax=True,
            )

            if not edit_res.success:
                step_dur = (time.time() - step_start) * 1000
                steps.append(
                    IterationStep(
                        iteration=iteration,
                        test_report=current_report,
                        hypotheses=hypotheses,
                        patch_attempted={"target": patch_target, "replacement": patch_replacement},
                        snapshot_version=snap_ver,
                        notes=f"SafeCodeModifier rejected patch: {edit_res.error}",
                        duration_ms=step_dur,
                    )
                )
                total_dur = (time.time() - start_time) * 1000
                return DiagnosticLoopResult(
                    success=False,
                    termination_reason=TerminationGuardReason.SYNTAX_ERROR_ABORT,
                    initial_failures_count=initial_failures,
                    final_failures_count=curr_fail_count,
                    total_iterations=iteration,
                    steps=steps,
                    snapshots_taken=snapshots_taken,
                    rollbacks_triggered=rollbacks_triggered,
                    summary=f"Syntax/Safety Gate aborted loop: {edit_res.error}",
                    total_duration_ms=total_dur,
                )

            # 7. Re-test to observe results
            new_report = self.test_runner.run_command(test_command)
            new_fail_count = new_report.failed_count + new_report.error_count

            # 8. Check for Regression
            rollback_occurred = False
            if new_report.passed_count < previous_passed_count or new_fail_count > curr_fail_count:
                if auto_rollback_on_regression and snap:
                    logger.warning(
                        f"Regression detected: Failures increased from {curr_fail_count} to {new_fail_count}. Rolling back."
                    )
                    self.auditor.revert_to_snapshot(file_to_patch, snap.version)
                    rollbacks_triggered += 1
                    rollback_occurred = True
                    step_dur = (time.time() - step_start) * 1000
                    steps.append(
                        IterationStep(
                            iteration=iteration,
                            test_report=new_report,
                            hypotheses=hypotheses,
                            patch_attempted={"target": patch_target, "replacement": patch_replacement},
                            snapshot_version=snap_ver,
                            rollback_occurred=True,
                            notes=f"Regression detected ({new_fail_count} failures vs previous {curr_fail_count}). Reverted file to snapshot v{snap_ver}.",
                            duration_ms=step_dur,
                        )
                    )
                    total_dur = (time.time() - start_time) * 1000
                    return DiagnosticLoopResult(
                        success=False,
                        termination_reason=TerminationGuardReason.REGRESSION_ABORT,
                        initial_failures_count=initial_failures,
                        final_failures_count=curr_fail_count,
                        total_iterations=iteration,
                        steps=steps,
                        snapshots_taken=snapshots_taken,
                        rollbacks_triggered=rollbacks_triggered,
                        summary=f"Regression Guard Triggered: Test failures worsened. Atomic rollback restored snapshot v{snap_ver}.",
                        total_duration_ms=total_dur,
                    )

            step_dur = (time.time() - step_start) * 1000
            steps.append(
                IterationStep(
                    iteration=iteration,
                    test_report=new_report,
                    hypotheses=hypotheses,
                    patch_attempted={"target": patch_target, "replacement": patch_replacement},
                    snapshot_version=snap_ver,
                    rollback_occurred=rollback_occurred,
                    notes=f"Applied patch. Failures: {curr_fail_count} -> {new_fail_count}.",
                    duration_ms=step_dur,
                )
            )

            current_report = new_report
            previous_passed_count = new_report.passed_count

        # Max iterations reached without complete resolution
        total_dur = (time.time() - start_time) * 1000
        final_fail_count = current_report.failed_count + current_report.error_count
        return DiagnosticLoopResult(
            success=current_report.all_passed,
            termination_reason=TerminationGuardReason.RESOLVED if current_report.all_passed else TerminationGuardReason.MAX_ITERATIONS_REACHED,
            initial_failures_count=initial_failures,
            final_failures_count=final_fail_count,
            total_iterations=max_iterations,
            steps=steps,
            snapshots_taken=snapshots_taken,
            rollbacks_triggered=rollbacks_triggered,
            summary=f"Reached maximum iteration limit ({max_iterations}). Remaining failures: {final_fail_count}.",
            total_duration_ms=total_dur,
        )
