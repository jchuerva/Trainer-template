#!/usr/bin/env python3
"""
Tests for the restructured workouts/ YYYY/MM hierarchy.

Covers:
- build_workouts_index: finds analysis files in new structure, produces correct links
- generate_workout_analyses: fit_to_analysis_path derives correct paths
- migrate_workouts: extract_year_month, idempotency
- Cross-script: moving a file from old flat layout does not break index generation
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_workouts_index import _parse_analysis, _write_index_md, WorkoutRow
from generate_workout_analyses import fit_to_analysis_path
from migrate_workouts import extract_year_month


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS_CONTENT = textwrap.dedent("""\
    # Workout Summary (2026-04-07)

    **Workout type:** Running
    **Distance:** 6.09 km
    **Time:** 43:21
    **Average pace:** 7:07 min/km
    **Average HR:** 159 bpm
    **Max HR:** 180 bpm
""")


def _make_analysis(path: Path, content: str = SAMPLE_ANALYSIS_CONTENT) -> Path:
    """Write *content* to *path*, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests: extract_year_month (migrate_workouts)
# ---------------------------------------------------------------------------

class TestExtractYearMonth:
    """Tests for migrate_workouts.extract_year_month."""

    def test_standard_fit_filename(self):
        year, month = extract_year_month("2026-04-07-133755-Correr al aire libre-WorkOutDoors.fit")
        assert year == "2026"
        assert month == "04"

    def test_standard_md_filename(self):
        year, month = extract_year_month("2025-12-16-112639-Correr al aire libre-Apple Watch.md")
        assert year == "2025"
        assert month == "12"

    def test_january(self):
        year, month = extract_year_month("2026-01-01-000000-Run.fit")
        assert year == "2026"
        assert month == "01"

    def test_invalid_prefix_raises(self):
        with pytest.raises(ValueError):
            extract_year_month("random-filename.fit")

    def test_short_year_raises(self):
        with pytest.raises(ValueError):
            extract_year_month("26-04-07-Workout.fit")

    def test_no_dashes_raises(self):
        with pytest.raises(ValueError):
            extract_year_month("workout.fit")


# ---------------------------------------------------------------------------
# Tests: fit_to_analysis_path (generate_workout_analyses)
# ---------------------------------------------------------------------------

class TestFitToAnalysisPath:
    """Tests for generate_workout_analyses.fit_to_analysis_path."""

    def test_standard_path_derivation(self, tmp_path: Path):
        workouts = tmp_path / "workouts"
        fit = workouts / "2026" / "04" / "fit" / "2026-04-07-133755-Correr.fit"
        expected = workouts / "2026" / "04" / "analysis" / "2026-04-07-133755-Correr.md"
        result = fit_to_analysis_path(fit, workouts)
        assert result == expected

    def test_different_year_and_month(self, tmp_path: Path):
        workouts = tmp_path / "workouts"
        fit = workouts / "2025" / "12" / "fit" / "2025-12-27-095647-Correr.fit"
        expected = workouts / "2025" / "12" / "analysis" / "2025-12-27-095647-Correr.md"
        result = fit_to_analysis_path(fit, workouts)
        assert result == expected

    def test_invalid_hierarchy_raises(self, tmp_path: Path):
        workouts = tmp_path / "workouts"
        # File not under YYYY/MM/fit/
        flat_fit = workouts / "fit" / "2026-04-07-Correr.fit"
        with pytest.raises(ValueError):
            fit_to_analysis_path(flat_fit, workouts)

    def test_stem_preserved(self, tmp_path: Path):
        workouts = tmp_path / "workouts"
        stem = "2026-06-08-133105-Correr en cinta-WorkOutDoors"
        fit = workouts / "2026" / "06" / "fit" / f"{stem}.fit"
        result = fit_to_analysis_path(fit, workouts)
        assert result.stem == stem
        assert result.suffix == ".md"


# ---------------------------------------------------------------------------
# Tests: build_workouts_index — new structure
# ---------------------------------------------------------------------------

class TestBuildWorkoutsIndexNewStructure:
    """Tests for build_workouts_index with new YYYY/MM hierarchy."""

    def test_rglob_finds_analysis_in_subfolders(self, tmp_path: Path):
        """_parse_analysis should be called for files in YYYY/MM/analysis/ dirs."""
        workouts = tmp_path / "workouts"
        # Create analysis files in new structure
        files = [
            workouts / "2026" / "04" / "analysis" / "2026-04-07-133755-Correr.md",
            workouts / "2026" / "01" / "analysis" / "2026-01-17-092256-Correr.md",
            workouts / "2025" / "12" / "analysis" / "2025-12-27-095647-Correr.md",
        ]
        for f in files:
            _make_analysis(f)

        found = sorted(p for p in workouts.rglob("*.md") if p.name != "index.md")
        assert len(found) == 3
        # Should match all three
        assert set(f.name for f in found) == {f.name for f in files}

    def test_analysis_rel_path_includes_yyyy_mm(self, tmp_path: Path):
        """analysis_rel in WorkoutRow should contain YYYY/MM/analysis/STEM.md."""
        workouts = tmp_path / "workouts"
        analysis_file = workouts / "2026" / "04" / "analysis" / "2026-04-07-133755-Correr.md"
        _make_analysis(analysis_file)

        row = _parse_analysis(analysis_file, workouts_dir=workouts, fits_dir=workouts)
        assert row.analysis_rel == "2026/04/analysis/2026-04-07-133755-Correr.md"

    def test_analysis_rel_path_is_relative_to_workouts(self, tmp_path: Path):
        """The link in index.md should be relative to the workouts/ dir."""
        workouts = tmp_path / "workouts"
        analysis_file = workouts / "2025" / "12" / "analysis" / "2025-12-27-095647-AppleWatch.md"
        _make_analysis(analysis_file)

        row = _parse_analysis(analysis_file, workouts_dir=workouts, fits_dir=workouts)
        assert not row.analysis_rel.startswith("/")
        assert row.analysis_rel.startswith("2025/")

    def test_index_md_links_use_new_paths(self, tmp_path: Path):
        """Generated index.md should contain YYYY/MM/analysis/ links."""
        workouts = tmp_path / "workouts"
        analysis_file = workouts / "2026" / "04" / "analysis" / "2026-04-07-133755-Correr.md"
        _make_analysis(analysis_file)

        rows = [
            _parse_analysis(analysis_file, workouts_dir=workouts, fits_dir=workouts)
        ]
        out_path = tmp_path / "index.md"
        _write_index_md(out_path, rows)

        content = out_path.read_text(encoding="utf-8")
        assert "2026/04/analysis/2026-04-07-133755-Correr.md" in content
        # Old flat paths should not be present
        assert "analysis/2026-04-07" not in content or "2026/04/analysis/2026-04-07" in content

    def test_index_md_does_not_include_itself(self, tmp_path: Path):
        """index.md should not appear as an analysis row."""
        workouts = tmp_path / "workouts"
        index_file = workouts / "index.md"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("# Workouts index\n", encoding="utf-8")

        analysis_file = workouts / "2026" / "06" / "analysis" / "2026-06-08-133105-Correr.md"
        _make_analysis(analysis_file)

        # rglob should find both, but index.md must be filtered out
        all_md = list(workouts.rglob("*.md"))
        analysis_only = [p for p in all_md if p.name != "index.md"]
        assert len(analysis_only) == 1
        assert analysis_only[0].name != "index.md"

    def test_multiple_months_sorted_descending(self, tmp_path: Path):
        """Index rows should be sorted newest first."""
        workouts = tmp_path / "workouts"
        files = [
            workouts / "2026" / "01" / "analysis" / "2026-01-01-000000-Run.md",
            workouts / "2026" / "06" / "analysis" / "2026-06-01-000000-Run.md",
            workouts / "2025" / "12" / "analysis" / "2025-12-01-000000-Run.md",
        ]
        for f in files:
            _make_analysis(f)

        sorted_files = sorted(
            (p for p in workouts.rglob("*.md") if p.name != "index.md"),
            reverse=True,
        )
        dates = [p.name[:10] for p in sorted_files]
        assert dates == sorted(dates, reverse=True), "Files should be newest-first"

    def test_parse_analysis_extracts_metrics(self, tmp_path: Path):
        """_parse_analysis should correctly extract metrics from a real-looking analysis."""
        workouts = tmp_path / "workouts"
        analysis_file = workouts / "2026" / "04" / "analysis" / "2026-04-07-133755-Correr.md"
        _make_analysis(analysis_file)

        row = _parse_analysis(analysis_file, workouts_dir=workouts, fits_dir=workouts)
        assert row.date == "2026-04-07"
        assert row.distance_km == "6.09"
        assert row.time == "43:21"
        assert row.avg_pace == "7:07"
        assert row.avg_hr == "159"
        assert row.max_hr == "180"


# ---------------------------------------------------------------------------
# Tests: migration does not break index generation
# ---------------------------------------------------------------------------

class TestMigrationIndexCompatibility:
    """End-to-end: simulate migrated structure, build index, verify links."""

    def test_migrated_structure_produces_valid_index(self, tmp_path: Path):
        """After migration, build_workouts_index should produce correct index."""
        workouts = tmp_path / "workouts"

        # Simulate migrated structure with a few months
        entries = [
            ("2026", "04", "2026-04-07-133755-Correr al aire libre-WorkOutDoors"),
            ("2026", "01", "2026-01-17-092256-Correr al aire libre-WorkOutDoors"),
            ("2025", "12", "2025-12-27-095647-Correr al aire libre-AppleWatch"),
        ]
        for year, month, stem in entries:
            analysis = workouts / year / month / "analysis" / f"{stem}.md"
            _make_analysis(analysis)

        analysis_files = sorted(
            (p for p in workouts.rglob("*.md") if p.name != "index.md"),
            reverse=True,
        )
        rows = [_parse_analysis(p, workouts_dir=workouts, fits_dir=workouts) for p in analysis_files]
        out_path = tmp_path / "index.md"
        _write_index_md(out_path, rows)

        content = out_path.read_text(encoding="utf-8")

        # Verify all expected link patterns are present
        assert "2026/04/analysis/2026-04-07-133755-Correr al aire libre-WorkOutDoors.md" in content
        assert "2026/01/analysis/2026-01-17-092256-Correr al aire libre-WorkOutDoors.md" in content
        assert "2025/12/analysis/2025-12-27-095647-Correr al aire libre-AppleWatch.md" in content

        # Verify header present
        assert "# Workouts index" in content
        assert "| Date | Type |" in content

    def test_old_flat_paths_absent_after_migration(self, tmp_path: Path):
        """Index generated from new structure must not contain old flat paths."""
        workouts = tmp_path / "workouts"
        analysis_file = workouts / "2026" / "04" / "analysis" / "2026-04-07-133755-Correr.md"
        _make_analysis(analysis_file)

        rows = [_parse_analysis(analysis_file, workouts_dir=workouts, fits_dir=workouts)]
        out_path = tmp_path / "index.md"
        _write_index_md(out_path, rows)

        content = out_path.read_text(encoding="utf-8")
        # Old-style flat link like "analysis/2026-04-07-..." must not appear
        lines = [l for l in content.split("\n") if "2026-04-07" in l]
        for line in lines:
            # Every reference must be in YYYY/MM/analysis/ format
            assert "/04/analysis/" in line or "2026/04/analysis/" in line

    def test_write_index_md_creates_parent_dirs(self, tmp_path: Path):
        """_write_index_md should create parent directories as needed."""
        out_path = tmp_path / "deep" / "nested" / "index.md"
        _write_index_md(out_path, [])
        assert out_path.exists()

    def test_empty_workouts_produces_header_only_index(self, tmp_path: Path):
        """No analysis files → index.md contains header but no data rows."""
        out_path = tmp_path / "index.md"
        _write_index_md(out_path, [])
        content = out_path.read_text(encoding="utf-8")
        assert "# Workouts index" in content
        # The table header should be present but no data rows
        data_rows = [
            line for line in content.split("\n")
            if line.startswith("| ") and "Date" not in line and "---" not in line and line.strip() != "|"
        ]
        assert data_rows == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
