#!/usr/bin/env python3
"""
Generate a yearly health & training report.

Produces health/yearly/YYYY.md with:
  - Training stats (workouts, km, streaks, type breakdown)
  - Health stats (HRV, RHR, sleep averages)
  - Charts: heatmap + monthly volume + monthly HRV/RHR

Usage:
    python3 scripts/generate_yearly_report.py           # current year
    python3 scripts/generate_yearly_report.py --year 2025
    python3 scripts/generate_yearly_report.py --year 2025 --final  # mark as definitive
"""

from __future__ import annotations

import argparse
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from utils import get_repo_root, RUNNING_KEYWORDS, NON_RUNNING_KEYWORDS
from build_health_index import load_index


# Spanish month names (used in stats and report text)
MONTH_NAMES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_workout_days(repo_root: Path, year: int) -> list[dict]:
    """Load all workouts for a given year from workouts/index.md (primary source).

    Multiple workouts on the same date are preserved as separate entries
    (e.g. 2026-02-22 has both a run and a cross-training session).
    """
    index_path = repo_root / "workouts" / "index.md"
    workouts: list[dict] = []

    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            cells = parts[1:-1]
            if len(cells) < 7:
                continue
            date_str = cells[0]
            if not date_str or not date_str.startswith(str(year)):
                continue
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            # Skip header/separator rows
            if date_str.lower() == "date" or set(date_str) == {"-"}:
                continue

            workout_type = cells[1] if len(cells) > 1 else ""
            try:
                distance_km = float(cells[2]) if cells[2] else None
            except ValueError:
                distance_km = None
            time_str = cells[3] if len(cells) > 3 else None
            avg_pace = cells[4] if len(cells) > 4 else None
            try:
                avg_hr = int(cells[5]) if cells[5].isdigit() else None
            except (ValueError, IndexError):
                avg_hr = None

            workouts.append({
                "date": date_str,
                "name": workout_type,
                "distance_km": distance_km,
                "time": time_str,
                "avg_pace": avg_pace,
                "avg_hr": avg_hr,
                "source": "index",
            })

    # Enrich workout names from health JSONs where available
    health_dir = repo_root / "health" / "daily" / str(year)
    for f in sorted(health_dir.rglob("*.json")) if health_dir.exists() else []:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            health_workouts = data.get("data", {}).get("workouts", [])
            if not health_workouts:
                continue
            date_str = f.stem
            # Apply enriched name to all entries matching this date
            for entry in workouts:
                if entry["date"] == date_str:
                    entry["name"] = health_workouts[0].get("name", entry["name"])
        except (json.JSONDecodeError, IOError):
            continue

    return sorted(workouts, key=lambda x: x["date"])


def load_health_snapshots(repo_root: Path, year: int) -> list[dict]:
    """Load health data for a year from health/index.md (source of truth).
    Returns rows as dicts with numeric fields, filtered to the given year.
    """
    all_rows = load_index(repo_root)
    return [
        r for r in all_rows
        if r.get("date", "").startswith(str(year))
    ]


def get_metric_single(metrics: list[dict], name: str) -> float | None:
    """Kept for compatibility — not used when reading from index."""
    for m in metrics:
        if m["name"] == name and m.get("data"):
            val = m["data"][0].get("qty")
            return float(val) if val is not None else None
    return None


def get_hrv_avg(metrics: list[dict]) -> float | None:
    """Kept for compatibility — not used when reading from index."""
    for m in metrics:
        if m["name"] == "heart_rate_variability" and m.get("data"):
            vals = [e["qty"] for e in m["data"] if e.get("qty") is not None]
            return sum(vals) / len(vals) if vals else None
    return None


def get_sleep_total(metrics: list[dict]) -> float | None:
    """Kept for compatibility — not used when reading from index."""
    for m in metrics:
        if m["name"] == "sleep_analysis" and m.get("data"):
            return m["data"][0].get("totalSleep")
    return None


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def compute_training_stats(workouts: list[dict], year: int) -> dict:
    if not workouts:
        return {}

    total = len(workouts)
    km_values = [w["distance_km"] for w in workouts if w.get("distance_km")]
    total_km = sum(km_values) if km_values else None
    runs_with_km = len(km_values)

    # Pace stats (running only)
    pace_values = []
    hr_values = []
    for w in workouts:
        pace = w.get("avg_pace", "")
        if pace and ":" in str(pace):
            try:
                mins, secs = pace.split(":")
                pace_values.append(int(mins) * 60 + int(secs))
            except ValueError:
                pass
        if w.get("avg_hr"):
            hr_values.append(w["avg_hr"])

    # Per-month breakdown
    by_month = defaultdict(list)
    for w in workouts:
        month = int(w["date"][5:7])
        by_month[month].append(w)

    # Longest streak
    date_set = {datetime.strptime(w["date"], "%Y-%m-%d").date() for w in workouts}
    max_streak = current_streak = 0
    check = date(year, 1, 1)
    end = date(year, 12, 31) if year < date.today().year else date.today()
    while check <= end:
        if check in date_set:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
        check += timedelta(days=1)

    # Best month (Spanish name)
    best_month_num = max(by_month, key=lambda m: len(by_month[m])) if by_month else None
    best_month_name = MONTH_NAMES[best_month_num - 1] if best_month_num else None

    # Workout type breakdown — explicit mapping for index.md type values
    RUNNING_TYPES = {"running", "correr", "treadmill"}
    CROSS_TYPES = {"fitness_equipment", "cross", "cycling", "swimming", "walking", "hiit", "yoga", "strength"}
    type_counts = defaultdict(int)
    for w in workouts:
        name_lower = w["name"].lower().strip()
        if name_lower in CROSS_TYPES or any(k in name_lower for k in NON_RUNNING_KEYWORDS):
            type_counts["Cross-training"] += 1
        elif name_lower in RUNNING_TYPES or any(k in name_lower for k in RUNNING_KEYWORDS):
            type_counts["Running"] += 1
        else:
            type_counts["Otro"] += 1

    # Avg pace: true average (mean of all pace values in seconds)
    avg_pace_str = None
    if pace_values:
        avg_secs = sum(pace_values) / len(pace_values)
        avg_pace_str = f"{int(avg_secs)//60}:{int(avg_secs)%60:02d}"

    return {
        "total_workouts": total,
        "total_km": round(total_km, 1) if total_km else None,
        "runs_with_km": runs_with_km,
        "avg_km_per_run": round(total_km / runs_with_km, 1) if km_values else None,
        "avg_pace": avg_pace_str,
        "avg_hr": round(sum(hr_values) / len(hr_values)) if hr_values else None,
        "by_month": {m: len(ws) for m, ws in by_month.items()},
        "km_by_month": {
            m: round(sum(w["distance_km"] for w in ws if w.get("distance_km")), 1)
            for m, ws in by_month.items()
        },
        "max_streak_days": max_streak,
        "max_streak_label": "día consecutivo" if max_streak == 1 else "días consecutivos",
        "best_month": best_month_name,
        "type_counts": dict(type_counts),
    }


def compute_health_stats(snapshots: list[dict]) -> dict:
    """Compute annual health stats from index rows."""
    if not snapshots:
        return {}

    hrvs = [(r["date"], r["hrv_ms"]) for r in snapshots if r.get("hrv_ms") is not None]
    rhrs = [(r["date"], r["rhr"]) for r in snapshots if r.get("rhr") is not None]
    sleeps = [(r["date"], r["sleep_h"]) for r in snapshots
              if r.get("sleep_h") is not None and r["sleep_h"] > 0]

    def stats(vals):
        if not vals:
            return {}
        values = [v for _, v in vals]
        return {
            "avg": round(sum(values) / len(values), 1),
            "min": round(min(values), 1),
            "max": round(max(values), 1),
        }

    poor_sleep_days = sum(1 for _, h in sleeps if h < 6.0)

    return {
        "hrv": stats(hrvs),
        "rhr": stats(rhrs),
        "sleep": {**stats(sleeps), "poor_days": poor_sleep_days},
        "days_with_data": sum(
            1 for r in snapshots
            if any(r.get(k) is not None for k in ("hrv_ms", "rhr", "sleep_h", "steps", "spo2", "resp"))
        ),
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

BG = "#0d1117"
CELL_NO_WORKOUT = "#21262d"
CELL_WORKOUT = "#39d353"
CELL_FUTURE = "#161b22"
CELL_TODAY = "#58a6ff"
TEXT_MUTED = "#8b949e"
TEXT_BRIGHT = "#e6edf3"
CHART_BG = "white"


def chart_heatmap_year(workouts: list[dict], year: int, out_path: Path):
    """Full-year heatmap (Jan–Dec) for a specific year."""
    workout_dates = {w["date"] for w in workouts}
    today = date.today()

    start = date(year, 1, 1)
    # Align to Monday of that week
    start = start - timedelta(days=start.weekday())
    end = date(year, 12, 31)

    CELL, GAP = 11, 3
    STEP = CELL + GAP
    LEFT_PAD = 28
    TOP_PAD = 20

    weeks = []
    week = []
    d = start
    while d <= end + timedelta(days=6):
        week.append(d)
        if d.weekday() == 6:
            weeks.append(week)
            week = []
        d += timedelta(days=1)
    if week:
        weeks.append(week)

    fig, ax = plt.subplots(figsize=(max(len(weeks) * STEP / 72, 12), 2.4))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    month_labels = {}
    for col, wk in enumerate(weeks):
        for day_obj in wk:
            # Render all cells; style out-of-year days as CELL_FUTURE
            # This avoids visually incomplete trailing columns
            row = day_obj.weekday()
            date_str = day_obj.strftime("%Y-%m-%d")
            x = LEFT_PAD + col * STEP
            y = TOP_PAD + row * STEP

            if day_obj.year != year:
                color = CELL_FUTURE
            elif day_obj > today:
                color = CELL_FUTURE
            elif day_obj == today:
                if date_str in workout_dates:
                    color = CELL_WORKOUT
                else:
                    color = CELL_TODAY
            elif date_str in workout_dates:
                color = CELL_WORKOUT
            else:
                color = CELL_NO_WORKOUT

            rect = patches.FancyBboxPatch(
                (x, y), CELL, CELL,
                boxstyle="round,pad=1.5",
                facecolor=color, edgecolor="none"
            )
            ax.add_patch(rect)

            if day_obj.day <= 7 and row == 0 and day_obj.year == year:
                month_labels[day_obj.strftime("%b")] = x

    for month, x in month_labels.items():
        ax.text(x, TOP_PAD - 4, month, color=TEXT_MUTED, fontsize=7.5, va="bottom")

    for i, label in enumerate(["Mon", "", "Wed", "", "Fri", "", "Sun"]):
        if label:
            ax.text(LEFT_PAD - 4, TOP_PAD + i * STEP + CELL / 2,
                    label, color=TEXT_MUTED, fontsize=7, va="center", ha="right")

    total_w = LEFT_PAD + len(weeks) * STEP + 10
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, TOP_PAD + 7 * STEP + 8)
    ax.invert_yaxis()
    ax.axis("off")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.2)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def chart_monthly_volume(stats: dict, year: int, out_path: Path):
    """Bar chart: workouts per month."""
    months = list(range(1, 13))
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    by_month = stats.get("by_month", {})
    counts = [by_month.get(m, 0) for m in months]

    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)

    colors = ["#39d353" if c > 0 else "#21262d" for c in counts]
    bars = ax.bar(month_labels, counts, color=colors, width=0.6, zorder=3)

    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    str(count), ha="center", va="bottom", fontsize=8, color="#333")

    ax.set_title(f"Workouts per month — {year}", fontsize=11,
                 fontweight="bold", color="#333", pad=10)
    ax.set_ylabel("Workouts")
    ax.set_ylim(0, max(counts) * 1.3 + 1 if counts else 5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#eee", linewidth=0.8, zorder=0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_monthly_health(snapshots: list[dict], year: int, out_path: Path):
    """Line chart: average HRV and RHR per month (reads from index rows)."""
    hrv_by_month: dict[int, list[float]] = defaultdict(list)
    rhr_by_month: dict[int, list[float]] = defaultdict(list)
    for r in snapshots:
        month = int(r["date"][5:7])
        if r.get("hrv_ms") is not None:
            hrv_by_month[month].append(r["hrv_ms"])
        if r.get("rhr") is not None:
            rhr_by_month[month].append(r["rhr"])

    months_with_data = sorted(set(list(hrv_by_month.keys()) + list(rhr_by_month.keys())))
    if not months_with_data:
        return

    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    hrv_avgs = [sum(hrv_by_month[m]) / len(hrv_by_month[m]) if hrv_by_month.get(m) else None
                for m in months_with_data]
    rhr_avgs = [sum(rhr_by_month[m]) / len(rhr_by_month[m]) if rhr_by_month.get(m) else None
                for m in months_with_data]

    fig, ax1 = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor(CHART_BG)
    ax1.set_facecolor(CHART_BG)
    ax2 = ax1.twinx()

    x_labels = [month_labels[m - 1] for m in months_with_data]

    hrv_vals = [v for v in hrv_avgs if v is not None]
    rhr_vals = [v for v in rhr_avgs if v is not None]
    hrv_x = [x_labels[i] for i, v in enumerate(hrv_avgs) if v is not None]
    rhr_x = [x_labels[i] for i, v in enumerate(rhr_avgs) if v is not None]

    if hrv_vals:
        ax1.plot(hrv_x, hrv_vals, color="#4C9BE8", linewidth=2,
                 marker="o", markersize=5, label="HRV (ms)", zorder=3)
    if rhr_vals:
        ax2.plot(rhr_x, rhr_vals, color="#E85C4C", linewidth=2,
                 marker="s", markersize=5, label="RHR (bpm)", zorder=3)

    ax1.set_title(f"HRV & FC reposo por mes — {year}", fontsize=11,
                  fontweight="bold", color="#333", pad=10)
    ax1.set_ylabel("HRV (ms)", color="#4C9BE8")
    ax2.set_ylabel("RHR (bpm)", color="#E85C4C")
    ax1.tick_params(axis="y", colors="#4C9BE8")
    ax2.tick_params(axis="y", colors="#E85C4C")
    ax1.spines["top"].set_visible(False)
    ax1.grid(axis="y", color="#eee", linewidth=0.8, zorder=0)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_monthly_activity(snapshots: list[dict], year: int, out_path: Path):
    """Two-panel chart: avg sleep hours per month + avg daily steps per month (from index)."""
    sleep_by_month: dict[int, list[float]] = defaultdict(list)
    steps_by_month: dict[int, list[float]] = defaultdict(list)

    for r in snapshots:
        month = int(r["date"][5:7])
        if r.get("sleep_h") is not None and r["sleep_h"] > 0:
            sleep_by_month[month].append(r["sleep_h"])
        if r.get("steps") is not None and r["steps"] > 0:
            steps_by_month[month].append(r["steps"])

    months_with_data = sorted(
        set(list(sleep_by_month.keys()) + list(steps_by_month.keys()))
    )
    if not months_with_data:
        return

    month_labels_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                       "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    x_labels = [month_labels_es[m - 1] for m in months_with_data]

    sleep_avgs = [
        round(sum(sleep_by_month[m]) / len(sleep_by_month[m]), 1)
        if sleep_by_month.get(m) else None
        for m in months_with_data
    ]
    steps_avgs = [
        round(sum(steps_by_month[m]) / len(steps_by_month[m]))
        if steps_by_month.get(m) else None
        for m in months_with_data
    ]

    fig, (ax_sleep, ax_steps) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.patch.set_facecolor(CHART_BG)

    # --- Panel 1: Sleep ---
    sleep_vals = [v if v is not None else 0 for v in sleep_avgs]
    sleep_colors = ["#2E7D32" if v is not None and v >= 7 else ("#FFA500" if v is not None and v >= 6 else ("#E85C4C" if v is not None else "#CCCCCC"))
                    for v in sleep_avgs]
    bars = ax_sleep.bar(x_labels, sleep_vals, color=sleep_colors, width=0.6, zorder=3)
    ax_sleep.axhline(7, color="#2E7D32", linewidth=1.2, linestyle="--",
                     alpha=0.7, label="Objetivo 7h")
    ax_sleep.axhline(6, color="#F57F17", linewidth=1.0, linestyle=":",
                     alpha=0.6, label="Mínimo 6h")
    for bar, val in zip(bars, sleep_avgs):
        if val is not None:
            ax_sleep.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                          f"{val:.1f}h", ha="center", va="bottom", fontsize=8, color="#333")
    ax_sleep.set_title(f"Sueño y actividad por mes — {year}", fontsize=11,
                       fontweight="bold", color="#333", pad=10)
    ax_sleep.set_ylabel("Sueño medio (h)")
    ax_sleep.set_ylim(0, max((v for v in sleep_avgs if v), default=8) * 1.25 + 1)
    ax_sleep.spines["top"].set_visible(False)
    ax_sleep.spines["right"].set_visible(False)
    ax_sleep.grid(axis="y", color="#eee", linewidth=0.8, zorder=0)
    ax_sleep.legend(fontsize=8, loc="upper right")
    ax_sleep.set_facecolor(CHART_BG)

    # --- Panel 2: Steps ---
    steps_vals = [v if v is not None else 0 for v in steps_avgs]
    steps_colors = ["#39d353" if v is not None and v >= 8000 else ("#FFA500" if v is not None and v >= 5000 else ("#E85C4C" if v is not None else "#CCCCCC"))
                    for v in steps_avgs]
    bars2 = ax_steps.bar(x_labels, steps_vals, color=steps_colors, width=0.6, zorder=3)
    ax_steps.axhline(8000, color="#2E7D32", linewidth=1.2, linestyle="--",
                     alpha=0.7, label="Objetivo 8k pasos")
    for bar, val in zip(bars2, steps_avgs):
        if val is not None:
            ax_steps.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                          f"{int(val):,}", ha="center", va="bottom", fontsize=7.5, color="#333")
    ax_steps.set_ylabel("Pasos medios/día")
    ax_steps.set_ylim(0, max((v for v in steps_avgs if v), default=10000) * 1.3 + 500)
    ax_steps.spines["top"].set_visible(False)
    ax_steps.spines["right"].set_visible(False)
    ax_steps.grid(axis="y", color="#eee", linewidth=0.8, zorder=0)
    ax_steps.legend(fontsize=8, loc="upper right")
    ax_steps.set_facecolor(CHART_BG)
    ax_steps.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{int(x):,}")
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ {out_path.relative_to(get_repo_root())}")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def chart_monthly_vitals(snapshots: list[dict], year: int, out_path: Path):
    """Two-panel chart: avg SpO2 and avg respiratory rate per month (from index)."""
    spo2_by_month: dict[int, list[float]] = defaultdict(list)
    resp_by_month: dict[int, list[float]] = defaultdict(list)

    for r in snapshots:
        month = int(r["date"][5:7])
        if r.get("spo2") is not None:
            spo2_by_month[month].append(r["spo2"])
        if r.get("resp") is not None:
            resp_by_month[month].append(r["resp"])

    months_with_data = sorted(set(list(spo2_by_month.keys()) + list(resp_by_month.keys())))
    if not months_with_data:
        return

    month_labels_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                       "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    x_labels = [month_labels_es[m - 1] for m in months_with_data]

    spo2_avgs = [
        round(sum(spo2_by_month[m]) / len(spo2_by_month[m]), 1)
        if spo2_by_month.get(m) else None
        for m in months_with_data
    ]
    resp_avgs = [
        round(sum(resp_by_month[m]) / len(resp_by_month[m]), 1)
        if resp_by_month.get(m) else None
        for m in months_with_data
    ]

    fig, (ax_spo2, ax_resp) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.patch.set_facecolor(CHART_BG)

    # --- Panel 1: SpO2 ---
    spo2_vals = [v if v is not None else 0 for v in spo2_avgs]
    spo2_colors = ["#26A69A" if v and v >= 95 else ("#FFA500" if v and v >= 94 else "#E85C4C")
                   for v in spo2_avgs]
    bars = ax_spo2.bar(x_labels, spo2_vals, color=spo2_colors, width=0.6, zorder=3)
    ax_spo2.axhline(95, color="#F57F17", linewidth=1, linestyle=":",
                    alpha=0.7, label="Mínimo 95%")
    for bar, val in zip(bars, spo2_avgs):
        if val:
            ax_spo2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                         f"{val:.1f}%", ha="center", va="bottom", fontsize=8, color="#333")
    ax_spo2.set_title(f"SpO₂ y frecuencia respiratoria por mes — {year}", fontsize=11,
                      fontweight="bold", color="#333", pad=10)
    ax_spo2.set_ylabel("SpO₂ media (%)")
    y_min = min((v for v in spo2_avgs if v), default=95) * 0.998 - 0.3
    ax_spo2.set_ylim(min(y_min, 93), 101)
    ax_spo2.spines["top"].set_visible(False)
    ax_spo2.spines["right"].set_visible(False)
    ax_spo2.grid(axis="y", color="#eee", linewidth=0.8, zorder=0)
    ax_spo2.legend(fontsize=8)
    ax_spo2.set_facecolor(CHART_BG)

    # --- Panel 2: Respiratory rate ---
    resp_vals = [v if v is not None else 0 for v in resp_avgs]
    resp_colors = ["#7E57C2" if v and 12 <= v <= 20 else "#FFA500"
                   for v in resp_avgs]
    bars2 = ax_resp.bar(x_labels, resp_vals, color=resp_colors, width=0.6, zorder=3)
    ax_resp.axhspan(12, 20, alpha=0.08, color="#E8F5E9", zorder=0, label="Zona normal (12–20)")
    for bar, val in zip(bars2, resp_avgs):
        if val:
            ax_resp.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                         f"{val:.1f}", ha="center", va="bottom", fontsize=8, color="#333")
    ax_resp.set_ylabel("Frec. respiratoria (rpm)")
    y_max_resp = max((v for v in resp_avgs if v), default=20) * 1.25 + 1
    ax_resp.set_ylim(0, y_max_resp)
    ax_resp.spines["top"].set_visible(False)
    ax_resp.spines["right"].set_visible(False)
    ax_resp.grid(axis="y", color="#eee", linewidth=0.8, zorder=0)
    ax_resp.legend(fontsize=8)
    ax_resp.set_facecolor(CHART_BG)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_report(year: int, final: bool = False) -> str:
    repo_root = get_repo_root()
    workouts = load_workout_days(repo_root, year)
    snapshots = load_health_snapshots(repo_root, year)
    t = compute_training_stats(workouts, year)
    h = compute_health_stats(snapshots)

    today = date.today()
    is_current_year = (year == today.year)
    status_tag = "" if final or not is_current_year else " _(en curso)_"

    charts_dir = repo_root / "health" / "yearly" / "charts" / str(year)

    # Generate charts
    heatmap_path = charts_dir / "heatmap.png"
    monthly_path = charts_dir / "monthly-volume.png"
    health_path = charts_dir / "monthly-health.png"
    activity_path = charts_dir / "monthly-activity.png"
    vitals_path = charts_dir / "monthly-vitals.png"

    chart_heatmap_year(workouts, year, heatmap_path)
    if t:
        chart_monthly_volume(t, year, monthly_path)
    if snapshots:
        chart_monthly_health(snapshots, year, health_path)
        chart_monthly_activity(snapshots, year, activity_path)
        chart_monthly_vitals(snapshots, year, vitals_path)

    # --- Build markdown ---
    lines = [
        f"# 📅 {year} — Resumen anual{status_tag}",
        "",
        f"_Generado: {today.strftime('%Y-%m-%d')}_",
        "",
    ]

    # Heatmap
    lines += [
        "## 🗓️ Actividad del año",
        "",
        f"![Heatmap {year}](charts/{year}/heatmap.png)",
        "",
    ]

    # Training stats
    lines.append("## 🏃 Entrenamiento")
    lines.append("")
    if t:
        lines.append(f"| Métrica | Valor |")
        lines.append(f"|---------|-------|")
        lines.append(f"| Total workouts | **{t['total_workouts']}** |")
        if t.get("total_km"):
            lines.append(f"| Kilómetros totales | **{t['total_km']} km** ({t.get('runs_with_km',0)} runs con GPS) |")
        if t.get("avg_km_per_run"):
            lines.append(f"| Media por entreno | {t['avg_km_per_run']} km |")
        if t.get("avg_pace"):
            lines.append(f"| Ritmo medio | {t['avg_pace']} min/km |")
        if t.get("avg_hr"):
            lines.append(f"| FC media | {t['avg_hr']} bpm |")
        if t.get("max_streak_days"):
            lines.append(f"| Racha máxima | {t['max_streak_days']} {t.get('max_streak_label', 'días consecutivos')} |")
        if t.get("best_month"):
            lines.append(f"| Mejor mes | {t['best_month']} ({max(t['by_month'].values())} workouts) |")
        lines.append("")

        # Type breakdown
        if t.get("type_counts"):
            lines.append("**Por tipo:**")
            for wtype, count in sorted(t["type_counts"].items(), key=lambda x: -x[1]):
                lines.append(f"- {wtype}: {count}")
            lines.append("")

        # Monthly volume chart
        if monthly_path.exists():
            lines += [
                f"![Volumen mensual](charts/{year}/monthly-volume.png)",
                "",
            ]

        # Monthly table
        lines.append("**Por mes:**")
        lines.append("")
        lines.append("| Mes | Workouts | Km |")
        lines.append("|-----|----------|----|")
        for m in range(1, 13):
            count = t["by_month"].get(m, 0)
            km = t["km_by_month"].get(m, "—")
            km_str = f"{km} km" if km and km != "—" and km > 0 else "—"
            if count > 0:
                lines.append(f"| {MONTH_NAMES[m-1]} | {count} | {km_str} |")
        lines.append("")
    else:
        lines.append("_Sin datos de entrenamiento para este año._")
        lines.append("")

    # Health stats
    lines.append("## 🏥 Salud")
    lines.append("")
    if h:
        lines.append(f"_Basado en {h.get('days_with_data', 0)} días con datos de Apple Health._")
        lines.append("")
        if h.get("hrv"):
            hrv = h["hrv"]
            lines.append(f"**HRV:** media {hrv.get('avg')} ms | mín {hrv.get('min')} ms | máx {hrv.get('max')} ms")
        if h.get("rhr"):
            rhr = h["rhr"]
            lines.append(f"**FC reposo:** media {rhr.get('avg')} bpm | mín {rhr.get('min')} bpm | máx {rhr.get('max')} bpm")
        if h.get("sleep"):
            sl = h["sleep"]
            lines.append(f"**Sueño:** media {sl.get('avg')} h | {sl.get('poor_days', 0)} noches con < 6h")
        lines.append("")

        if health_path.exists():
            lines += [
                f"![HRV y RHR mensual](charts/{year}/monthly-health.png)",
                "",
            ]

        if activity_path.exists():
            lines += [
                f"![Sueño y pasos por mes](charts/{year}/monthly-activity.png)",
                "",
            ]

        if vitals_path.exists():
            lines += [
                f"![SpO₂ y frec. respiratoria por mes](charts/{year}/monthly-vitals.png)",
                "",
            ]

        # Daily trend charts for the full year
        daily_dir = repo_root / "health" / "yearly" / "charts" / str(year) / "daily"
        daily_charts = [
            ("HRV", daily_dir / "hrv-trend.png"),
            ("FC en reposo", daily_dir / "rhr-trend.png"),
            ("Sueño", daily_dir / "sleep-trend.png"),
            ("SpO₂ y frec. respiratoria", daily_dir / "vitals-trend.png"),
        ]
        if any(p.exists() for _, p in daily_charts):
            lines += [
                f"## Tendencias diarias {year}",
                "",
                "_Gráficas día a día del año completo. Eje X = meses._",
                "",
            ]
            for label, path in daily_charts:
                if path.exists():
                    rel = path.relative_to(repo_root / "health" / "yearly")
                    lines += [f"![{label} — tendencia diaria {year}]({rel})", ""]
    else:
        lines.append("_Sin datos de salud para este año. Empieza a enviar exportaciones de Apple Health para ver estadísticas aquí._")
        lines.append("")

    if final:
        lines.append("---")
        lines.append("_✅ Informe definitivo — año cerrado._")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate yearly health & training report")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--final", action="store_true",
                        help="Mark as definitive (closed year)")
    args = parser.parse_args()

    repo_root = get_repo_root()
    report = generate_report(args.year, final=args.final)

    out_path = repo_root / "health" / "yearly" / f"{args.year}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"✅ {out_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
