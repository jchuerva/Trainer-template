#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from fitparse import FitFile
    FITPARSE_AVAILABLE = True
except ImportError:
    FITPARSE_AVAILABLE = False


@dataclass(frozen=True)
class WorkoutRow:
    date: str
    workout_type: str
    distance_km: str
    time: str
    avg_pace: str
    avg_hr: str
    max_hr: str
    analysis_rel: str | None


def _extract(pattern: str, text: str) -> str:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _get_sport_from_fit(fit_path: Path) -> str:
    """Extract sport type from FIT file."""
    if not FITPARSE_AVAILABLE or not fit_path.exists():
        return ""
    
    try:
        fitfile = FitFile(str(fit_path))
        
        # Try to get sport from session message
        for record in fitfile.get_messages('session'):
            for field in record:
                if field.name == 'sport':
                    sport = str(field.value)
                    # Capitalize first letter for consistency
                    return sport.capitalize() if sport else ""
        
        # Fallback to sport message
        for record in fitfile.get_messages('sport'):
            for field in record:
                if field.name == 'sport':
                    sport = str(field.value)
                    return sport.capitalize() if sport else ""
    except (FileNotFoundError, IOError, ValueError):
        # FIT file parsing errors - silently fall back to analysis file
        pass
    except Exception:
        # Unexpected errors - silently fall back to analysis file
        pass
    
    return ""


def _find_fit_for_analysis(analysis_path: Path, workouts_root: Path) -> Path | None:
    """Find the .fit file corresponding to an analysis file in the YYYY/MM structure.

    Given an analysis at ``workouts/YYYY/MM/analysis/STEM.md``, look for the
    matching fit at ``workouts/YYYY/MM/fit/STEM.fit``.

    Args:
        analysis_path: Path to the .md analysis file.
        workouts_root: Root workouts directory (e.g. ``workouts/``).

    Returns:
        Path to the .fit file, or ``None`` if not found.
    """
    rel = analysis_path.relative_to(workouts_root)  # YYYY/MM/analysis/STEM.md
    parts = rel.parts
    if len(parts) == 4 and parts[2] == "analysis":
        # New YYYY/MM/analysis/ layout — look in sibling fit/ dir
        year, month, _, name = parts
        stem = Path(name).stem
        fit_dir = workouts_root / year / month / "fit"
        exact = fit_dir / f"{stem}.fit"
        if exact.exists():
            return exact
        # glob fallback for Unicode/space variants
        for candidate in fit_dir.glob(f"{stem}*.fit"):
            if candidate.stem == stem or (
                candidate.stem.startswith(stem)
                and len(candidate.stem) > len(stem)
                and not candidate.stem[len(stem)].isalnum()
            ):
                return candidate
    return None


def _parse_analysis(path: Path, *, workouts_dir: Path, fits_dir: Path) -> WorkoutRow:
    """Parse a single analysis .md file into a WorkoutRow.

    Args:
        path: Path to the analysis .md file.
        workouts_dir: Root workouts directory (used for relative-path computation).
        fits_dir: Root directory to search for matching .fit files.
            Ignored in favour of the YYYY/MM co-location when *path* follows the
            new hierarchy.

    Returns:
        Populated WorkoutRow.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    stem = path.stem

    date = _extract(r"Workout Summary \((\d{4}-\d{2}-\d{2})\)", text)
    if not date:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
        date = m.group(1) if m else ""

    # Try to find corresponding FIT file and extract sport type.
    # Prefer co-located YYYY/MM/fit/ sibling; fall back to flat fits_dir.
    workout_type = ""
    fit_file = _find_fit_for_analysis(path, workouts_dir)
    if fit_file is not None:
        workout_type = _get_sport_from_fit(fit_file)

    if not workout_type and fits_dir and fits_dir.exists():
        # Legacy flat layout fallback
        exact_fit = fits_dir / f"{stem}.fit"
        if exact_fit.exists():
            workout_type = _get_sport_from_fit(exact_fit)
        if not workout_type:
            for fit_file_candidate in fits_dir.glob(f"{stem}*.fit"):
                if (
                    fit_file_candidate.stem == stem
                    or (
                        fit_file_candidate.stem.startswith(stem)
                        and len(fit_file_candidate.stem) > len(stem)
                        and not fit_file_candidate.stem[len(stem)].isalnum()
                    )
                ):
                    workout_type = _get_sport_from_fit(fit_file_candidate)
                    if workout_type:
                        break

    # Fallback to analysis if no FIT file found or sport couldn't be extracted
    if not workout_type:
        workout_type = _extract(r"\*\*Workout type:\*\*\s*(.+)", text)

    distance_km = _extract(r"\*\*Distance:\*\*\s*([0-9]+(?:\.[0-9]+)?)\s*km\b", text)
    time = _extract(r"\*\*Time:\*\*\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)\b", text)
    avg_pace = _extract(r"\*\*Average pace:\*\*\s*~?\s*([0-9]{1,2}:[0-9]{2})\s*min/km\b", text)
    avg_hr = _extract(r"\*\*Average HR:\*\*\s*([0-9]{2,3})\s*bpm\b", text)
    max_hr = _extract(r"\*\*Max HR:\*\*\s*([0-9]{2,3})\s*bpm\b", text)

    try:
        analysis_rel = path.relative_to(workouts_dir).as_posix()
    except ValueError:
        analysis_rel = None

    return WorkoutRow(
        date=date,
        workout_type=workout_type,
        distance_km=distance_km,
        time=time,
        avg_pace=avg_pace,
        avg_hr=avg_hr,
        max_hr=max_hr,
        analysis_rel=analysis_rel,
    )


def _write_index_md(out_path: Path, rows: list[WorkoutRow]) -> None:
    """Write the workout index markdown table to *out_path*.

    Args:
        out_path: Destination path for the index file.
        rows: Sorted list of WorkoutRow objects.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Workouts index")
    lines.append("")
    lines.append("Generated from files in `workouts/`.")
    lines.append("")
    lines.append("| Date | Type | Distance (km) | Time | Avg pace (min/km) | Avg HR | Max HR | Analysis |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")

    for r in rows:
        analysis_link = f"[view]({r.analysis_rel})" if r.analysis_rel else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    r.date or "",
                    r.workout_type or "",
                    r.distance_km or "",
                    r.time or "",
                    r.avg_pace or "",
                    r.avg_hr or "",
                    r.max_hr or "",
                    analysis_link,
                ]
            )
            + " |"
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def main() -> int:
    """Entry point: scan analysis files and regenerate workouts/index.md.

    Returns:
        Exit code (0 for success).
    """
    ap = argparse.ArgumentParser(description="Build workouts/index.md from workout analysis markdown files")
    ap.add_argument(
        "--analysis-dir",
        default="workouts",
        help="Root directory to scan recursively for analysis .md files (default: workouts)",
    )
    ap.add_argument(
        "--fits-dir",
        default="workouts",
        help="Root directory to search for .fit files (default: workouts)",
    )
    ap.add_argument("--out-md", default="workouts/index.md")
    args = ap.parse_args()

    repo_root = Path.cwd()
    workouts_dir = (repo_root / "workouts").resolve()
    analysis_root = (repo_root / args.analysis_dir).resolve()
    fits_dir = (repo_root / args.fits_dir).resolve()

    if not analysis_root.exists():
        return 0

    # Scan recursively so we find files in YYYY/MM/analysis/ sub-trees
    analysis_files = sorted(
        (p for p in analysis_root.rglob("*.md") if p.is_file() and p.name != "index.md"),
        reverse=True,
    )
    rows = [_parse_analysis(p, workouts_dir=workouts_dir, fits_dir=fits_dir) for p in analysis_files]

    _write_index_md((repo_root / args.out_md).resolve(), rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
