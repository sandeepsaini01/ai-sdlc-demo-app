"""Append one structured JSON line per agent event. Fail open."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[2] / "ai-interaction-log.jsonl"
INTERESTING = (
    "prompt",
    "text",
    "message",
    "response",
    "file_path",
    "path",
    "command",
    "subagent_type",
    "name",
    "reason",
    "status",
    "error",
)
SECRET = re.compile(r"(ChangeMe123!|Bearer\s+[A-Za-z0-9]+)", re.IGNORECASE)
SECRET_KEYS = {"password", "token", "authorization", "secret"}
LIMIT = 2000


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {"unparsed": raw[:LIMIT]}
    if not isinstance(payload, dict):
        payload = {"payload": payload}

    event = sys.argv[1] if len(sys.argv) > 1 else str(payload.get("hook_event_name") or "unknown")
    path = str(payload.get("file_path") or payload.get("path") or "")
    if path.replace("\\", "/").endswith("ai-interaction-log.jsonl"):
        sys.stdout.write("{}\n")
        return

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "hook",
        "event": event,
        "keys": sorted(str(key) for key in payload.keys()),
        "fields": {key: redact(payload[key]) for key in INTERESTING if key in payload},
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    sys.stdout.write("{}\n")


def redact(value):
    if isinstance(value, dict):
        return {
            key: ("[redacted]" if key.lower() in SECRET_KEYS else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value[:20]]
    if isinstance(value, str):
        return SECRET.sub("[redacted]", value)[:LIMIT]
    return value


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stdout.write("{}\n")
        sys.exit(0)
