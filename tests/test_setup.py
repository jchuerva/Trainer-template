#!/usr/bin/env python3
"""
Tests for setup.py
"""

from pathlib import Path
import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from setup import format_training_status


class TestFormatTrainingStatus:
    """Tests for the format_training_status function."""

    def test_active_status_no_note_returns_none(self):
        """Active status with no note should return None (no section needed)."""
        config = {
            "training_status": {
                "status": "active"
            }
        }
        result = format_training_status(config)
        assert result is None

    def test_active_status_with_note_returns_section(self):
        """Active status with a note should return a section."""
        config = {
            "training_status": {
                "status": "active",
                "note": "Feeling great this week!"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Training Status" in result
        assert "Feeling great this week!" in result

    def test_sick_status(self):
        """Sick status should return correct section with emoji and guidance."""
        config = {
            "training_status": {
                "status": "sick"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Training Status" in result
        assert "Sick" in result
        assert "rest" in result.lower() or "recovery" in result.lower()

    def test_sick_status_with_note(self):
        """Sick status with note should include the note."""
        config = {
            "training_status": {
                "status": "sick",
                "note": "Cold since Monday, fever gone"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Cold since Monday, fever gone" in result
        assert "Sick" in result

    def test_injury_status(self):
        """Injury status should return correct section."""
        config = {
            "training_status": {
                "status": "injury"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Training Status" in result
        assert "Injury" in result
        assert "injured" in result.lower()

    def test_injury_status_with_note(self):
        """Injury status with note should include details."""
        config = {
            "training_status": {
                "status": "injury",
                "note": "Left knee pain, doing PT"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Left knee pain, doing PT" in result

    def test_holidays_status(self):
        """Holidays status should return correct section."""
        config = {
            "training_status": {
                "status": "holidays"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Training Status" in result
        assert "Holidays" in result
        assert "flexible" in result.lower() or "lighter" in result.lower()

    def test_returning_status(self):
        """Returning status should return correct section with ramp-up guidance."""
        config = {
            "training_status": {
                "status": "returning"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "Training Status" in result
        assert "Returning" in result
        assert "gradual" in result.lower() or "ramp" in result.lower() or "50" in result

    def test_missing_training_status_section(self):
        """Config without training_status section should return None."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15"
            }
        }
        result = format_training_status(config)
        assert result is None

    def test_empty_training_status_section(self):
        """Empty training_status section should return None (defaults to active)."""
        config = {
            "training_status": {}
        }
        result = format_training_status(config)
        assert result is None

    def test_section_markers_present(self):
        """Output should contain proper HTML comment markers."""
        config = {
            "training_status": {
                "status": "sick"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "<!-- TRAINING STATUS -->" in result
        assert "<!-- END TRAINING STATUS -->" in result

    def test_status_emoji_mapping(self):
        """Each status should have appropriate emoji."""
        statuses = {
            'sick': '🤒',
            'injury': '🩹',
            'holidays': '🏖️',
            'returning': '🔄'
        }
        
        for status, expected_emoji in statuses.items():
            config = {
                "training_status": {
                    "status": status
                }
            }
            result = format_training_status(config)
            assert result is not None
            assert expected_emoji in result, f"Expected emoji {expected_emoji} for status {status}"

    def test_note_formatting(self):
        """Note should be properly formatted with bold label."""
        config = {
            "training_status": {
                "status": "injury",
                "note": "Achilles tendon issue"
            }
        }
        result = format_training_status(config)
        assert result is not None
        assert "**Note:**" in result
        assert "Achilles tendon issue" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
