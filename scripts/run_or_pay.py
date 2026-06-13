#!/usr/bin/env python3
"""
Run or Pay - Penalty calculation and tracking.

This module handles:
1. Counting completed workouts from the previous week
2. Comparing against planned workouts
3. Calculating and recording penalties
4. Resetting penalties at year boundaries
"""

from __future__ import annotations

import functools
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_config_path, get_penalties_path, get_repo_root, RUNNING_KEYWORDS as running_keywords, NON_RUNNING_KEYWORDS as non_running_keywords

import yaml


@functools.lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Load configuration from config/config.yaml. Cached after first read."""
    config_path = get_config_path()
    
    if not config_path.exists():
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def load_penalties() -> dict[str, Any]:
    """Load penalty tracking data."""
    penalties_path = get_penalties_path()
    
    if not penalties_path.exists():
        return {
            'year': datetime.now().year,
            'total_penalty': 0,
            'currency': 'EUR',
            'history': []
        }
    
    with open(penalties_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_penalties(penalties: dict[str, Any]) -> None:
    """Save penalty tracking data."""
    penalties_path = get_penalties_path()
    penalties_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(penalties_path, 'w', encoding='utf-8') as f:
        yaml.dump(penalties, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_previous_week_dates() -> tuple[datetime, datetime]:
    """
    Get the start (Monday) and end (Sunday) dates of the week to evaluate for penalties.
    
    The workflow runs on Sunday to generate next week's plan. At that point:
    - The week ending today (Sunday) should be evaluated
    - So we want the Monday 6 days ago through today
    
    For other days, we want the most recently completed full week (Mon-Sun).
    """
    today = datetime.now()
    days_since_monday = today.weekday()  # Monday=0, Sunday=6
    
    if days_since_monday == 6:  # Today is Sunday
        # Evaluate the week ending today (Monday was 6 days ago)
        week_monday = today - timedelta(days=6)
        week_sunday = today
    else:
        # Evaluate the most recently completed week (last Mon-Sun)
        week_monday = today - timedelta(days=days_since_monday + 7)
        week_sunday = week_monday + timedelta(days=6)
    
    return week_monday, week_sunday


def count_running_workouts_in_week(start_date: datetime, end_date: datetime) -> int:
    """
    Count the number of running workouts completed in a given week.
    
    Reads from workouts/index.md and counts workouts within the date range.
    """
    repo_root = get_repo_root()
    index_path = repo_root / "workouts" / "index.md"
    
    if not index_path.exists():
        return 0
    
    count = 0
    
    for line in index_path.read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.startswith('|'):
            continue
        
        parts = [p.strip() for p in line.split('|')]
        cells = parts[1:-1]
        
        if len(cells) < 7:
            continue
        
        date_str = cells[0]
        if not date_str or date_str.lower() == 'date' or set(date_str) == {'-'}:
            continue
        
        try:
            workout_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            continue
        
        # Check if workout is within the week (normalize to date-only comparison)
        workout_day = workout_date.date()
        if not (start_date.date() <= workout_day <= end_date.date()):
            continue
        
        # Determine workout type (column 1 in new format, or infer from old format)
        workout_type = cells[1].lower() if len(cells) >= 8 else ''
        
        # Check if it's a non-running workout
        if any(kw in workout_type for kw in non_running_keywords):
            continue
        
        # Check if it's a running workout
        if any(kw in workout_type for kw in running_keywords):
            count += 1
        elif not workout_type or 'unknown' in workout_type:
            # For unknown types with distance > 0, assume it might be running
            # but be conservative - only count if there's significant distance
            try:
                distance_idx = 2 if len(cells) >= 8 else 1
                distance = float(cells[distance_idx]) if cells[distance_idx] else 0
                if distance >= 2.0:  # At least 2km to count as a potential run
                    count += 1
            except (ValueError, IndexError):
                # Distance is missing, non-numeric, or column is absent.
                # Be conservative: only count workouts we can positively identify as runs.
                pass
    
    return count


def get_planned_runs_from_config() -> int:
    """Get the number of planned runs per week from config."""
    config = load_config()
    return config.get('preferences', {}).get('weekly_runs', 3)


def is_feature_enabled() -> bool:
    """Check if Run or Pay feature is enabled."""
    config = load_config()
    run_or_pay = config.get('run_or_pay', {})
    return run_or_pay.get('enabled', False)


def get_penalty_amount() -> float:
    """Get the penalty amount per week from config."""
    config = load_config()
    run_or_pay = config.get('run_or_pay', {})
    return run_or_pay.get('penalty_per_week', 0)


def get_currency() -> str:
    """Get the currency from config."""
    config = load_config()
    run_or_pay = config.get('run_or_pay', {})
    return run_or_pay.get('currency', 'EUR')


def get_training_status() -> str:
    """Get the current training status."""
    config = load_config()
    return config.get('training_status', {}).get('status', 'active')


def _count_consecutive_clean_weeks(history: list[dict[str, Any]]) -> int:
    """
    Count consecutive weeks (from the most recent) where all planned runs were completed.

    Only active/returning weeks with no missed runs count toward the streak.
    """
    count = 0
    for entry in reversed(history):
        # Only count weeks where the runner was active/returning and missed no runs.
        # Missing keys mean we cannot confirm it was a clean week, so we stop the streak.
        if (
            entry.get('status_at_time') in ('active', 'returning')
            and 'missed_runs' in entry
            and entry['missed_runs'] == 0
            and entry.get('penalty_applied', 0) == 0
        ):
            count += 1
        else:
            break
    return count


def calculate_weekly_penalty() -> dict[str, Any] | None:
    """
    Calculate the penalty for the previous week.
    
    Returns None if:
    - Feature is disabled
    - Already calculated for this week
    
    Returns a dict with penalty details (penalty may be 0 for non-active/returning status).
    """
    if not is_feature_enabled():
        return None
    
    penalties = load_penalties()
    current_year = datetime.now().year
    
    # Reset if new year (or year is null/missing) - persist immediately to avoid data loss
    if penalties.get('year') != current_year:
        penalties = {
            'year': current_year,
            'total_penalty': 0,
            'currency': get_currency(),
            'history': []
        }
        save_penalties(penalties)  # Persist reset immediately
    
    # Get previous week dates
    week_start, week_end = get_previous_week_dates()
    week_key = week_start.strftime('%Y-%m-%d')
    
    # Check if already calculated
    existing_weeks = [h.get('week') for h in penalties.get('history', [])]
    if week_key in existing_weeks:
        return None  # Already calculated
    
    status = get_training_status()
    
    # For non-active/returning status, record with zero penalty
    if status not in ('active', 'returning'):
        history_entry = {
            'week': week_key,
            'planned_runs': get_planned_runs_from_config(),
            'completed_runs': 0,
            'missed_runs': 0,
            'penalty_applied': 0,
            'reason': f'No penalty - status was "{status}"',
            'status_at_time': status
        }
        
        penalties['history'].append(history_entry)
        penalties['currency'] = get_currency()
        save_penalties(penalties)
        
        return history_entry
    
    # Count workouts
    planned_runs = get_planned_runs_from_config()
    completed_runs = count_running_workouts_in_week(week_start, week_end)
    missed_runs = max(0, planned_runs - completed_runs)
    
    # Calculate penalty
    penalty_per_week = get_penalty_amount()
    penalty_applied = penalty_per_week if missed_runs > 0 else 0
    
    # Record in history
    history_entry = {
        'week': week_key,
        'planned_runs': planned_runs,
        'completed_runs': completed_runs,
        'missed_runs': missed_runs,
        'penalty_applied': penalty_applied,
        'status_at_time': status
    }
    
    penalties['history'].append(history_entry)
    penalties['total_penalty'] = penalties.get('total_penalty', 0) + penalty_applied
    penalties['currency'] = get_currency()
    
    # Apply discount every 3 consecutive clean weeks
    if penalty_applied == 0:
        consecutive_clean = _count_consecutive_clean_weeks(penalties['history'])
        if consecutive_clean > 0 and consecutive_clean % 3 == 0:
            discount = penalty_per_week
            actual_discount = min(discount, penalties.get('total_penalty', 0))
            if actual_discount > 0:
                penalties['total_penalty'] -= actual_discount
                history_entry['discount_applied'] = actual_discount
    
    save_penalties(penalties)
    
    return history_entry


def get_penalty_summary() -> dict[str, Any]:
    """
    Get a summary of the current penalty status.
    
    Returns dict with:
    - enabled: bool
    - total_penalty: float
    - currency: str
    - year: int
    - last_week: dict or None
    - weeks_with_penalty: int (count of weeks with penalties this year)
    - current_streak: int (consecutive weeks with penalties, 0 if last week was clean)
    - history: list (full history for the year)
    """
    if not is_feature_enabled():
        return {'enabled': False}
    
    penalties = load_penalties()
    current_year = datetime.now().year
    
    # Reset if new year - persist immediately to avoid stale data
    if penalties.get('year') != current_year:
        penalties = {
            'year': current_year,
            'total_penalty': 0,
            'currency': get_currency(),
            'history': []
        }
        save_penalties(penalties)
        return {
            'enabled': True,
            'total_penalty': 0,
            'currency': get_currency(),
            'year': current_year,
            'last_week': None,
            'weeks_with_penalty': 0,
            'current_streak': 0,
            'consecutive_clean_weeks': 0,
            'history': []
        }
    
    history = penalties.get('history', [])
    last_week = history[-1] if history else None
    
    # Count weeks with penalties
    weeks_with_penalty = sum(1 for h in history if h.get('penalty_applied', 0) > 0)
    
    # Calculate current streak of consecutive penalties
    current_streak = 0
    for entry in reversed(history):
        if entry.get('penalty_applied', 0) > 0:
            current_streak += 1
        else:
            break
    
    # Calculate consecutive clean weeks streak
    consecutive_clean_weeks = _count_consecutive_clean_weeks(history)
    
    return {
        'enabled': True,
        'total_penalty': penalties.get('total_penalty', 0),
        'currency': penalties.get('currency', 'EUR'),
        'year': penalties.get('year', current_year),
        'last_week': last_week,
        'weeks_with_penalty': weeks_with_penalty,
        'current_streak': current_streak,
        'consecutive_clean_weeks': consecutive_clean_weeks,
        'history': history
    }


def format_penalty_section() -> str:
    """
    Format the penalty section for the weekly plan.
    
    Returns empty string if feature is disabled.
    """
    if not is_feature_enabled():
        return ""
    
    summary = get_penalty_summary()
    
    if not summary.get('enabled'):
        return ""
    
    total = summary.get('total_penalty', 0)
    currency = summary.get('currency', 'EUR')
    year = summary.get('year', datetime.now().year)
    last_week = summary.get('last_week')
    weeks_with_penalty = summary.get('weeks_with_penalty', 0)
    current_streak = summary.get('current_streak', 0)
    consecutive_clean_weeks = summary.get('consecutive_clean_weeks', 0)
    history = summary.get('history', [])
    
    lines = []
    lines.append("## 💸 Run or Pay")
    lines.append("")
    lines.append(f"**Year {year} Total Penalty:** {total} {currency}")
    
    # Show weeks with penalties count if any
    total_weeks = len(history)
    if total_weeks > 0:
        lines.append(f"**Weeks tracked:** {total_weeks} ({weeks_with_penalty} with penalties)")
    
    lines.append("")
    
    # Show streak warning if consecutive failures
    if current_streak >= 2:
        lines.append(f"🔥 **{current_streak} consecutive weeks with missed runs!** Time to get back on track.")
        lines.append("")
    
    if last_week:
        if last_week.get('penalty_applied', 0) > 0:
            lines.append(f"⚠️ **Last week: {last_week['completed_runs']}/{last_week['planned_runs']} runs completed → +{last_week['penalty_applied']} {currency} penalty**")
        elif last_week.get('status_at_time') not in ('active', 'returning'):
            lines.append(f"✓ **Last week: No penalty (status: {last_week['status_at_time']})**")
        else:
            lines.append(f"✅ **Last week: {last_week['completed_runs']}/{last_week['planned_runs']} runs completed → No penalty!**")
            # Show discount if it was applied this week
            if last_week.get('discount_applied', 0) > 0:
                lines.append(f"🎉 **3 consecutive weeks completed! -{last_week['discount_applied']} {currency} discount applied to your total penalty!**")
            # Show progress toward next discount
            elif consecutive_clean_weeks > 0:
                weeks_to_discount = 3 - (consecutive_clean_weeks % 3)
                if weeks_to_discount < 3:
                    lines.append(f"💪 **{consecutive_clean_weeks} consecutive clean week(s) — {weeks_to_discount} more to earn a -{get_penalty_amount()} {currency} discount!**")
    else:
        # Explicitly state when no data is available - prevents AI from inferring/hallucinating
        lines.append("⚠️ **Last week: No penalty data available** (this may be the first week of tracking)")
    
    lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # When run directly, calculate and print the penalty
    result = calculate_weekly_penalty()
    
    if result is None:
        if not is_feature_enabled():
            print("Run or Pay feature is disabled.")
        else:
            print("Penalty already calculated for this week.")
    else:
        print(f"Week penalty calculated:")
        print(f"  Planned runs: {result.get('planned_runs', 'N/A')}")
        print(f"  Completed runs: {result.get('completed_runs', 'N/A')}")
        print(f"  Missed runs: {result.get('missed_runs', 'N/A')}")
        print(f"  Penalty applied: {result.get('penalty_applied', 0)} {get_currency()}")
        
        summary = get_penalty_summary()
        print(f"\nYear total: {summary.get('total_penalty', 0)} {summary.get('currency', 'EUR')}")
