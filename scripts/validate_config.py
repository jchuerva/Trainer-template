#!/usr/bin/env python3
"""
Validate config/config.yaml against the JSON schema.

This script validates the configuration file to ensure:
- All required fields are present
- Values are in the correct format (dates, numbers, enums)
- Values are within acceptable ranges

Usage:
    python3 scripts/validate_config.py
    
Exit codes:
    0: Configuration is valid
    1: Configuration is invalid or file not found
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_config_path, get_schema_path

import yaml

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("Error: jsonschema package not installed.", file=sys.stderr)
    print("Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


def load_schema():
    """Load the JSON schema for config validation."""
    schema_path = get_schema_path()
    
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}", file=sys.stderr)
        return None
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in schema file: {e}", file=sys.stderr)
        return None


def load_config():
    """Load the YAML configuration file."""
    config_path = get_config_path()
    
    if not config_path.exists():
        print(f"Error: config/config.yaml not found at {config_path}", file=sys.stderr)
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in config/config.yaml: {e}", file=sys.stderr)
        return None


def format_validation_error(error):
    """Format a validation error into a human-readable message."""
    path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
    
    # Make common errors more readable
    if error.validator == "required":
        missing = error.validator_value
        return f"Missing required field(s) at '{path}': {missing}"
    elif error.validator == "enum":
        allowed = error.validator_value
        return f"Invalid value at '{path}': got '{error.instance}', allowed values are: {allowed}"
    elif error.validator == "pattern":
        return f"Invalid format at '{path}': '{error.instance}' doesn't match expected pattern (e.g., YYYY-MM-DD for dates)"
    elif error.validator == "minimum":
        return f"Value too low at '{path}': {error.instance} is below minimum {error.validator_value}"
    elif error.validator == "maximum":
        return f"Value too high at '{path}': {error.instance} is above maximum {error.validator_value}"
    elif error.validator == "type":
        expected = error.validator_value
        got = type(error.instance).__name__
        return f"Wrong type at '{path}': expected {expected}, got {got}"
    else:
        return f"Validation error at '{path}': {error.message}"


def validate_config(config, schema):
    """Validate configuration against schema."""
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(config))
    
    return errors


def main():
    """Main entry point."""
    print("🔍 Validating config/config.yaml...")
    print()
    
    # Load schema
    schema = load_schema()
    if schema is None:
        return 1
    
    # Load config
    config = load_config()
    if config is None:
        return 1
    
    # Validate
    errors = validate_config(config, schema)
    
    if errors:
        print(f"❌ Found {len(errors)} validation error(s):\n", file=sys.stderr)
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {format_validation_error(error)}", file=sys.stderr)
        print()
        print("Please fix the errors in config/config.yaml and run validation again.", file=sys.stderr)
        return 1
    
    print("✅ config/config.yaml is valid!")
    
    # Show current configuration summary
    print()
    print("Configuration summary:")
    
    runner = config.get('runner', {})
    print(f"  - Runner: DOB {runner.get('date_of_birth')}, {runner.get('weight')}kg, {runner.get('height')}cm")
    
    prefs = config.get('preferences', {})
    run_days = prefs.get('run_days', [])
    print(f"  - Schedule: {len(run_days)} runs/week on {', '.join(run_days)}")
    
    status = config.get('training_status', {})
    if status:
        status_val = status.get('status', 'active')
        note = status.get('note', '')
        status_str = f"{status_val}"
        if note:
            status_str += f" ({note})"
        print(f"  - Training status: {status_str}")
    else:
        print("  - Training status: active (default)")
    
    # Run or Pay feature
    run_or_pay = config.get('run_or_pay', {})
    if run_or_pay.get('enabled'):
        penalty = run_or_pay.get('penalty_per_week', 0)
        currency = run_or_pay.get('currency', 'EUR')
        print(f"  - Run or Pay: enabled ({penalty} {currency}/week)")
    else:
        print("  - Run or Pay: disabled")
    
    # Weekly plan generation
    weekly_plan = config.get('weekly_plan', {})
    plan_enabled = weekly_plan.get('enabled', True)
    if plan_enabled:
        print("  - Weekly plan generation: enabled")
    else:
        reason = weekly_plan.get('pause_reason', '')
        pause_str = f" — {reason}" if reason else ""
        print(f"  - Weekly plan generation: ⏸️  PAUSED{pause_str}")
    
    goal = config.get('current_goal', {})
    print(f"  - Current goal: {goal.get('file', 'not set')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
