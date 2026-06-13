#!/usr/bin/env python3
"""
Extract workout data from FIT files.

This script parses FIT files and outputs structured data that can be passed
to the workout-analyst agent, removing the need for the agent to execute code.

Fields extracted from the FIT session record:
  - start_time, sport, sub_sport
  - total_distance, total_timer_time, total_elapsed_time
  - avg_speed / enhanced_avg_speed
  - avg_heart_rate, max_heart_rate
  - avg_cadence / avg_running_cadence
  - total_ascent, total_descent
  - total_calories
  - avg_temperature
  - avg_power, normalized_power (if available — e.g. running power meter)
  - total_strides (if available)
  - training_stress_score, intensity_factor (if device computes them)

Fields extracted per lap:
  - total_distance, total_timer_time
  - avg_speed / enhanced_avg_speed
  - avg_heart_rate, max_heart_rate
  - avg_cadence / avg_running_cadence
  - total_ascent, total_descent (per-lap elevation)
  - avg_power (if available)
  - lap_trigger (manual/distance/time)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import fitparse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round(value, digits=2):
    """Round a numeric value, return None if value is None."""
    return round(value, digits) if value is not None else None


def format_time(seconds: float | None) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    if seconds is None:
        return "—"
    total_secs = int(seconds)
    hours, remainder = divmod(total_secs, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_pace(speed_mps: float | None) -> str:
    """Convert m/s to min/km pace string."""
    if speed_mps is None or speed_mps <= 0:
        return "—"
    pace_seconds = 1000 / speed_mps
    minutes = int(pace_seconds // 60)
    seconds = int(pace_seconds % 60)
    return f"{minutes}:{seconds:02d}"


# ---------------------------------------------------------------------------
# Field mapping tables
# ---------------------------------------------------------------------------
# Each entry maps a FIT field name to a list of (metric_key, transform) tuples.
# A field may populate multiple metric keys (e.g. speed → pace + mps).
# When two FIT fields target the same metric key, the later one wins
# (e.g. enhanced_avg_speed overwrites avg_speed).

SESSION_FIELD_MAP: dict[str, list[tuple[str, callable]]] = {
    "sport":                [("sport", str)],
    "sub_sport":            [("sub_sport", str)],
    "total_distance":       [("total_distance_km", lambda v: round(v / 1000, 2))],
    "total_timer_time":     [("total_time_seconds", lambda v: v),
                             ("total_time_formatted", format_time)],
    "total_elapsed_time":   [("total_elapsed_time_seconds", lambda v: v)],
    "avg_speed":            [("average_speed_mps", lambda v: v),
                             ("average_pace", format_pace)],
    "enhanced_avg_speed":   [("average_speed_mps", lambda v: v),
                             ("average_pace", format_pace)],
    "avg_heart_rate":       [("average_hr", int)],
    "max_heart_rate":       [("max_hr", int)],
    "avg_cadence":          [("average_cadence", int)],
    "avg_running_cadence":  [("average_cadence", int)],
    "total_strides":        [("total_strides", int)],
    "total_ascent":         [("total_ascent_m", int)],
    "total_descent":        [("total_descent_m", int)],
    "total_calories":       [("total_calories", int)],
    "avg_temperature":      [("avg_temperature_c", int)],
    "avg_power":            [("avg_power_w", int)],
    "normalized_power":     [("normalized_power_w", int)],
    "training_stress_score": [("training_stress_score", lambda v: _round(v, 1))],
    "intensity_factor":     [("intensity_factor", lambda v: _round(v, 3))],
}

LAP_FIELD_MAP: dict[str, list[tuple[str, callable]]] = {
    "total_distance":       [("distance_km", lambda v: round(v / 1000, 2))],
    "total_timer_time":     [("time_seconds", lambda v: v),
                             ("time_formatted", format_time)],
    "avg_speed":            [("pace", format_pace)],
    "enhanced_avg_speed":   [("pace", format_pace)],
    "avg_heart_rate":       [("avg_hr", int)],
    "max_heart_rate":       [("max_hr", int)],
    "avg_cadence":          [("avg_cadence", int)],
    "avg_running_cadence":  [("avg_cadence", int)],
    "total_ascent":         [("total_ascent_m", int)],
    "total_descent":        [("total_descent_m", int)],
    "avg_power":            [("avg_power_w", int)],
    "lap_trigger":          [("lap_trigger", str)],
}


def _apply_field_map(field_map: dict, record, target: dict) -> None:
    """Apply a field mapping table to populate *target* from *record* fields."""
    for field in record:
        mappings = field_map.get(field.name)
        if mappings is None or field.value is None:
            continue
        for metric_key, transform in mappings:
            target[metric_key] = transform(field.value)


def parse_fit_file(fit_path: Path) -> dict:
    """
    Parse FIT file and extract key workout metrics.
    Returns a dictionary with workout summary and lap data.
    """
    fitfile = fitparse.FitFile(str(fit_path))

    # Initialize metrics
    metrics = {
        "file_name": fit_path.name,
        "start_time": None,
        "start_time_formatted": None,
        "sport": None,
        "sub_sport": None,
        "total_distance_km": None,
        "total_time_seconds": None,
        "total_time_formatted": None,
        "total_elapsed_time_seconds": None,   # includes pauses
        "average_pace": None,
        "average_speed_mps": None,
        "average_hr": None,
        "max_hr": None,
        "average_cadence": None,
        "total_strides": None,
        "total_ascent_m": None,
        "total_descent_m": None,
        "total_calories": None,
        "avg_temperature_c": None,
        "avg_power_w": None,
        "normalized_power_w": None,
        "training_stress_score": None,
        "intensity_factor": None,
        "laps": [],
    }

    # Parse session records for summary data
    for record in fitfile.get_messages("session"):
        # Handle start_time specially (requires truthiness check + formatted variant)
        for field in record:
            if field.name == "start_time" and field.value:
                metrics["start_time"] = str(field.value)
                if isinstance(field.value, datetime):
                    metrics["start_time_formatted"] = field.value.strftime(
                        "%Y-%m-%d %H:%M"
                    )
        # Apply the declarative mapping for all other session fields
        _apply_field_map(SESSION_FIELD_MAP, record, metrics)

    # Parse lap data for segment analysis
    for lap_num, record in enumerate(fitfile.get_messages("lap"), start=1):
        lap = {
            "lap_number": lap_num,
            "distance_km": None,
            "time_seconds": None,
            "time_formatted": None,
            "pace": None,
            "avg_hr": None,
            "max_hr": None,
            "avg_cadence": None,
            "total_ascent_m": None,
            "total_descent_m": None,
            "avg_power_w": None,
            "lap_trigger": None,
        }
        _apply_field_map(LAP_FIELD_MAP, record, lap)
        metrics["laps"].append(lap)

    return metrics


def format_as_markdown(metrics: dict) -> str:
    """Format extracted metrics as markdown for the agent prompt."""
    lines = []
    lines.append("## Extracted Workout Data")
    lines.append("")
    lines.append("### Session Summary")
    lines.append("")
    lines.append(f"- **File:** {metrics['file_name']}")
    lines.append(f"- **Date/Time:** {metrics['start_time_formatted'] or '—'}")
    lines.append(f"- **Sport:** {metrics['sport'] or '—'}")
    lines.append(f"- **Distance:** {metrics['total_distance_km'] or '—'} km")
    lines.append(f"- **Duration:** {metrics['total_time_formatted'] or '—'}")
    lines.append(f"- **Average Pace:** {metrics['average_pace'] or '—'} /km")
    lines.append(f"- **Average HR:** {metrics['average_hr'] or '—'} bpm")
    lines.append(f"- **Max HR:** {metrics['max_hr'] or '—'} bpm")
    lines.append(f"- **Average Cadence:** {metrics['average_cadence'] or '—'} spm")
    lines.append(f"- **Total Ascent:** {metrics['total_ascent_m'] or '—'} m")
    lines.append(f"- **Total Descent:** {metrics['total_descent_m'] or '—'} m")
    if metrics["total_calories"]:
        lines.append(f"- **Calories:** {metrics['total_calories']} kcal")
    if metrics["avg_temperature_c"]:
        lines.append(f"- **Temperature:** {metrics['avg_temperature_c']}°C")
    if metrics.get("avg_power_w"):
        np_str = f" / NP {metrics.get('normalized_power_w')} W" if metrics.get("normalized_power_w") else ""
        lines.append(f"- **Avg Power:** {metrics.get('avg_power_w')} W{np_str}")
    if metrics.get("training_stress_score"):
        if_str = f" / IF {metrics.get('intensity_factor')}" if metrics.get("intensity_factor") else ""
        lines.append(f"- **Training Stress Score (TSS):** {metrics.get('training_stress_score')}{if_str}")
    if metrics.get("sub_sport") and metrics.get("sub_sport") not in ("generic", "None", "none"):
        lines.append(f"- **Sub-sport:** {metrics.get('sub_sport')}")
    if metrics.get("total_strides"):
        lines.append(f"- **Total Strides:** {metrics.get('total_strides')}")
    if metrics.get("total_elapsed_time_seconds") and metrics.get("total_time_seconds"):
        pause_s = int(metrics["total_elapsed_time_seconds"] - metrics["total_time_seconds"])
        if pause_s > 5:
            lines.append(f"- **Paused time:** {format_time(pause_s)} (elapsed - moving)")

    if metrics.get("laps"):
        lines.append("")
        lines.append("### Lap/Split Data")
        lines.append("")
        # Show elevation/power per lap only when at least one lap has the data
        has_lap_elevation = any(
            lap.get("total_ascent_m") or lap.get("total_descent_m") for lap in metrics["laps"]
        )
        has_lap_power = any(lap.get("avg_power_w") for lap in metrics["laps"])

        header_cols = "| Lap | Distance (km) | Time | Pace | Avg HR | Max HR | Cadence |"
        sep_cols = "|---:|---:|---:|---:|---:|---:|---:|"
        if has_lap_elevation:
            header_cols += " Ascent/Descent |"
            sep_cols += "---:|"
        if has_lap_power:
            header_cols += " Avg Power |"
            sep_cols += "---:|"

        lines.append(header_cols)
        lines.append(sep_cols)

        for lap in metrics["laps"]:
            row = (
                f"| {lap['lap_number']} "
                f"| {lap['distance_km'] or '—'} "
                f"| {lap['time_formatted'] or '—'} "
                f"| {lap['pace'] or '—'} "
                f"| {lap['avg_hr'] or '—'} "
                f"| {lap['max_hr'] or '—'} "
                f"| {lap['avg_cadence'] or '—'} |"
            )
            if has_lap_elevation:
                asc = lap.get('total_ascent_m') or 0
                desc = lap.get('total_descent_m') or 0
                row += f" +{asc}/-{desc} m |"
            if has_lap_power:
                row += f" {lap.get('avg_power_w') or '—'} W |"
            lines.append(row)

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract workout data from FIT files."
    )
    ap.add_argument("fit_file", type=Path, help="Path to .fit file")
    ap.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    args = ap.parse_args()

    if not args.fit_file.exists():
        print(f"Error: FIT file not found: {args.fit_file}", file=sys.stderr)
        return 1

    try:
        metrics = parse_fit_file(args.fit_file)
    except Exception as e:
        print(f"Error parsing FIT file: {e}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(metrics, indent=2, default=str))
    else:
        print(format_as_markdown(metrics))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
