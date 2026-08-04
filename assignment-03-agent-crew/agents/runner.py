#!/usr/bin/env python3
"""
Echoes — Python Agent Orchestrator (runner.py)

Dispatches the 10 development-time agents defined in this directory, routing
each one to its assigned model. Every call is served by a SUBSCRIPTION account
through an official headless CLI — no LLM SDKs and no per-token API keys are
involved, so subscription quota is what pays for the work.

Two subscription lanes:

  - Claude Pro Team  -> `claude` CLI in headless mode (`-p`). The subprocess is
    pinned to the project config dir (CLAUDE_CONFIG_DIR) so it authenticates
    against the correct team account, not the machine default. Serves
    Haiku 4.5, Sonnet 5, Opus 4.8.
  - Antigravity (Gemini Pro) -> `agy` CLI in headless mode (`-p`). Serves the
    Gemini 3.x family and Claude Sonnet 4.6.

Design guarantees:
  - Fail loud: a CLI error exits non-zero with the real stderr. Output is never
    fabricated to look like success.
  - Model integrity: the requested model is validated (agy) or the model that
    actually ran is checked against the request (claude); silent substitution
    is surfaced, not hidden.
  - Token accounting: every call appends a record to
    production/output/usage_log.jsonl so spend can be measured, not guessed.

Usage:
  python3 agents/runner.py --list
  python3 agents/runner.py --agent 01-level-designer --input "Generate Room_SeqA_01"
  python3 agents/runner.py --agent 09 --vault-notes 03-bosses/la-costurera-overview --input "Audit revive timing"
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Make the sibling validators module importable whether this file is run as a
# script (python3 agents/runner.py) or imported as a package module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validators  # noqa: E402

# Base paths relative to repository root
BASE_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = BASE_DIR / "agents"
VAULT_DIR = BASE_DIR / "vault"
OUTPUT_DIR = BASE_DIR / "production" / "output"
USAGE_LOG = OUTPUT_DIR / "usage_log.jsonl"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# The `claude` binary defaults to the machine-wide config dir. The project keeps
# its own login (the team subscription) under this directory, so it must be set
# explicitly for every subprocess — the interactive shell wrapper is not present
# when Python spawns the binary directly.
CLAUDE_CONFIG_DIR = str(Path.home() / ".claude-elvtr")

DEFAULT_TIMEOUT = 420  # seconds; Opus and Gemini Pro on large inputs can be slow

# Agent -> assigned model and subscription lane.
#   provider "claude" : served by the `claude` CLI (Claude Pro Team)
#   provider "agy"    : served by the `agy` CLI (Antigravity / Gemini Pro)
# Gemini model names carry a reasoning-effort suffix (-high/-medium/-low).
AGENT_REGISTRY = {
    "01": {"file": "01-level-designer.md",            "name": "Level Designer",            "provider": "agy",    "model": "gemini-3.6-flash-medium"},
    "02": {"file": "02-encounter-designer.md",        "name": "Encounter Designer",        "provider": "agy",    "model": "gemini-3.6-flash-medium"},
    "03": {"file": "03-room-reviewer.md",             "name": "Room Reviewer",             "provider": "claude", "model": "claude-haiku-4-5"},
    "04": {"file": "04-lore-scribe.md",               "name": "Lore Scribe",               "provider": "agy",    "model": "claude-sonnet-4-6"},
    "05": {"file": "05-style-ip-guard.md",            "name": "Style & IP Guard",          "provider": "claude", "model": "claude-haiku-4-5"},
    "06": {"file": "06-boss-brain-designer.md",       "name": "Boss-Brain Designer",       "provider": "claude", "model": "claude-sonnet-5"},
    "07": {"file": "07-ui-designer.md",               "name": "UI Designer",               "provider": "agy",    "model": "gemini-3.6-flash-medium"},
    "08": {"file": "08-coder.md",                     "name": "Coder",                     "provider": "claude", "model": "claude-sonnet-5"},
    "09": {"file": "09-adversarial-design-critic.md", "name": "Adversarial Design Critic", "provider": "claude", "model": "claude-opus-4-8"},
    "10": {"file": "10-adversarial-qa-crew.md",       "name": "Adversarial QA Crew",       "provider": "agy",    "model": "gemini-3.1-pro-high"},
    "11": {"file": "11-asset-scout.md",               "name": "Asset Scout",               "provider": "agy",    "model": "gemini-3.1-pro-high"},
    "12": {"file": "12-controls-game-feel-designer.md","name": "Controls & Game-Feel Designer","provider": "claude", "model": "claude-sonnet-5"},
}

ASSET_MANIFEST = BASE_DIR / "production" / "asset-manifest.json"

# Generate-then-judge chains: generator -> deterministic validator kind -> LLM reviewer.
PIPELINE = {
    "01": {"validator": "room",      "reviewer": "03"},
    "02": {"validator": "encounter", "reviewer": "03"},
    "04": {"validator": "text",      "reviewer": "05"},
    "06": {"validator": "goap",      "reviewer": "09"},
}


def list_agents():
    """Prints the registered agent roster along with lane and model."""
    print("=" * 82)
    print("                        ECHOES — AI AGENT ROSTER")
    print("=" * 82)
    for code, info in AGENT_REGISTRY.items():
        lane = "Claude Pro Team" if info["provider"] == "claude" else "Antigravity/Gemini Pro"
        print(f" [{code}] {info['name']:<26} | {lane:<22} | {info['model']}")
    print("=" * 82)


def parse_required_vault(content: str) -> List[str]:
    """Extracts the note paths an agent declares under '## Required Vault Context'.

    This is the minimal-context mechanism: each spec lists exactly the vault notes
    it needs, so the agent is never handed the whole vault. Paths are the
    backtick-quoted `*.md` entries in that section only.
    """
    section = re.search(r"##\s*Required Vault Context\s*(.*?)(?:\n##\s|\Z)", content, re.DOTALL)
    if not section:
        return []
    return re.findall(r"`([^`]+\.md)`", section.group(1))


def load_agent_spec(agent_identifier: str) -> Tuple[str, str, Dict, List[str]]:
    """Resolves an agent and returns (name, system_prompt, info, required_vault_notes)."""
    target_info = None
    for code, info in AGENT_REGISTRY.items():
        if agent_identifier in (code, info["name"], info["file"], info["file"].replace(".md", "")):
            target_info = info
            break
    if not target_info:
        for code, info in AGENT_REGISTRY.items():
            if agent_identifier.lower() in info["file"].lower():
                target_info = info
                break
    if not target_info:
        raise ValueError(f"Agent '{agent_identifier}' not found. Use --list to see available agents.")

    spec_path = AGENTS_DIR / target_info["file"]
    if not spec_path.exists():
        raise FileNotFoundError(f"Specification file missing: {spec_path}")

    content = spec_path.read_text(encoding="utf-8")
    # System prompt is the fenced ```markdown ... ``` block in each spec.
    prompt_match = re.search(r"```markdown\s*(.*?)\s*```", content, re.DOTALL)
    system_prompt = prompt_match.group(1).strip() if prompt_match else content
    required_notes = parse_required_vault(content)
    return target_info["name"], system_prompt, target_info, required_notes


def load_vault_notes(notes_arg: Optional[str]) -> str:
    """Loads and formats context notes from the vault/ directory."""
    if not notes_arg:
        return ""
    context_blocks = []
    for note in [n.strip() for n in notes_arg.split(",") if n.strip()]:
        rel_path = note if note.endswith(".md") else f"{note}.md"
        full_path = VAULT_DIR / rel_path
        if not full_path.exists():
            matches = list(VAULT_DIR.rglob(f"*{Path(rel_path).name}"))
            if matches:
                full_path = matches[0]
            else:
                sys.exit(f"❌ Vault note '{note}' not found under {VAULT_DIR}. Aborting so context is never silently dropped.")
        note_content = full_path.read_text(encoding="utf-8")
        context_blocks.append(f"--- VAULT NOTE: {full_path.relative_to(VAULT_DIR)} ---\n{note_content}\n")
    return "\n".join(context_blocks)


def _run(cmd: List[str], timeout: int, extra_env: Optional[Dict] = None) -> str:
    """Runs a subprocess, failing loud on any error. Never fabricates output."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except FileNotFoundError:
        sys.exit(f"❌ CLI not found: '{cmd[0]}'. Is it installed and on PATH?")
    except subprocess.TimeoutExpired:
        sys.exit(f"❌ Timeout after {timeout}s running: {cmd[0]}")
    if proc.returncode != 0:
        sys.stderr.write((proc.stderr or "").strip() + "\n")
        sys.exit(f"❌ '{cmd[0]}' exited {proc.returncode}. Real error above — no output was fabricated.")
    return proc.stdout


def call_claude(system_prompt: str, user_prompt: str, model: str, timeout: int) -> Tuple[str, Dict]:
    """Calls the `claude` CLI headless, pinned to the team subscription config."""
    cmd = [
        "claude", "-p", user_prompt,
        "--append-system-prompt", system_prompt,
        "--model", model,
        "--output-format", "json",
    ]
    out = _run(cmd, timeout, extra_env={"CLAUDE_CONFIG_DIR": CLAUDE_CONFIG_DIR})
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        sys.exit("❌ Could not parse `claude` JSON output.")
    if data.get("is_error"):
        sys.exit(f"❌ `claude` returned an error: {data.get('result')}")
    ran = list((data.get("modelUsage") or {}).keys())
    if ran and not any(model in r for r in ran):
        sys.stderr.write(f"⚠️  Requested '{model}' but the run reported {ran}. Model integrity check failed.\n")
    usage = {
        "provider": "claude", "requested_model": model, "ran_model": ran,
        "cost_usd": data.get("total_cost_usd"), "tokens": data.get("usage"),
    }
    return data.get("result", ""), usage


_AGY_MODELS: Optional[List[str]] = None


def agy_models(timeout: int = 180) -> List[str]:
    """Lists (and caches) the models Antigravity currently offers."""
    global _AGY_MODELS
    if _AGY_MODELS is None:
        out = _run(["agy", "models"], timeout)
        _AGY_MODELS = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return _AGY_MODELS


def call_agy(system_prompt: str, user_prompt: str, model: str, timeout: int) -> Tuple[str, Dict]:
    """Calls the `agy` CLI headless (Antigravity / Gemini Pro subscription)."""
    available = agy_models()
    if model not in available:
        sys.exit(f"❌ Model '{model}' is not offered by Antigravity.\n   Available: {', '.join(available)}")
    # `agy` has no dedicated system-prompt flag, so the instructions are prepended.
    combined = f"[SYSTEM INSTRUCTIONS]\n{system_prompt}\n\n[TASK]\n{user_prompt}"
    # --dangerously-skip-permissions keeps headless runs from hanging on tool
    # approval prompts; these agents only emit text/JSON and touch no files.
    cmd = ["agy", "-p", combined, "--model", model, "--dangerously-skip-permissions"]
    out = _run(cmd, timeout)
    usage = {"provider": "agy", "requested_model": model, "ran_model": [model], "cost_usd": None, "tokens": None}
    return out.strip(), usage


def extract_json(text: str) -> Optional[Dict]:
    """Attempts to extract and parse a JSON payload from response text."""
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    raw_json = json_match.group(1) if json_match else text
    try:
        return json.loads(raw_json.strip())
    except Exception:
        return None


def log_usage(agent_name: str, model: str, usage: Dict):
    """Appends one call record to the usage log for later token accounting."""
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "agent": agent_name, "model": model}
    record.update(usage)
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_context(required_notes: List[str], extra_notes_arg: Optional[str]) -> Tuple[List[str], str]:
    """Auto-load an agent's declared minimal notes, plus any caller extras, deduped."""
    notes: List[str] = list(required_notes)
    if extra_notes_arg:
        notes += [n.strip() for n in extra_notes_arg.split(",") if n.strip()]
    seen = set()
    notes = [n for n in notes if not (n in seen or seen.add(n))]
    return notes, (load_vault_notes(",".join(notes)) if notes else "")


def dispatch(info: Dict, system_prompt: str, user_prompt: str, timeout: int) -> Tuple[str, Dict]:
    """Route one call to the correct subscription CLI based on the agent's lane."""
    if info["provider"] == "claude":
        return call_claude(system_prompt, user_prompt, info["model"], timeout)
    return call_agy(system_prompt, user_prompt, info["model"], timeout)


def _registry_code(info: Dict) -> Optional[str]:
    for code, i in AGENT_REGISTRY.items():
        if i is info:
            return code
    return None


def run_pipeline(gen_key: str, user_input: str, extra_notes_arg: Optional[str],
                 retries: int, timeout: int, output: Optional[str]):
    """Generate -> deterministic validate (hard gate, with retry) -> semantic review.

    The validator is the gate: if generation cannot pass it within the retry
    budget, the pipeline HALTS and nothing is forwarded to the reviewer or engine.
    """
    gen_name, gen_sys, gen_info, gen_notes = load_agent_spec(gen_key)
    code = _registry_code(gen_info)
    cfg = PIPELINE.get(code)
    if not cfg:
        sys.exit(f"❌ Agent '{gen_key}' has no pipeline mapping. Pipeline generators: {sorted(PIPELINE)}.")
    validator_fn = validators.VALIDATORS[cfg["validator"]]

    notes, vault_context = build_context(gen_notes, extra_notes_arg)
    print(f"\n🔗 PIPELINE: {gen_name} → validate:{cfg['validator']} → review:[{cfg['reviewer']}]")
    print(f"🔑 Generator lane: {'Claude Pro Team' if gen_info['provider']=='claude' else 'Antigravity/Gemini Pro'} | Model: {gen_info['model']}")
    print(f"📚 Vault context: {', '.join(notes)}")
    print("-" * 82)

    parsed: Optional[Dict] = None
    hard: List[Dict] = []
    warns: List[Dict] = []
    feedback = ""
    max_attempts = retries + 1
    for attempt in range(1, max_attempts + 1):
        user_prompt = ""
        if vault_context:
            user_prompt += f"CONTEXT FROM VAULT:\n{vault_context}\n\n"
        user_prompt += f"TASK INSTRUCTION:\n{user_input}{feedback}"
        raw, usage = dispatch(gen_info, gen_sys, user_prompt, timeout)
        log_usage(gen_name, gen_info["model"], usage)

        parsed = extract_json(raw)
        if parsed is None:
            hard = [{"code": "ERR_INVALID_JSON", "message": "generator did not return parseable JSON", "path": ""}]
            warns = []
        else:
            errs = validator_fn(parsed)
            hard = [e for e in errs if e["code"].startswith("ERR_")]
            warns = [e for e in errs if not e["code"].startswith("ERR_")]
        verdict = "PASS" if not hard else "FAIL"
        print(f"  • generate+validate attempt {attempt}/{max_attempts}: {verdict}"
              + (f" — {len(hard)} error(s)" if hard else "")
              + (f", {len(warns)} warning(s)" if warns else ""))
        if not hard:
            break
        for e in hard:
            print(f"      ↳ {e['code']} @ {e['path']}: {e['message']}")
        feedback = ("\n\nYOUR PREVIOUS OUTPUT FAILED DETERMINISTIC VALIDATION. "
                    "Correct exactly these and re-emit ONLY the corrected JSON:\n"
                    + json.dumps(hard, ensure_ascii=False))

    if hard:
        print(f"\n❌ PIPELINE HALTED at the deterministic gate after {max_attempts} attempt(s). "
              "Nothing was forwarded to the reviewer or the engine.")
        print(json.dumps({"stage": "validate", "status": "FAIL", "errors": hard}, indent=2, ensure_ascii=False))
        sys.exit(1)

    print(f"  ✅ deterministic gate PASSED" + (f" (with {len(warns)} in-engine warning(s))" if warns else ""))

    # Semantic reviewer runs ONLY on validated content.
    rev_name, rev_sys, rev_info, rev_notes = load_agent_spec(cfg["reviewer"])
    _, rev_vault = build_context(rev_notes, None)
    rev_input = (f"A deterministic validator has already PASSED this {cfg['validator']} spec"
                 + (f" (open in-engine warnings: {json.dumps(warns, ensure_ascii=False)})" if warns else "")
                 + ". Perform your semantic review only. Spec JSON:\n"
                 + json.dumps(parsed, ensure_ascii=False))
    rev_prompt = ""
    if rev_vault:
        rev_prompt += f"CONTEXT FROM VAULT:\n{rev_vault}\n\n"
    rev_prompt += f"TASK INSTRUCTION:\n{rev_input}"
    rev_raw, rev_usage = dispatch(rev_info, rev_sys, rev_prompt, timeout)
    log_usage(rev_name, rev_info["model"], rev_usage)
    print(f"  🔎 semantic review by [{cfg['reviewer']}] {rev_name} ({rev_info['model']}) — subscription lane\n")

    if output:
        out_file = OUTPUT_DIR / output
        out_file.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 82)
    print("VALIDATED GENERATOR OUTPUT:")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    if warns:
        print("\nOPEN WARNINGS (need in-engine confirmation):")
        print(json.dumps(warns, indent=2, ensure_ascii=False))
    print("\nSEMANTIC REVIEWER VERDICT:")
    print(rev_raw)
    print("=" * 82)
    if output:
        print(f"\n✅ Validated artifact saved to: {OUTPUT_DIR / output}")


def _validate(kind: str, obj: Dict, room: Optional[Dict] = None) -> List[Dict]:
    """Dispatch to the right validator; the encounter validator takes room context."""
    if kind == "encounter":
        return validators.validate_encounter(obj, room)
    return validators.VALIDATORS[kind](obj)


def _gen_and_validate(gen_code: str, user_input: str, validator_kind: str, retries: int,
                      timeout: int, stage_label: str, room_ctx: Optional[Dict] = None):
    """Run one generator through the deterministic gate with retry-on-failure.

    Returns (parsed_dict, warnings, agent_name). Exits(1) if the gate is never passed.
    """
    name, system_prompt, info, notes = load_agent_spec(gen_code)
    _, vault_context = build_context(notes, None)
    parsed: Optional[Dict] = None
    hard: List[Dict] = []
    warns: List[Dict] = []
    feedback = ""
    max_attempts = retries + 1
    lane = "Claude Pro Team" if info["provider"] == "claude" else "Antigravity/Gemini Pro"
    print(f"\n▶ {stage_label}: {name} ({info['model']}, {lane})")
    for attempt in range(1, max_attempts + 1):
        prompt = ""
        if vault_context:
            prompt += f"CONTEXT FROM VAULT:\n{vault_context}\n\n"
        prompt += f"TASK INSTRUCTION:\n{user_input}{feedback}"
        raw, usage = dispatch(info, system_prompt, prompt, timeout)
        log_usage(name, info["model"], usage)
        parsed = extract_json(raw)
        if parsed is None:
            hard = [{"code": "ERR_INVALID_JSON", "message": "generator did not return parseable JSON", "path": ""}]
            warns = []
        else:
            errs = _validate(validator_kind, parsed, room_ctx)
            hard = [e for e in errs if e["code"].startswith("ERR_")]
            warns = [e for e in errs if not e["code"].startswith("ERR_")]
        print(f"    validate:{validator_kind} attempt {attempt}/{max_attempts}: "
              + ("PASS" if not hard else f"FAIL ({len(hard)} error(s))")
              + (f", {len(warns)} warning(s)" if warns else ""))
        if not hard:
            break
        for e in hard:
            print(f"        ↳ {e['code']} @ {e['path']}: {e['message']}")
        feedback = ("\n\nYOUR PREVIOUS OUTPUT FAILED DETERMINISTIC VALIDATION. "
                    "Correct exactly these and re-emit ONLY the corrected JSON:\n"
                    + json.dumps(hard, ensure_ascii=False))
    if hard:
        print(f"\n❌ PIPELINE HALTED at {stage_label} after {max_attempts} attempt(s). "
              "Nothing was forwarded downstream or to the engine.")
        print(json.dumps({"stage": stage_label, "status": "FAIL", "errors": hard}, indent=2, ensure_ascii=False))
        sys.exit(1)
    return parsed, warns, name


def run_room_pipeline(room_brief: str, retries: int, timeout: int, output_prefix: Optional[str]):
    """Chain THREE LLM agents in one run to produce a complete, reviewed room:
    01 Level Designer -> validate:room -> 02 Encounter Designer -> validate:encounter -> 03 Room Reviewer.
    """
    print(f"\n🔗🔗 ROOM PRODUCTION CREW (3 coordinating LLM agents)")
    print("   01 Level Designer → validate:room → 02 Encounter Designer → validate:encounter → 03 Room Reviewer")
    print("=" * 82)

    # Stage 1 — Level Designer generates the room geometry.
    room, room_warns, n01 = _gen_and_validate("01", room_brief, "room", retries, timeout,
                                               "Stage 1 — Level Designer")

    # Stage 2 — Encounter Designer populates THAT validated room (hand-off).
    enc_brief = (f"{room_brief}\n\nPopulate THIS already-validated room with a single encounter. "
                 "Place enemies consistent with the room's segment and dimensions. "
                 f"VALIDATED ROOM JSON:\n{json.dumps(room, ensure_ascii=False)}")
    enc, enc_warns, n02 = _gen_and_validate("02", enc_brief, "encounter", retries, timeout,
                                            "Stage 2 — Encounter Designer", room_ctx=room)

    # Stage 3 — Room Reviewer semantically reviews the combined room + encounter (hand-off).
    n03, sys03, i03, notes03 = load_agent_spec("03")
    _, vault03 = build_context(notes03, None)
    warns_all = room_warns + enc_warns
    rev_input = ("A deterministic validator has PASSED both the room and the encounter"
                 + (f" (open in-engine warnings: {json.dumps(warns_all, ensure_ascii=False)})" if warns_all else "")
                 + ". Perform your semantic review of the COMBINED room + encounter (design intent, "
                 "unintended exploits, asymmetry health).\n\n"
                 f"ROOM:\n{json.dumps(room, ensure_ascii=False)}\n\nENCOUNTER:\n{json.dumps(enc, ensure_ascii=False)}")
    rev_prompt = (f"CONTEXT FROM VAULT:\n{vault03}\n\n" if vault03 else "") + f"TASK INSTRUCTION:\n{rev_input}"
    lane03 = "Claude Pro Team" if i03["provider"] == "claude" else "Antigravity/Gemini Pro"
    print(f"\n▶ Stage 3 — Room Reviewer: {n03} ({i03['model']}, {lane03})")
    rev_raw, rev_usage = dispatch(i03, sys03, rev_prompt, timeout)
    log_usage(n03, i03["model"], rev_usage)
    print("    semantic review complete")

    if output_prefix:
        (OUTPUT_DIR / f"{output_prefix}_room.json").write_text(json.dumps(room, indent=2, ensure_ascii=False), encoding="utf-8")
        (OUTPUT_DIR / f"{output_prefix}_encounter.json").write_text(json.dumps(enc, indent=2, ensure_ascii=False), encoding="utf-8")
        rev_parsed = extract_json(rev_raw)
        (OUTPUT_DIR / f"{output_prefix}_review.json").write_text(
            json.dumps(rev_parsed, indent=2, ensure_ascii=False) if rev_parsed else rev_raw,
            encoding="utf-8")

    print("\n" + "=" * 82)
    print(f"✅ ROOM PRODUCED — 3 LLM agents coordinated without crashing: {n01} → {n02} → {n03}")
    print("=" * 82)
    print("\nROOM (Level Designer, validated):")
    print(json.dumps(room, indent=2, ensure_ascii=False))
    print("\nENCOUNTER (Encounter Designer, validated against the room):")
    print(json.dumps(enc, indent=2, ensure_ascii=False))
    if warns_all:
        print("\nOPEN IN-ENGINE WARNINGS:")
        print(json.dumps(warns_all, indent=2, ensure_ascii=False))
    print("\nSEMANTIC REVIEW (Room Reviewer, combined):")
    print(rev_raw)
    if output_prefix:
        print(f"\n✅ Saved: {OUTPUT_DIR}/{output_prefix}_room.json, {output_prefix}_encounter.json, {output_prefix}_review.json")


def run_scout(phase: Optional[str], priority: Optional[str], limit: Optional[int], timeout: int):
    """Drive the Asset Scout over the marketplace entries of the asset manifest.

    Web browsing runs on the `agy` lane. Every candidate is a proposal a human
    must verify (per GDD V2) — links cannot be auto-verified from here.
    """
    if not ASSET_MANIFEST.exists():
        sys.exit(f"❌ Asset manifest not found: {ASSET_MANIFEST}")
    manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    global_constraints = manifest.get("global_constraints", {})
    items = [a for a in manifest.get("assets", []) if a.get("source") == "marketplace"]
    if phase:
        items = [a for a in items if a.get("phase") == phase]
    if priority:
        items = [a for a in items if a.get("priority") == priority]
    if limit:
        items = items[:limit]
    if not items:
        sys.exit("❌ No marketplace assets match the given filters.")

    name, system_prompt, info, _ = load_agent_spec("11")
    print(f"\n🛰️  ASSET SCOUT over {len(items)} manifest entr(y/ies)"
          + (f" | phase={phase}" if phase else "") + (f" | priority={priority}" if priority else ""))
    print(f"🔑 Lane: Antigravity / Gemini Pro (web browsing) | Model: {info['model']}")
    print("-" * 82)

    results = []
    for a in items:
        user_prompt = ("TASK INSTRUCTION:\nSource this asset and return candidates.\n\n"
                       f"GLOBAL CONSTRAINTS:\n{json.dumps(global_constraints, ensure_ascii=False)}\n\n"
                       f"ASSET:\n{json.dumps(a, ensure_ascii=False)}")
        raw, usage = dispatch(info, system_prompt, user_prompt, timeout)
        log_usage(name, info["model"], usage)
        parsed = extract_json(raw)
        n = len(parsed.get("candidates", [])) if isinstance(parsed, dict) else 0
        print(f"  • {a['id']:<22} [{a['priority']}/{a['phase']}]: {n} candidate(s)")
        results.append({"asset_id": a["id"], "result": parsed if parsed is not None else {"raw": raw}})

    out_file = OUTPUT_DIR / "asset-candidates.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(r["result"].get("candidates", [])) for r in results if isinstance(r["result"], dict))
    print("-" * 82)
    print(f"✅ {total} candidate(s) across {len(items)} asset(s) saved to: {out_file}")
    print("⚠️  All candidates are PROPOSALS — a human must open each link and confirm license before purchase.")


def main():
    parser = argparse.ArgumentParser(description="Echoes AI Agent Orchestrator (subscription lanes)")
    parser.add_argument("--list", action="store_true", help="List agents, lanes and models")
    parser.add_argument("--agent", type=str, help="Agent code or identifier (e.g. 01, level-designer)")
    parser.add_argument("--input", type=str, help="Task instruction for the agent")
    parser.add_argument("--vault-notes", type=str, help="Comma-separated vault note paths to inject as context")
    parser.add_argument("--output", type=str, help="Optional filename to save the response under production/output/")
    parser.add_argument("--json-only", action="store_true", help="Extract and print strictly the JSON payload")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Per-call timeout in seconds (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--pipeline", action="store_true", help="Run generate -> deterministic validate (with retry) -> semantic review")
    parser.add_argument("--pipeline-room", action="store_true", help="Chain 3 LLM agents: 01 Level -> validate -> 02 Encounter -> validate -> 03 Reviewer")
    parser.add_argument("--retries", type=int, default=2, help="Validation-failure retries in pipeline modes (default 2)")
    parser.add_argument("--scout", action="store_true", help="Drive the Asset Scout over the marketplace entries of the asset manifest")
    parser.add_argument("--phase", type=str, help="Scout filter: manifest phase (e.g. R3)")
    parser.add_argument("--priority", type=str, help="Scout filter: manifest priority (e.g. P0)")
    parser.add_argument("--limit", type=int, help="Scout: cap the number of assets processed")
    args = parser.parse_args()

    if args.scout:
        run_scout(args.phase, args.priority, args.limit, args.timeout)
        return

    if args.pipeline_room:
        if not args.input:
            sys.exit("❌ --input (a room brief) is required for --pipeline-room.")
        run_room_pipeline(args.input, args.retries, args.timeout, args.output)
        return

    if args.list or not args.agent:
        list_agents()
        if not args.list and not args.agent:
            print("\nExample: python3 agents/runner.py --agent 01-level-designer --input 'Generate Room_SeqA_01'")
        sys.exit(0)

    if not args.input:
        sys.exit("❌ --input is required when running an agent.")

    if args.pipeline:
        run_pipeline(args.agent, args.input, args.vault_notes, args.retries, args.timeout, args.output)
        return

    agent_name, system_prompt, info, required_notes = load_agent_spec(args.agent)
    provider, model = info["provider"], info["model"]

    # Minimal context: auto-load the notes the agent declares, then any the
    # caller adds explicitly, deduped while preserving order. The full vault is
    # never sent — only each agent's declared slice.
    notes: List[str] = list(required_notes)
    if args.vault_notes:
        notes += [n.strip() for n in args.vault_notes.split(",") if n.strip()]
    seen = set()
    notes = [n for n in notes if not (n in seen or seen.add(n))]

    vault_context = load_vault_notes(",".join(notes)) if notes else ""
    full_user_prompt = ""
    if vault_context:
        full_user_prompt += f"CONTEXT FROM VAULT:\n{vault_context}\n\n"
    full_user_prompt += f"TASK INSTRUCTION:\n{args.input}"

    lane = "Claude Pro Team" if provider == "claude" else "Antigravity / Gemini Pro"
    print(f"\n🚀 Agent [{info['file']}] {agent_name}")
    print(f"🔑 Lane: {lane} (subscription) | Model: {model}")
    if notes:
        auto = f"{len(required_notes)} auto"
        extra = f" + {len(notes) - len(required_notes)} manual" if len(notes) > len(required_notes) else ""
        print(f"📚 Vault context ({auto}{extra}): {', '.join(notes)}")
    print("-" * 82)

    if provider == "claude":
        raw_response, usage = call_claude(system_prompt, full_user_prompt, model, args.timeout)
    else:
        raw_response, usage = call_agy(system_prompt, full_user_prompt, model, args.timeout)

    log_usage(agent_name, model, usage)

    if args.json_only:
        parsed = extract_json(raw_response)
        output_content = json.dumps(parsed, indent=2, ensure_ascii=False) if parsed else raw_response
    else:
        output_content = raw_response

    print(output_content)

    if args.output:
        out_file = OUTPUT_DIR / args.output
        out_file.write_text(output_content, encoding="utf-8")
        print(f"\n✅ Saved to: {out_file}")


if __name__ == "__main__":
    main()
