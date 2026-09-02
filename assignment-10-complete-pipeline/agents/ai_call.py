#!/usr/bin/env python3
"""
The `claude` CLI, headless — one personal subscription account, no per-token
API key, no SDK. Shared by any tool in this directory that needs a model
call: fail loud on any CLI or parse error (never fabricate a response so a
failure looks like success), and log every call's usage so spend is
measured, not guessed.

Ported from the ELVTR course monorepo's `agents/runner.py`, which serves a
twelve-agent roster tied to a different game's vault — copied out as the
one function every caller there actually needed, not imported wholesale.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_TIMEOUT_S = 120


def call_claude(system_prompt: str, user_prompt: str, *, model: str = DEFAULT_MODEL,
                 timeout_s: int = DEFAULT_TIMEOUT_S) -> Tuple[str, Dict[str, Any]]:
    """Calls the `claude` CLI on the machine-default (personal, subscription)
    login. Never fabricates a response: any failure exits loud."""
    env = os.environ.copy()
    env.pop("CLAUDE_CONFIG_DIR", None)
    cmd = [
        "claude", "-p",
        "--append-system-prompt", system_prompt,
        "--model", model,
        "--output-format", "json",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s,
                               env=env, input=user_prompt)
    except FileNotFoundError:
        sys.exit("the `claude` CLI is not on PATH — install/log in to Claude Code first.")
    except subprocess.TimeoutExpired:
        sys.exit(f"`claude` timed out after {timeout_s}s.")
    if proc.returncode != 0:
        sys.stderr.write((proc.stderr or "").strip() + "\n")
        sys.exit(f"`claude` exited {proc.returncode}. Real error above.")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.exit("could not parse `claude`'s JSON envelope.")
    if data.get("is_error"):
        sys.exit(f"`claude` returned an error: {data.get('result')}")
    usage = {
        "model": model,
        "cost_usd": data.get("total_cost_usd"),
        "tokens": data.get("usage"),
    }
    return data.get("result", ""), usage


def log_usage(log_path: Path, tool: str, turn: int, usage: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"tool": tool, "turn": turn,
                             "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **usage}) + "\n")
