#!/usr/bin/env python3
"""
Generate health trend charts from health/index.md (source of truth).

Produces PNG charts in health/charts/:
  - hrv-trend.png     → HRV ms over time with baseline + zones
  - rhr-trend.png     → Resting heart rate with zones
  - sleep-trend.png   → Sleep stages stacked bar chart
  - vitals-trend.png  → SpO2 + respiratory rate

Usage:
    python3 scripts/generate_health_charts.py
    python3 scripts/generate_health_charts.py --days 30
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from build_health_index import load_index
from utils import get_repo_root


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLORS = {
    "hrv": "#4C9BE8",
    "hrv_baseline": "#1A5FA8",
    "rhr": "#E85C4C",
    "rhr_baseline": "#A83030",
    "sleep_deep": "#1A0A6E",
    "sleep_rem": "#9B59B6",
    "sleep_core": "#AEB6E8",
    "zone_good": "#E8F5E9",
    "zone_warn": "#FFF9C4",
    "zone_bad": "#FFEBEE",
    "grid": "#EEEEEE",
    "text": "#333333",
    "workout": "#FF8C00",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_chart(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ {path.relative_to(get_repo_root())}")


def filter_recent(rows: list[dict], days: int) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for r in rows:
        try:
            dt = datetime.strptime(r["date"].split()[0], "%Y-%m-%d")
            if dt >= cutoff:
                result.append({**r, "_dt": dt})
        except (ValueError, KeyError):
            continue
    return sorted(result, key=lambda x: x["_dt"])


def add_workout_bands(ax, rows: list[dict], y_min: float, y_max: float):
    """Shade workout days with orange background."""
    added_label = False
    for r in rows:
        if r.get("workout") and r["workout"] != "-":
            label = "Día de entreno" if not added_label else None
            ax.axvspan(
                r["_dt"] - timedelta(hours=12),
                r["_dt"] + timedelta(hours=12),
                alpha=0.12, color=COLORS["workout"], zorder=1, label=label
            )
            added_label = True


# ---------------------------------------------------------------------------
# HRV chart
# ---------------------------------------------------------------------------

def _apply_xaxis(ax, dates, month_labels: bool):
    """Apply day or month labels to X axis."""
    if month_labels:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        ax.tick_params(axis="x", rotation=0)
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 8)))
        ax.tick_params(axis="x", rotation=30)


def chart_hrv(rows: list[dict], out_path: Path, month_labels: bool = False):
    data = [(r["_dt"], r["hrv_ms"]) for r in rows if r.get("hrv_ms") is not None]
    if len(data) < 2:
        print("⚠️  Not enough HRV data (need ≥2 days)")
        return

    dates, vals = zip(*data)
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y_max = max(max(vals) * 1.25 + 10, 65)
    ax.axhspan(0, 25, alpha=0.15, color=COLORS["zone_bad"], zorder=0)
    ax.axhspan(25, 40, alpha=0.12, color=COLORS["zone_warn"], zorder=0)
    ax.axhspan(40, 60, alpha=0.10, color=COLORS["zone_good"], zorder=0)
    ax.axhspan(60, y_max, alpha=0.12, color="#C8E6C9", zorder=0)
    ax.text(dates[0], 12, "Bajo (<25)", fontsize=8, color="#B71C1C", alpha=0.8)
    ax.text(dates[0], 30, "Normal (25–40)", fontsize=8, color="#F57F17", alpha=0.8)
    ax.text(dates[0], 47, "Bueno (40–60)", fontsize=8, color="#2E7D32", alpha=0.8)

    add_workout_bands(ax, rows, 0, y_max)

    workout_dts = {r["_dt"] for r in rows if r.get("workout") and r["workout"] != "-"}
    ax.plot(dates, vals, color=COLORS["hrv"], linewidth=2, zorder=3)
    for d, v in zip(dates, vals):
        marker, size = ("*", 120) if d in workout_dts else ("o", 50)
        ax.scatter(d, v, color=COLORS["hrv"], s=size, marker=marker, zorder=5)

    baseline = np.mean(vals)
    ax.axhline(baseline, color=COLORS["hrv_baseline"], linewidth=1.2,
               linestyle="--", alpha=0.7, label=f"Media {baseline:.0f} ms")

    ax.set_title("HRV — Variabilidad de frecuencia cardíaca", fontsize=13,
                 fontweight="bold", color=COLORS["text"], pad=12)
    ax.set_ylabel("ms")
    ax.set_ylim(0, y_max)
    _apply_xaxis(ax, dates, month_labels)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8, zorder=0)
    ax.legend(fontsize=9)
    save_chart(fig, out_path)


# ---------------------------------------------------------------------------
# RHR chart
# ---------------------------------------------------------------------------

def chart_rhr(rows: list[dict], out_path: Path, month_labels: bool = False):
    data = [(r["_dt"], r["rhr"]) for r in rows if r.get("rhr") is not None]
    if len(data) < 2:
        print("⚠️  Not enough RHR data (need ≥2 days)")
        return

    dates, vals = zip(*data)
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    y_min = min(vals) * 0.9 - 2
    y_max = max(vals) * 1.1 + 2

    ax.axhspan(y_min, 60, alpha=0.12, color=COLORS["zone_good"], zorder=0)
    ax.axhspan(60, 70, alpha=0.10, color="#F9FBE7", zorder=0)
    ax.axhspan(70, 80, alpha=0.12, color=COLORS["zone_warn"], zorder=0)
    ax.axhspan(80, y_max, alpha=0.12, color=COLORS["zone_bad"], zorder=0)
    ax.text(dates[0], max(y_min + 1, 54), "Excelente (<60)", fontsize=8, color="#2E7D32", alpha=0.8)
    ax.text(dates[0], 63, "Normal (60–70)", fontsize=8, color="#558B2F", alpha=0.8)
    ax.text(dates[0], 73, "Aceptable (70–80)", fontsize=8, color="#F57F17", alpha=0.8)
    ax.text(dates[0], 83, "Elevada (>80)", fontsize=8, color="#B71C1C", alpha=0.8)

    add_workout_bands(ax, rows, y_min, y_max)

    workout_dts = {r["_dt"] for r in rows if r.get("workout") and r["workout"] != "-"}
    ax.plot(dates, vals, color=COLORS["rhr"], linewidth=2, zorder=3)
    for d, v in zip(dates, vals):
        marker, size = ("*", 120) if d in workout_dts else ("o", 50)
        ax.scatter(d, v, color=COLORS["rhr"], s=size, marker=marker, zorder=5)

    baseline = np.mean(vals)
    ax.axhline(baseline, color=COLORS["rhr_baseline"], linewidth=1.2,
               linestyle="--", alpha=0.7, label=f"Media {baseline:.0f} bpm")

    ax.set_title("FC en reposo (RHR)", fontsize=13, fontweight="bold",
                 color=COLORS["text"], pad=12)
    ax.set_ylabel("bpm")
    ax.set_ylim(y_min, y_max)
    _apply_xaxis(ax, dates, month_labels)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8, zorder=0)
    ax.legend(fontsize=9)
    save_chart(fig, out_path)


# ---------------------------------------------------------------------------
# Sleep chart
# ---------------------------------------------------------------------------

def chart_sleep(rows: list[dict], out_path: Path, month_labels: bool = False):
    data = [(r["_dt"], r.get("deep_h") or 0, r.get("rem_h") or 0,
             max((r.get("sleep_h") or 0) - (r.get("deep_h") or 0) - (r.get("rem_h") or 0), 0),
             r.get("workout"))
            for r in rows if r.get("sleep_h")]
    if len(data) < 2:
        print("⚠️  Not enough sleep data (need ≥2 days)")
        return

    dates, deeps, rems, cores, workout_flags = zip(*[(d, deep, rem, core, wf) for d, deep, rem, core, wf in data])
    import numpy as np_loc
    x = np_loc.arange(len(dates))
    width = 0.6

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    workout_idxs = {i for i, wf in enumerate(workout_flags) if wf and wf != "-"}
    for i in workout_idxs:
        ax.axvspan(x[i] - 0.38, x[i] + 0.38, alpha=0.15, color=COLORS["workout"],
                   zorder=2, label="Día de entreno" if i == min(workout_idxs) else None)

    ax.bar(x, deeps, width, label="Profundo", color=COLORS["sleep_deep"], zorder=3)
    ax.bar(x, rems, width, bottom=deeps, label="REM", color=COLORS["sleep_rem"], zorder=3)
    ax.bar(x, cores, width, bottom=[d + r for d, r in zip(deeps, rems)],
           label="Core", color=COLORS["sleep_core"], zorder=3)
    ax.axhline(7, color="#2E7D32", linewidth=1.2, linestyle="--", alpha=0.8, label="Objetivo 7h")

    ax.set_title("Sueño — Fases por noche", fontsize=13, fontweight="bold",
                 color=COLORS["text"], pad=12)
    ax.set_ylabel("horas")
    ax.set_xticks(x)
    if month_labels:
        # For month labels on bar chart, show month name at first day of each month
        # Label only the first datapoint of each new month (clean month boundaries)
        seen_months = set()
        tick_positions = []
        for i, d in enumerate(dates):
            key = (d.year, d.month)
            if key not in seen_months:
                seen_months.add(key)
                tick_positions.append(i)
        ax.set_xticks(tick_positions)
        ax.set_xticklabels([dates[i].strftime("%b") for i in tick_positions], rotation=0)
    else:
        step = max(1, len(dates) // 8)
        tick_positions = list(range(0, len(dates), step))
        ax.set_xticks(tick_positions)
        ax.set_xticklabels([dates[i].strftime("%d %b") for i in tick_positions], rotation=30, ha="right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8, zorder=0)
    ax.legend(fontsize=9, loc="upper left")
    save_chart(fig, out_path)


# ---------------------------------------------------------------------------
# Vitals chart (SpO2 + respiratory rate)
# ---------------------------------------------------------------------------

def chart_vitals(rows: list[dict], out_path: Path, month_labels: bool = False):
    spo2_data = [(r["_dt"], r["spo2"]) for r in rows if r.get("spo2") is not None]
    resp_data = [(r["_dt"], r["resp"]) for r in rows if r.get("resp") is not None]

    if not spo2_data and not resp_data:
        print("⚠️  Not enough SpO2/respiratory data")
        return

    fig, (ax_spo2, ax_resp) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    fig.patch.set_facecolor("white")

    # --- SpO2 panel ---
    if spo2_data:
        dates, vals = zip(*spo2_data)
        y_min = min(vals) * 0.998 - 0.5
        ax_spo2.axhspan(y_min, 94, alpha=0.12, color=COLORS["zone_bad"], zorder=0)
        ax_spo2.axhspan(94, 95, alpha=0.10, color=COLORS["zone_warn"], zorder=0)
        ax_spo2.axhspan(95, 101, alpha=0.10, color=COLORS["zone_good"], zorder=0)
        ax_spo2.axhline(95, color="#F57F17", linewidth=1, linestyle=":", alpha=0.7)
        ax_spo2.plot(dates, vals, color="#26A69A", linewidth=2, zorder=3)
        ax_spo2.scatter(dates, vals, color="#26A69A", s=40, marker="o", zorder=5)
        baseline = np.mean(vals)
        ax_spo2.axhline(baseline, color="#00796B", linewidth=1.2, linestyle="--",
                        alpha=0.7, label=f"Media {baseline:.1f}%")
        ax_spo2.set_title("SpO₂ y frecuencia respiratoria", fontsize=13,
                          fontweight="bold", color=COLORS["text"], pad=12)
        ax_spo2.set_ylabel("SpO₂ (%)")
        ax_spo2.set_ylim(min(y_min, 93), 101)
        if month_labels:
            ax_spo2.xaxis.set_major_locator(mdates.MonthLocator())
            ax_spo2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
            ax_spo2.tick_params(axis="x", rotation=0)
        else:
            ax_spo2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            ax_spo2.tick_params(axis="x", rotation=30)
        ax_spo2.spines["top"].set_visible(False)
        ax_spo2.spines["right"].set_visible(False)
        ax_spo2.grid(axis="y", color=COLORS["grid"], linewidth=0.8, zorder=0)
        ax_spo2.legend(fontsize=9)

    # --- Respiratory rate panel ---
    if resp_data:
        dates, vals = zip(*resp_data)
        y_max = max(vals) * 1.1 + 1
        ax_resp.axhspan(12, 20, alpha=0.10, color=COLORS["zone_good"], zorder=0)
        ax_resp.axhspan(20, y_max, alpha=0.10, color=COLORS["zone_warn"], zorder=0)
        ax_resp.plot(dates, vals, color="#7E57C2", linewidth=2, zorder=3)
        ax_resp.scatter(dates, vals, color="#7E57C2", s=40, marker="o", zorder=5)
        baseline = np.mean(vals)
        ax_resp.axhline(baseline, color="#512DA8", linewidth=1.2, linestyle="--",
                        alpha=0.7, label=f"Media {baseline:.1f} rpm")
        ax_resp.set_ylabel("Frec. respiratoria (rpm)")
        ax_resp.set_ylim(max(0, min(vals) * 0.9 - 1), y_max)
        if month_labels:
            ax_resp.xaxis.set_major_locator(mdates.MonthLocator())
            ax_resp.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
            ax_resp.tick_params(axis="x", rotation=0)
        else:
            ax_resp.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            ax_resp.tick_params(axis="x", rotation=30)
        ax_resp.spines["top"].set_visible(False)
        ax_resp.spines["right"].set_visible(False)
        ax_resp.grid(axis="y", color=COLORS["grid"], linewidth=0.8, zorder=0)
        ax_resp.legend(fontsize=9)

    save_chart(fig, out_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate health trend charts from index")
    parser.add_argument("--days", type=int, default=90, help="Days of history to include")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for charts (default: health/charts/)")
    parser.add_argument("--month-labels", action="store_true",
                        help="Use month labels on X axis instead of day labels")
    args = parser.parse_args()

    repo_root = get_repo_root()
    charts_dir = (repo_root / args.output).resolve() if args.output else repo_root / "health" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    all_rows = load_index(repo_root)
    rows = filter_recent(all_rows, args.days)

    if not rows:
        print("No health data found in index.")
        return

    ml = args.month_labels
    print(f"Generating charts from {len(rows)} days of data → {charts_dir}...")
    chart_hrv(rows, charts_dir / "hrv-trend.png", month_labels=ml)
    chart_rhr(rows, charts_dir / "rhr-trend.png", month_labels=ml)
    chart_sleep(rows, charts_dir / "sleep-trend.png", month_labels=ml)
    chart_vitals(rows, charts_dir / "vitals-trend.png", month_labels=ml)


if __name__ == "__main__":
    main()

