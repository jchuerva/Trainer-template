#!/usr/bin/env python3
"""
Generate training plan for next week using GitHub Copilot.

This script:
1. Analyzes last 14 days of workouts
2. Reads current goal
3. Prepares context for GitHub Copilot
4. Outputs a prompt for Copilot to generate the next week's plan
5. Formats the Run or Pay penalty section (if enabled)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# Import Run or Pay module
sys.path.insert(0, str(Path(__file__).parent))
from calculate_next_monday import get_next_monday
from run_or_pay import format_penalty_section, is_feature_enabled
from utils import get_config_path, get_repo_root, RUNNING_KEYWORDS, NON_RUNNING_KEYWORDS


def read_workouts_last_14_days():
    """Read workouts from the last 14 days from workouts/index.md."""
    repo_root = get_repo_root()
    index_path = repo_root / "workouts" / "index.md"

    if not index_path.exists():
        return []

    cutoff_date = datetime.now() - timedelta(days=14)
    workouts = []

    for line in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue

        parts = [p.strip() for p in line.split("|")]
        cells = parts[1:-1]
        
        # Skip header rows and invalid rows
        # Old format columns: Date | Distance | Time | Pace | HR | Max HR | Analysis  -> len(cells) == 7
        # New format columns: Date | Type | Distance | Time | Pace | HR | Max HR | Analysis  -> len(cells) == 8
        if len(cells) < 7:
            continue

        date_str = cells[0]
        if not date_str or date_str.lower() == "date" or set(date_str) == {"-"}:
            continue

        try:
            workout_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if workout_date < cutoff_date:
            continue

        # Check if we have the new format with Type column
        has_type_column = len(cells) >= 8
        
        if has_type_column:
            workout_type = cells[1]
            distance_km_idx = 2
            time_idx = 3
            avg_pace_idx = 4
            avg_hr_idx = 5
            max_hr_idx = 6
        else:
            # Old format without Type column - assume running for backward compatibility
            workout_type = "Running (unknown type)"
            distance_km_idx = 1
            time_idx = 2
            avg_pace_idx = 3
            avg_hr_idx = 4
            max_hr_idx = 5

        try:
            distance_km = float(cells[distance_km_idx]) if cells[distance_km_idx] else 0.0
        except ValueError:
            continue

        time = cells[time_idx]
        avg_pace = cells[avg_pace_idx]

        avg_hr = None
        if cells[avg_hr_idx].isdigit():
            avg_hr = int(cells[avg_hr_idx])

        max_hr = None
        if cells[max_hr_idx].isdigit():
            max_hr = int(cells[max_hr_idx])

        workouts.append(
            {
                "date": date_str,
                "type": workout_type,
                "distance_km": distance_km,
                "time": time,
                "avg_pace": avg_pace,
                "avg_hr": avg_hr,
                "max_hr": max_hr,
            }
        )

    workouts.sort(key=lambda x: x["date"])
    return workouts

def read_current_goal():
    """Read the current goal file (not needed with custom agent)."""
    return ""  # Agent has goal built-in

def read_latest_plan():
    """Read the most recent weekly plan to understand context."""
    repo_root = get_repo_root()
    plans_dir = repo_root / "plans"
    
    # Find all weekly plan files
    plan_files = list(plans_dir.rglob("week-*.md"))
    
    if not plan_files:
        return "No previous plans found."
    
    # Sort by filename (YYYY-MM-DD format) and get latest
    latest_plan = sorted(plan_files, key=lambda p: p.stem)[-1]
    
    with open(latest_plan, 'r') as f:
        return f.read()

def format_workouts_summary(workouts):
    """Format workouts into a readable summary."""
    if not workouts:
        return "No workouts in the last 14 days."
    
    def is_running_workout(workout_type: str | None) -> bool:
        """
        Determine if a workout is running-based on its type.
        
        Args:
            workout_type: The workout type string, or None/empty for unknown types
        
        Returns:
            True if the workout is identified as a running activity, False otherwise
        
        Uses keyword detection with conservative approach:
        - Explicitly identifies non-running activities first
        - Then checks for running indicators
        - Defaults to running only if type suggests "unknown running"
        - Defaults to False for None or unclear types
        """
        if not workout_type:  # Handles None, empty string, or other falsy values
            return False
        
        type_lower = workout_type.lower()
        
        # Non-running activity indicators (checked first)
        if any(keyword in type_lower for keyword in NON_RUNNING_KEYWORDS):
            return False
        
        # Running indicators (including common phrases from the analyst)
        if any(keyword in type_lower for keyword in RUNNING_KEYWORDS):
            return True
        
        # Default to non-running for unclear types to be conservative
        return False
    
    running_workouts = [w for w in workouts if is_running_workout(w.get('type', ''))]
    other_workouts = [w for w in workouts if not is_running_workout(w.get('type', ''))]
    
    summary = []
    summary.append(f"Total workouts: {len(workouts)} ({len(running_workouts)} running, {len(other_workouts)} other)")
    
    if running_workouts:
        total_running_distance = sum(w['distance_km'] for w in running_workouts)
        summary.append(f"Total running distance: {total_running_distance:.2f} km")
        
        avg_distance = total_running_distance / len(running_workouts)
        summary.append(f"Average distance per run: {avg_distance:.2f} km")
    
    if other_workouts:
        summary.append(f"\nOther activities (for context/recovery assessment):")

        # Group by sport type: show count and total duration/distance per type
        sport_groups: dict[str, list] = {}
        for w in other_workouts:
            sport_key = (w.get('type') or 'Unknown').strip()
            sport_groups.setdefault(sport_key, []).append(w)

        for sport_type, sport_ws in sorted(sport_groups.items()):
            total_dist = sum(w['distance_km'] for w in sport_ws)
            # Collect unique durations (non-empty)
            durations = [w['time'] for w in sport_ws if w.get('time') and w['time'] not in ('-', '')]
            dur_str = f", total time: {', '.join(durations)}" if durations else ""
            dist_str = f"{total_dist:.2f} km" if total_dist > 0 else "\u2014"
            summary.append(f"  \u2022 {sport_type}: {len(sport_ws)} session(s) \u2014 {dist_str}{dur_str}")

        # Show last 5 non-running workouts with full detail
        summary.append("\nRecent other workouts:")
        for w in other_workouts[-5:]:
            hr_info = ""
            if w.get('avg_hr') and w.get('max_hr'):
                hr_info = f" | HR: {w['avg_hr']} (max {w['max_hr']})"
            elif w.get('avg_hr'):
                hr_info = f" | HR: {w['avg_hr']}"
            workout_type = w.get('type', 'Unknown')
            dist = w['distance_km']
            dist_str = f"{dist:.2f} km" if dist > 0 else "\u2014"
            summary.append(f"  - {w['date']}: {workout_type} - {dist_str} in {w['time']} (pace: {w['avg_pace']}/km{hr_info})")

    summary.append("\nRecent running workouts:")
    for w in running_workouts[-5:]:  # Last 5 running workouts
        hr_info = ""
        if w.get('avg_hr') and w.get('max_hr'):
            hr_info = f" | HR: {w['avg_hr']} (max {w['max_hr']})"
        elif w.get('avg_hr'):
            hr_info = f" | HR: {w['avg_hr']}"
        workout_type = w.get('type', 'Unknown')
        summary.append(f"  - {w['date']}: {workout_type} - {w['distance_km']:.2f} km in {w['time']} (pace: {w['avg_pace']}/km{hr_info})")
    
    return "\n".join(summary)

def read_week_plan_template():
    """Read the week plan template."""
    repo_root = get_repo_root()
    template_path = repo_root / "templates" / "week-plan-template.md"
    
    if not template_path.exists():
        return ""
    
    with open(template_path, 'r') as f:
        return f.read()

def get_recovery_alerts():
    """Get recovery alerts from the detection script."""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', 'scripts/detect_recovery_needs.py'],
            capture_output=True,
            text=True,
            cwd=get_repo_root()
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def read_health_last_7_days() -> str:
    """Read last 7 days of health snapshots and format a summary for the prompt."""
    from datetime import timedelta
    repo_root = get_repo_root()
    health_dir = repo_root / "health" / "daily"
    if not health_dir.exists():
        return ""

    cutoff = datetime.now() - timedelta(days=7)
    snapshots = []
    for json_file in sorted(health_dir.rglob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            date_str = data.get("date", "")
            if date_str and datetime.strptime(date_str, "%Y-%m-%d") >= cutoff:
                snapshots.append(data)
        except Exception:
            continue

    if not snapshots:
        return ""

    snapshots = sorted(snapshots, key=lambda x: x.get("date", ""))
    lines = ["## 🏥 Health Data (Last 7 Days)", ""]
    lines.append("| Date | Sleep | RHR | HRV | Steps | SpO2 |")
    lines.append("|------|-------|-----|-----|-------|------|")
    for s in snapshots:
        date = s.get("date", "-")
        sleep_h = s.get("sleep", {}).get("total_h")
        sleep_str = f"{sleep_h:.1f}h" if sleep_h else "-"
        rhr = s.get("resting_hr_bpm") or "-"
        hrv = f"{s.get('hrv_ms')}ms" if s.get("hrv_ms") else "-"
        steps = s.get("activity", {}).get("steps")
        steps_str = f"{steps:,}" if steps else "-"
        spo2 = s.get("spo2_pct")
        spo2_str = f"{spo2}%" if spo2 else "-"
        lines.append(f"| {date} | {sleep_str} | {rhr} | {hrv} | {steps_str} | {spo2_str} |")
    lines.append("")
    return "\n".join(lines)


def read_config():
    """Read configuration from config/config.yaml."""
    config_path = get_config_path()
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError, OSError):
        return {}


def get_training_status_section():
    """Get training status section for the prompt if athlete is not actively training."""
    config = read_config()
    status_config = config.get('training_status', {})
    status = status_config.get('status', 'active')
    
    # If active with no special note, return empty
    if status == 'active' and not status_config.get('note'):
        return ""
    
    # Status descriptions for the AI
    status_descriptions = {
        'sick': '🤒 **RUNNER IS CURRENTLY SICK** - Prioritize rest and recovery. Reduce or skip workouts entirely. Do not plan any high-intensity sessions.',
        'injury': '🩹 **RUNNER IS CURRENTLY INJURED** - Plan only recovery-compatible activities. Avoid exercises that may aggravate the injury.',
        'holidays': '🏖️ **RUNNER IS ON HOLIDAYS** - Plan lighter, flexible workouts. Focus on maintenance rather than progression.',
        'returning': '🔄 **RUNNER IS RETURNING FROM A BREAK** - Apply gradual ramp-up: start at 50-60% of previous volume, avoid intensity in first week.',
        'active': '🟢 **Active** (with note)'
    }
    
    lines = []
    lines.append("## ⚠️ Training Status Alert")
    lines.append("")
    lines.append(status_descriptions.get(status, f'Status: {status}'))
    
    if status_config.get('note'):
        lines.append(f"\n**Note from athlete:** {status_config['note']}")
    
    lines.append("")
    lines.append("**IMPORTANT:** Adjust the training plan according to this status. The athlete's health and recovery take priority over any training goals.")
    lines.append("")
    
    return "\n".join(lines)

def generate_copilot_prompt():
    """Generate the prompt for GitHub Copilot."""
    workouts = read_workouts_last_14_days()
    latest_plan = read_latest_plan()
    template = read_week_plan_template()
    training_status = get_training_status_section()
    health_summary = read_health_last_7_days()
    next_monday, _, _ = get_next_monday()
    
    # Format Run or Pay penalty section (if enabled)
    # Penalty calculation is handled by the dedicated "Update penalties" workflow step
    # which runs before this script, so we only need to read and format the existing data.
    try:
        penalty_section = format_penalty_section()
    except Exception:
        # Log silently and continue - penalty feature shouldn't break plan generation
        penalty_section = ""
    
    # Add newline after training_status if present for proper markdown spacing
    status_section = f"{training_status}\n" if training_status else ""
    
    # Add penalty section if enabled
    penalty_prompt = ""
    if penalty_section:
        penalty_prompt = f"""
{penalty_section}

**Note for AI Coach:** Include the "Run or Pay" section in the generated plan. This is a motivation feature - show empathy if there was a penalty, and encouragement if the athlete completed all workouts.

**CRITICAL:** Use ONLY the penalty data provided above. NEVER copy, infer, or estimate penalty information from the previous week's plan. If the data above shows "No penalty data available", state exactly that - do not make up completion numbers.
"""

    health_section = f"{health_summary}\n" if health_summary else ""

    prompt = f"""Generate the next week's training plan for the week starting {next_monday}.

## Recent Performance (Last 14 Days)
{format_workouts_summary(workouts)}

{health_section}{status_section}{penalty_prompt}## Previous Week's Plan
{latest_plan}

## Use this template structure
{template}

Start the plan with a short **"Last week quick evaluation"** section (3–5 sentences max) based on the recent workouts and the previous plan.

Fill in the template with actual workout details based on:
1. Recent workout data analysis (focus on running workouts for training plan)
2. Current training status and recovery alerts
3. Training coach guidelines
4. Progressive overload principles
5. Runner's current fitness level

**Important:** 
- **ALWAYS use the Personal Information section from the template above** (weight, height, date of birth) - NOT from the previous week's plan, as it may be outdated
- **NEVER copy or infer "Run or Pay" penalty data from the previous week's plan** - use ONLY the penalty section provided above in this prompt
- Focus the training plan on RUNNING workouts only
- Use other activities (walking, cycling, etc.) for context on recovery and overall training load
- When counting "runs" or "weekly volume", only include running workouts
- Non-running activities provide valuable recovery and fatigue context but should not be included in the running plan itself
- **Health data (HRV, RHR, sleep) is key for recovery assessment**: low HRV or high RHR indicate need to reduce intensity
- If athlete status is sick/injured/holidays/returning, adjust the plan accordingly - health comes first!

Generate a complete, filled-in training plan ready to save as plans/{next_monday[:4]}/{next_monday[5:7]}/week-{next_monday}.md
"""
    
    return prompt

def main():
    """Main entry point."""
    prompt = generate_copilot_prompt()
    print(prompt)

if __name__ == "__main__":
    main()
