"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for bin/ wrapper scripts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


BIN_DIR = Path(__file__).resolve().parent.parent / "bin"


def test_export_script_exists():
    assert (BIN_DIR / "ccgraft-export").exists()


def test_import_script_exists():
    assert (BIN_DIR / "ccgraft-import").exists()


def test_restore_script_exists():
    assert (BIN_DIR / "ccgraft-restore").exists()


def test_export_script_help():
    result = subprocess.run(
        ["bash", str(BIN_DIR / "ccgraft-export"), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Export a Claude Code session" in result.stdout


def test_import_script_help():
    result = subprocess.run(
        ["bash", str(BIN_DIR / "ccgraft-import"), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Import an exported Claude Code session" in result.stdout


def test_restore_script_help():
    result = subprocess.run(
        ["bash", str(BIN_DIR / "ccgraft-restore"), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Restore a pre-import snapshot" in result.stdout


def test_scripts_work_without_execute_permission(tmp_path: Path):
    script = BIN_DIR / "ccgraft-export"
    result = subprocess.run(
        ["bash", str(script), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
