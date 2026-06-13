#!/usr/bin/env python3
"""
Generate a GitHub-style workout heatmap.

Reads workout data from:
  1. health/daily/YYYY/MM/YYYY-MM-DD.json (has workouts embedded)
  2. workouts/YYYY/MM/analysis/*.md (filename date = workout day)

Produces health/charts/workout-heatmap.png

Usage:
    python3 scripts/generate_workout_heatmap.py
"""

from __future__ import annotations

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import date, timedelta
from pathlib import Path

from utils import get_repo_root


# ---------------------------------------------------------------------------
# Colors (dark GitHub theme)
# ---------------------------------------------------------------------------
BG = "#0d1117"
CELL_EMPTY = "#161b22"
CELL_NO_WORKOUT = "#21262d"
CELL_WORKOUT = "#39d353"
CELL_TODAY = "#58a6ff"
TEXT_MUTED = "#8b949e"
TEXT_BRIGHT = "#e6edf3"


def collect_workout_days(repo_root: Path) -> dict[str, list[str]]:
    """Return {date_str: [workout_name, ...]} from health JSONs + analysis files."""
    workout_days: dict[str, list[str]] = {}

    # From health/daily JSONs (most accurate, includes workout names)
    for f in sorted((repo_root / "health" / "daily").rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            workouts = data.get("data", {}).get("workouts", [])
            if workouts:
                workout_days[f.stem] = [w.get("name", "Workout") for w in workouts]
        except (json.JSONDecodeError, IOError):
            continue

    # From workouts/ analysis files (full history, YYYY/MM/analysis/ structure)
    for f in sorted((repo_root / "workouts").rglob("**/analysis/*.md")):
        # Skip the index file
        if f.name == "index.md":
            continue
        date_str = f.stem[:10]
        if date_str not in workout_days:
            workout_days[date_str] = [f.stem[11:].replace("-", " ").title()]

    return workout_days


def workout_color(names: list[str]) -> str:
    """Return workout color — single green for any workout day."""
    if not names:
        return CELL_NO_WORKOUT
    return CELL_WORKOUT


def build_heatmap(workout_days: dict[str, list[str]], out_path: Path):
    today = date.today()

    # Start from the Monday 52 weeks ago
    start = today - timedelta(weeks=52)
    start = start - timedelta(days=start.weekday())  # back to Monday

    # Build list of all days
    days = []
    d = start
    while d <= today:
        days.append(d)
        d += timedelta(days=1)

    # Group into weeks (Mon–Sun columns)
    weeks: list[list[date]] = []
    week: list[date] = []
    for d in days:
        week.append(d)
        if d.weekday() == 6:  # Sunday
            weeks.append(week)
            week = []
    if week:
        weeks.append(week)

    # --- Layout constants ---
    CELL = 11
    GAP = 3
    STEP = CELL + GAP
    LEFT_PAD = 28
    TOP_PAD = 22

    total_cols = len(weeks)
    fig_w = LEFT_PAD / 72 + total_cols * STEP / 72 + 0.3
    fig_h = 2.6

    fig, ax = plt.subplots(figsize=(max(fig_w, 12), fig_h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # --- Draw cells ---
    month_labels: dict[str, float] = {}  # month abbr -> x pixel

    for col, week in enumerate(weeks):
        for day_obj in week:
            row = day_obj.weekday()  # Mon=0 … Sun=6
            date_str = day_obj.strftime("%Y-%m-%d")

            x = LEFT_PAD + col * STEP
            y = TOP_PAD + (6 - row) * STEP  # Mon at top

            if day_obj > today:
                color = CELL_EMPTY
            elif day_obj == today:
                if date_str in workout_days:
                    color = workout_color(workout_days[date_str])
                else:
                    color = CELL_TODAY
            elif date_str in workout_days:
                color = workout_color(workout_days[date_str])
            else:
                color = CELL_NO_WORKOUT

            rect = patches.FancyBboxPatch(
                (x, y), CELL, CELL,
                boxstyle="round,pad=1.5",
                facecolor=color,
                edgecolor="none",
            )
            ax.add_patch(rect)

            # Month label: first cell of each month in the top row (Mon)
            if day_obj.day <= 7 and row == 0:
                month_labels[day_obj.strftime("%b")] = x

    # --- Month labels ---
    for month, x in month_labels.items():
        ax.text(x, TOP_PAD + 7 * STEP + 4, month,
                color=TEXT_MUTED, fontsize=7.5, va="bottom")

    # --- Day of week labels ---
    for i, label in enumerate(["Mon", "", "Wed", "", "Fri", "", "Sun"]):
        if label:
            ax.text(LEFT_PAD - 4, TOP_PAD + (6 - i) * STEP + CELL / 2,
                    label, color=TEXT_MUTED, fontsize=7, va="center", ha="right")

    # --- Title ---
    workout_count = len(workout_days)
    ax.text(LEFT_PAD, TOP_PAD + 7 * STEP + 18,
            f"{workout_count} workout days in the last year",
            color=TEXT_BRIGHT, fontsize=10, fontweight="bold", va="bottom")

    # --- Axes ---
    total_w = LEFT_PAD + total_cols * STEP + 10
    total_h = TOP_PAD + 7 * STEP + 28
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    ax.invert_yaxis()
    ax.axis("off")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.3)
    fig.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✅ {out_path.relative_to(get_repo_root())}")


def main():
    repo_root = get_repo_root()
    workout_days = collect_workout_days(repo_root)
    print(f"Found {len(workout_days)} workout days")
    build_heatmap(workout_days, repo_root / "workouts" / "charts" / "workout-heatmap.png")


if __name__ == "__main__":
    main()
