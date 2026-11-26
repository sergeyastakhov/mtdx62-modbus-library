"""The version the package reports matches the one it is published under."""

from __future__ import annotations

import tomllib
from pathlib import Path

import mtdx62_modbus_library


def test_version_matches_pyproject() -> None:
    """0.4.1 was published with __version__ still saying 0.4.0; never again."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]

    assert mtdx62_modbus_library.__version__ == declared
