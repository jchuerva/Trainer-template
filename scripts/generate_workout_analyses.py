#!/usr/bin/env python3
"""
Generate workout analyses from FIT files using Copilot agent.

This script:
1. Finds FIT files without corresponding analysis files
2. Pre-extracts workout data from FIT files using extract_fit_data.py
3. Passes the extracted data to the workout-analyst agent
4. The agent only needs to analyze data and write the file (no code execution needed)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

try:
    import yaml  # PyYAML — explicitly listed in requirements.txt
except ImportError:
    yaml = None  # type: ignore

# Add scripts directory to path for importing utils and extract_fit_data
sys.path.insert(0, str(Path(__file__).parent))
from utils import get_config_path, get_repo_root
from extract_fit_data import format_as_markdown, parse_fit_file


def log(msg: str, verbose: bool = True) -> None:
    """Print debug message to stderr."""
    if verbose:
        print(f"[DEBUG] {msg}", file=sys.stderr)


def normalize_filename(name: str) -> str:
    """Normalize Unicode in filename for comparison.
    
    Handles:
    - Unicode normalization (NFC)
    - Non-breaking spaces (\xa0) -> regular spaces
    - Other whitespace variants
    """
    # First, normalize Unicode form
    normalized = unicodedata.normalize("NFC", name)
    # Replace non-breaking space with regular space
    normalized = normalized.replace("\xa0", " ")
    # Replace other Unicode whitespace variants
    normalized = normalized.replace("\u00a0", " ")  # NO-BREAK SPACE
    normalized = normalized.replace("\u2007", " ")  # FIGURE SPACE
    normalized = normalized.replace("\u202f", " ")  # NARROW NO-BREAK SPACE
    return normalized


def find_created_file(expected_path: Path, verbose: bool = False) -> Path | None:
    """
    Find the created file, handling Unicode normalization differences.
    Returns the actual path if found, None otherwise.
    """
    # First, try exact match
    if expected_path.exists():
        return expected_path

    # If not found, search directory for similar filename
    parent = expected_path.parent
    if not parent.exists():
        return None

    expected_name_normalized = normalize_filename(expected_path.name)
    expected_stem_normalized = normalize_filename(expected_path.stem)
    
    log(f"Looking for normalized name: {expected_name_normalized!r}", verbose)

    for f in parent.iterdir():
        f_name_normalized = normalize_filename(f.name)
        f_stem_normalized = normalize_filename(f.stem)

        # Try normalized comparison
        if f_name_normalized == expected_name_normalized:
            log(f"Found file via normalized match: {f}", verbose)
            return f

        # Try stem comparison (without extension)
        if f_stem_normalized == expected_stem_normalized and f.suffix == expected_path.suffix:
            log(f"Found file via stem match: {f}", verbose)
            return f

    return None


def _run_copilot(
    prompt: str, *, model: str, verbose: bool = False, out_path: Path
) -> int:
    cmd = [
        "copilot",
        "--model",
        model,
        "--allow-all-tools",
        "--allow-all-paths",
        "-p",
        prompt,
    ]

    log(f"Command: {' '.join(cmd[:5])} -p '<prompt>' ", verbose)
    log(f"Expected output file: {out_path}", verbose)
    log(f"Output file exists before copilot: {out_path.exists()}", verbose)
    log(f"Current working directory: {Path.cwd()}", verbose)

    env = os.environ.copy()

    # Always capture output for debugging
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as f:
        log_file = Path(f.name)

    log(f"Copilot output will be logged to: {log_file}", verbose)

    # Run copilot and capture both stdout and stderr
    with open(log_file, "w") as f:
        result = subprocess.run(
            cmd,
            env=env,
            stdout=f,
            stderr=subprocess.STDOUT,
        )

    # Read and display the copilot output
    copilot_output = log_file.read_text()
    if verbose:
        print("=== COPILOT OUTPUT START ===", file=sys.stderr)
        print(copilot_output, file=sys.stderr)
        print("=== COPILOT OUTPUT END ===", file=sys.stderr)

    log(f"Copilot exit code: {result.returncode}", verbose)
    log(f"Output file exists after copilot: {out_path.exists()}", verbose)

    if out_path.exists():
        log(f"Output file size: {out_path.stat().st_size} bytes", verbose)
        # Show first few lines
        content = out_path.read_text()
        preview = content[:500] + "..." if len(content) > 500 else content
        log(f"Output file preview:\n{preview}", verbose)
    else:
        log("OUTPUT FILE WAS NOT CREATED!", verbose)
        # List what files ARE in the analysis directory
        analysis_dir = out_path.parent
        if analysis_dir.exists():
            files = list(analysis_dir.iterdir())
            log(f"Files in {analysis_dir}: {[f.name for f in files]}", verbose)
            # Debug: compare expected filename with actual files
            expected_name = out_path.name
            log(f"Expected filename: {expected_name!r}", verbose)
            log(f"Expected filename bytes: {expected_name.encode('utf-8')!r}", verbose)
            for f in files:
                if expected_name in f.name or f.name in expected_name:
                    log(f"Similar file found: {f.name!r}", verbose)
                    log(f"Similar file bytes: {f.name.encode('utf-8')!r}", verbose)
                    log(f"Names equal: {f.name == expected_name}", verbose)

    # Clean up log file
    try:
        log_file.unlink()
    except Exception:
        pass

    return result.returncode


def detect_sport_from_markdown(markdown: str) -> str:
    """
    Parse the sport field from the extracted FIT data markdown.
    Looks for a line like: **Sport:** running
    Returns the lowercase sport string, or 'unknown' if not found.
    """
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("**Sport:**"):
            sport = stripped.removeprefix("**Sport:**").strip().lower()
            return sport
    return "unknown"


def build_agent_instructions(sport: str) -> str:
    """
    Build sport-specific agent instructions for the workout analysis prompt.
    """
    sport_lower = sport.lower()

    if sport_lower in ("running", "walking", "hiking"):
        coach_title = "expert running and endurance coach"
        focus = "pace, cadence, and per-km splits"
        next_session = "next run"
    elif sport_lower == "cycling":
        coach_title = "expert cycling coach"
        focus = "power, cadence, and speed"
        next_session = "next ride"
    elif sport_lower == "swimming":
        coach_title = "expert swimming coach"
        focus = "stroke count, laps, and SWOLF score"
        next_session = "next swim"
    else:
        coach_title = "expert fitness and training coach"
        focus = "effort level, heart rate, and session duration"
        next_session = "next session"

    return f"""You are an {coach_title} and workout data analyst. Your job is to analyze **one workout session** from pre-extracted workout data and produce a clear, actionable markdown analysis.

## Analysis Guidelines
- Match the analysis depth to the workout type (easy vs quality session).
- Always include:
  - Segments/intervals or per-km splits (from the lap data table)
  - Elevation/grade and cadence notes (if available)
  - Focus especially on {focus}
  - Heart-rate interpretation (zone estimate + whether it matches the session goal)
  - Aerobic efficiency note
  - Training load & recovery recommendation
- End with **1–3 concrete action points** for the {next_session}.

## Important Rules
- Do **not** invent data you don't have.
- Do **not** reference the template in the final analysis (no \"as per template…\").
- Keep it tight: prefer bullet points; avoid long narratives.
- **IMPORTANT**: The workout data is already extracted and provided. Do NOT try to read or decode FIT files yourself - use the data given to you.
- **IMPORTANT**: Write the output file using the `edit` or `write` tool — do NOT print the content to stdout.
- **IMPORTANT**: Ensure the file is fully written before finishing. Do not truncate or leave placeholders in the output.
"""


def extract_fit_metrics(fit_path: Path, verbose: bool = False) -> str | None:
    """
    Extract metrics from a FIT file and return as markdown.
    Returns None if extraction fails.
    """
    try:
        metrics = parse_fit_file(fit_path)
        return format_as_markdown(metrics)
    except Exception as e:
        log(f"Failed to extract FIT data from {fit_path.name}: {e}", verbose)
        return None


def load_runner_profile(config_path: Path, verbose: bool = False) -> str:
    """
    Load runner personal info from config/config.yaml and format it as markdown.
    Returns an empty string if the file is missing or yaml is unavailable.
    """
    if yaml is None:
        log("PyYAML not available — skipping runner profile injection", verbose)
        return ""
    if not config_path.exists():
        log(f"config/config.yaml not found at {config_path} — skipping runner profile", verbose)
        return ""

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        log(f"Failed to parse config/config.yaml: {e}", verbose)
        return ""

    runner = cfg.get("runner", {})
    goal_cfg = cfg.get("current_goal", {})

    lines = ["## Runner Profile", ""]

    dob = runner.get("date_of_birth")
    if dob:
        try:
            birth = date.fromisoformat(str(dob))
            today = date.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            # Tanaka formula: 208 - 0.7 × age
            max_hr_est = round(208 - 0.7 * age)
            lines.append(f"- **Date of birth:** {dob} (age {age})")
            lines.append(f"- **Estimated max HR (Tanaka):** {max_hr_est} bpm")
            lines.append(f"  - Z1 (<60%): <{round(max_hr_est * 0.60)} bpm")
            lines.append(f"  - Z2 (60–70%): {round(max_hr_est * 0.60)}–{round(max_hr_est * 0.70)} bpm")
            lines.append(f"  - Z3 (70–80%): {round(max_hr_est * 0.70)}–{round(max_hr_est * 0.80)} bpm")
            lines.append(f"  - Z4 (80–90%): {round(max_hr_est * 0.80)}–{round(max_hr_est * 0.90)} bpm")
            lines.append(f"  - Z5 (>90%): >{round(max_hr_est * 0.90)} bpm")
        except ValueError:
            lines.append(f"- **Date of birth:** {dob}")

    weight = runner.get("weight")
    height = runner.get("height")
    if weight:
        lines.append(f"- **Weight:** {weight} kg")
    if height:
        lines.append(f"- **Height:** {height} cm")

    # Current goal
    goal_file = goal_cfg.get("file") if isinstance(goal_cfg, dict) else None
    if goal_file:
        goal_path = get_repo_root() / goal_file
        if goal_path.exists():
            try:
                goal_text = goal_path.read_text(encoding="utf-8")[:800]
                lines.append("")
                lines.append("## Current Training Goal (summary)")
                lines.append("")
                lines.append(goal_text.strip()[:600] + ("..." if len(goal_text) > 600 else ""))
            except Exception:
                pass

    lines.append("")
    return "\n".join(lines)


def fit_to_analysis_path(fit_path: Path, workouts_root: Path) -> Path:
    """Derive the expected analysis path for a FIT file in the new YYYY/MM structure.

    Given a fit file at ``workouts/YYYY/MM/fit/STEM.fit``, the corresponding
    analysis file lives at ``workouts/YYYY/MM/analysis/STEM.md``.

    Args:
        fit_path: Absolute path to the .fit file.
        workouts_root: Absolute path to the workouts root directory.

    Returns:
        Absolute path where the analysis .md file should live.

    Raises:
        ValueError: If the fit file is not inside a recognised ``YYYY/MM/fit/``
            sub-tree under *workouts_root*.
    """
    rel = fit_path.relative_to(workouts_root)  # e.g. 2026/04/fit/STEM.fit
    parts = rel.parts  # ('2026', '04', 'fit', 'STEM.fit')
    if len(parts) < 4 or parts[2] != "fit":
        raise ValueError(
            f"FIT file {fit_path} is not in expected YYYY/MM/fit/ hierarchy under {workouts_root}"
        )
    year, month = parts[0], parts[1]
    return workouts_root / year / month / "analysis" / f"{fit_path.stem}.md"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate missing workout analyses from .fit files using Copilot agent."
    )
    ap.add_argument(
        "--fits-dir",
        default="workouts",
        help="Root directory to scan recursively for .fit files (default: workouts)",
    )
    ap.add_argument(
        "--analysis-dir",
        default="workouts",
        help="Root workouts directory where YYYY/MM/analysis/ sub-trees are created (default: workouts)",
    )
    ap.add_argument(
        "--template",
        default="templates/workout-analysis-template.md",
        help="Workout analysis template path",
    )
    ap.add_argument("--model", default="claude-sonnet-4.5", help="Copilot model")
    ap.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml for runner profile injection (default: config/config.yaml)",
    )
    ap.add_argument(
        "--verbose", "-v", action="store_true", help="Show copilot output for debugging"
    )
    args = ap.parse_args()

    repo_root = get_repo_root()
    fits_root = (repo_root / args.fits_dir).resolve()
    workouts_root = (repo_root / args.analysis_dir).resolve()
    template_path = (repo_root / args.template).resolve()
    config_path = Path(args.config).resolve() if args.config else get_config_path()

    log(f"Repository root: {repo_root}", args.verbose)
    log(f"FIT files root: {fits_root}", args.verbose)
    log(f"Workouts root (analysis target): {workouts_root}", args.verbose)
    log(f"Template path: {template_path}", args.verbose)
    log(f"Config path: {config_path}", args.verbose)

    if not fits_root.exists():
        print(f"fits root not found: {fits_root}", file=sys.stderr)
        return 2
    if not template_path.exists():
        print(f"template not found: {template_path}", file=sys.stderr)
        return 2

    template_text = template_path.read_text(encoding="utf-8")

    # Load runner profile once (injected into every prompt)
    runner_profile = load_runner_profile(config_path, verbose=args.verbose)
    if runner_profile:
        log("Runner profile loaded and will be injected into prompts", args.verbose)
    else:
        log("Runner profile unavailable — prompts will not include personal data", args.verbose)

    # List all FIT files recursively (covers YYYY/MM/fit/*.fit structure)
    fit_files = sorted(p for p in fits_root.rglob("*.fit") if p.is_file())
    log(f"Found {len(fit_files)} FIT files", args.verbose)

    # Count existing analysis files without using relative_to() (avoids ValueError
    # when a FIT file lives outside workouts_root).
    existing_count = len(list(workouts_root.rglob("*.md")))
    log(f"Found {existing_count} existing analyses", args.verbose)

    created: list[Path] = []

    for fit_path in fit_files:
        # Derive expected analysis path from YYYY/MM structure
        try:
            out_path = fit_to_analysis_path(fit_path, workouts_root)
        except ValueError:
            # FIT file is not in expected YYYY/MM/fit/ hierarchy — skip to avoid
            # polluting workouts root with analysis files
            log(
                f"WARNING: skipping {fit_path} — not in YYYY/MM/fit/ hierarchy under {workouts_root}",
                verbose=True,
            )
            continue

        # Ensure the analysis directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing analysis with Unicode normalization handling
        # This handles cases where FIT file has non-breaking space but analysis has regular space (or vice versa)
        existing_analysis = find_created_file(out_path, verbose=args.verbose)
        if existing_analysis is not None:
            log(f"Skipping {fit_path.name} - analysis already exists at {existing_analysis}", args.verbose)
            continue

        log(f"Processing: {fit_path.name}", args.verbose)
        log(f"Target output: {out_path}", args.verbose)

        # Pre-extract FIT data so the agent doesn't need to execute code
        extracted_data = extract_fit_metrics(fit_path, verbose=args.verbose)

        # Detect sport from extracted data and build sport-specific agent instructions
        sport = detect_sport_from_markdown(extracted_data) if extracted_data else "unknown"
        log(f"Detected sport: {sport}", args.verbose)
        agent_instructions = build_agent_instructions(sport)

        if extracted_data:
            log(f"Successfully extracted data from {fit_path.name}", args.verbose)
            log(f"Extracted data length: {len(extracted_data)} chars", args.verbose)
            prompt = f"""{agent_instructions}

## Task
Analyze this workout and write a complete markdown analysis.

{runner_profile}
## Pre-extracted Workout Data

The following data has been extracted from the FIT file. Use this data for your analysis:

{extracted_data}

## Output instructions
- Use the template structure below as a guide.
- Replace placeholders only when the corresponding value is present in the data above.
- If data for a placeholder or section is unavailable, omit that section or mark it as "N/A".
- **Do NOT include the template comments or instructions in the output file.**
- Write the output to the exact path provided below using the `write` or `edit` tool.

## Template structure
{template_text}

Output file path: {out_path.as_posix()}
"""
        else:
            log(f"Failed to extract data, using fallback prompt", args.verbose)
            # Fallback: ask agent to decode (requires bash tool with Python)
            prompt = f"""{agent_instructions}

## Task
Analyze this workout and write a complete markdown analysis.

{runner_profile}
## Workout file
- FIT file path: {fit_path.as_posix()}

Note: Pre-extraction failed. You may need to decode the FIT file yourself using Python + fitparse.

## Output instructions
- Use the template structure below as a guide.
- Replace placeholders only when the corresponding value is present in the available workout data.
- If data for a placeholder or section is unavailable, omit that section or mark it as "N/A".
- **Do NOT include the template comments or instructions in the output file.**
- Write the output to the exact path provided below using the `write` or `edit` tool.

## Template structure
{template_text}

Output file path: {out_path.as_posix()}
"""

        log(f"Prompt length: {len(prompt)} chars", args.verbose)

        rc = _run_copilot(
            prompt,
            model=args.model,
            verbose=args.verbose,
            out_path=out_path,
        )
        if rc != 0:
            print(f"copilot failed for {fit_path.name} (exit {rc})", file=sys.stderr)
            return rc

        # Check if file was created (handle Unicode normalization differences)
        actual_path = find_created_file(out_path, verbose=args.verbose)
        if actual_path is None:
            print(f"analysis file not created: {out_path}", file=sys.stderr)
            return 1

        log(f"Successfully created: {actual_path}", args.verbose)
        created.append(actual_path)

    log(f"Total files created: {len(created)}", args.verbose)

    # Print created files (relative paths) one per line for workflows to consume.
    for p in created:
        try:
            print(p.relative_to(repo_root).as_posix())
        except Exception:
            print(p.as_posix())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
