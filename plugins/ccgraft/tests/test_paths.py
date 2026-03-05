"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for path normalization.
"""

from __future__ import annotations

from unittest.mock import patch

from ccgraft.paths import normalize_project_path, get_projects_dir


def test_normalize_unix_path():
    result = normalize_project_path("/Users/dev/my-project")
    assert result == "-Users-dev-my-project"


def test_normalize_dots_and_underscores():
    result = normalize_project_path("/Users/dev/my_project.v2")
    assert result == "-Users-dev-my-project-v2"


def test_normalize_strips_leading_slash():
    result = normalize_project_path("/home/user/code")
    assert "-home-user-code" in result


@patch("ccgraft.paths.os.name", "nt")
def test_normalize_windows_path():
    result = normalize_project_path("C:\\Users\\dev\\project")
    assert "C--Users-dev-project" == result
    assert not result.startswith("-")


def test_get_projects_dir():
    result = get_projects_dir()
    assert result.name == "projects"
    assert result.parent.name == ".claude"
