from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .capture import redact_private_values


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(redact_private_values(report), sort_keys=True, indent=2) + "\n"


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "smart-remake-report.json"
    markdown_path = output_dir / "smart-remake-report.md"
    safe = redact_private_values(report)
    json_path.write_text(render_json(safe), encoding="utf-8")
    markdown_path.write_text(
        "# Smart Remake captured-evidence report\n\n"
        f"Mode: `{safe['mode']}`. Protocol: `{safe['protocol']['status']}`.\n\n"
        f"Planned: {safe['planned_runs']}; captured: {safe['captured_runs']}; "
        f"accepted: {safe['accepted_outputs']}; all attempts: {safe['attempts']}.\n\n"
        "Missing measurements remain null/unmeasured. No provider call is made by replay.\n\n"
        f"```json\n{render_json(safe).rstrip()}\n```\n",
        encoding="utf-8",
    )
    return json_path, markdown_path
