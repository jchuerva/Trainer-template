#!/usr/bin/env python3
"""
Detect recovery needs based on recent daily health data.

Analyzes the last 7 days of health snapshots and outputs alerts
for the training plan generator. Called by generate_weekly_plan_prompt.py.

Exit code 0 always; prints empty string if no alerts.

Usage:
    python3 scripts/detect_recovery_needs.py
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from utils import get_repo_root


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

HRV_LOW_THRESHOLD = 40          # ms — below this = poor recovery signal
HRV_DROP_PCT = 20               # % drop from personal baseline = alert
RHR_HIGH_THRESHOLD = 72         # bpm — above baseline = fatigue signal
RHR_RISE_BPM = 7                # bpm above baseline = alert
SLEEP_LOW_H = 6.0               # hours — below this = insufficient sleep
SLEEP_POOR_DAYS = 2             # consecutive low-sleep nights = alert
SPO2_LOW = 94.0                 # % — below this = alert


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_recent_snapshots(days: int = 7) -> list[dict]:
    repo_root = get_repo_root()
    health_dir = repo_root / "health" / "daily"
    cutoff = datetime.now() - timedelta(days=days)
    snapshots = []
    for json_file in sorted(health_dir.rglob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            date_str = data.get("date", "")
            if date_str:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                if dt >= cutoff:
                    snapshots.append(data)
        except (json.JSONDecodeError, IOError, ValueError):
            continue
    return sorted(snapshots, key=lambda x: x.get("date", ""))


def load_baseline_snapshots(days: int = 30) -> list[dict]:
    """Load last 30 days for baseline calculation."""
    return load_recent_snapshots(days=days)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def compute_baseline(snapshots: list[dict], metric_fn) -> float | None:
    values = [metric_fn(s) for s in snapshots if metric_fn(s) is not None]
    return sum(values) / len(values) if values else None


def analyze(snapshots: list[dict], baseline_snapshots: list[dict]) -> list[str]:
    alerts = []

    # Baseline values (from 30-day history)
    hrv_baseline = compute_baseline(baseline_snapshots, lambda s: s.get("hrv_ms"))
    rhr_baseline = compute_baseline(baseline_snapshots, lambda s: s.get("resting_hr_bpm"))

    # Recent data (last 7 days)
    recent_hrvs = [s.get("hrv_ms") for s in snapshots if s.get("hrv_ms")]
    recent_rhrs = [s.get("resting_hr_bpm") for s in snapshots if s.get("resting_hr_bpm")]
    recent_sleeps = [
        s.get("sleep", {}).get("total_h")
        for s in snapshots
        if s.get("sleep") and s["sleep"].get("total_h")
    ]

    # --- HRV alerts ---
    if recent_hrvs:
        avg_recent_hrv = sum(recent_hrvs) / len(recent_hrvs)
        last_hrv = recent_hrvs[-1]

        if last_hrv < HRV_LOW_THRESHOLD:
            alerts.append(
                f"⚠️ HRV muy bajo: {last_hrv}ms (umbral: {HRV_LOW_THRESHOLD}ms) — "
                "posible fatiga acumulada o enfermedad. Considerar reducir intensidad."
            )
        elif hrv_baseline and avg_recent_hrv < hrv_baseline * (1 - HRV_DROP_PCT / 100):
            drop = ((hrv_baseline - avg_recent_hrv) / hrv_baseline) * 100
            alerts.append(
                f"📉 HRV caída del {drop:.0f}% respecto a baseline ({hrv_baseline:.0f}ms → "
                f"{avg_recent_hrv:.0f}ms en últimos {len(recent_hrvs)} días) — "
                "reducir carga de entrenamiento esta semana."
            )

    # --- RHR alerts ---
    if recent_rhrs:
        last_rhr = recent_rhrs[-1]
        if rhr_baseline and last_rhr > rhr_baseline + RHR_RISE_BPM:
            alerts.append(
                f"❤️ FC reposo elevada: {last_rhr}bpm (baseline: {rhr_baseline:.0f}bpm, "
                f"+{last_rhr - rhr_baseline:.0f}bpm) — "
                "probable fatiga o inicio de enfermedad."
            )
        elif last_rhr > RHR_HIGH_THRESHOLD:
            alerts.append(
                f"❤️ FC reposo alta: {last_rhr}bpm — monitorizar recuperación."
            )

    # --- Sleep alerts ---
    if recent_sleeps:
        low_sleep_days = [h for h in recent_sleeps if h < SLEEP_LOW_H]
        if len(low_sleep_days) >= SLEEP_POOR_DAYS:
            avg_low = sum(low_sleep_days) / len(low_sleep_days)
            alerts.append(
                f"😴 {len(low_sleep_days)} noches con menos de {SLEEP_LOW_H}h de sueño "
                f"(media: {avg_low:.1f}h) en los últimos {len(recent_sleeps)} días — "
                "priorizar descanso, evitar sesiones de alta intensidad."
            )
        elif recent_sleeps and recent_sleeps[-1] < SLEEP_LOW_H:
            alerts.append(
                f"😴 Sueño insuficiente anoche: {recent_sleeps[-1]:.1f}h — "
                "ajustar intensidad del entreno de hoy si aplica."
            )

    # --- SpO2 ---
    for s in snapshots[-3:]:  # last 3 days
        spo2 = s.get("spo2_pct")
        if spo2 and spo2 < SPO2_LOW:
            alerts.append(
                f"🫁 SpO2 bajo el {s['date']}: {spo2}% — consultar médico si persiste."
            )

    return alerts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    recent = load_recent_snapshots(days=7)
    baseline = load_baseline_snapshots(days=30)

    if not recent:
        return  # No data, no output

    alerts = analyze(recent, baseline)

    if alerts:
        print("## 🏥 Recovery Alerts (Health Data)")
        print("")
        for alert in alerts:
            print(f"- {alert}")
        print("")
        # Summary stats for context
        last = recent[-1]
        stats = []
        if last.get("hrv_ms"):
            stats.append(f"HRV ayer: {last['hrv_ms']}ms")
        if last.get("resting_hr_bpm"):
            stats.append(f"RHR ayer: {last['resting_hr_bpm']}bpm")
        if last.get("sleep", {}).get("total_h"):
            stats.append(f"Sueño ayer: {last['sleep']['total_h']:.1f}h")
        if stats:
            print(f"**Últimos datos ({last.get('date', '?')}):** {' | '.join(stats)}")
            print("")


if __name__ == "__main__":
    main()
