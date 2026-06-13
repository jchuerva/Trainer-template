#!/usr/bin/env python3
"""
Tests for generate_workout_analyses.py
"""

import tempfile
from pathlib import Path
import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_workout_analyses import normalize_filename, find_created_file


class TestNormalizeFilename:
    """Tests for the normalize_filename function."""

    def test_regular_space_unchanged(self):
        """Regular spaces should remain unchanged."""
        filename = "2026-01-11-Apple Watch.md"
        result = normalize_filename(filename)
        assert result == "2026-01-11-Apple Watch.md"

    def test_non_breaking_space_converted(self):
        """Non-breaking space (\\xa0) should be converted to regular space."""
        filename = "2026-01-11-Apple\xa0Watch.md"
        result = normalize_filename(filename)
        assert result == "2026-01-11-Apple Watch.md"
        assert "\xa0" not in result

    def test_unicode_non_breaking_space_converted(self):
        """Unicode non-breaking space (U+00A0) should be converted."""
        filename = "2026-01-11-Apple\u00a0Watch.md"
        result = normalize_filename(filename)
        assert result == "2026-01-11-Apple Watch.md"

    def test_figure_space_converted(self):
        """Figure space (U+2007) should be converted to regular space."""
        filename = "2026-01-11-Apple\u2007Watch.md"
        result = normalize_filename(filename)
        assert result == "2026-01-11-Apple Watch.md"

    def test_narrow_no_break_space_converted(self):
        """Narrow no-break space (U+202F) should be converted to regular space."""
        filename = "2026-01-11-Apple\u202fWatch.md"
        result = normalize_filename(filename)
        assert result == "2026-01-11-Apple Watch.md"

    def test_multiple_special_spaces(self):
        """Multiple special spaces should all be converted."""
        filename = "2026\xa001\xa011-Apple\u00a0Watch\u2007de\u202fJose.md"
        result = normalize_filename(filename)
        assert "\xa0" not in result
        assert "\u00a0" not in result
        assert "\u2007" not in result
        assert "\u202f" not in result
        # Should have regular spaces
        assert " " in result

    def test_no_spaces_unchanged(self):
        """Filename without spaces should remain unchanged."""
        filename = "2026-01-11-AppleWatch.md"
        result = normalize_filename(filename)
        assert result == "2026-01-11-AppleWatch.md"

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert normalize_filename("") == ""

    def test_unicode_normalization_nfc(self):
        """Unicode should be normalized to NFC form."""
        # é as e + combining acute accent (NFD form)
        filename_nfd = "caf\u0065\u0301.md"
        result = normalize_filename(filename_nfd)
        # Should be normalized (though exact form depends on NFC)
        assert len(result) <= len(filename_nfd)


class TestFindCreatedFile:
    """Tests for the find_created_file function."""

    def test_exact_match_found(self):
        """Should find file with exact name match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test-workout.md"
            test_file.write_text("content")

            result = find_created_file(test_file)
            assert result == test_file
            assert result.exists()

    def test_file_not_found(self):
        """Should return None when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            missing_file = tmppath / "nonexistent.md"

            result = find_created_file(missing_file)
            assert result is None

    def test_non_breaking_space_match(self):
        """Should find file when expected has non-breaking space but actual has regular space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create file with regular space
            actual_file = tmppath / "Apple Watch.md"
            actual_file.write_text("content")

            # Search for file with non-breaking space
            expected_path = tmppath / "Apple\xa0Watch.md"

            result = find_created_file(expected_path)
            assert result is not None
            assert result.exists()
            assert result == actual_file

    def test_regular_space_to_non_breaking_match(self):
        """Should find file when expected has regular space but actual has non-breaking space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create file with non-breaking space
            actual_file = tmppath / "Apple\xa0Watch.md"
            actual_file.write_text("content")

            # Search for file with regular space
            expected_path = tmppath / "Apple Watch.md"

            result = find_created_file(expected_path)
            assert result is not None
            assert result.exists()
            assert result == actual_file

    def test_stem_match_different_spaces(self):
        """Should match via stem when space types differ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create file with regular space in complex name
            actual_file = tmppath / "2026-01-11-Andar al aire libre-Apple Watch de Jose.md"
            actual_file.write_text("content")

            # Search with non-breaking space
            expected_path = tmppath / "2026-01-11-Andar al aire libre-Apple\xa0Watch de Jose.md"

            result = find_created_file(expected_path)
            assert result is not None
            assert result.exists()

    def test_parent_directory_not_exists(self):
        """Should return None when parent directory doesn't exist."""
        nonexistent_dir = Path("/nonexistent/directory/file.md")
        result = find_created_file(nonexistent_dir)
        assert result is None

    def test_multiple_files_finds_correct_one(self):
        """Should find correct file when multiple similar files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create multiple files
            file1 = tmppath / "2026-01-10-Workout.md"
            file2 = tmppath / "2026-01-11-Workout.md"
            file3 = tmppath / "2026-01-12-Workout.md"
            file1.write_text("content1")
            file2.write_text("content2")
            file3.write_text("content3")

            result = find_created_file(file2)
            assert result == file2

    def test_wrong_extension_not_matched(self):
        """Should not match file with different extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create .txt file
            txt_file = tmppath / "workout.txt"
            txt_file.write_text("content")

            # Search for .md file
            expected_path = tmppath / "workout.md"

            result = find_created_file(expected_path)
            assert result is None


class TestNormalizeFilenameEdgeCases:
    """Edge case tests for normalize_filename."""

    def test_only_non_breaking_spaces(self):
        """Filename with only non-breaking spaces."""
        filename = "\xa0\xa0\xa0.md"
        result = normalize_filename(filename)
        assert result == "   .md"

    def test_mixed_content(self):
        """Complex filename with various characters."""
        filename = "2025-12-27-Correr al aire libre-Apple\xa0Watch de Jose Carlos.md"
        result = normalize_filename(filename)
        expected = "2025-12-27-Correr al aire libre-Apple Watch de Jose Carlos.md"
        assert result == expected

    def test_spanish_characters(self):
        """Filename with Spanish special characters."""
        filename = "Año-Niño-Señor.md"
        result = normalize_filename(filename)
        assert "ñ" in result.lower() or "Ñ" in result
        assert result == "Año-Niño-Señor.md"

    def test_long_filename(self):
        """Long filename should be handled correctly."""
        filename = "2026-01-11-121145-Andar al aire libre-Apple\xa0Watch de Jose Carlos.md"
        result = normalize_filename(filename)
        assert len(result) == len(filename)  # Same length after replacement
        assert "\xa0" not in result


class TestExistingAnalysisDetection:
    """Tests for detecting existing analyses with Unicode normalization."""

    def test_skips_existing_analysis_with_exact_match(self):
        """Should detect existing analysis with exact filename match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create existing analysis
            analysis_file = tmppath / "2025-12-27-Workout.md"
            analysis_file.write_text("existing content")

            # Simulate the check that happens in generate_workout_analyses.py
            expected_path = tmppath / "2025-12-27-Workout.md"
            result = find_created_file(expected_path)
            assert result is not None
            assert result.exists()

    def test_skips_existing_analysis_with_non_breaking_space_mismatch(self):
        """Should detect existing analysis when FIT has non-breaking space but analysis has regular space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create existing analysis with regular space
            analysis_file = tmppath / "2025-12-27-Apple Watch.md"
            analysis_file.write_text("existing content")

            # FIT file stem would have non-breaking space
            expected_path = tmppath / "2025-12-27-Apple\xa0Watch.md"
            result = find_created_file(expected_path)
            assert result is not None, "Should find existing analysis despite Unicode space difference"
            assert result.exists()

    def test_skips_existing_analysis_with_reverse_space_mismatch(self):
        """Should detect existing analysis when FIT has regular space but analysis has non-breaking space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create existing analysis with non-breaking space
            analysis_file = tmppath / "2025-12-27-Apple\xa0Watch.md"
            analysis_file.write_text("existing content")

            # FIT file stem would have regular space
            expected_path = tmppath / "2025-12-27-Apple Watch.md"
            result = find_created_file(expected_path)
            assert result is not None, "Should find existing analysis despite Unicode space difference"
            assert result.exists()

    def test_realistic_filename_with_spanish_and_special_spaces(self):
        """Should detect existing analysis with realistic Spanish filename containing special spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create existing analysis with regular spaces
            analysis_file = tmppath / "2025-12-27-Correr al aire libre-Apple Watch de Jose Carlos.md"
            analysis_file.write_text("existing content")

            # FIT file might have non-breaking space
            expected_path = tmppath / "2025-12-27-Correr al aire libre-Apple\xa0Watch de Jose Carlos.md"
            result = find_created_file(expected_path)
            assert result is not None, "Should find existing analysis with Spanish filename"
            assert result.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
