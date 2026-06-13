#!/usr/bin/env python3
"""Shared utilities for running-trainer scripts."""

from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root directory (two levels up from this file)."""
    return Path(__file__).parent.parent


def get_config_path() -> Path:
    """Get the path to config/config.yaml."""
    return get_repo_root() / "config" / "config.yaml"


def get_schema_path() -> Path:
    """Get the path to config/config.schema.json."""
    return get_repo_root() / "config" / "config.schema.json"


def get_penalties_path() -> Path:
    """Get the path to the run-or-pay penalties data file."""
    return get_repo_root() / "config" / "data" / "penalties.yaml"


# Running workout classification keywords
RUNNING_KEYWORDS: frozenset[str] = frozenset([
    'running', 'run', 'carrera', 'correr',
])

NON_RUNNING_KEYWORDS: frozenset[str] = frozenset([
    'walk', 'cycling', 'swim', 'swimming', 'strength', 'yoga', 'gym',
    'elliptical', 'rowing', 'bike',
    'andar', 'caminar', 'entreno funcional', 'entreno cruzado', 'cross training',
])
