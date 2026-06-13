#!/usr/bin/env python3
"""Tests for shared script utilities."""

from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import generate_weekly_plan_prompt
import run_or_pay
import setup
import validate_config
from utils import get_repo_root, get_config_path, get_schema_path, get_penalties_path


class TestGetRepoRoot:
    """Tests for the shared get_repo_root function."""

    def test_returns_repository_root(self):
        """Should resolve to repository root from scripts/utils.py."""
        expected = Path(__file__).parent.parent
        assert get_repo_root() == expected

    def test_scripts_use_shared_function(self):
        """Target scripts should import shared functions from utils."""
        # Scripts that still use get_repo_root directly
        assert run_or_pay.get_repo_root is get_repo_root
        assert setup.get_repo_root is get_repo_root
        assert generate_weekly_plan_prompt.get_repo_root is get_repo_root
        # validate_config uses get_config_path/get_schema_path (not get_repo_root directly)
        assert validate_config.get_config_path is get_config_path
        assert validate_config.get_schema_path is get_schema_path


class TestConfigPathHelpers:
    """Tests for centralized config path helpers."""

    def test_get_config_path_points_to_config_dir(self):
        """config.yaml should be under config/ subfolder."""
        path = get_config_path()
        assert path.parts[-2] == "config"
        assert path.name == "config.yaml"

    def test_get_schema_path_points_to_config_dir(self):
        """config.schema.json should be under config/ subfolder."""
        path = get_schema_path()
        assert path.parts[-2] == "config"
        assert path.name == "config.schema.json"

    def test_get_penalties_path_points_to_config_data_dir(self):
        """penalties.yaml should be under config/data/ subfolder."""
        path = get_penalties_path()
        assert path.parts[-3] == "config"
        assert path.parts[-2] == "data"
        assert path.name == "penalties.yaml"

    def test_all_helpers_are_under_repo_root(self):
        """All config paths should be children of the repo root."""
        repo_root = get_repo_root()
        assert get_config_path().is_relative_to(repo_root)
        assert get_schema_path().is_relative_to(repo_root)
        assert get_penalties_path().is_relative_to(repo_root)

    def test_config_and_schema_in_same_directory(self):
        """config.yaml and config.schema.json should live in the same directory."""
        assert get_config_path().parent == get_schema_path().parent

    def test_config_files_exist(self):
        """config.yaml and config.schema.json should actually exist in the repo."""
        assert get_config_path().exists(), "config/config.yaml not found"
        assert get_schema_path().exists(), "config/config.schema.json not found"

    def test_scripts_use_config_path_helper(self):
        """Scripts that load config should use the shared helper."""
        assert run_or_pay.get_config_path is get_config_path
        assert run_or_pay.get_penalties_path is get_penalties_path
        assert setup.get_config_path is get_config_path
        assert generate_weekly_plan_prompt.get_config_path is get_config_path

