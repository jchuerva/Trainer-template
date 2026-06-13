#!/usr/bin/env python3
"""
Tests for extract_fit_data.py
"""

from pathlib import Path
import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from extract_fit_data import format_time, format_pace, format_as_markdown


class TestFormatTime:
    """Tests for the format_time function."""

    def test_none_returns_dash(self):
        """None should return '—'."""
        assert format_time(None) == "—"

    def test_zero_seconds(self):
        """Zero seconds should return '0:00'."""
        assert format_time(0) == "0:00"

    def test_seconds_only(self):
        """Less than a minute should show MM:SS."""
        assert format_time(45) == "0:45"

    def test_minutes_and_seconds(self):
        """Minutes and seconds should show MM:SS."""
        assert format_time(125) == "2:05"
        assert format_time(600) == "10:00"
        assert format_time(3599) == "59:59"

    def test_hours_minutes_seconds(self):
        """Hours should show HH:MM:SS."""
        assert format_time(3600) == "1:00:00"
        assert format_time(3661) == "1:01:01"
        assert format_time(7325) == "2:02:05"

    def test_float_seconds(self):
        """Float seconds should be truncated."""
        assert format_time(125.7) == "2:05"
        assert format_time(59.9) == "0:59"


class TestFormatPace:
    """Tests for the format_pace function."""

    def test_none_returns_dash(self):
        """None should return '—'."""
        assert format_pace(None) == "—"

    def test_zero_returns_dash(self):
        """Zero speed should return '—'."""
        assert format_pace(0) == "—"

    def test_negative_returns_dash(self):
        """Negative speed should return '—'."""
        assert format_pace(-1.5) == "—"

    def test_typical_running_pace(self):
        """Typical running speed should give reasonable pace."""
        # 3 m/s = 5:33 per km
        result = format_pace(3.0)
        assert result == "5:33"

    def test_fast_running_pace(self):
        """Fast running speed."""
        # 5 m/s = 3:20 per km
        result = format_pace(5.0)
        assert result == "3:20"

    def test_walking_pace(self):
        """Walking speed should give slower pace."""
        # 1.5 m/s = 11:06 per km
        result = format_pace(1.5)
        assert result == "11:06"

    def test_very_slow_pace(self):
        """Very slow speed."""
        # 1 m/s = 16:40 per km
        result = format_pace(1.0)
        assert result == "16:40"


class TestFormatAsMarkdown:
    """Tests for the format_as_markdown function."""

    def test_minimal_metrics(self):
        """Should handle minimal metrics with None values."""
        metrics = {
            "file_name": "test.fit",
            "start_time_formatted": None,
            "sport": None,
            "total_distance_km": None,
            "total_time_formatted": None,
            "average_pace": None,
            "average_hr": None,
            "max_hr": None,
            "average_cadence": None,
            "total_ascent_m": None,
            "total_descent_m": None,
            "total_calories": None,
            "avg_temperature_c": None,
            "laps": [],
        }
        result = format_as_markdown(metrics)
        assert "## Extracted Workout Data" in result
        assert "test.fit" in result
        assert "—" in result  # Missing values shown as dash

    def test_full_metrics(self):
        """Should format all metrics correctly."""
        metrics = {
            "file_name": "workout.fit",
            "start_time_formatted": "2026-01-11 12:30",
            "sport": "running",
            "total_distance_km": 5.25,
            "total_time_formatted": "28:30",
            "average_pace": "5:26",
            "average_hr": 155,
            "max_hr": 172,
            "average_cadence": 180,
            "total_ascent_m": 45,
            "total_descent_m": 42,
            "total_calories": 350,
            "avg_temperature_c": 18,
            "laps": [],
        }
        result = format_as_markdown(metrics)
        assert "workout.fit" in result
        assert "2026-01-11 12:30" in result
        assert "running" in result
        assert "5.25" in result
        assert "28:30" in result
        assert "5:26" in result
        assert "155" in result
        assert "172" in result
        assert "180" in result
        assert "45" in result
        assert "350" in result
        assert "18°C" in result

    def test_lap_data_table(self):
        """Should format lap data as markdown table."""
        metrics = {
            "file_name": "test.fit",
            "start_time_formatted": "2026-01-11 12:30",
            "sport": "running",
            "total_distance_km": 3.0,
            "total_time_formatted": "18:00",
            "average_pace": "6:00",
            "average_hr": 150,
            "max_hr": 165,
            "average_cadence": 175,
            "total_ascent_m": 20,
            "total_descent_m": 18,
            "total_calories": None,
            "avg_temperature_c": None,
            "laps": [
                {
                    "lap_number": 1,
                    "distance_km": 1.0,
                    "time_formatted": "6:10",
                    "pace": "6:10",
                    "avg_hr": 145,
                    "max_hr": 155,
                    "avg_cadence": 172,
                },
                {
                    "lap_number": 2,
                    "distance_km": 1.0,
                    "time_formatted": "5:55",
                    "pace": "5:55",
                    "avg_hr": 152,
                    "max_hr": 162,
                    "avg_cadence": 176,
                },
                {
                    "lap_number": 3,
                    "distance_km": 1.0,
                    "time_formatted": "5:55",
                    "pace": "5:55",
                    "avg_hr": 158,
                    "max_hr": 168,
                    "avg_cadence": 180,
                },
            ],
        }
        result = format_as_markdown(metrics)
        assert "### Lap/Split Data" in result
        assert "| Lap | Distance (km) | Time | Pace | Avg HR | Max HR | Cadence |" in result
        assert "|---:|---:|---:|---:|---:|---:|---:|" in result
        assert "| 1 " in result
        assert "| 2 " in result
        assert "| 3 " in result
        assert "6:10" in result
        assert "5:55" in result

    def test_lap_with_missing_values(self):
        """Should handle laps with missing values."""
        metrics = {
            "file_name": "test.fit",
            "start_time_formatted": None,
            "sport": None,
            "total_distance_km": None,
            "total_time_formatted": None,
            "average_pace": None,
            "average_hr": None,
            "max_hr": None,
            "average_cadence": None,
            "total_ascent_m": None,
            "total_descent_m": None,
            "total_calories": None,
            "avg_temperature_c": None,
            "laps": [
                {
                    "lap_number": 1,
                    "distance_km": None,
                    "time_formatted": None,
                    "pace": None,
                    "avg_hr": None,
                    "max_hr": None,
                    "avg_cadence": None,
                },
            ],
        }
        result = format_as_markdown(metrics)
        assert "| 1 " in result
        # Should have dashes for missing values
        assert "—" in result


class TestFormatTimeEdgeCases:
    """Edge case tests for format_time."""

    def test_large_hours(self):
        """Very long duration should still work."""
        # 10 hours
        assert format_time(36000) == "10:00:00"

    def test_fractional_seconds_truncated(self):
        """Fractional seconds should be truncated, not rounded."""
        assert format_time(59.99) == "0:59"
        assert format_time(119.99) == "1:59"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
