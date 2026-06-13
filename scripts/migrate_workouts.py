#!/usr/bin/env python3
"""
Migrate workouts/ from flat layout to YYYY/MM date-based hierarchy.

Old layout:
    workouts/fit/<stem>.fit
    workouts/analysis/<stem>.md

New layout:
    workouts/YYYY/MM/fit/<stem>.fit
    workouts/YYYY/MM/analysis/<stem>.md

Also supports --inbox mode: moves FIT files from workouts/inbox/ into
workouts/YYYY/MM/fit/ based on the date prefix in the filename.

This script is idempotent — safe to run multiple times.
It uses ``git mv`` so git history is preserved.
"""

from __future__ import annotations

import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

from utils import get_repo_root


def extract_year_month(filename: str) -> tuple[str, str]:
    """Extract YYYY and MM from a filename that starts with YYYY-MM-DD-.

    Args:
        filename: Filename such as ``2026-04-07-133755-Correr.fit``

    Returns:
        Tuple of (year, month) as strings, e.g. (``"2026"``, ``"04"``).

    Raises:
        ValueError: If the filename does not start with a valid date prefix.
    """
    parts = filename.split("-")
    if len(parts) < 3 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError(f"Filename does not start with YYYY-MM-: {filename!r}")
    return parts[0], parts[1]


def git_mv(src: Path, dst: Path) -> None:
    """Run ``git mv src dst``, creating destination parent dirs first.

    Args:
        src: Source path (must exist in the git index).
        dst: Destination path.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "mv", str(src), str(dst)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ERROR: git mv failed: {result.stderr.strip()}", file=sys.stderr)
        raise RuntimeError(f"git mv failed: {result.stderr.strip()}")


def migrate_inbox(inbox_dir: Path, workouts_dir: Path) -> int:
    """Move all .fit files from *inbox_dir* into workouts/YYYY/MM/fit/.

    Args:
        inbox_dir: Path to the inbox directory (e.g. ``workouts/inbox``).
        workouts_dir: Root workouts directory.

    Returns:
        Number of files moved.
    """
    if not inbox_dir.exists():
        print(f"  Inbox {inbox_dir} does not exist — nothing to migrate")
        return 0

    moved = 0
    for src_file in sorted(inbox_dir.glob("*.fit")):
        if not src_file.is_file():
            continue

        try:
            year, month = extract_year_month(src_file.name)
        except ValueError as exc:
            print(f"  WARNING: {exc} — skipping {src_file.name}")
            continue

        dst_file = workouts_dir / year / month / "fit" / src_file.name

        if dst_file.exists():
            print(f"  Already exists at destination: {dst_file.relative_to(workouts_dir.parent)} (skipping)")
            continue

        print(f"  git mv {src_file.relative_to(workouts_dir.parent)} → {dst_file.relative_to(workouts_dir.parent)}")
        git_mv(src_file, dst_file)
        moved += 1

    return moved


def migrate_directory(src_dir: Path, kind: str, workouts_dir: Path) -> int:
    """Move all files from *src_dir* into the YYYY/MM/*kind*/ hierarchy.

    Args:
        src_dir: Flat source directory (e.g. ``workouts/fit``).
        kind: Sub-directory name in the target hierarchy (``"fit"`` or ``"analysis"``).
        workouts_dir: Root workouts directory.

    Returns:
        Number of files moved.
    """
    if not src_dir.exists():
        print(f"  Skipping {src_dir} — does not exist")
        return 0

    moved = 0
    for src_file in sorted(src_dir.iterdir()):
        if not src_file.is_file():
            continue

        try:
            year, month = extract_year_month(src_file.name)
        except ValueError as exc:
            print(f"  WARNING: {exc} — skipping {src_file.name}")
            continue

        dst_file = workouts_dir / year / month / kind / src_file.name

        if dst_file.exists():
            print(f"  Already moved: {src_file.relative_to(workouts_dir.parent)} (skipping)")
            continue

        print(f"  git mv {src_file.relative_to(workouts_dir.parent)} → {dst_file.relative_to(workouts_dir.parent)}")
        git_mv(src_file, dst_file)
        moved += 1

    return moved


def remove_empty_dir(directory: Path) -> None:
    """Remove a directory if it is empty (via ``git rm -r --cached``).

    Args:
        directory: Directory to remove from git tracking.
    """
    if not directory.exists():
        return

    remaining = list(directory.iterdir())
    if remaining:
        print(f"  Skipping removal of {directory} — still has {len(remaining)} file(s)")
        return

    # Remove from git index and from disk
    result = subprocess.run(
        ["git", "rm", "-r", "--cached", "--ignore-unmatch", str(directory)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  WARNING: git rm failed: {result.stderr.strip()}", file=sys.stderr)
    else:
        try:
            directory.rmdir()
            print(f"  Removed empty directory: {directory}")
        except OSError:
            pass  # already gone


def main() -> int:
    """Migrate workouts/ to the YYYY/MM date-based hierarchy.

    Returns:
        Exit code (0 for success).
    """
    parser = ArgumentParser(description="Migrate workout files to YYYY/MM hierarchy")
    parser.add_argument(
        "--inbox",
        metavar="DIR",
        help="Move .fit files from this inbox directory into workouts/YYYY/MM/fit/",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    workouts_dir = repo_root / "workouts"

    if args.inbox:
        inbox_dir = Path(args.inbox)
        if not inbox_dir.is_absolute():
            inbox_dir = repo_root / inbox_dir
        print(f"=== Migrating inbox: {inbox_dir} ===")
        moved = migrate_inbox(inbox_dir, workouts_dir)
        print(f"\n=== Done: moved {moved} FIT file(s) from inbox ===")
        return 0

    print("=== Migrating workouts/fit/ ===")
    fit_moved = migrate_directory(workouts_dir / "fit", "fit", workouts_dir)

    print(f"\n=== Migrating workouts/analysis/ ===")
    analysis_moved = migrate_directory(workouts_dir / "analysis", "analysis", workouts_dir)

    print(f"\n=== Cleaning up empty flat directories ===")
    remove_empty_dir(workouts_dir / "fit")
    remove_empty_dir(workouts_dir / "analysis")

    print(f"\n=== Done: moved {fit_moved} fit files + {analysis_moved} analysis files ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
