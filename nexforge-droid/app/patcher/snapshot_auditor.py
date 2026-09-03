"""File snapshotting, SHA-256 content verification, and atomic file operations."""

from collections import defaultdict
import hashlib
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from app.patcher.base import FileSnapshot


class StaleFileConflictError(Exception):
    """Raised when target file on disk differs from expected snapshot hash."""
    def __init__(self, file_path: str, expected_hash: str, actual_hash: str):
        self.file_path = file_path
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            f"Stale file conflict on '{file_path}'. "
            f"Expected SHA-256 hash {expected_hash[:12]}... but found {actual_hash[:12]}... on disk. "
            f"The file was modified externally or in another turn. Please re-read the file before modifying."
        )


class FileSnapshotAuditor:
    """Manages file version snapshots, stale-file conflict detection, and atomic disk writes."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
        # In-memory history: file_path -> List[FileSnapshot]
        self._snapshots: Dict[str, List[FileSnapshot]] = defaultdict(list)

    def _resolve_path(self, file_path: str) -> Path:
        """Resolves file path against workspace root if relative."""
        p = Path(file_path)
        if p.is_absolute():
            return p
        return Path(self.workspace_root) / file_path

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Computes a hexadecimal SHA-256 hash of text content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_file_sha256(self, file_path: str) -> Optional[str]:
        """Reads file and returns SHA-256 hash, or None if file doesn't exist."""
        p = self._resolve_path(file_path)
        if not p.exists() or not p.is_file():
            return None
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return self.compute_sha256(content)
        except Exception:
            return None

    def take_snapshot(self, file_path: str, reason: str = "pre-edit") -> Optional[FileSnapshot]:
        """Captures a point-in-time snapshot of the specified file."""
        p = self._resolve_path(file_path)
        if not p.exists() or not p.is_file():
            return None

        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            history = self._snapshots[str(p.resolve())]
            version = len(history) + 1
            snapshot = FileSnapshot(
                path=str(p),
                version=version,
                sha256_hash=self.compute_sha256(content),
                content=content,
                timestamp=time.time(),
                reason=reason,
            )
            history.append(snapshot)
            return snapshot
        except Exception:
            return None

    def verify_file_freshness(self, file_path: str, expected_hash: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Verifies if the file hash matches expected_hash. Returns (is_fresh, actual_hash, error_msg)."""
        if not expected_hash:
            return True, self.compute_file_sha256(file_path), None

        actual_hash = self.compute_file_sha256(file_path)
        if actual_hash is None:
            return False, None, f"File '{file_path}' does not exist on disk."

        # Allow matching prefix (e.g. first 8, 12, or full 64 chars)
        if actual_hash == expected_hash or actual_hash.startswith(expected_hash):
            return True, actual_hash, None

        return False, actual_hash, f"Stale file detected. Expected hash {expected_hash[:12]}..., but got {actual_hash[:12]}..."

    def atomic_write(self, file_path: str, content: str) -> Tuple[bool, Optional[str]]:
        """Writes content atomically to disk using a temporary file in the same directory."""
        p = Path(file_path).resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Create temp file in the same directory to ensure atomic rename across filesystem boundaries
            with tempfile.NamedTemporaryFile("w", dir=str(p.parent), delete=False, encoding="utf-8") as tf:
                tf.write(content)
                temp_name = tf.name

            # Atomic replace
            os.replace(temp_name, str(p))
            return True, None
        except Exception as e:
            # Clean up temp file if failed
            if 'temp_name' in locals() and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            return False, f"Atomic write failed: {str(e)}"

    def revert_to_snapshot(self, file_path: str, version: Optional[int] = None) -> Tuple[bool, Optional[FileSnapshot], Optional[str]]:
        """Restores a file to a previous snapshot version (default: most recent snapshot)."""
        p = self._resolve_path(file_path).resolve()
        resolved_key = str(p)
        history = self._snapshots.get(resolved_key, [])

        if not history:
            return False, None, f"No snapshots found for '{file_path}'"

        target_snap: Optional[FileSnapshot] = None
        if version is None:
            target_snap = history[-1]
        else:
            for snap in history:
                if snap.version == version:
                    target_snap = snap
                    break

        if not target_snap:
            return False, None, f"Snapshot version {version} not found for '{file_path}' (available versions: 1..{len(history)})"

        success, err = self.atomic_write(str(p), target_snap.content)
        if not success:
            return False, None, err

        return True, target_snap, None

    def get_snapshots(self, file_path: str) -> List[FileSnapshot]:
        """Returns all snapshots for the given file."""
        p = self._resolve_path(file_path).resolve()
        return list(self._snapshots.get(str(p), []))

    def clear_snapshots(self, file_path: Optional[str] = None) -> None:
        """Clears snapshot history."""
        if file_path:
            p = self._resolve_path(file_path).resolve()
            self._snapshots.pop(str(p), None)
        else:
            self._snapshots.clear()
