#!/usr/bin/env python3
"""CLI utility for safe code modification, syntax validation, diff generation, and snapshot auditing."""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.patcher.diff_engine import DiffEngine
from app.patcher.safe_modifier import SafeCodeModifier
from app.patcher.snapshot_auditor import FileSnapshotAuditor
from app.patcher.syntax_validator import SyntaxValidator


def cmd_validate(args):
    """Validate syntax of a file."""
    path = args.file
    p = Path(path)
    if not p.exists():
        print(f"Error: File '{path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(p, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    validator = SyntaxValidator()
    res = validator.validate(content, path, language=args.language)

    print(f"=== Syntax Validation: {path} ===")
    print(f"Language: {res.language}")
    print(f"Status:   {'VALID' if res.is_valid else 'INVALID'}")
    if not res.is_valid:
        print(f"Error:    {res.error_message}")
        if res.error_line:
            print(f"Location: Line {res.error_line}, Column {res.error_col}")
        if res.diagnostics:
            print(f"\nDiagnostics:\n{res.diagnostics}")
        sys.exit(1)
    else:
        print("All structural and AST syntax checks passed.")


def cmd_diff(args):
    """Generate unified diff between two files or contents."""
    f1 = Path(args.file1)
    f2 = Path(args.file2)

    if not f1.exists() or not f2.exists():
        print("Error: Both files must exist to generate diff.", file=sys.stderr)
        sys.exit(1)

    with open(f1, "r", encoding="utf-8") as a, open(f2, "r", encoding="utf-8") as b:
        diff_str = DiffEngine.create_unified_diff(
            a.read(),
            b.read(),
            from_file=str(f1),
            to_file=str(f2),
        )

    print(diff_str if diff_str else "(Files are identical - no diff)")


def cmd_edit(args):
    """Perform surgical edit on a file."""
    path = args.file
    modifier = SafeCodeModifier()

    res = modifier.apply_surgical_edit(
        file_path=path,
        target_content=args.target,
        replacement_content=args.replacement,
        expected_hash=args.expected_hash,
        allow_fuzzy=args.fuzzy,
        dry_run=args.dry_run,
        validate_syntax=not args.no_validate,
    )

    print(f"=== Surgical Edit: {path} ===")
    print(f"Success:      {res.success}")
    print(f"Pre-Hash:     {res.pre_hash[:16] if res.pre_hash else 'N/A'}...")
    print(f"Post-Hash:    {res.post_hash[:16] if res.post_hash else 'N/A'}...")
    print(f"Syntax Valid: {res.syntax_valid}")
    if res.snapshot_version:
        print(f"Snapshot:     Version {res.snapshot_version} captured")
    if not res.success:
        print(f"Error:        {res.error}")
        if res.syntax_error_line:
            print(f"Syntax Line:  {res.syntax_error_line}")
        sys.exit(1)
    else:
        print(f"Changes:      +{res.additions} lines, -{res.deletions} lines")
        if args.dry_run:
            print("(Dry run: file on disk was not modified)")


def cmd_snapshot(args):
    """Inspect or capture file snapshots."""
    path = args.file
    auditor = FileSnapshotAuditor()

    if args.action == "hash":
        sha = auditor.compute_file_sha256(path)
        print(f"File: {path}")
        print(f"SHA-256: {sha}")
    elif args.action == "take":
        snap = auditor.take_snapshot(path, reason=args.reason or "manual")
        if snap:
            print(f"Snapshot v{snap.version} created for '{path}' ({snap.line_count} lines, {snap.byte_count} bytes)")
            print(f"SHA-256: {snap.sha256_hash}")
        else:
            print(f"Failed to capture snapshot for '{path}'.", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NexForge Droid Safe Code Modification CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # validate
    v_parser = subparsers.add_parser("validate", help="Validate AST syntax of a file")
    v_parser.add_argument("file", help="Path to code file")
    v_parser.add_argument("--language", "-l", help="Explicit language override")
    v_parser.set_defaults(func=cmd_validate)

    # diff
    d_parser = subparsers.add_parser("diff", help="Generate unified diff between two files")
    d_parser.add_argument("file1", help="Original file path")
    d_parser.add_argument("file2", help="Modified file path")
    d_parser.set_defaults(func=cmd_diff)

    # edit
    e_parser = subparsers.add_parser("edit", help="Apply surgical edit to a file")
    e_parser.add_argument("file", help="Path to file to edit")
    e_parser.add_argument("--target", "-t", required=True, help="Target content to find and replace")
    e_parser.add_argument("--replacement", "-r", required=True, help="Replacement content")
    e_parser.add_argument("--expected-hash", help="Expected SHA-256 hash before edit")
    e_parser.add_argument("--fuzzy", action="store_true", help="Enable fuzzy whitespace tolerance")
    e_parser.add_argument("--dry-run", action="store_true", help="Dry run without writing to disk")
    e_parser.add_argument("--no-validate", action="store_true", help="Disable syntax validation")
    e_parser.set_defaults(func=cmd_edit)

    # snapshot
    s_parser = subparsers.add_parser("snapshot", help="Manage file snapshots and hash verification")
    s_parser.add_argument("action", choices=["hash", "take"], help="Action to perform")
    s_parser.add_argument("file", help="Path to file")
    s_parser.add_argument("--reason", help="Reason for taking snapshot")
    s_parser.set_defaults(func=cmd_snapshot)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
