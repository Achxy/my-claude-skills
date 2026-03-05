"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Project configuration snapshot collection.

Gathers Claude Code project configuration files (commands, skills, hooks,
agents, rules, settings, CLAUDE.md) for inclusion in session exports.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConfigSnapshot:
    """Collected project configuration files."""

    commands: list[Path] = field(default_factory=list)
    skills: list[Path] = field(default_factory=list)
    hooks: list[Path] = field(default_factory=list)
    agents: list[Path] = field(default_factory=list)
    rules: list[Path] = field(default_factory=list)
    settings: Path | None = None
    claude_md: Path | None = None

    @property
    def is_empty(self) -> bool:
        """True if no configuration files were found."""
        return (
            not self.commands
            and not self.skills
            and not self.hooks
            and not self.agents
            and not self.rules
            and self.settings is None
            and self.claude_md is None
        )

    def to_relative_paths(self) -> dict[str, list[str] | str | None]:
        """Return config file paths relative to the export config/ directory."""
        return {
            "commands": [f"config/commands/{f.name}" for f in self.commands],
            "skills": [f"config/skills/{f.name}" for f in self.skills],
            "hooks": [f"config/hooks/{f.name}" for f in self.hooks],
            "agents": [f"config/agents/{f.name}" for f in self.agents],
            "rules": [f"config/rules/{f.name}" for f in self.rules],
            "settings": "config/settings.json" if self.settings else None,
            "claude_md": "config/CLAUDE.md" if self.claude_md else None,
        }

    def write_to(self, config_dir: Path) -> None:
        """Copy all collected config files into an export config directory."""
        _copy_files_to_subdir(config_dir / "commands", self.commands)
        _copy_files_to_subdir(config_dir / "skills", self.skills)
        _copy_files_to_subdir(config_dir / "hooks", self.hooks)
        _copy_files_to_subdir(config_dir / "agents", self.agents)
        _copy_files_to_subdir(config_dir / "rules", self.rules)

        if self.settings:
            shutil.copy2(self.settings, config_dir / "settings.json")

        if self.claude_md:
            shutil.copy2(self.claude_md, config_dir / "CLAUDE.md")


def collect_config(project_path: Path) -> ConfigSnapshot:
    """Collect project configuration files from .claude/ and project root.

    Scans for commands, skills, hooks, agents, rules, settings.json,
    and CLAUDE.md in the expected locations.

    Args:
        project_path: Absolute path to the project directory.

    Returns:
        A ConfigSnapshot containing all discovered config files.
    """
    claude_dir = project_path / ".claude"
    snapshot = ConfigSnapshot()

    for commands_dir in [claude_dir / "commands", project_path / "commands"]:
        if commands_dir.exists():
            snapshot.commands.extend(sorted(commands_dir.glob("*.md")))

    _collect_glob(claude_dir / "skills", "**/SKILL.md", snapshot.skills)
    _collect_all_files(claude_dir / "hooks", snapshot.hooks)
    _collect_glob(claude_dir / "agents", "*.md", snapshot.agents)
    _collect_glob(claude_dir / "rules", "*.md", snapshot.rules)

    settings_file = claude_dir / "settings.json"
    if settings_file.exists():
        snapshot.settings = settings_file

    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        snapshot.claude_md = claude_md

    return snapshot


def _collect_glob(directory: Path, pattern: str, target: list[Path]) -> None:
    """Append matching files from a directory glob to a target list."""
    if directory.exists():
        target.extend(sorted(directory.glob(pattern)))


def _collect_all_files(directory: Path, target: list[Path]) -> None:
    """Append all files (not directories) from a directory to a target list."""
    if directory.exists():
        target.extend(sorted(f for f in directory.iterdir() if f.is_file()))


def _copy_files_to_subdir(target_dir: Path, files: list[Path]) -> None:
    """Create a subdirectory and copy files into it."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for src in files:
        shutil.copy2(src, target_dir / src.name)
