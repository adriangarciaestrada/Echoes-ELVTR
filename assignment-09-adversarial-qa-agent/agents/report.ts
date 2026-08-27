/**
 * The structured report.
 *
 * The audience is another developer at triage, so every row has to answer three
 * questions without opening the game: WHERE it happened (the game system and
 * the symbol that owns the rule), WHAT KIND of failure it is, and WHAT THE GAME
 * WAS DOING at the time. Anything that fails those three is a log line, not a
 * bug report.
 *
 * Findings are deduped by (code, system, symbol): a fuzzer that runs ten
 * thousand steps will hit the same break hundreds of times, and a report with
 * three hundred identical rows is one a developer stops reading. The count and
 * the first and last contexts are kept instead.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { Severity, Snapshot, Violation } from "./oracle.js";

export interface GameContext {
  surface: "core-fuzz" | "browser-ui";
  tactic: string;
  class: string;
  seed: number | null;
  phase: string;
  wave: number;
  level: number;
  gold: number;
  beacon_hp: number;
  beacon_max: number;
  relics: number;
  cells: number;
  buffs: number;
  enemies_alive: number | null;
  battle_elapsed: number | null;
  /** The last actions the agent took, oldest first — the reproduction recipe. */
  steps_to_reproduce: string[];
}

export interface Finding {
  id: string;
  code: string;
  error_type: Violation["errorType"];
  severity: Severity;
  location: {
    surface: "core-fuzz" | "browser-ui";
    system: string;
    file: string;
    symbol: string;
    /** Browser surface only: the pixel the agent was poking. */
    screen?: { x: number; y: number; label: string };
  };
  game_context: GameContext;
  expected: string;
  observed: string;
  occurrences: number;
  /**
   * Which surfaces and tactics actually saw it. A break the core fuzzer finds
   * and the browser agent then reproduces through real clicks is a different
   * class of report from one only the headless side ever hit, and the triage
   * order depends on knowing which is which.
   */
  witnessed_by: Array<{ surface: string; tactic: string; phase: string; wave: number; note?: string }>;
  /** Screenshots the browser agent captured at the moment it broke. */
  evidence: string[];
  first_seen: string;
  last_seen: string;
  /** Set when the agent re-ran the recorded steps and got the same break. */
  reproduced: boolean | null;
}

export function contextFrom(
  snap: Snapshot, surface: "core-fuzz" | "browser-ui", tactic: string,
  seed: number | null, trace: string[],
): GameContext {
  return {
    surface, tactic, class: snap.cls, seed,
    phase: snap.phase, wave: snap.wave, level: snap.level, gold: snap.gold,
    beacon_hp: snap.battle ? snap.battle.beaconHp : snap.beaconHp,
    beacon_max: snap.beaconMax,
    relics: snap.relics.length, cells: snap.unlocked.length, buffs: snap.buffs,
    enemies_alive: snap.battle ? snap.battle.enemies.length : null,
    battle_elapsed: snap.battle ? +snap.battle.elapsed.toFixed(2) : null,
    steps_to_reproduce: trace.slice(-12),
  };
}

export class FindingLog {
  private readonly byKey = new Map<string, Finding>();
  private n = 0;

  get size(): number { return this.byKey.size; }

  add(v: Violation, ctx: GameContext, screen?: { x: number; y: number; label: string }): Finding {
    const note = v.observed.slice(0, 260);
    const key = `${v.code}|${v.system}|${v.symbol}`;
    const now = new Date().toISOString();
    const existing = this.byKey.get(key);
    if (existing) {
      existing.occurrences++;
      existing.last_seen = now;
      const w = { surface: ctx.surface, tactic: ctx.tactic, phase: ctx.phase, wave: ctx.wave, note };
      const known = existing.witnessed_by.some(
        (x) => x.surface === w.surface && x.tactic === w.tactic);
      if (!known && existing.witnessed_by.length < 8) existing.witnessed_by.push(w);
      return existing;
    }
    const f: Finding = {
      id: `LOOM-ADV-${String(++this.n).padStart(3, "0")}`,
      code: v.code,
      error_type: v.errorType,
      severity: v.severity,
      location: {
        surface: ctx.surface, system: v.system, file: v.file, symbol: v.symbol,
        ...(screen ? { screen } : {}),
      },
      game_context: ctx,
      expected: v.expected,
      observed: v.observed,
      occurrences: 1,
      witnessed_by: [{ surface: ctx.surface, tactic: ctx.tactic, phase: ctx.phase, wave: ctx.wave, note }],
      evidence: [],
      first_seen: now,
      last_seen: now,
      reproduced: null,
    };
    this.byKey.set(key, f);
    return f;
  }

  /** Mark a finding's recorded steps as replayed and confirmed (or not). */
  markReproduced(code: string, ok: boolean): void {
    for (const f of this.byKey.values()) if (f.code === code) f.reproduced = ok;
  }

  all(): Finding[] {
    const rank: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    return [...this.byKey.values()].sort(
      (a, b) => rank[a.severity] - rank[b.severity] || b.occurrences - a.occurrences);
  }
}

export interface RunSummary {
  started: string;
  finished: string;
  seconds: number;
  core_steps: number;
  core_runs: number;
  browser_cycles: number;
  browser_tactics: string[];
  page_errors: number;
}

const CSV_COLUMNS = [
  "id", "severity", "error_type", "code",
  "location_surface", "location_system", "location_file", "location_symbol", "location_screen",
  "context_class", "context_seed", "context_phase", "context_wave", "context_level",
  "context_gold", "context_beacon_hp", "context_beacon_max",
  "context_relics", "context_cells", "context_buffs",
  "context_enemies_alive", "context_battle_elapsed",
  "expected", "observed", "occurrences", "reproduced", "witnessed_by", "evidence",
  "steps_to_reproduce",
] as const;

const csvCell = (value: unknown): string => {
  const s = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(s) ? `"${s.split('"').join('""')}"` : s;
};

function csvRow(f: Finding): string {
  const c = f.game_context;
  const s = f.location.screen;
  return [
    f.id, f.severity, f.error_type, f.code,
    f.location.surface, f.location.system, f.location.file, f.location.symbol,
    s ? `${s.label} @ (${s.x},${s.y})` : "",
    c.class, c.seed, c.phase, c.wave, c.level,
    c.gold, c.beacon_hp, c.beacon_max,
    c.relics, c.cells, c.buffs,
    c.enemies_alive, c.battle_elapsed,
    f.expected, f.observed, f.occurrences,
    f.reproduced === null ? "" : String(f.reproduced),
    f.witnessed_by.map((w) => `${w.surface}:${w.tactic}`).join(" | "),
    f.evidence.join(" | "),
    c.steps_to_reproduce.join(" > "),
  ].map(csvCell).join(",");
}

export function write(
  jsonPath: string, csvPath: string, findings: Finding[], summary: RunSummary,
): void {
  mkdirSync(dirname(jsonPath), { recursive: true });
  const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const f of findings) counts[f.severity] = (counts[f.severity] ?? 0) + 1;
  writeFileSync(jsonPath, JSON.stringify({
    tool: "loom adversarial QA agent",
    schema: 1,
    summary: { ...summary, findings: findings.length, by_severity: counts },
    findings,
  }, null, 2) + "\n");
  writeFileSync(csvPath,
    [CSV_COLUMNS.join(","), ...findings.map(csvRow)].join("\n") + "\n");
}
