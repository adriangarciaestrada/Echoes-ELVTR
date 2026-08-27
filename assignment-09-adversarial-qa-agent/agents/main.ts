/**
 * The adversarial QA agent — entry point.
 *
 *   npx tsx src/qa/adversary/main.ts               # ~2 min, writes qa-reports/
 *   npx tsx src/qa/adversary/main.ts --core 120 --browser 180
 *   npx tsx src/qa/adversary/main.ts --headed      # watch it play
 *   npx tsx src/qa/adversary/main.ts --no-browser  # core only, no dev server
 *
 * Three stages, in this order on purpose:
 *
 *   1. PROBES    hand-written minimal reproductions, including rules the game
 *                already gets right — they calibrate the oracle before the
 *                fuzzer's volume starts landing on it.
 *   2. FUZZ      the headless core, attacked flat out for as long as it is
 *                given: hundreds of runs, tens of thousands of hostile calls.
 *   3. BROWSER   the shipped build, in a real Chromium, clicked at by an agent
 *                that never plays fair.
 *
 * All three are judged by the same oracle, so a break found in two of them is
 * one finding with two witnesses.
 */
import { spawn, type ChildProcess } from "node:child_process";
import { mkdirSync } from "node:fs";
import { BrowserAgent } from "./browser.js";
import { CoreFuzzer } from "./fuzz.js";
import { FindingLog, write, type RunSummary } from "./report.js";
import { contextFrom } from "./report.js";
import { runProbes } from "./probes.js";
import type { Snapshot } from "./oracle.js";

const argv = process.argv.slice(2);
const flag = (name: string, fallback: number): number => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? Number(argv[i + 1]) : fallback;
};
const CORE_SECONDS = flag("core", 45);
const BROWSER_SECONDS = flag("browser", 150);
const WITH_BROWSER = !argv.includes("--no-browser");
const HEADED = argv.includes("--headed");
const OUT = (() => {
  const i = argv.indexOf("--out");
  return i >= 0 && argv[i + 1] ? argv[i + 1]! : "qa-reports";
})();
const URL = process.env.LOOM_URL ?? "http://localhost:5173";

/** A snapshot placeholder for findings that are not tied to a running game. */
const OFFLINE: Snapshot = {
  phase: "n/a", wave: 0, gold: 0, exp: 0, level: 0, beaconHp: 0, beaconMax: 0,
  freeRerolls: 0, rerollsUsed: 0, pendingBuffChoices: 0, pendingExpansionCells: 0,
  cls: "n/a", env: { w: 7, h: 7 }, unlocked: [], relics: [], tray: [],
  offers: [], offerTiers: [], removed: [], buffs: 0, buffChoiceIds: [],
  handDefId: null, battle: null,
};

async function alreadyServing(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch { return false; }
}

async function startVite(): Promise<ChildProcess | null> {
  const child = spawn("npx", ["vite", "--port", "5173", "--strictPort"],
                      { stdio: "ignore", detached: false });
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => setTimeout(r, 500));
    if (await alreadyServing(URL)) return child;
  }
  child.kill();
  return null;
}

const started = new Date();
const log = new FindingLog();
mkdirSync(`${OUT}/shots`, { recursive: true });

// -- 1. probes ---------------------------------------------------------------
console.log("── probes: minimal reproductions, and the rules that must hold ──");
const probes = runProbes();
let held = 0;
for (const p of probes) {
  if (p.threw) {
    console.log(`  THREW  ${p.name}\n         ${p.threw}`);
    continue;
  }
  if (!p.violation) { held++; console.log(`  held   ${p.name}`); continue; }
  console.log(`  BROKE  ${p.name}`);
  const f = log.add(p.violation,
    contextFrom(OFFLINE, "core-fuzz", `probe: ${p.name}`, null, p.steps));
  f.reproduced = true;
  f.game_context.steps_to_reproduce = p.steps;
}
console.log(`  ${held}/${probes.length} rules held\n`);

// -- 2. core fuzz ------------------------------------------------------------
console.log(`── fuzzing the core for ${CORE_SECONDS}s ──`);
const fuzz = new CoreFuzzer(log);
const fuzzResult = fuzz.sweep(CORE_SECONDS);
console.log(`  ${fuzzResult.runs} runs, ${fuzzResult.steps} adversarial steps, ` +
            `deepest wave ${fuzzResult.deepestWave}\n`);

// -- 3. browser --------------------------------------------------------------
let browserResult = { cycles: 0, tactics: [] as string[], pageErrors: 0 };
if (WITH_BROWSER) {
  let vite: ChildProcess | null = null;
  const serving = await alreadyServing(URL);
  if (!serving) {
    console.log("── starting the dev server ──");
    vite = await startVite();
    if (!vite) {
      console.log(`  could not reach ${URL}; skipping the browser stage`);
    }
  }
  if (serving || vite) {
    console.log(`── driving the real build at ${URL} for ${BROWSER_SECONDS}s ──`);
    const agent = new BrowserAgent(log, {
      url: URL, seconds: BROWSER_SECONDS, headless: !HEADED,
      shotDir: `${OUT}/shots`, shotRef: "shots",
    });
    browserResult = await agent.run();
    console.log(`  ${browserResult.cycles} tactic cycles, ` +
                `${browserResult.pageErrors} page errors\n`);
  }
  vite?.kill("SIGTERM");
}

// -- the report --------------------------------------------------------------
const finished = new Date();
const summary: RunSummary = {
  started: started.toISOString(),
  finished: finished.toISOString(),
  seconds: Math.round((finished.getTime() - started.getTime()) / 1000),
  core_steps: fuzzResult.steps,
  core_runs: fuzzResult.runs,
  browser_cycles: browserResult.cycles,
  browser_tactics: browserResult.tactics,
  page_errors: browserResult.pageErrors,
};
const findings = log.all();
write(`${OUT}/adversarial-report.json`, `${OUT}/adversarial-report.csv`, findings, summary);

console.log("── findings ──");
for (const f of findings) {
  console.log(`  ${f.id}  [${f.severity}] ${f.code}  x${f.occurrences}`);
  console.log(`         ${f.location.system} — ${f.location.file} (${f.location.symbol})`);
  console.log(`         ${f.observed.slice(0, 160)}`);
}
console.log(`\n  ${findings.length} distinct findings, ` +
            `${held}/${probes.length} rules held`);
console.log(`  ${OUT}/adversarial-report.json`);
console.log(`  ${OUT}/adversarial-report.csv`);
