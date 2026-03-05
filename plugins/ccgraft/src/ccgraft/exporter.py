"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Session export orchestration.

Coordinates the full export pipeline: session discovery, metadata
extraction, artifact collection, rendering, and manifest creation.
"""

from __future__ import annotations

import getpass
import json
import logging
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from xml.dom import minidom

from ._io import atomic_write_text
from .config import ConfigSnapshot, collect_config
from .errors import ExportError
from .manifest import Manifest, OriginalContext, SessionData
from .paths import get_project_session_dir
from .session import SessionInfo, read_messages

log = logging.getLogger("ccgraft")


@dataclass
class SessionMetadata:
    """Aggregated statistics from a parsed session."""

    session_id: str = ""
    project_dir: str = ""
    start_time: str = ""
    end_time: str = ""
    total_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tool_uses: int = 0
    models_used: list[str] = field(default_factory=list)
    claude_code_version: str = ""
    git_branch: str = ""
    slug: str = ""


def extract_metadata(messages: list[dict]) -> SessionMetadata:
    """Extract aggregated metadata from a list of session messages.

    Scans every message to collect session ID, timestamps, message
    counts, tool usage, model names, version, and git branch.
    """
    meta = SessionMetadata()
    models: set[str] = set()

    for msg in messages:
        if not meta.session_id and "sessionId" in msg:
            meta.session_id = msg["sessionId"]
        if not meta.project_dir and "cwd" in msg:
            meta.project_dir = msg["cwd"]
        if not meta.claude_code_version and "version" in msg:
            meta.claude_code_version = msg["version"]
        if not meta.git_branch and "gitBranch" in msg:
            meta.git_branch = msg["gitBranch"]
        if not meta.slug and "slug" in msg:
            meta.slug = msg["slug"]

        ts = msg.get("timestamp", "")
        if ts:
            if not meta.start_time or ts < meta.start_time:
                meta.start_time = ts
            if not meta.end_time or ts > meta.end_time:
                meta.end_time = ts

        inner = msg.get("message", {})
        role = inner.get("role", "")
        if role == "user":
            meta.user_messages += 1
        elif role == "assistant":
            meta.assistant_messages += 1
            model = inner.get("model", "")
            if model:
                models.add(model)

        for block in inner.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                meta.tool_uses += 1

    meta.total_messages = len(messages)
    meta.models_used = sorted(models)
    return meta


def compute_duration_seconds(meta: SessionMetadata) -> int | None:
    """Calculate session duration from start/end timestamps."""
    if not meta.start_time or not meta.end_time:
        return None
    try:
        start = datetime.fromisoformat(meta.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(meta.end_time.replace("Z", "+00:00"))
        return int((end - start).total_seconds())
    except (ValueError, TypeError):
        return None


@dataclass
class SessionArtifacts:
    """Collected session-related files beyond the main JSONL."""

    agent_sessions: dict[str, Path] = field(default_factory=dict)
    file_history: list[Path] = field(default_factory=list)
    plan_file: Path | None = None
    todos: list[Path] = field(default_factory=list)
    session_env: Path | None = None


def collect_artifacts(
    project_path: Path,
    session_id: str,
    messages: list[dict],
    slug: str,
) -> SessionArtifacts:
    """Collect all session artifacts (agents, file history, plan, todos, env).

    Args:
        project_path: Absolute path to the project directory.
        session_id: The session's unique identifier.
        messages: Parsed messages from the main session.
        slug: Session slug for plan file lookup.
    """
    artifacts = SessionArtifacts()
    artifacts.agent_sessions = _collect_agent_sessions(project_path, session_id, messages)
    artifacts.file_history = _collect_file_history(session_id)
    artifacts.plan_file = _collect_plan_file(slug)
    artifacts.todos = _collect_todos(session_id)
    artifacts.session_env = _collect_session_env(session_id)
    return artifacts


def _collect_agent_sessions(
    project_path: Path, session_id: str, messages: list[dict]
) -> dict[str, Path]:
    """Find agent JSONL files referenced by the main session."""
    agent_ids: set[str] = set()
    for msg in messages:
        aid = msg.get("agentId", "")
        if aid and len(aid) == 7:
            agent_ids.add(aid)

    session_dir = get_project_session_dir(project_path)
    if not session_dir.exists():
        return {}

    agents: dict[str, Path] = {}
    for agent_file in session_dir.glob("agent-*.jsonl"):
        aid = agent_file.stem.removeprefix("agent-")
        if aid not in agent_ids:
            continue
        try:
            with open(agent_file, "r", encoding="utf-8") as fh:
                first_line = fh.readline().strip()
                if first_line:
                    data = json.loads(first_line)
                    if data.get("sessionId") == session_id:
                        agents[aid] = agent_file
        except (json.JSONDecodeError, OSError):
            continue

    return agents


def _collect_file_history(session_id: str) -> list[Path]:
    """Collect file history snapshots for a session."""
    fh_dir = Path.home() / ".claude" / "file-history" / session_id
    if not fh_dir.exists():
        return []
    return sorted(f for f in fh_dir.iterdir() if f.is_file())


def _collect_plan_file(slug: str) -> Path | None:
    """Locate the plan file for a session by slug."""
    if not slug:
        return None
    plan = Path.home() / ".claude" / "plans" / f"{slug}.md"
    return plan if plan.exists() else None


def _collect_todos(session_id: str) -> list[Path]:
    """Collect todo JSON files for a session."""
    todos_dir = Path.home() / ".claude" / "todos"
    if not todos_dir.exists():
        return []
    return sorted(todos_dir.glob(f"{session_id}-*.json"))


def _collect_session_env(session_id: str) -> Path | None:
    """Locate the session environment directory if it has content."""
    env_dir = Path.home() / ".claude" / "session-env" / session_id
    if env_dir.exists() and any(env_dir.iterdir()):
        return env_dir
    return None


def build_manifest(
    meta: SessionMetadata,
    artifacts: SessionArtifacts,
    config: ConfigSnapshot,
    export_name: str,
    project_path: Path,
    anonymized: bool = False,
) -> Manifest:
    """Construct a Manifest from collected data."""
    sd = SessionData(
        main_session="session/main.jsonl",
        file_history=[f"session/file-history/{f.name}" for f in artifacts.file_history],
        todos="session/todos.json" if artifacts.todos else "",
        plan_file="session/plan.md" if artifacts.plan_file else "",
    )

    ctx = OriginalContext(
        user="" if anonymized else getpass.getuser(),
        platform=sys.platform,
        repo_path=str(project_path),
    )

    return Manifest(
        session_id=meta.session_id,
        session_slug=meta.slug,
        export_name=export_name,
        export_timestamp=datetime.now(timezone.utc).isoformat(),
        claude_code_version=meta.claude_code_version,
        session_data=sd,
        original_context=ctx,
        config_snapshot=config.to_relative_paths(),
    )


def write_session_dir(
    export_dir: Path,
    session_path: Path,
    artifacts: SessionArtifacts,
) -> None:
    """Write the session/ subdirectory of an export."""
    session_dir = export_dir / "session"
    session_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(session_path, session_dir / "main.jsonl")

    agents_dir = session_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    for aid, path in artifacts.agent_sessions.items():
        shutil.copy2(path, agents_dir / f"agent-{aid}.jsonl")

    fh_dir = session_dir / "file-history"
    fh_dir.mkdir(exist_ok=True)
    for fh in artifacts.file_history:
        shutil.copy2(fh, fh_dir / fh.name)

    if artifacts.plan_file:
        shutil.copy2(artifacts.plan_file, session_dir / "plan.md")

    if artifacts.todos:
        all_todos: list[dict] = []
        for todo_file in artifacts.todos:
            try:
                raw = json.loads(todo_file.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    all_todos.extend(raw)
                else:
                    all_todos.append(raw)
            except (json.JSONDecodeError, OSError):
                continue
        atomic_write_text(
            session_dir / "todos.json",
            json.dumps(all_todos, indent=2),
        )

    if artifacts.session_env:
        env_dir = session_dir / "session-env"
        env_dir.mkdir(exist_ok=True)
        for f in artifacts.session_env.iterdir():
            if f.is_file():
                shutil.copy2(f, env_dir / f.name)


@dataclass
class ExportResult:
    """Summary of a completed export operation."""

    export_dir: Path
    manifest: Manifest
    meta: SessionMetadata


def export_session(
    session: SessionInfo,
    project_path: Path,
    export_name: str,
    output_dir: Path | None = None,
    output_format: str = "all",
    anonymized: bool = False,
    in_repo: bool = True,
) -> ExportResult:
    """Run the full export pipeline for a session.

    Args:
        session: The session to export.
        project_path: Absolute path to the project directory.
        export_name: Human-readable name for the export folder.
        output_dir: Override the output directory. Defaults to
            ``<project>/.claude-sessions/`` (in-repo) or
            ``~/claude_sessions/exports/`` (legacy).
        output_format: Rendering format: ``'md'``, ``'xml'``, or ``'all'``.
        anonymized: If True, omit user identity from the manifest.
        in_repo: If True, export into the project repo.

    Returns:
        An ExportResult with the export directory, manifest, and metadata.
    """
    log.info("Reading session: %s", session.path.name)
    messages = read_messages(session.path)
    meta = extract_metadata(messages)

    if not meta.session_id:
        meta.session_id = session.session_id
    if not meta.slug:
        meta.slug = session.slug

    if not messages:
        raise ExportError("Session contains no messages.")

    export_dir = _resolve_export_dir(
        project_path, export_name, output_dir, in_repo, meta.session_id
    )
    export_dir.mkdir(parents=True, exist_ok=True)

    log.info("Collecting artifacts...")
    artifacts = collect_artifacts(project_path, meta.session_id, messages, meta.slug)
    config = collect_config(project_path)

    manifest = build_manifest(meta, artifacts, config, export_name, project_path, anonymized)

    log.info("Writing session data...")
    write_session_dir(export_dir, session.path, artifacts)
    config.write_to(export_dir / "config")
    manifest.write(export_dir)

    if output_format in ("md", "all"):
        rendered = render_markdown(messages, meta, manifest)
        atomic_write_text(export_dir / "RENDERED.md", rendered)

    if output_format in ("xml", "all"):
        xml_str = render_xml(messages, meta)
        atomic_write_text(export_dir / "conversation.xml", xml_str)

    return ExportResult(export_dir=export_dir, manifest=manifest, meta=meta)


def _resolve_export_dir(
    project_path: Path,
    export_name: str,
    output_dir: Path | None,
    in_repo: bool,
    session_id: str,
) -> Path:
    """Determine the target directory for an export."""
    if output_dir:
        return output_dir / export_name

    if in_repo:
        return project_path / ".claude-sessions" / export_name

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return Path.home() / "claude_sessions" / "exports" / f"{timestamp}_{session_id[:8]}"


def render_markdown(
    messages: list[dict],
    meta: SessionMetadata,
    manifest: Manifest,
) -> str:
    """Render a GitHub-optimized markdown view of the session."""
    lines: list[str] = []
    lines.append(f"# Claude Code Session: {manifest.export_name}")
    lines.append("")

    lines.append("## Session Info")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Session ID | `{meta.session_id}` |")
    if meta.slug:
        lines.append(f"| Session Name | {meta.slug} |")
    lines.append(f"| Project | `{meta.project_dir}` |")
    if meta.git_branch:
        lines.append(f"| Git Branch | `{meta.git_branch}` |")
    if meta.claude_code_version:
        lines.append(f"| Claude Code | v{meta.claude_code_version} |")
    lines.append(f"| Messages | {meta.total_messages} |")
    lines.append(f"| Tool Uses | {meta.tool_uses} |")

    duration = compute_duration_seconds(meta)
    if duration is not None:
        lines.append(f"| Duration | {_format_duration(duration)} |")
    if meta.models_used:
        lines.append(f"| Models | {', '.join(meta.models_used)} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Conversation")
    lines.append("")

    for msg in messages:
        rendered = _format_message_md(msg)
        if rendered:
            lines.append(rendered)
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def _format_message_md(message_data: dict) -> str:
    """Format a single message as markdown."""
    if "message" not in message_data:
        return ""

    parts: list[str] = []
    msg = message_data["message"]
    ts = message_data.get("timestamp", "")

    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            parts.append(f"**[{dt.strftime('%Y-%m-%d %H:%M:%S')}]**")
        except ValueError:
            pass

    role = msg.get("role", "unknown")
    if role == "user":
        parts.append("\n### User\n")
    elif role == "assistant":
        model = msg.get("model", "")
        label = f" ({model})" if model else ""
        parts.append(f"\n### Assistant{label}\n")

    content = msg.get("content", "")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type", "")

            if block_type == "text":
                parts.append(block.get("text", ""))

            elif block_type == "thinking":
                parts.append("\n<details>")
                parts.append("<summary>Internal Reasoning (click to expand)</summary>\n")
                parts.append("```")
                parts.append(block.get("thinking", ""))
                parts.append("```")
                parts.append("</details>\n")

            elif block_type == "tool_use":
                name = block.get("name", "unknown")
                tid = block.get("id", "")
                parts.append(f"\n**Tool Use: {name}** (ID: {tid})")
                parts.append("```json")
                parts.append(json.dumps(block.get("input", {}), indent=2))
                parts.append("```\n")

            elif block_type == "tool_result":
                parts.append("\n**Tool Result:**")
                parts.append("```")
                result = block.get("content", "")
                text = result if isinstance(result, str) else str(result)
                if len(text) > 5000:
                    parts.append(text[:5000])
                    parts.append(f"\n... (truncated, {len(text) - 5000} chars omitted)")
                else:
                    parts.append(text)
                parts.append("```\n")

    return "\n".join(parts)


def _format_duration(seconds: int) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds > 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    if seconds > 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"


def _clean_xml_text(text: str) -> str:
    """Remove control characters that cause XML parsing issues."""
    if not text:
        return text
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)


def render_xml(messages: list[dict], meta: SessionMetadata) -> str:
    """Render the session as a pretty-printed XML document."""
    root = ET.Element("claude-session")

    meta_elem = ET.SubElement(root, "metadata")
    ET.SubElement(meta_elem, "session-id").text = meta.session_id
    ET.SubElement(meta_elem, "working-directory").text = meta.project_dir
    ET.SubElement(meta_elem, "start-time").text = meta.start_time
    ET.SubElement(meta_elem, "end-time").text = meta.end_time
    ET.SubElement(meta_elem, "export-time").text = datetime.now(timezone.utc).isoformat()

    stats = ET.SubElement(meta_elem, "statistics")
    ET.SubElement(stats, "total-messages").text = str(meta.total_messages)
    ET.SubElement(stats, "user-messages").text = str(meta.user_messages)
    ET.SubElement(stats, "assistant-messages").text = str(meta.assistant_messages)
    ET.SubElement(stats, "tool-uses").text = str(meta.tool_uses)
    models_elem = ET.SubElement(stats, "models-used")
    for model in meta.models_used:
        ET.SubElement(models_elem, "model").text = model

    messages_elem = ET.SubElement(root, "messages")
    for msg_data in messages:
        _format_message_xml(msg_data, messages_elem)

    return _prettify_xml(root)


def _format_message_xml(message_data: dict, parent: ET.Element) -> None:
    """Append a single message as an XML sub-element."""
    msg_elem = ET.SubElement(parent, "message")
    msg_elem.set("uuid", message_data.get("uuid", ""))
    if message_data.get("parentUuid"):
        msg_elem.set("parent-uuid", message_data["parentUuid"])
    msg_elem.set("timestamp", message_data.get("timestamp", ""))

    if "type" in message_data:
        ET.SubElement(msg_elem, "event-type").text = message_data["type"]
    if "cwd" in message_data:
        ET.SubElement(msg_elem, "working-directory").text = message_data["cwd"]

    msg = message_data.get("message")
    if not msg:
        return

    if "role" in msg:
        ET.SubElement(msg_elem, "role").text = msg["role"]
    if "model" in msg:
        ET.SubElement(msg_elem, "model").text = msg["model"]

    content = msg.get("content")
    if content is not None:
        content_elem = ET.SubElement(msg_elem, "content")
        if isinstance(content, str):
            content_elem.text = _clean_xml_text(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                _render_content_block_xml(block, content_elem)

    usage = msg.get("usage")
    if usage:
        _render_usage_xml(usage, msg_elem)


def _render_content_block_xml(block: dict, parent: ET.Element) -> None:
    """Render a single content block as XML."""
    btype = block.get("type", "")

    if btype == "text":
        elem = ET.SubElement(parent, "text")
        elem.text = _clean_xml_text(block.get("text", ""))

    elif btype == "thinking":
        elem = ET.SubElement(parent, "thinking")
        if "signature" in block:
            elem.set("signature", block["signature"])
        elem.text = _clean_xml_text(block.get("thinking", ""))

    elif btype == "tool_use":
        elem = ET.SubElement(parent, "tool-use")
        elem.set("id", block.get("id", ""))
        elem.set("name", block.get("name", ""))
        inp = ET.SubElement(elem, "input")
        inp.text = _clean_xml_text(json.dumps(block.get("input", {}), indent=2))

    elif btype == "tool_result":
        elem = ET.SubElement(parent, "tool-result")
        if "tool_use_id" in block:
            elem.set("tool-use-id", block["tool_use_id"])
        result = block.get("content", "")
        elem.text = _clean_xml_text(result if isinstance(result, str) else str(result))


def _render_usage_xml(usage: dict, parent: ET.Element) -> None:
    """Render token usage information as XML."""
    usage_elem = ET.SubElement(parent, "usage")
    for key, tag in [
        ("input_tokens", "input-tokens"),
        ("output_tokens", "output-tokens"),
        ("cache_creation_input_tokens", "cache-creation-tokens"),
        ("cache_read_input_tokens", "cache-read-tokens"),
    ]:
        if key in usage:
            ET.SubElement(usage_elem, tag).text = str(usage[key])
    if "service_tier" in usage:
        ET.SubElement(usage_elem, "service-tier").text = usage["service_tier"]


def _prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string."""
    try:
        rough = ET.tostring(elem, encoding="unicode", method="xml")
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ")
    except Exception:
        return ET.tostring(elem, encoding="unicode", method="xml")
