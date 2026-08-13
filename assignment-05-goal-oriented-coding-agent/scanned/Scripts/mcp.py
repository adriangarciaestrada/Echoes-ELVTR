#!/usr/bin/env python3
"""Minimal client for the editor's Model Context Protocol endpoint (UE 5.8.1).

Runs outside the editor. This is Layer B of the authoring pipeline described in
`vault/08-pipeline/authoring-pipeline.md`: deterministic Python computes a plan
and emits a tool script, and this client hands that script to the editor in one
call.

    ./Scripts/mcp.py <script.py>          # run a tool script
    ./Scripts/mcp.py --call <toolset> <tool> '<json args>'

The editor must be running with `-ModelContextProtocolStartServer`; `editor.sh`
passes it. Two details cost turns before they were written down:

  * responses arrive as SSE frames and may span several lines, so the body has
    to be reassembled before parsing rather than read line by line;
  * `call_tool` names its parameters `toolset_name` / `tool_name` / `arguments`.

Tool scripts run in a sandbox with only `json`, `math`, `datetime`, `copy`, `re`
and `time` importable — no `unreal`. A failing `execute_tool` aborts the script
and cannot be caught, so scripts check preconditions instead of handling errors.
See `vault/08-pipeline/editor-tooling.md`.
"""
import json
import subprocess
import sys
import tempfile

URL = "http://127.0.0.1:8000/mcp"
HEADERS = ["-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream"]

PROGRAMMATIC = "editor_toolset.toolsets.programmatic.ProgrammaticToolset"


class McpError(RuntimeError):
    pass


def _post(body, session_id=None, header_sink=None):
    cmd = ["curl", "-s", "--max-time", "600"]
    if header_sink:
        cmd += ["-D", header_sink]
    cmd += HEADERS
    if session_id:
        cmd += ["-H", "Mcp-Session-Id: " + session_id]
    cmd += ["-X", "POST", URL, "-d", json.dumps(body)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise McpError(f"transport failed: {result.stderr.strip() or result.returncode}")

    # Reassemble the whole body before parsing: the payload is pretty-printed
    # JSON delivered inside SSE frames, so it spans many lines.
    blob = "\n".join(line.removeprefix("data: ") for line in result.stdout.splitlines()
                     if line.strip() and not line.startswith("event:"))
    if not blob.strip():
        return None
    return json.loads(blob)


def connect():
    """Handshake, returning the session id every later call must carry."""
    with tempfile.NamedTemporaryFile("w+", suffix=".hdr", delete=False) as sink:
        header_path = sink.name
    _post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "echoes", "version": "1"}}}, header_sink=header_path)

    session_id = ""
    with open(header_path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.lower().startswith("mcp-session-id:"):
                session_id = line.split(":", 1)[1].strip()
    if not session_id:
        raise McpError("no session id — is the editor running with the MCP server?")

    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id)
    return session_id


def call(session_id, toolset, tool, arguments=None):
    """Call one tool. Returns its text payload; raises on a tool-side error."""
    args = {"tool_name": tool, "arguments": arguments or {}}
    if toolset:
        args["toolset_name"] = toolset

    response = _post({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                      "params": {"name": "call_tool", "arguments": args}}, session_id)
    result = (response or {}).get("result") or {}
    text = (result.get("content") or [{}])[0].get("text", "")
    if result.get("isError"):
        raise McpError(f"{tool}: {text}")
    return text


def run_script(session_id, script):
    """Execute a tool script and return the dict its run() produced."""
    text = call(session_id, PROGRAMMATIC, "execute_tool_script", {"script": script})
    # The sandbox returns run()'s dict JSON-encoded inside a JSON envelope.
    try:
        return json.loads(json.loads(text)["returnValue"])
    except (ValueError, KeyError, TypeError):
        return text


def main(argv):
    if len(argv) >= 4 and argv[1] == "--call":
        session = connect()
        arguments = json.loads(argv[4]) if len(argv) > 4 else {}
        print(call(session, argv[2], argv[3], arguments))
        return 0

    if len(argv) < 2:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: mcp.py <script.py> | mcp.py --call <toolset> <tool> '<json>'",
              file=sys.stderr)
        return 2

    session = connect()
    with open(argv[1], encoding="utf-8") as handle:
        print(json.dumps(run_script(session, handle.read()), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except McpError as exc:
        print(f"[mcp] {exc}", file=sys.stderr)
        sys.exit(1)
