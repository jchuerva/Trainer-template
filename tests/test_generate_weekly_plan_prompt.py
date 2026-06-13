#!/usr/bin/env python3
"""
Tests for generate_weekly_plan_prompt.py
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_weekly_plan_prompt import (
    format_workouts_summary,
    generate_copilot_prompt,
    get_training_status_section,
    NON_RUNNING_KEYWORDS,
    RUNNING_KEYWORDS
)


class TestFormatWorkoutsSummary:
    """Tests for the format_workouts_summary function."""

    def test_empty_workouts_list(self):
        """Empty workout list should return appropriate message."""
        result = format_workouts_summary([])
        assert "No workouts in the last 14 days" in result

    def test_single_running_workout(self):
        """Single running workout should be summarized correctly."""
        workouts = [
            {
                "date": "2026-01-10",
                "type": "Running",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 150,
                "max_hr": 170
            }
        ]
        result = format_workouts_summary(workouts)
        assert "Total workouts: 1" in result
        assert "1 running" in result
        assert "0 other" in result
        assert "5.00 km" in result

    def test_multiple_running_workouts(self):
        """Multiple running workouts should be summarized with totals."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "running",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 150,
                "max_hr": 170
            },
            {
                "date": "2026-01-10",
                "type": "Running",
                "distance_km": 10.0,
                "time": "60:00",
                "avg_pace": "6:00",
                "avg_hr": 155,
                "max_hr": 175
            }
        ]
        result = format_workouts_summary(workouts)
        assert "Total workouts: 2" in result
        assert "2 running" in result
        assert "15.00 km" in result  # Total distance
        assert "7.50 km" in result  # Average distance

    def test_mixed_workout_types(self):
        """Mixed workout types should separate running and other."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "running",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 150,
                "max_hr": 170
            },
            {
                "date": "2026-01-09",
                "type": "walking",
                "distance_km": 3.0,
                "time": "45:00",
                "avg_pace": "15:00",
                "avg_hr": 100,
                "max_hr": 120
            }
        ]
        result = format_workouts_summary(workouts)
        assert "1 running" in result
        assert "1 other" in result
        assert "Other activities" in result

    def test_walking_classified_as_non_running(self):
        """Walking should be classified as non-running."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "walking",
                "distance_km": 3.0,
                "time": "45:00",
                "avg_pace": "15:00",
                "avg_hr": 100,
                "max_hr": 120
            }
        ]
        result = format_workouts_summary(workouts)
        assert "0 running" in result
        assert "1 other" in result

    def test_cycling_classified_as_non_running(self):
        """Cycling should be classified as non-running."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "cycling",
                "distance_km": 20.0,
                "time": "60:00",
                "avg_pace": "3:00",
                "avg_hr": 130,
                "max_hr": 150
            }
        ]
        result = format_workouts_summary(workouts)
        assert "0 running" in result
        assert "1 other" in result

    def test_empty_type_classified_as_non_running(self):
        """Empty workout type should be classified as non-running (conservative)."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": None,
                "max_hr": None
            }
        ]
        result = format_workouts_summary(workouts)
        assert "0 running" in result
        assert "1 other" in result

    def test_none_type_classified_as_non_running(self):
        """None workout type should be classified as non-running (conservative)."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": None,
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": None,
                "max_hr": None
            }
        ]
        result = format_workouts_summary(workouts)
        assert "0 running" in result

    def test_missing_type_key(self):
        """Missing type key should be handled gracefully."""
        workouts = [
            {
                "date": "2026-01-08",
                # no 'type' key
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 150,
                "max_hr": 170
            }
        ]
        result = format_workouts_summary(workouts)
        # Should not crash, should classify as non-running
        assert "Total workouts: 1" in result

    def test_heart_rate_info_displayed(self):
        """Heart rate info should be displayed when available."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "running",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 155,
                "max_hr": 175
            }
        ]
        result = format_workouts_summary(workouts)
        assert "155" in result
        assert "175" in result

    def test_recent_workouts_section(self):
        """Recent running workouts section should show last 5."""
        workouts = [
            {
                "date": f"2026-01-{10+i:02d}",
                "type": "running",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 150,
                "max_hr": 170
            }
            for i in range(7)  # 7 workouts
        ]
        result = format_workouts_summary(workouts)
        assert "Recent running workouts:" in result
        # Should only show last 5


class TestGetTrainingStatusSection:
    """Tests for the get_training_status_section function."""

    def test_active_status_returns_empty(self):
        """Active status with no note should return empty string."""
        mock_config = {
            "training_status": {
                "status": "active"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert result == ""

    def test_active_status_with_note(self):
        """Active status with note should return a section."""
        mock_config = {
            "training_status": {
                "status": "active",
                "note": "Feeling great!"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "Training Status Alert" in result
            assert "Feeling great!" in result

    def test_sick_status_returns_alert(self):
        """Sick status should return warning section."""
        mock_config = {
            "training_status": {
                "status": "sick"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "Training Status Alert" in result
            assert "SICK" in result
            assert "rest" in result.lower() or "recovery" in result.lower()

    def test_sick_status_with_note(self):
        """Sick status with note should include the note."""
        mock_config = {
            "training_status": {
                "status": "sick",
                "note": "Cold since Monday"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "Cold since Monday" in result
            assert "Note from runner" in result

    def test_injury_status_returns_alert(self):
        """Injury status should return appropriate alert."""
        mock_config = {
            "training_status": {
                "status": "injury"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "Training Status Alert" in result
            assert "INJURED" in result

    def test_holidays_status_returns_alert(self):
        """Holidays status should return appropriate alert."""
        mock_config = {
            "training_status": {
                "status": "holidays"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "Training Status Alert" in result
            assert "HOLIDAYS" in result
            assert "lighter" in result.lower() or "flexible" in result.lower()

    def test_returning_status_returns_alert(self):
        """Returning status should return ramp-up guidance."""
        mock_config = {
            "training_status": {
                "status": "returning"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "Training Status Alert" in result
            assert "RETURNING" in result
            assert "gradual" in result.lower() or "50" in result or "ramp" in result.lower()

    def test_missing_training_status(self):
        """Missing training_status section should return empty."""
        mock_config = {}
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert result == ""

    def test_empty_training_status(self):
        """Empty training_status section should default to active (return empty)."""
        mock_config = {
            "training_status": {}
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert result == ""

    def test_health_priority_message(self):
        """Non-active status should include health priority message."""
        mock_config = {
            "training_status": {
                "status": "injury"
            }
        }
        with patch('generate_weekly_plan_prompt.read_config', return_value=mock_config):
            result = get_training_status_section()
            assert "health" in result.lower() or "recovery" in result.lower() or "priority" in result.lower()


class TestIsRunningWorkoutKeywords:
    """Tests for running vs non-running workout classification keywords."""

    def test_non_running_keywords_defined(self):
        """Non-running keywords should be defined."""
        assert len(NON_RUNNING_KEYWORDS) > 0
        assert 'walk' in NON_RUNNING_KEYWORDS
        assert 'cycling' in NON_RUNNING_KEYWORDS
        assert 'swim' in NON_RUNNING_KEYWORDS
        assert 'andar' in NON_RUNNING_KEYWORDS
        assert 'caminar' in NON_RUNNING_KEYWORDS
        assert 'entreno funcional' in NON_RUNNING_KEYWORDS
        assert 'entreno cruzado' in NON_RUNNING_KEYWORDS
        assert 'cross training' in NON_RUNNING_KEYWORDS

    def test_running_keywords_defined(self):
        """Running keywords should be defined."""
        assert len(RUNNING_KEYWORDS) > 0
        assert 'running' in RUNNING_KEYWORDS
        assert 'run' in RUNNING_KEYWORDS
        assert 'carrera' in RUNNING_KEYWORDS
        assert 'correr' in RUNNING_KEYWORDS

    def test_keywords_are_lowercase(self):
        """Keywords should be lowercase for consistent matching."""
        for keyword in NON_RUNNING_KEYWORDS:
            assert keyword == keyword.lower()
        for keyword in RUNNING_KEYWORDS:
            assert keyword == keyword.lower()


class TestFormatWorkoutsSummaryEdgeCases:
    """Edge case tests for format_workouts_summary."""

    def test_workout_missing_hr_data(self):
        """Workouts without HR data should be handled."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "running",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": None,
                "max_hr": None
            }
        ]
        result = format_workouts_summary(workouts)
        assert "5.00 km" in result
        # Should not crash

    def test_workout_with_only_avg_hr(self):
        """Workouts with only avg HR should show it."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "walking",
                "distance_km": 3.0,
                "time": "45:00",
                "avg_pace": "15:00",
                "avg_hr": 100,
                "max_hr": None
            }
        ]
        result = format_workouts_summary(workouts)
        assert "100" in result
        # Should not crash

    def test_case_insensitive_type_matching(self):
        """Workout type matching should be case-insensitive."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "RUNNING",
                "distance_km": 5.0,
                "time": "30:00",
                "avg_pace": "6:00",
                "avg_hr": 150,
                "max_hr": 170
            }
        ]
        result = format_workouts_summary(workouts)
        assert "1 running" in result

    def test_swimming_classified_correctly(self):
        """Swimming should be classified as non-running."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "swimming",
                "distance_km": 1.5,
                "time": "30:00",
                "avg_pace": "20:00",
                "avg_hr": 130,
                "max_hr": 150
            }
        ]
        result = format_workouts_summary(workouts)
        assert "0 running" in result
        assert "1 other" in result

    def test_strength_classified_correctly(self):
        """Strength training should be classified as non-running."""
        workouts = [
            {
                "date": "2026-01-08",
                "type": "strength training",
                "distance_km": 0.0,
                "time": "45:00",
                "avg_pace": "-",
                "avg_hr": 110,
                "max_hr": 140
            }
        ]
        result = format_workouts_summary(workouts)
        assert "0 running" in result
        assert "1 other" in result


class TestGenerateCopilotPrompt:
    """Tests for the generate_copilot_prompt function."""

    def test_uses_date_string_from_calculate_next_monday_tuple(self):
        """Should use the first tuple value from get_next_monday()."""
        with patch('generate_weekly_plan_prompt.read_workouts_last_14_days', return_value=[]), \
             patch('generate_weekly_plan_prompt.read_latest_plan', return_value='Latest plan'), \
             patch('generate_weekly_plan_prompt.read_week_plan_template', return_value='Template'), \
             patch('generate_weekly_plan_prompt.get_training_status_section', return_value=''), \
             patch('generate_weekly_plan_prompt.format_penalty_section', return_value=''), \
             patch('generate_weekly_plan_prompt.format_workouts_summary', return_value='Summary'), \
             patch('generate_weekly_plan_prompt.get_next_monday', return_value=('2030-01-06', '2030', '01')):
            prompt = generate_copilot_prompt()

        assert "week starting 2030-01-06" in prompt
        assert "plans/2030/01/week-2030-01-06.md" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
