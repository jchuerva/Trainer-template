#!/usr/bin/env python3
"""
Tests for generate_yearly_report.py
"""

import json
import sys
from pathlib import Path
import pytest

# Add scripts directory to path (same pattern as other test files)
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_yearly_report import (
    MONTH_NAMES,
    compute_health_stats,
    compute_training_stats,
    load_health_snapshots,
    load_workout_days,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workout_index_content(rows: list[str]) -> str:
    """Build a minimal workouts/index.md with given pipe-delimited rows."""
    header = "| Date | Type | Distance | Time | Avg Pace | Avg HR | Notes |"
    sep = "| --- | --- | --- | --- | --- | --- | --- |"
    return "\n".join([header, sep] + rows) + "\n"


def _make_health_json(hrv: float | None = None,
                      rhr: float | None = None,
                      sleep_h: float | None = None) -> dict:
    """Build a minimal HealthAutoExport JSON payload (kept for load_health_snapshots tests)."""
    metrics = []
    if hrv is not None:
        metrics.append({
            "name": "heart_rate_variability",
            "data": [{"qty": hrv}],
        })
    if rhr is not None:
        metrics.append({
            "name": "resting_heart_rate",
            "data": [{"qty": rhr}],
        })
    if sleep_h is not None:
        metrics.append({
            "name": "sleep_analysis",
            "data": [{"totalSleep": sleep_h}],
        })
    return {"data": {"metrics": metrics, "workouts": []}}


def _make_index_row(date: str,
                   hrv_ms: float | None = None,
                   rhr: float | None = None,
                   sleep_h: float | None = None,
                   steps: int | None = None) -> dict:
    """Build a health/index.md row dict (new source-of-truth format used by compute_health_stats)."""
    return {
        "date": date,
        "hrv_ms": hrv_ms,
        "rhr": rhr,
        "sleep_h": sleep_h,
        "steps": steps,
        "spo2": None,
        "resp": None,
        "workout": None,
    }


# ---------------------------------------------------------------------------
# load_workout_days
# ---------------------------------------------------------------------------

class TestLoadWorkoutDays:
    """Tests for load_workout_days."""

    def test_parses_correctly_from_index(self, tmp_path):
        """Parses a well-formed workouts/index.md for the requested year."""
        (tmp_path / "workouts").mkdir()
        content = _make_workout_index_content([
            "| 2026-01-15 | Running | 10.0 | 50:00 | 5:00 | 150 |  |",
            "| 2026-03-22 | Fitness_equipment | 0.0 | 45:00 |  | 120 |  |",
        ])
        (tmp_path / "workouts" / "index.md").write_text(content, encoding="utf-8")

        result = load_workout_days(tmp_path, 2026)

        assert len(result) == 2
        assert result[0]["date"] == "2026-01-15"
        assert result[0]["name"] == "Running"
        assert result[0]["distance_km"] == 10.0
        assert result[1]["date"] == "2026-03-22"

    def test_same_day_duplicates_preserved(self, tmp_path):
        """Multiple workouts on the same date are kept as separate entries."""
        (tmp_path / "workouts").mkdir()
        content = _make_workout_index_content([
            "| 2026-02-22 | Running | 8.5 | 45:00 | 5:18 | 155 |  |",
            "| 2026-02-22 | Fitness_equipment | 0.0 | 30:00 |  | 130 |  |",
        ])
        (tmp_path / "workouts" / "index.md").write_text(content, encoding="utf-8")

        result = load_workout_days(tmp_path, 2026)

        assert len(result) == 2, "Same-day duplicates must NOT be deduplicated"
        assert result[0]["date"] == "2026-02-22"
        assert result[1]["date"] == "2026-02-22"
        names = {r["name"] for r in result}
        assert "Running" in names
        assert "Fitness_equipment" in names

    def test_skips_header_and_separator_rows(self, tmp_path):
        """Header and separator rows in the table are not included."""
        (tmp_path / "workouts").mkdir()
        content = _make_workout_index_content([
            "| 2026-05-01 | Running | 5.0 | 25:00 | 5:00 | 145 |  |",
        ])
        (tmp_path / "workouts" / "index.md").write_text(content, encoding="utf-8")

        result = load_workout_days(tmp_path, 2026)

        # Only the single data row should be returned (not the 2 header/sep rows)
        assert len(result) == 1
        assert result[0]["date"] == "2026-05-01"

    def test_returns_sorted_list(self, tmp_path):
        """Results are sorted by date ascending."""
        (tmp_path / "workouts").mkdir()
        content = _make_workout_index_content([
            "| 2026-12-01 | Running | 5.0 | 25:00 | 5:00 | 148 |  |",
            "| 2026-01-10 | Running | 6.0 | 30:00 | 5:00 | 150 |  |",
            "| 2026-06-15 | Fitness_equipment | 0.0 | 40:00 |  | 120 |  |",
        ])
        (tmp_path / "workouts" / "index.md").write_text(content, encoding="utf-8")

        result = load_workout_days(tmp_path, 2026)

        dates = [r["date"] for r in result]
        assert dates == sorted(dates)

    def test_ignores_other_years(self, tmp_path):
        """Workouts from other years are excluded."""
        (tmp_path / "workouts").mkdir()
        content = _make_workout_index_content([
            "| 2025-12-31 | Running | 5.0 | 25:00 | 5:00 | 150 |  |",
            "| 2026-01-01 | Running | 6.0 | 30:00 | 5:00 | 152 |  |",
            "| 2027-01-01 | Running | 7.0 | 35:00 | 5:00 | 154 |  |",
        ])
        (tmp_path / "workouts" / "index.md").write_text(content, encoding="utf-8")

        result = load_workout_days(tmp_path, 2026)

        assert len(result) == 1
        assert result[0]["date"] == "2026-01-01"

    def test_returns_empty_when_file_missing(self, tmp_path):
        """Returns an empty list if workouts/index.md does not exist."""
        result = load_workout_days(tmp_path, 2026)
        assert result == []


# ---------------------------------------------------------------------------
# compute_training_stats
# ---------------------------------------------------------------------------

class TestComputeTrainingStats:
    """Tests for compute_training_stats."""

    def _make_run(self, date: str, distance_km: float | None = 10.0,
                  avg_pace: str = "6:00", avg_hr: int | None = 150,
                  name: str = "Running") -> dict:
        return {
            "date": date,
            "name": name,
            "distance_km": distance_km,
            "avg_pace": avg_pace,
            "avg_hr": avg_hr,
            "source": "index",
        }

    def test_total_workouts_counts_duplicates(self):
        """total_workouts counts ALL entries including same-day duplicates."""
        workouts = [
            self._make_run("2026-02-22", name="Running"),
            self._make_run("2026-02-22", distance_km=None, avg_pace=None, name="Fitness_equipment"),
        ]
        stats = compute_training_stats(workouts, 2026)
        assert stats["total_workouts"] == 2

    def test_avg_pace_is_true_mean(self):
        """avg_pace is the arithmetic mean of all pace values, not min or max."""
        workouts = [
            self._make_run("2026-01-10", avg_pace="6:00"),
            self._make_run("2026-01-11", avg_pace="7:00"),
        ]
        stats = compute_training_stats(workouts, 2026)
        # Mean of 360s and 420s = 390s = 6:30
        assert stats["avg_pace"] == "6:30"

    def test_best_month_returns_spanish_name(self):
        """best_month is a Spanish month name from MONTH_NAMES (e.g. 'Enero')."""
        workouts = [
            self._make_run("2026-01-10"),
            self._make_run("2026-01-11"),
            self._make_run("2026-01-12"),
            self._make_run("2026-03-01"),
        ]
        stats = compute_training_stats(workouts, 2026)
        # January (3 workouts) beats March (1)
        assert stats["best_month"] == "Enero"
        # Confirm it's a valid Spanish name from MONTH_NAMES
        assert stats["best_month"] in MONTH_NAMES

    def test_type_counts_fitness_equipment_is_cross_training(self):
        """Fitness_equipment type maps to 'Cross-training'."""
        workouts = [
            self._make_run("2026-01-10", name="Fitness_equipment"),
        ]
        stats = compute_training_stats(workouts, 2026)
        assert "Cross-training" in stats["type_counts"]
        assert stats["type_counts"]["Cross-training"] == 1

    def test_type_counts_running_is_running(self):
        """Running type maps to 'Running'."""
        workouts = [
            self._make_run("2026-01-10", name="Running"),
        ]
        stats = compute_training_stats(workouts, 2026)
        assert "Running" in stats["type_counts"]
        assert stats["type_counts"]["Running"] == 1

    def test_max_streak_label_singular(self):
        """max_streak_label is 'día consecutivo' when streak == 1."""
        # Only one workout, isolated — streak is exactly 1
        # Use a past year/date so compute_training_stats doesn't cap at today
        workouts = [
            self._make_run("2023-07-15"),
        ]
        stats = compute_training_stats(workouts, 2023)
        assert stats["max_streak_days"] == 1
        assert stats["max_streak_label"] == "día consecutivo"

    def test_max_streak_label_plural(self):
        """max_streak_label is 'días consecutivos' when streak > 1."""
        # Use a past year/date so compute_training_stats doesn't cap at today
        workouts = [
            self._make_run("2023-01-01"),
            self._make_run("2023-01-02"),
            self._make_run("2023-01-03"),
        ]
        stats = compute_training_stats(workouts, 2023)
        assert stats["max_streak_days"] == 3
        assert stats["max_streak_label"] == "días consecutivos"

    def test_total_km_handles_missing_distance(self):
        """total_km and avg_km_per_run are computed only from runs with distance."""
        workouts = [
            self._make_run("2026-01-10", distance_km=10.0),
            self._make_run("2026-01-11", distance_km=None),  # no distance
        ]
        # Must not crash
        stats = compute_training_stats(workouts, 2026)
        assert stats is not None
        assert stats["total_km"] == 10.0
        assert stats["avg_km_per_run"] == 10.0
        assert stats["runs_with_km"] == 1

    def test_total_km_all_missing_distance(self):
        """Gracefully handles workouts where ALL distance values are None."""
        workouts = [
            self._make_run("2026-01-10", distance_km=None, avg_pace=None),
        ]
        stats = compute_training_stats(workouts, 2026)
        assert stats is not None
        assert stats["total_km"] is None
        assert stats["avg_km_per_run"] is None

    def test_returns_empty_dict_for_no_workouts(self):
        """Returns empty dict when workouts list is empty."""
        stats = compute_training_stats([], 2026)
        assert stats == {}

    def test_all_month_names_are_spanish(self):
        """MONTH_NAMES contains 12 Spanish month names."""
        assert len(MONTH_NAMES) == 12
        assert MONTH_NAMES[0] == "Enero"
        assert MONTH_NAMES[11] == "Diciembre"


# ---------------------------------------------------------------------------
# compute_health_stats
# ---------------------------------------------------------------------------

class TestComputeHealthStats:
    """Tests for compute_health_stats.

    compute_health_stats now reads index rows (dicts with hrv_ms/rhr/sleep_h/steps)
    rather than raw HealthAutoExport JSON. Use _make_index_row() as fixture helper.
    """

    def test_returns_empty_dict_for_empty_list(self):
        """Returns empty dict when snapshot list is empty."""
        result = compute_health_stats([])
        assert result == {}

    def test_averages_hrv_correctly(self):
        """Correctly averages HRV values across index rows."""
        rows = [
            _make_index_row("2026-01-01", hrv_ms=40.0),
            _make_index_row("2026-01-02", hrv_ms=60.0),
        ]
        result = compute_health_stats(rows)
        assert result["hrv"]["avg"] == 50.0

    def test_hrv_zero_is_valid_and_contributes_to_average(self):
        """HRV=0 is a valid value (not None) and must be included in the average.

        If compute_health_stats used a truthy check instead of `is not None`,
        hrv_ms=0 would be skipped, giving avg=10.0 instead of 5.0.
        """
        rows = [
            _make_index_row("2026-01-01", hrv_ms=0.0),
            _make_index_row("2026-01-02", hrv_ms=10.0),
        ]
        result = compute_health_stats(rows)
        assert result["hrv"]["avg"] == 5.0

    def test_averages_rhr_correctly(self):
        """Correctly averages RHR values across index rows."""
        rows = [
            _make_index_row("2026-01-01", rhr=50.0),
            _make_index_row("2026-01-02", rhr=60.0),
        ]
        result = compute_health_stats(rows)
        assert result["rhr"]["avg"] == 55.0

    def test_averages_sleep_correctly(self):
        """Correctly averages sleep hours across index rows."""
        rows = [
            _make_index_row("2026-01-01", sleep_h=7.0),
            _make_index_row("2026-01-02", sleep_h=9.0),
        ]
        result = compute_health_stats(rows)
        assert result["sleep"]["avg"] == 8.0

    def test_counts_poor_sleep_days(self):
        """Counts nights with less than 6 hours sleep as poor_days."""
        rows = [
            _make_index_row("2026-01-01", sleep_h=5.5),  # poor
            _make_index_row("2026-01-02", sleep_h=4.9),  # poor
            _make_index_row("2026-01-03", sleep_h=7.0),  # ok
            _make_index_row("2026-01-04", sleep_h=6.0),  # boundary (ok)
        ]
        result = compute_health_stats(rows)
        assert result["sleep"]["poor_days"] == 2

    def test_days_with_data_count(self):
        """days_with_data counts only rows that have at least one non-None metric."""
        rows = [
            _make_index_row("2026-01-01", hrv_ms=45.0),
            _make_index_row("2026-01-02", hrv_ms=55.0),
            _make_index_row("2026-01-03", hrv_ms=50.0),
        ]
        result = compute_health_stats(rows)
        assert result["days_with_data"] == 3

    def test_handles_row_with_no_metrics(self):
        """Rows with all-None metrics are handled without crash; days_with_data=0."""
        rows = [
            _make_index_row("2026-01-01"),  # all metrics None
        ]
        result = compute_health_stats(rows)
        assert result is not None
        assert result["days_with_data"] == 0

    def test_missing_health_metrics_produce_empty_stat_blocks(self):
        """When no HRV data exists, hrv stat block is empty dict."""
        rows = [
            _make_index_row("2026-01-01", rhr=55.0),
        ]
        result = compute_health_stats(rows)
        assert result["hrv"] == {}


# ---------------------------------------------------------------------------
# load_health_snapshots
# ---------------------------------------------------------------------------

def _make_index_md(rows: list[dict]) -> str:
    """Build a health/index.md string from a list of row dicts."""
    header = "| Date | HRV ms | RHR | Sleep h | Steps | SpO2 | Resp | Workout |"
    sep    = "| --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [header, sep]
    for r in rows:
        def fmt(v):
            return str(v) if v is not None else "-"
        lines.append(
            f"| {r['date']} | {fmt(r.get('hrv_ms'))} | {fmt(r.get('rhr'))} "
            f"| {fmt(r.get('sleep_h'))} | {fmt(r.get('steps'))} "
            f"| {fmt(r.get('spo2'))} | {fmt(r.get('resp'))} "
            f"| {fmt(r.get('workout'))} |"
        )
    return "\n".join(lines) + "\n"


class TestLoadHealthSnapshots:
    """Tests for load_health_snapshots.

    Since PR #141, load_health_snapshots reads from health/index.md (source of truth)
    rather than raw daily JSON files. Tests create a minimal index.md in tmp_path.
    """

    def test_returns_only_rows_matching_requested_year(self, tmp_path):
        """Only rows from the requested year are returned."""
        health_dir = tmp_path / "health"
        health_dir.mkdir(parents=True)
        rows = [
            _make_index_row("2026-01-15", hrv_ms=45.0),
            _make_index_row("2026-06-01", hrv_ms=50.0),
            _make_index_row("2025-12-31", hrv_ms=40.0),  # different year
        ]
        (health_dir / "index.md").write_text(_make_index_md(rows), encoding="utf-8")

        result = load_health_snapshots(tmp_path, 2026)

        assert len(result) == 2
        for entry in result:
            assert entry["date"].startswith("2026")

    def test_returns_empty_list_when_no_index(self, tmp_path):
        """Returns empty list if health/index.md does not exist."""
        result = load_health_snapshots(tmp_path, 2026)
        assert result == []

    def test_entry_has_date_key(self, tmp_path):
        """Each returned row has a 'date' key matching YYYY-MM-DD."""
        health_dir = tmp_path / "health"
        health_dir.mkdir(parents=True)
        rows = [_make_index_row("2026-03-10", hrv_ms=50.0)]
        (health_dir / "index.md").write_text(_make_index_md(rows), encoding="utf-8")

        result = load_health_snapshots(tmp_path, 2026)

        assert len(result) == 1
        assert result[0]["date"] == "2026-03-10"
        assert result[0]["hrv_ms"] == 50.0

    def test_returns_empty_list_when_no_rows_for_year(self, tmp_path):
        """Returns empty list when index exists but has no rows for the requested year."""
        health_dir = tmp_path / "health"
        health_dir.mkdir(parents=True)
        rows = [_make_index_row("2025-12-31", hrv_ms=40.0)]
        (health_dir / "index.md").write_text(_make_index_md(rows), encoding="utf-8")

        result = load_health_snapshots(tmp_path, 2026)
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
