#!/usr/bin/env python3
"""
Tests for validate_config.py
"""

from pathlib import Path
import pytest
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_config import validate_config, format_validation_error

# Load the schema once for all tests
import json
SCHEMA_PATH = Path(__file__).parent.parent / "config" / "config.schema.json"
with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
    SCHEMA = json.load(f)


class TestValidateConfig:
    """Tests for the validate_config function."""

    def test_valid_config_passes(self):
        """A valid config should return no errors."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 75,
                "height": 180
            },
            "preferences": {
                "run_days": ["Tuesday", "Thursday", "Saturday"],
                "long_run_day": "Saturday",
                "weekly_runs": 3
            },
            "current_goal": {
                "file": "config/goals/2026-marathon.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) == 0

    def test_valid_config_with_training_status(self):
        """A valid config with training_status should return no errors."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 75,
                "height": 180
            },
            "preferences": {
                "run_days": ["Tuesday", "Thursday", "Saturday"],
                "long_run_day": "Saturday",
                "weekly_runs": 3
            },
            "current_goal": {
                "file": "config/goals/2026-marathon.md"
            },
            "training_status": {
                "status": "sick",
                "note": "Cold since Monday"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) == 0

    def test_missing_athlete_section(self):
        """Missing athlete section should be caught."""
        config = {
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0
        error_messages = [format_validation_error(e) for e in errors]
        assert any("athlete" in msg.lower() for msg in error_messages)

    def test_missing_required_athlete_field(self):
        """Missing required field in athlete should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                # missing weight and height
            },
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0

    def test_invalid_date_format(self):
        """Invalid date format should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "15/01/1990",  # Wrong format
                "weight": 75,
                "height": 180
            },
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0
        error_messages = [format_validation_error(e) for e in errors]
        assert any("pattern" in msg.lower() or "format" in msg.lower() for msg in error_messages)

    def test_invalid_status_value(self):
        """Invalid training status value should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 75,
                "height": 180
            },
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "training_status": {
                "status": "invalid_status"  # Not in enum
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0
        error_messages = [format_validation_error(e) for e in errors]
        assert any("invalid" in msg.lower() or "enum" in msg.lower() or "allowed" in msg.lower() for msg in error_messages)

    def test_weight_below_minimum(self):
        """Weight below minimum should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 20,  # Below minimum of 30
                "height": 180
            },
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0
        error_messages = [format_validation_error(e) for e in errors]
        assert any("minimum" in msg.lower() or "below" in msg.lower() or "low" in msg.lower() for msg in error_messages)

    def test_height_above_maximum(self):
        """Height above maximum should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 75,
                "height": 300  # Above maximum of 250
            },
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0
        error_messages = [format_validation_error(e) for e in errors]
        assert any("maximum" in msg.lower() or "above" in msg.lower() or "high" in msg.lower() for msg in error_messages)

    def test_invalid_day_in_run_days(self):
        """Invalid day value in run_days should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 75,
                "height": 180
            },
            "preferences": {
                "run_days": ["InvalidDay"],  # Not a valid day
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "config/goals/test.md"
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0

    def test_invalid_goal_file_path(self):
        """Goal file path not starting with goals/ should be caught."""
        config = {
            "athlete": {
                "date_of_birth": "1990-01-15",
                "weight": 75,
                "height": 180
            },
            "preferences": {
                "run_days": ["Tuesday"],
                "long_run_day": "Saturday",
                "weekly_runs": 1
            },
            "current_goal": {
                "file": "invalid/path.md"  # Not in goals/ directory
            },
            "copilot": {
                "model": "gpt-4"
            }
        }
        errors = validate_config(config, SCHEMA)
        assert len(errors) > 0


class TestFormatValidationError:
    """Tests for the format_validation_error function."""

    def test_format_required_error(self):
        """Required field error should be formatted nicely."""
        # Create a mock error-like object
        class MockError:
            def __init__(self):
                self.absolute_path = ['athlete']
                self.validator = 'required'
                self.validator_value = ['weight', 'height']
                self.instance = {}
                self.message = "is a required property"
        
        error = MockError()
        result = format_validation_error(error)
        assert "athlete" in result
        assert "weight" in result or "height" in result
        assert "required" in result.lower() or "missing" in result.lower()

    def test_format_enum_error(self):
        """Enum error should show allowed values."""
        class MockError:
            def __init__(self):
                self.absolute_path = ['training_status', 'status']
                self.validator = 'enum'
                self.validator_value = ['active', 'sick', 'injury', 'holidays', 'returning']
                self.instance = 'invalid'
                self.message = "is not one of"

    def test_format_pattern_error(self):
        """Pattern error should mention format."""
        class MockError:
            def __init__(self):
                self.absolute_path = ['athlete', 'date_of_birth']
                self.validator = 'pattern'
                self.validator_value = '^\\d{4}-\\d{2}-\\d{2}$'
                self.instance = '15/01/1990'
                self.message = "does not match"
        
        error = MockError()
        result = format_validation_error(error)
        assert "format" in result.lower() or "pattern" in result.lower()
        assert "15/01/1990" in result

    def test_format_minimum_error(self):
        """Minimum value error should show the limit."""
        class MockError:
            def __init__(self):
                self.absolute_path = ['athlete', 'weight']
                self.validator = 'minimum'
                self.validator_value = 30
                self.instance = 20
                self.message = "is less than minimum"
        
        error = MockError()
        result = format_validation_error(error)
        assert "20" in result
        assert "30" in result
        assert "low" in result.lower() or "minimum" in result.lower() or "below" in result.lower()

    def test_format_maximum_error(self):
        """Maximum value error should show the limit."""
        class MockError:
            def __init__(self):
                self.absolute_path = ['athlete', 'height']
                self.validator = 'maximum'
                self.validator_value = 250
                self.instance = 300
                self.message = "is greater than maximum"
        
        error = MockError()
        result = format_validation_error(error)
        assert "300" in result
        assert "250" in result
        assert "high" in result.lower() or "maximum" in result.lower() or "above" in result.lower()

    def test_format_type_error(self):
        """Type error should show expected vs actual type."""
        class MockError:
            def __init__(self):
                self.absolute_path = ['athlete', 'weight']
                self.validator = 'type'
                self.validator_value = 'number'
                self.instance = "seventy five"
                self.message = "is not of type 'number'"
        
        error = MockError()
        result = format_validation_error(error)
        assert "number" in result
        assert "str" in result
        assert "type" in result.lower()

    def test_format_generic_error(self):
        """Generic error should still produce output."""
        class MockError:
            def __init__(self):
                self.absolute_path = ['some', 'path']
                self.validator = 'unknown_validator'
                self.validator_value = 'some_value'
                self.instance = 'some_instance'
                self.message = "Some error message"
        
        error = MockError()
        result = format_validation_error(error)
        assert "Some error message" in result
        assert "some -> path" in result

    def test_format_root_level_error(self):
        """Root level error (no path) should be handled."""
        class MockError:
            def __init__(self):
                self.absolute_path = []  # Empty path = root
                self.validator = 'required'
                self.validator_value = ['athlete']
                self.instance = {}
                self.message = "'athlete' is a required property"
        
        error = MockError()
        result = format_validation_error(error)
        assert "root" in result
        assert "athlete" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
