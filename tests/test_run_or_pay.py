#!/usr/bin/env python3
"""Tests for the Run or Pay feature."""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from run_or_pay import (
    get_previous_week_dates,
    is_feature_enabled,
    get_penalty_amount,
    get_currency,
    get_training_status,
    get_planned_runs_from_config,
    load_config,
    format_penalty_section,
    count_running_workouts_in_week,
    _count_consecutive_clean_weeks,
)


class TestGetPreviousWeekDates:
    """Tests for get_previous_week_dates function."""
    
    def test_returns_monday_to_sunday(self):
        """Should return Monday and Sunday of previous week."""
        monday, sunday = get_previous_week_dates()
        
        # Monday should be a Monday (weekday 0)
        assert monday.weekday() == 0
        # Sunday should be a Sunday (weekday 6)
        assert sunday.weekday() == 6
        # They should be 6 days apart
        assert (sunday - monday).days == 6
    
    def test_previous_week_is_in_the_past(self):
        """Previous week should be before today."""
        monday, sunday = get_previous_week_dates()
        today = datetime.now()
        
        assert sunday < today


class TestFeatureFlags:
    """Tests for feature flag functions."""
    
    @patch('run_or_pay.load_config')
    def test_feature_disabled_by_default(self, mock_config):
        """Feature should be disabled when not in config."""
        mock_config.return_value = {}
        assert is_feature_enabled() is False
    
    @patch('run_or_pay.load_config')
    def test_feature_disabled_when_false(self, mock_config):
        """Feature should be disabled when explicitly set to false."""
        mock_config.return_value = {'run_or_pay': {'enabled': False}}
        assert is_feature_enabled() is False
    
    @patch('run_or_pay.load_config')
    def test_feature_enabled_when_true(self, mock_config):
        """Feature should be enabled when set to true."""
        mock_config.return_value = {'run_or_pay': {'enabled': True}}
        assert is_feature_enabled() is True


class TestPenaltyAmount:
    """Tests for get_penalty_amount function."""
    
    @patch('run_or_pay.load_config')
    def test_default_penalty_is_zero(self, mock_config):
        """Default penalty should be 0 when not configured."""
        mock_config.return_value = {}
        assert get_penalty_amount() == 0
    
    @patch('run_or_pay.load_config')
    def test_returns_configured_penalty(self, mock_config):
        """Should return the configured penalty amount."""
        mock_config.return_value = {'run_or_pay': {'penalty_per_week': 10}}
        assert get_penalty_amount() == 10


class TestCurrency:
    """Tests for get_currency function."""
    
    @patch('run_or_pay.load_config')
    def test_default_currency_is_eur(self, mock_config):
        """Default currency should be EUR."""
        mock_config.return_value = {}
        assert get_currency() == 'EUR'
    
    @patch('run_or_pay.load_config')
    def test_returns_configured_currency(self, mock_config):
        """Should return the configured currency."""
        mock_config.return_value = {'run_or_pay': {'currency': 'USD'}}
        assert get_currency() == 'USD'


class TestTrainingStatus:
    """Tests for get_training_status function."""
    
    @patch('run_or_pay.load_config')
    def test_default_status_is_active(self, mock_config):
        """Default status should be active."""
        mock_config.return_value = {}
        assert get_training_status() == 'active'
    
    @patch('run_or_pay.load_config')
    def test_returns_configured_status(self, mock_config):
        """Should return the configured status."""
        mock_config.return_value = {'training_status': {'status': 'sick'}}
        assert get_training_status() == 'sick'


class TestPlannedRuns:
    """Tests for get_planned_runs_from_config function."""
    
    @patch('run_or_pay.load_config')
    def test_default_planned_runs(self, mock_config):
        """Default should be 3 runs per week."""
        mock_config.return_value = {}
        assert get_planned_runs_from_config() == 3
    
    @patch('run_or_pay.load_config')
    def test_returns_configured_runs(self, mock_config):
        """Should return the configured weekly runs."""
        mock_config.return_value = {'preferences': {'weekly_runs': 4}}
        assert get_planned_runs_from_config() == 4


class TestLoadConfigCaching:
    """Tests for load_config caching behavior."""

    def test_load_config_cached_across_getters(self, tmp_path):
        """Should parse config only once when multiple getters are called."""
        config_data = {
            'run_or_pay': {'enabled': True, 'penalty_per_week': 10, 'currency': 'USD'},
            'training_status': {'status': 'active'},
            'preferences': {'weekly_runs': 4}
        }
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)
        config_file = tmp_path / "config" / "config.yaml"
        config_file.write_text("test: config", encoding="utf-8")

        load_config.cache_clear()
        try:
            with patch('run_or_pay.get_config_path', return_value=config_file), patch(
                'run_or_pay.yaml.safe_load', return_value=config_data
            ) as mock_safe_load:
                assert is_feature_enabled() is True
                assert get_penalty_amount() == 10
                assert get_currency() == 'USD'
                assert get_training_status() == 'active'
                assert get_planned_runs_from_config() == 4
                assert mock_safe_load.call_count == 1
        finally:
            load_config.cache_clear()


class TestFormatPenaltySection:
    """Tests for format_penalty_section function."""
    
    @patch('run_or_pay.is_feature_enabled')
    def test_returns_empty_when_disabled(self, mock_enabled):
        """Should return empty string when feature is disabled."""
        mock_enabled.return_value = False
        assert format_penalty_section() == ""
    
    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_includes_total_penalty(self, mock_summary, mock_enabled):
        """Should include total penalty in output."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 30,
            'currency': 'EUR',
            'year': 2026,
            'last_week': None,
            'weeks_with_penalty': 3,
            'current_streak': 0,
            'history': []
        }
        
        result = format_penalty_section()
        assert '30 EUR' in result
        assert '2026' in result
        assert 'Run or Pay' in result
    
    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_shows_last_week_penalty(self, mock_summary, mock_enabled):
        """Should show last week's penalty if there was one."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 10,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'planned_runs': 3,
                'completed_runs': 2,
                'missed_runs': 1,
                'penalty_applied': 10,
                'status_at_time': 'active'
            },
            'weeks_with_penalty': 1,
            'current_streak': 1,
            'history': [{'penalty_applied': 10}]
        }
        
        result = format_penalty_section()
        assert '2/3' in result
        assert '+10' in result or '10 EUR' in result
    
    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_shows_no_penalty_for_non_active_status(self, mock_summary, mock_enabled):
        """Should show no penalty message for non-active status recorded in history."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 0,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'week': '2026-01-06',
                'planned_runs': 3,
                'completed_runs': 0,
                'missed_runs': 0,
                'penalty_applied': 0,
                'reason': 'No penalty - status was "sick"',
                'status_at_time': 'sick'
            },
            'weeks_with_penalty': 0,
            'current_streak': 0,
            'history': [{
                'week': '2026-01-06',
                'planned_runs': 3,
                'completed_runs': 0,
                'missed_runs': 0,
                'penalty_applied': 0,
                'reason': 'No penalty - status was "sick"',
                'status_at_time': 'sick'
            }]
        }
        
        result = format_penalty_section()
        assert 'sick' in result.lower() or 'No penalty' in result

    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_penalty_applies_for_returning_status(self, mock_summary, mock_enabled):
        """Should apply penalty when status is returning."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 10,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'planned_runs': 3,
                'completed_runs': 2,
                'missed_runs': 1,
                'penalty_applied': 10,
                'status_at_time': 'returning'
            },
            'weeks_with_penalty': 1,
            'current_streak': 1,
            'history': [{'penalty_applied': 10}]
        }
        
        result = format_penalty_section()
        assert '+10' in result or '10 EUR' in result
        assert '2/3' in result

    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_shows_consecutive_streak_warning(self, mock_summary, mock_enabled):
        """Should show warning for consecutive weeks with penalties."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 30,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'planned_runs': 3,
                'completed_runs': 1,
                'missed_runs': 2,
                'penalty_applied': 10,
                'status_at_time': 'active'
            },
            'weeks_with_penalty': 3,
            'current_streak': 3,
            'history': [
                {'penalty_applied': 10},
                {'penalty_applied': 10},
                {'penalty_applied': 10}
            ]
        }
        
        result = format_penalty_section()
        assert '3 consecutive weeks' in result
        assert 'back on track' in result.lower()

    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_shows_weeks_tracked(self, mock_summary, mock_enabled):
        """Should show total weeks tracked and weeks with penalties."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 20,
            'currency': 'EUR',
            'year': 2026,
            'last_week': None,
            'weeks_with_penalty': 2,
            'current_streak': 0,
            'history': [
                {'penalty_applied': 10},
                {'penalty_applied': 0},
                {'penalty_applied': 10},
                {'penalty_applied': 0}
            ]
        }
        
        result = format_penalty_section()
        assert '4' in result  # 4 weeks tracked
        assert '2 with penalties' in result


class TestConfigSchema:
    """Tests to verify the config schema includes run_or_pay."""
    
    def test_schema_includes_run_or_pay(self):
        """Schema should include run_or_pay section."""
        schema_path = Path(__file__).parent.parent / "config" / "config.schema.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        assert 'run_or_pay' in schema['properties']
        
        run_or_pay_schema = schema['properties']['run_or_pay']
        assert 'enabled' in run_or_pay_schema['properties']
        assert 'penalty_per_week' in run_or_pay_schema['properties']
        assert 'currency' in run_or_pay_schema['properties']
    
    def test_schema_property_types_and_defaults(self):
        """Schema properties should have correct types and defaults."""
        schema_path = Path(__file__).parent.parent / "config" / "config.schema.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        run_or_pay = schema['properties']['run_or_pay']['properties']
        
        # Check enabled property
        assert run_or_pay['enabled']['type'] == 'boolean'
        assert run_or_pay['enabled']['default'] is False
        
        # Check penalty_per_week property
        assert run_or_pay['penalty_per_week']['type'] == 'number'
        assert run_or_pay['penalty_per_week']['minimum'] == 0
        
        # Check currency property
        assert run_or_pay['currency']['type'] == 'string'
        assert run_or_pay['currency']['default'] == 'EUR'


class TestCountConsecutiveCleanWeeks:
    """Tests for _count_consecutive_clean_weeks helper."""

    def test_empty_history_returns_zero(self):
        """Should return 0 for empty history."""
        assert _count_consecutive_clean_weeks([]) == 0

    def test_single_clean_week(self):
        """One clean active week should return 1."""
        history = [
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0}
        ]
        assert _count_consecutive_clean_weeks(history) == 1

    def test_three_consecutive_clean_weeks(self):
        """Three consecutive clean active weeks should return 3."""
        history = [
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
        ]
        assert _count_consecutive_clean_weeks(history) == 3

    def test_streak_broken_by_penalty(self):
        """A week with a penalty should reset the streak."""
        history = [
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
            {'status_at_time': 'active', 'missed_runs': 2, 'penalty_applied': 10},
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
        ]
        # Only the last clean week counts
        assert _count_consecutive_clean_weeks(history) == 1

    def test_non_active_status_breaks_streak(self):
        """A non-active/returning status week should break the clean streak."""
        history = [
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
            {'status_at_time': 'sick', 'missed_runs': 0, 'penalty_applied': 0},
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
        ]
        assert _count_consecutive_clean_weeks(history) == 1

    def test_returning_status_counts_as_clean(self):
        """A clean returning-status week should count toward the streak."""
        history = [
            {'status_at_time': 'returning', 'missed_runs': 0, 'penalty_applied': 0},
            {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
        ]
        assert _count_consecutive_clean_weeks(history) == 2


class TestConsecutiveCleanWeeksDiscount:
    """Tests for the 3-consecutive-clean-weeks discount in format_penalty_section."""

    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_discount_shown_when_applied(self, mock_summary, mock_enabled):
        """Should show discount message when a discount was applied this week."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 20,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'planned_runs': 3,
                'completed_runs': 3,
                'missed_runs': 0,
                'penalty_applied': 0,
                'status_at_time': 'active',
                'discount_applied': 10,
            },
            'weeks_with_penalty': 2,
            'current_streak': 0,
            'consecutive_clean_weeks': 3,
            'history': [
                {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
                {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
                {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0,
                 'discount_applied': 10},
            ]
        }

        result = format_penalty_section()
        assert '3 consecutive weeks' in result
        assert '-10 EUR' in result or 'discount' in result.lower()

    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    @patch('run_or_pay.get_penalty_amount')
    def test_progress_shown_toward_discount(self, mock_amount, mock_summary, mock_enabled):
        """Should show progress toward next discount when 1 or 2 clean weeks in a row."""
        mock_enabled.return_value = True
        mock_amount.return_value = 10
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 10,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'planned_runs': 3,
                'completed_runs': 3,
                'missed_runs': 0,
                'penalty_applied': 0,
                'status_at_time': 'active',
            },
            'weeks_with_penalty': 1,
            'current_streak': 0,
            'consecutive_clean_weeks': 2,
            'history': [
                {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
                {'status_at_time': 'active', 'missed_runs': 0, 'penalty_applied': 0},
            ]
        }

        result = format_penalty_section()
        assert '2 consecutive clean week(s)' in result
        assert '1 more' in result

    @patch('run_or_pay.is_feature_enabled')
    @patch('run_or_pay.get_penalty_summary')
    def test_no_progress_shown_when_penalty_last_week(self, mock_summary, mock_enabled):
        """Should NOT show clean-week progress when last week had a penalty."""
        mock_enabled.return_value = True
        mock_summary.return_value = {
            'enabled': True,
            'total_penalty': 10,
            'currency': 'EUR',
            'year': 2026,
            'last_week': {
                'planned_runs': 3,
                'completed_runs': 1,
                'missed_runs': 2,
                'penalty_applied': 10,
                'status_at_time': 'active',
            },
            'weeks_with_penalty': 1,
            'current_streak': 1,
            'consecutive_clean_weeks': 0,
            'history': [{'penalty_applied': 10}]
        }

        result = format_penalty_section()
        assert 'consecutive clean week' not in result
        assert 'discount' not in result.lower()


class TestCountRunningWorkoutsInWeek:
    """Tests for keyword-based running workout counting."""

    @patch('run_or_pay.get_repo_root')
    def test_counts_spanish_running_keyword(self, mock_repo_root, tmp_path):
        """Spanish running keywords should count as running workouts."""
        index_dir = tmp_path / "workouts"
        index_dir.mkdir(parents=True)
        (index_dir / "index.md").write_text(
            "| Date | Type | Distance | Time | Pace | HR | Max HR | Analysis |\n"
            "|------|------|----------|------|------|----|--------|----------|\n"
            "| 2026-01-08 | carrera | 5.0 | 30:00 | 6:00 | 150 | 170 | - |\n",
            encoding='utf-8',
        )
        mock_repo_root.return_value = tmp_path

        count = count_running_workouts_in_week(
            datetime(2026, 1, 5),
            datetime(2026, 1, 11),
        )
        assert count == 1

    @patch('run_or_pay.get_repo_root')
    def test_excludes_multiword_non_running_keyword(self, mock_repo_root, tmp_path):
        """Multiword non-running keywords should not count as runs."""
        index_dir = tmp_path / "workouts"
        index_dir.mkdir(parents=True)
        (index_dir / "index.md").write_text(
            "| Date | Type | Distance | Time | Pace | HR | Max HR | Analysis |\n"
            "|------|------|----------|------|------|----|--------|----------|\n"
            "| 2026-01-08 | entreno cruzado | 5.0 | 30:00 | 6:00 | 140 | 160 | - |\n",
            encoding='utf-8',
        )
        mock_repo_root.return_value = tmp_path

        count = count_running_workouts_in_week(
            datetime(2026, 1, 5),
            datetime(2026, 1, 11),
        )
        assert count == 0
