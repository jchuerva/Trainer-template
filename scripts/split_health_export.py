#!/usr/bin/env python3
"""
Split a multi-day HealthAutoExport JSON into one file per day.

Usage:
    python3 scripts/split_health_export.py <path-to-json>
    python3 scripts/split_health_export.py <path> --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from utils import get_repo_root


def parse_date(date_str: str) -> str | None:
    """Extract YYYY-MM-DD from a date string."""
    if not date_str:
        return None
    return date_str[:10]


def split_by_day(raw: dict) -> dict[str, dict]:
    """
    Split a multi-day HealthAutoExport JSON into per-day dicts.
    Returns {date_str: {data: {metrics: [...], workouts: [...]}}}
    """
    metrics = raw.get("data", {}).get("metrics", [])
    workouts = raw.get("data", {}).get("workouts", [])

    # Collect all dates
    all_dates: set[str] = set()

    # Group metric data entries by date
    metrics_by_date: dict[str, list[dict]] = defaultdict(list)
    for metric in metrics:
        by_date: dict[str, list] = defaultdict(list)
        for entry in metric.get("data", []):
            d = parse_date(entry.get("date", ""))
            if d:
                by_date[d].append(entry)
                all_dates.add(d)
        for d, entries in by_date.items():
            metrics_by_date[d].append({
                "name": metric["name"],
                "units": metric.get("units", ""),
                "data": entries,
            })

    # Group workouts by date (use start date)
    workouts_by_date: dict[str, list[dict]] = defaultdict(list)
    for w in workouts:
        d = parse_date(w.get("start", ""))
        if d:
            workouts_by_date[d].append(w)
            all_dates.add(d)

    # Build one dict per day
    result = {}
    for d in sorted(all_dates):
        day_data: dict = {"metrics": metrics_by_date.get(d, [])}
        if workouts_by_date.get(d):
            day_data["workouts"] = workouts_by_date[d]
        result[d] = {"data": day_data}

    return result


def save_day(date_str: str, day_data: dict, repo_root: Path) -> Path:
    year, month, _ = date_str.split("-")
    out_dir = repo_root / "health" / "daily" / year / month
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.json"

    # Merge with existing file if present
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        # Merge metrics: existing wins for already-present metric names
        existing_metrics = {m["name"]: m for m in existing.get("data", {}).get("metrics", [])}
        new_metrics = {m["name"]: m for m in day_data.get("data", {}).get("metrics", [])}
        merged_metrics = {**new_metrics, **existing_metrics}  # existing takes priority
        day_data["data"]["metrics"] = list(merged_metrics.values())
        # Merge workouts
        existing_workouts = existing.get("data", {}).get("workouts", [])
        new_workouts = day_data.get("data", {}).get("workouts", [])
        if new_workouts or existing_workouts:
            # Deduplicate by start time
            all_w = {w["start"]: w for w in (existing_workouts + new_workouts)}
            day_data["data"]["workouts"] = list(all_w.values())

    out_path.write_text(json.dumps(day_data, indent=2, ensure_ascii=False) + "\n")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Split multi-day HealthAutoExport JSON into daily files")
    parser.add_argument("input", help="Path to HealthAutoExport JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Print dates without saving")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    days = split_by_day(raw)

    if args.dry_run:
        for d, data in days.items():
            n_metrics = len(data["data"]["metrics"])
            n_workouts = len(data["data"].get("workouts", []))
            print(f"  {d} — {n_metrics} metrics, {n_workouts} workouts")
        print(f"\nTotal: {len(days)} days")
        return

    repo_root = get_repo_root()
    saved = []
    for d, data in days.items():
        out_path = save_day(d, data, repo_root)
        n_workouts = len(data["data"].get("workouts", []))
        workout_tag = f" +{n_workouts} workout(s)" if n_workouts else ""
        print(f"✅ {out_path.relative_to(repo_root)}{workout_tag}")
        saved.append(d)

    print(f"\n{len(saved)} daily files saved.")


if __name__ == "__main__":
    main()
