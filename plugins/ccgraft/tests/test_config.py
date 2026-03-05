"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for project config collection.
"""

from __future__ import annotations

from pathlib import Path

from ccgraft.config import collect_config


def test_collect_config_empty(tmp_path: Path):
    project = tmp_path / "empty-project"
    project.mkdir()
    config = collect_config(project)
    assert config.is_empty


def test_collect_config_with_files(tmp_project: Path):
    config = collect_config(tmp_project)
    assert config.settings is not None
    assert config.claude_md is not None
    assert not config.is_empty


def test_collect_config_commands(tmp_project: Path):
    cmd_dir = tmp_project / ".claude" / "commands"
    cmd_dir.mkdir()
    (cmd_dir / "test.md").write_text("# Test", encoding="utf-8")

    config = collect_config(tmp_project)
    assert len(config.commands) == 1
    assert config.commands[0].name == "test.md"


def test_collect_config_skills_and_agents(tmp_project: Path):
    skills_dir = tmp_project / ".claude" / "skills" / "my-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    agents_dir = tmp_project / ".claude" / "agents"
    agents_dir.mkdir()
    (agents_dir / "example.md").write_text("# Agent", encoding="utf-8")

    config = collect_config(tmp_project)
    assert len(config.skills) == 1
    assert config.skills[0].name == "SKILL.md"
    assert len(config.agents) == 1


def test_to_relative_paths(tmp_project: Path):
    config = collect_config(tmp_project)
    rel = config.to_relative_paths()
    assert rel["settings"] == "config/settings.json"
    assert rel["claude_md"] == "config/CLAUDE.md"


def test_write_to(tmp_project: Path, tmp_path: Path):
    config = collect_config(tmp_project)
    target = tmp_path / "export-config"
    target.mkdir()
    config.write_to(target)

    assert (target / "settings.json").exists()
    assert (target / "CLAUDE.md").exists()
    assert (target / "commands").is_dir()
