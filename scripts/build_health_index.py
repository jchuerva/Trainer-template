#!/usr/bin/env python3
"""
Build health/index.md — source of truth for daily health data.

Reads raw HealthAutoExport JSON files from health/daily/YYYY/MM/YYYY-MM-DD.json
and writes a machine-readable + human-readable table.

This index is the SINGLE source of truth: all chart scripts and yearly reports
read from this table, not from the raw JSONs directly.

Table columns (all numeric where applicable):
  Date | Sleep_h | Deep_h | REM_h | RHR | HRV_ms | SpO2 | Resp | Steps | Workout

Usage:
    python3 scripts/build_health_index.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from utils import get_repo_root


# ---------------------------------------------------------------------------
# Raw JSON extractors
# ---------------------------------------------------------------------------

def _qty_avg(metrics: list[dict], name: str) -> float | None:
    """Average of all qty entries for a named metric."""
    for m in metrics:
        if m["name"] == name and m.get("data"):
            vals = [e["qty"] for e in m["data"] if e.get("qty") is not None]
            return sum(vals) / len(vals) if vals else None
    return None


def _qty_sum(metrics: list[dict], name: str) -> float | None:
    """Sum of all qty entries for a named metric (e.g. steps)."""
    for m in metrics:
        if m["name"] == name and m.get("data"):
            vals = [e["qty"] for e in m["data"] if e.get("qty") is not None]
            return sum(vals) if vals else None
    return None


def _qty_single(metrics: list[dict], name: str) -> float | None:
    """Single daily value (first entry)."""
    for m in metrics:
        if m["name"] == name and m.get("data"):
            val = m["data"][0].get("qty")
            return float(val) if val is not None else None
    return None


def extract_day(date_str: str, raw: dict) -> dict:
    """Extract all daily metrics from a raw HealthAutoExport JSON."""
    metrics = raw.get("data", {}).get("metrics", [])
    workouts = raw.get("data", {}).get("workouts", [])

    # Sleep
    sleep_total = sleep_deep = sleep_rem = None
    for m in metrics:
        if m["name"] == "sleep_analysis" and m.get("data"):
            e = m["data"][0]
            sleep_total = e.get("totalSleep")
            sleep_deep = e.get("deep")
            sleep_rem = e.get("rem")
            break

    # Steps: sum all intraday
    steps_raw = _qty_sum(metrics, "step_count")
    steps = int(round(steps_raw)) if steps_raw is not None else None

    # HRV: average of all intraday readings
    hrv = _qty_avg(metrics, "heart_rate_variability")

    # RHR: single daily value
    rhr_raw = _qty_single(metrics, "resting_heart_rate")
    rhr = int(round(rhr_raw)) if rhr_raw is not None else None

    # SpO2: average of all readings
    spo2 = _qty_avg(metrics, "blood_oxygen_saturation")

    # Respiratory rate: average
    resp = _qty_avg(metrics, "respiratory_rate")

    # Workout flag + names
    workout_names = [w.get("name", "Workout") for w in workouts]

    return {
        "date": date_str,
        "sleep_h": round(sleep_total, 2) if sleep_total is not None else None,
        "deep_h": round(sleep_deep, 2) if sleep_deep is not None else None,
        "rem_h": round(sleep_rem, 2) if sleep_rem is not None else None,
        "rhr": rhr,
        "hrv_ms": round(hrv, 1) if hrv is not None else None,
        "spo2": round(spo2, 1) if spo2 is not None else None,
        "resp": round(resp, 1) if resp is not None else None,
        "steps": steps,
        "workout": ";".join(workout_names) if workout_names else None,
    }


# ---------------------------------------------------------------------------
# Index loader (for chart scripts)
# ---------------------------------------------------------------------------

def load_index(repo_root: Path | None = None) -> list[dict]:
    """
    Parse health/index.md and return list of dicts with numeric values.
    This is the canonical way for chart scripts to read health data.
    Returns rows sorted by date ascending.
    """
    if repo_root is None:
        repo_root = get_repo_root()
    index_path = repo_root / "health" / "index.md"
    if not index_path.exists():
        return []

    rows = []
    header = None
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells:
            continue
        # Header row
        if cells[0].lower() == "date":
            header = [c.lower().replace(" ", "_") for c in cells]
            continue
        # Separator row
        if set(cells[0]) <= {"-", " "}:
            continue
        if header is None:
            continue

        row: dict = {}
        for key, val in zip(header, cells):
            if key == "date":
                row["date"] = val
            elif key == "workout":
                row["workout"] = val if val and val != "-" else None
            else:
                try:
                    row[key] = float(val) if val and val != "-" else None
                except ValueError:
                    row[key] = None
        if row.get("date"):
            rows.append(row)

    return sorted(rows, key=lambda r: r["date"])


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def load_all_days(repo_root: Path) -> list[dict]:
    health_dir = repo_root / "health" / "daily"
    days = []
    for json_file in sorted(health_dir.rglob("*.json")):
        try:
            raw = json.loads(json_file.read_text(encoding="utf-8"))
            day = extract_day(json_file.stem, raw)
            days.append(day)
        except (json.JSONDecodeError, IOError):
            continue
    return sorted(days, key=lambda d: d["date"], reverse=True)


def fmt(val, decimals=None) -> str:
    if val is None:
        return "-"
    if decimals is not None:
        return f"{val:.{decimals}f}"
    return str(val)


def build_index_content(days: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    lines = [
        "# 🏥 Health Daily Index",
        "",
        "_Auto-generated — source of truth for health charts and yearly reports._  ",
        "_Do not edit manually. Run `python3 scripts/build_health_index.py` to regenerate._",
        "",
        f"**Last updated:** {now} UTC  ",
        f"**Total entries:** {len(days)}",
        "",
        "📖 [Guía de métricas y valores de referencia](METRICS.md)",
        "",
        "---",
        "",
        "## 📋 Datos diarios",
        "",
        "<!-- machine-readable table: numeric values only, '-' for missing -->",
        "| Date | Sleep_h | Deep_h | REM_h | RHR | HRV_ms | SpO2 | Resp | Steps | Workout |",
        "|------|---------|--------|-------|-----|--------|------|------|-------|---------|",
    ]

    for d in days:
        workout_tag = " 🏃" if d.get("workout") else ""
        row = (
            f"| {d['date']} "
            f"| {fmt(d.get('sleep_h'), 2)} "
            f"| {fmt(d.get('deep_h'), 2)} "
            f"| {fmt(d.get('rem_h'), 2)} "
            f"| {fmt(d.get('rhr'))} "
            f"| {fmt(d.get('hrv_ms'), 1)} "
            f"| {fmt(d.get('spo2'), 1)} "
            f"| {fmt(d.get('resp'), 1)} "
            f"| {fmt(d.get('steps'))} "
            f"| {d.get('workout') or '-'} |"
        )
        lines.append(row)

    lines.append("")
    return "\n".join(lines)


def main():
    repo_root = get_repo_root()
    days = load_all_days(repo_root)
    if not days:
        print("No health snapshots found.")
        return
    content = build_index_content(days)
    index_path = repo_root / "health" / "index.md"
    index_path.write_text(content, encoding="utf-8")
    print(f"✅ health/index.md updated ({len(days)} entries)")


if __name__ == "__main__":
    main()
