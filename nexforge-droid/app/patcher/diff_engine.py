"""Unified diff parsing, generation, and resilient patch application engine."""

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

from app.patcher.base import PatchHunk, PatchResult, SurgicalEditChunk, UnifiedDiff


class DiffEngine:
    """Parses, creates, and applies unified diffs and surgical edit hunks."""

    HUNK_HEADER_REGEX = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(?: *(.*))?$")

    @classmethod
    def create_unified_diff(
        cls,
        old_content: str,
        new_content: str,
        from_file: str = "a/file",
        to_file: str = "b/file",
        context_lines: int = 3,
    ) -> str:
        """Generates a standard unified diff string from old and new text content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=from_file,
                tofile=to_file,
                n=context_lines,
            )
        )
        return "".join(diff_lines)

    @classmethod
    def parse_unified_diff(cls, diff_str: str) -> List[UnifiedDiff]:
        """Parses raw unified diff text into structured UnifiedDiff and PatchHunk models."""
        diffs: List[UnifiedDiff] = []
        current_diff: Optional[UnifiedDiff] = None
        current_hunk: Optional[PatchHunk] = None

        lines = diff_str.splitlines()
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            if line.startswith("--- "):
                old_file = line[4:].strip()
                if old_file.startswith("a/"):
                    old_file = old_file[2:]
                # Next line usually has +++
                new_file = old_file
                if i + 1 < n and lines[i + 1].startswith("+++ "):
                    i += 1
                    new_file = lines[i][4:].strip()
                    if new_file.startswith("b/"):
                        new_file = new_file[2:]

                current_diff = UnifiedDiff(old_file=old_file, new_file=new_file)
                diffs.append(current_diff)
                current_hunk = None
                i += 1
                continue

            match = cls.HUNK_HEADER_REGEX.match(line)
            if match:
                old_start = int(match.group(1))
                old_len = int(match.group(2)) if match.group(2) is not None else 1
                new_start = int(match.group(3))
                new_len = int(match.group(4)) if match.group(4) is not None else 1
                context_hdr = match.group(5) or ""

                current_hunk = PatchHunk(
                    old_start=old_start,
                    old_length=old_len,
                    new_start=new_start,
                    new_length=new_len,
                    lines=[],
                    context_header=context_hdr,
                )

                if current_diff is None:
                    current_diff = UnifiedDiff(old_file="unknown", new_file="unknown")
                    diffs.append(current_diff)

                current_diff.hunks.append(current_hunk)
                i += 1
                continue

            if current_hunk is not None:
                if line.startswith(("+", "-", " ", "\\")):
                    current_hunk.lines.append(line)
                elif not line.strip():
                    # Empty context line
                    current_hunk.lines.append(" " + line)

            i += 1

        for d in diffs:
            d.raw_diff = diff_str

        return diffs

    @classmethod
    def apply_unified_diff(
        cls,
        original_content: str,
        diff: UnifiedDiff,
        fuzz_factor: int = 2,
    ) -> PatchResult:
        """Applies a parsed unified diff to target text with multi-pass fuzzy and offset tolerance."""
        orig_lines = original_content.splitlines()
        result_lines = list(orig_lines)
        offset = 0
        applied_hunks = 0
        failed_hunks = 0
        additions = 0
        deletions = 0

        for hunk_idx, hunk in enumerate(diff.hunks):
            # Extract expected old lines and replacement new lines from hunk
            expected_old: List[str] = []
            hunk_new: List[str] = []

            for line in hunk.lines:
                if line.startswith("-"):
                    expected_old.append(line[1:])
                    deletions += 1
                elif line.startswith("+"):
                    hunk_new.append(line[1:])
                    additions += 1
                elif line.startswith(" "):
                    expected_old.append(line[1:])
                    hunk_new.append(line[1:])
                elif line.startswith("\\"):
                    # \ No newline at end of file
                    continue
                else:
                    # Treat raw line as context
                    expected_old.append(line)
                    hunk_new.append(line)

            # Target 0-indexed line index in current result_lines
            target_idx = hunk.old_start - 1 + offset

            match_found = False
            best_idx = target_idx

            # Pass 1: Exact match at predicted target index
            if cls._matches_lines(result_lines, target_idx, expected_old):
                match_found = True
                best_idx = target_idx
            else:
                # Pass 2: Search within fuzz_factor radius
                for search_offset in range(1, fuzz_factor + 1):
                    # Check upward
                    idx_up = target_idx - search_offset
                    if idx_up >= 0 and cls._matches_lines(result_lines, idx_up, expected_old):
                        match_found = True
                        best_idx = idx_up
                        break
                    # Check downward
                    idx_down = target_idx + search_offset
                    if idx_down + len(expected_old) <= len(result_lines) and cls._matches_lines(result_lines, idx_down, expected_old):
                        match_found = True
                        best_idx = idx_down
                        break

                # Pass 3: Whitespace-tolerant match if still not found
                if not match_found:
                    for test_i in range(len(result_lines) - len(expected_old) + 1):
                        if cls._matches_lines_fuzzy(result_lines, test_i, expected_old):
                            match_found = True
                            best_idx = test_i
                            break

            if match_found:
                # Replace the old lines with the new lines
                result_lines[best_idx : best_idx + len(expected_old)] = hunk_new
                applied_hunks += 1
                # Adjust offset for subsequent hunks
                offset += len(hunk_new) - len(expected_old)
            else:
                failed_hunks += 1

        success = failed_hunks == 0 and (applied_hunks > 0 or len(diff.hunks) == 0)
        modified_text = "\n".join(result_lines)
        if original_content.endswith("\n") and not modified_text.endswith("\n"):
            modified_text += "\n"

        err = None
        if not success:
            err = f"Failed to apply {failed_hunks} of {len(diff.hunks)} diff hunk(s). Target content did not match."

        return PatchResult(
            success=success,
            file_path=diff.new_file,
            applied_hunks=applied_hunks,
            failed_hunks=failed_hunks,
            additions=additions,
            deletions=deletions,
            modified_content=modified_text if success else None,
            error=err,
        )

    @classmethod
    def apply_surgical_chunks(
        cls,
        original_content: str,
        chunks: List[SurgicalEditChunk],
    ) -> Tuple[bool, str, Optional[str]]:
        """Applies sequential surgical target-replacement chunks with uniqueness validation."""
        current_text = original_content

        for idx, chunk in enumerate(chunks):
            target = chunk.target_content
            replacement = chunk.replacement_content

            if not target:
                return False, current_text, f"Chunk {idx + 1}: target_content cannot be empty."

            # Exact match check
            count = current_text.count(target)
            if count == 1:
                current_text = current_text.replace(target, replacement, 1)
                continue

            if count > 1:
                return (
                    False,
                    current_text,
                    f"Chunk {idx + 1}: target_content matches {count} occurrences. Target must be unique within file. Provide more context.",
                )

            # If not found and allow_fuzzy is true, try line-normalized matching
            if chunk.allow_fuzzy:
                fuzzy_matched = False
                # Normalize line breaks and trailing spaces
                target_lines = [l.rstrip() for l in target.splitlines()]
                text_lines = current_text.splitlines()

                for i in range(len(text_lines) - len(target_lines) + 1):
                    candidate = [text_lines[i + j].rstrip() for j in range(len(target_lines))]
                    if candidate == target_lines:
                        # Matched
                        rep_lines = replacement.splitlines()
                        text_lines[i : i + len(target_lines)] = rep_lines
                        current_text = "\n".join(text_lines)
                        if original_content.endswith("\n") and not current_text.endswith("\n"):
                            current_text += "\n"
                        fuzzy_matched = True
                        break

                if fuzzy_matched:
                    continue

            return (
                False,
                current_text,
                f"Chunk {idx + 1}: target_content not found in current file content. Ensure exact characters, tabs, and indentation match.",
            )

        return True, current_text, None

    @staticmethod
    def _matches_lines(target: List[str], start_idx: int, pattern: List[str]) -> bool:
        if start_idx < 0 or start_idx + len(pattern) > len(target):
            return False
        for i, pat in enumerate(pattern):
            if target[start_idx + i] != pat:
                return False
        return True

    @staticmethod
    def _matches_lines_fuzzy(target: List[str], start_idx: int, pattern: List[str]) -> bool:
        if start_idx < 0 or start_idx + len(pattern) > len(target):
            return False
        for i, pat in enumerate(pattern):
            if target[start_idx + i].strip() != pat.strip():
                return False
        return True
