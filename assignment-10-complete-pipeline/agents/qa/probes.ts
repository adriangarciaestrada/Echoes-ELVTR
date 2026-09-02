/**
 * Minimal, deterministic reproductions.
 *
 * The fuzzer finds breaks the way a fuzzer does — a hundred thousand calls, and
 * a violation somewhere in the middle. That is enough to know something is
 * wrong and not enough for anyone to fix it. Each probe here is the shortest
 * sequence that produces one specific break from a fresh run, so the report can
 * carry a recipe a developer can paste rather than a haystack.
 *
 * The probes that PASS are load-bearing too. A QA agent that only ever reports
 * failures gives no way to tell a discriminating oracle from a broken one, so
 * the suite deliberately includes rules this game already gets right — the
 * scrap loop it closed, the buff screen it stabilised, the phase guard it
 * added — and the report says how many held.
 */
import { BUFFS, RELIC_BY_ID } from "../../core/content.js";
import { Run } from "../../core/run.js";
import { Hand } from "../../game/hand.js";
import { MAX_TIER } from "../../core/types.js";
import { playMarket, playUlt } from "../../sim/policy.js";
import { inspect } from "./oracle.js";
import { snapshotRun } from "./fuzz.js";
import type { Violation } from "./oracle.js";

export interface Probe {
  name: string;
  /** The recipe, in the order the agent performed it. */
  steps: string[];
  /** Returns the violation if the rule broke, or null if it held. */
  check: () => Violation | null;
}

/** Play one wave to completion so the run is in a settled post-battle state. */
function playOneWave(run: Run): void {
  playMarket(run, "competent");
  const b = run.startBattle();
  b.runToEnd(600, (bb) => playUlt(bb, "competent"));
  run.endBattle();
}

export const PROBES: Probe[] = [
  {
    name: "banishing a card cannot upgrade the card below it",
    steps: [
      'run = new Run("hunter", seed)   // search seeds for a shelf whose top card outranks the one below it',
      "run.wave = 30; run.rollOffers()  // deep enough that the market deals mixed rarities",
      "record offers[] and offerTiers[]",
      "run.removeFromPool(offers[0].id)   // the Banish button on the TOP card; costs nothing",
      "read offers[] and offerTiers[] again — the card that moved up now carries the banished card's tier",
    ],
    check() {
      // Banishing costs no gold and the tier array is never spliced, so every
      // surviving card inherits the tier of the slot ABOVE it. Whenever the
      // shelf happens to be ordered high-then-low, that is a free upgrade.
      for (let seed = 1; seed < 400; seed++) {
        const run = new Run("hunter", seed);
        run.wave = 30;
        run.rollOffers();
        if (run.offers.length < 2) continue;
        const topTier = run.offerTiers[0]!;
        const nextId = run.offers[1]!.id;
        const nextTier = run.offerTiers[1]!;
        if (topTier <= nextTier) continue;          // not the exploitable ordering
        const before = run.offers.map((o, i) => `${o.id}@${run.offerTiers[i]}`);
        run.removeFromPool(run.offers[0]!.id);
        if (run.offers[0]?.id !== nextId || run.offerTiers[0] === nextTier) continue;
        const gained = run.offerTiers[0]!;
        const stats = run.statsFor(nextId, gained);
        const was = run.statsFor(nextId, nextTier);
        return {
          code: "BANISH_UPGRADES_THE_NEXT_CARD", errorType: "economy_exploit", severity: "critical",
          system: "market / banish",
          file: "src/core/run.ts", symbol: "Run.removeFromPool",
          expected: "banishing a card removes its tier along with it; every card left " +
                    "keeps the rarity it was rolled at, and the only way to raise a " +
                    "relic's tier is to merge two of them",
          observed: `seed ${seed}, wave 30: shelf was [${before.join(", ")}]. Banishing the ` +
                    `top card — which is free — moved ${nextId} up a slot and handed it ` +
                    `tier ${gained} instead of ${nextTier}: ${was.damage} damage / ${was.cooldown}s ` +
                    `became ${stats.damage} damage / ${stats.cooldown}s. offerTiers is never ` +
                    `spliced (offers=${run.offers.length}, offerTiers=${run.offerTiers.length}), ` +
                    "so every surviving card inherits the tier of the slot above it, and a " +
                    "player can chain banishes to hand the last card the best tier on the shelf",
        };
      }
      return null;
    },
  },
  {
    name: "endBattle settles a finished wave exactly once",
    steps: [
      'run = new Run("hunter", 11)',
      "playMarket(); b = run.startBattle(); b.runToEnd()",
      "run.endBattle()   // the renderer's own call",
      "run.endBattle()   // a second call, as a stale handler would make",
    ],
    check() {
      const run = new Run("hunter", 11);
      playOneWave(run);
      const a = { wave: run.wave, gold: run.gold, exp: run.exp, level: run.level, phase: run.phase };
      run.endBattle();
      const b = { wave: run.wave, gold: run.gold, exp: run.exp, level: run.level, phase: run.phase };
      if (a.wave === b.wave && a.gold === b.gold && a.exp === b.exp) return null;
      return {
        code: "END_BATTLE_NOT_IDEMPOTENT", errorType: "state_desync", severity: "high",
        system: "run / phase machine",
        file: "src/core/run.ts", symbol: "Run.endBattle",
        expected: "settling a battle a second time is a no-op — the same guard " +
                  "settlePhase() already carries against a stale caller",
        observed: `one extra call took wave ${a.wave}->${b.wave}, gold ${a.gold}->${b.gold}, ` +
                  `exp ${a.exp}->${b.exp}, level ${a.level}->${b.level}, ` +
                  `phase ${a.phase}->${b.phase}: the wave's reward is paid twice and ` +
                  "the next wave is skipped without being fought",
      };
    },
  },
  {
    name: "a buff can only be taken against a grant that was earned",
    steps: [
      'run = new Run("warden", 9)   // pendingBuffChoices === 0',
      "run.takeBuff(BUFFS[0]) x3",
      "count run.buffs",
    ],
    check() {
      const run = new Run("warden", 9);
      const before = run.buffs.length;
      for (let i = 0; i < 3; i++) run.takeBuff(BUFFS[0]!);
      if (run.buffs.length === before) return null;
      return {
        code: "UNEARNED_BUFF_ACCEPTED", errorType: "rule_violation", severity: "high",
        system: "progression / buffs",
        file: "src/core/run.ts", symbol: "Run.takeBuff",
        expected: "takeBuff refuses when pendingBuffChoices is 0, the way buy() " +
                  "refuses when the gold is not there",
        observed: `${before} buffs became ${run.buffs.length} with nothing owed — ` +
                  "the only thing standing between one stale buff-card click zone " +
                  "and unlimited permanent buffs is the renderer remembering to " +
                  "destroy it (see Centre.zones, which had exactly that leak)",
      };
    },
  },
  {
    name: "settlePhase cannot pull a run out of a live battle",
    steps: [
      'run = new Run("titan", 5); playMarket(); run.startBattle()',
      "run.settlePhase() x5 mid-battle",
    ],
    check() {
      const run = new Run("titan", 5);
      playMarket(run, "competent");
      run.startBattle();
      for (let i = 0; i < 5; i++) run.settlePhase();
      if (run.phase === "battle") return null;
      return {
        code: "SETTLE_ESCAPES_BATTLE", errorType: "state_desync", severity: "critical",
        system: "run / phase machine",
        file: "src/core/run.ts", symbol: "Run.settlePhase",
        expected: "settlePhase is a no-op outside the two reward phases",
        observed: `phase became "${run.phase}" during a battle`,
      };
    },
  },
  {
    name: "destroying relics never mints gold",
    steps: [
      'run = new Run("hunter", 77); run.gold recorded',
      "take every offer into the hand and scrap it, 40 times, rerolling as needed",
      "compare gold",
    ],
    check() {
      const run = new Run("hunter", 77);
      const hand = new Hand(run);
      run.gold = 200;
      const before = run.gold;
      let spent = 0;
      for (let i = 0; i < 40; i++) {
        if (!run.offers.length) { const c = run.rerollCost; if (!run.reroll()) break; spent += c; }
        hand.takeOffer(0);
        hand.scrap();
        const uid = run.loom.relics[0]?.uid;
        if (uid !== undefined) run.scrap(uid);
      }
      if (run.gold <= before - spent) return null;
      return {
        code: "GOLD_FROM_NOTHING", errorType: "economy_exploit", severity: "critical",
        system: "economy / income",
        file: "src/core/run.ts", symbol: "Run.scrap",
        expected: "gold only ever comes from kills",
        observed: `gold went ${before} -> ${run.gold} having spent ${spent} on rerolls`,
      };
    },
  },
  {
    name: "the tray is emptied by starting a fight",
    steps: [
      'run = new Run("hunter", 21)',
      "hand.takeOffer(0); hand.toTray(true)  x3",
      "run.startBattle()",
    ],
    check() {
      const run = new Run("hunter", 21);
      const hand = new Hand(run);
      for (let i = 0; i < 3 && run.offers.length; i++) {
        hand.takeOffer(0);
        hand.toTray(true);
      }
      const staged = run.tray.length;
      run.startBattle();
      if (run.tray.length === 0) return null;
      return {
        code: "TRAY_SURVIVED_INTO_BATTLE", errorType: "rule_violation", severity: "medium",
        system: "market / tray",
        file: "src/core/run.ts", symbol: "Run.startBattle",
        expected: "anything left in the tray when the fight begins is scrapped",
        observed: `${staged} staged, ${run.tray.length} still there once the battle started`,
      };
    },
  },
  {
    name: "merging stops at Epic",
    steps: [
      'run = new Run("hunter", 4)',
      "place two bolt_needles, merge repeatedly past tier 4",
    ],
    check() {
      const run = new Run("hunter", 4);
      const def = RELIC_BY_ID.get("bolt_needle")!;
      for (let i = 0; i < 30; i++) {
        const spot = run.loom.findSpot(def.footprint, run.env);
        if (!spot) break;
        const placed = run.loom.place(def, spot.x, spot.y, spot.rot, 0);
        if (!placed) break;
        const top = run.loom.relics.reduce((a, b) => (b.tier > a.tier ? b : a), run.loom.relics[0]!);
        run.loom.merge(top.uid, placed.uid);
      }
      const over = run.loom.relics.find((r) => r.tier > MAX_TIER);
      if (!over) return null;
      return {
        code: "RELIC_TIER_RANGE", errorType: "invariant_break", severity: "high",
        system: "loom / merge",
        file: "src/core/grid.ts", symbol: "Loom.merge",
        expected: `a relic never climbs past tier ${MAX_TIER}`,
        observed: `${over.defId} reached tier ${over.tier}`,
      };
    },
  },
  {
    name: "expansion stays inside the envelope",
    steps: [
      'run = new Run("titan", 8); run.pendingExpansionCells = 200',
      "run.expandInto(x, y) for every x,y in -3..9",
    ],
    check() {
      const run = new Run("titan", 8);
      run.pendingExpansionCells = 200;
      for (let y = -3; y < 10; y++) for (let x = -3; x < 10; x++) run.expandInto(x, y);
      const snap = snapshotRun(run, null);
      const bad = inspect(snap, null).find(
        (v) => v.code === "UNLOCKED_OUTSIDE_ENVELOPE" || v.code === "LOOM_OVERGROWN");
      return bad ?? null;
    },
  },
  {
    name: "out-of-range market indices are refused, not thrown on",
    steps: [
      'run = new Run("hunter", 3)',
      "run.takeOffer(-1), (99), (NaN); hand.takeOffer(same)",
    ],
    check() {
      const run = new Run("hunter", 3);
      const hand = new Hand(run);
      try {
        for (const i of [-1, 99, Number.NaN, 1.5]) {
          run.takeOffer(i);
          hand.takeOffer(i);
          hand.cancel();
        }
      } catch (err) {
        return {
          code: "MARKET_INDEX_THROWS", errorType: "crash", severity: "high",
          system: "market / relic offers",
          file: "src/core/run.ts", symbol: "Run.takeOffer",
          expected: "an illegal index is refused with false",
          observed: `threw: ${String(err).slice(0, 160)}`,
        };
      }
      return null;
    },
  },
  {
    name: "the buff screen is dealt once and held",
    steps: [
      'run = new Run("hunter", 31); play waves until phase === "buff"',
      "read run.buffChoices() ten times without picking",
    ],
    check() {
      const run = new Run("hunter", 31);
      for (let i = 0; i < 12 && run.phase !== "buff"; i++) {
        if (run.phase === "market") playOneWave(run);
        else if (run.phase === "expansion") { run.pendingExpansionCells = 0; run.settlePhase(); }
        else break;
      }
      if (run.phase !== "buff") return null;
      const first = run.buffChoices().map((b) => b.id).join(",");
      for (let i = 0; i < 9; i++) {
        const again = run.buffChoices().map((b) => b.id).join(",");
        if (again !== first) {
          return {
            code: "BUFF_OFFER_REROLLED", errorType: "economy_exploit", severity: "high",
            system: "progression / buffs",
            file: "src/core/run.ts", symbol: "Run.buffChoices",
            expected: "reading the buff screen does not reroll it",
            observed: `[${first}] became [${again}] on read ${i + 2}`,
          };
        }
      }
      return null;
    },
  },
  {
    name: "a banished relic never comes back",
    steps: [
      'run = new Run("warden", 17)',
      "banish one relic, then reroll the market 200 times",
    ],
    check() {
      const run = new Run("warden", 17);
      const victim = run.offers[0]?.id;
      if (!victim) return null;
      run.removeFromPool(victim);
      run.gold = 100000;
      for (let i = 0; i < 200; i++) {
        run.reroll();
        if (run.offers.some((o) => o.id === victim)) {
          return {
            code: "BANISHED_RELIC_OFFERED", errorType: "rule_violation", severity: "high",
            system: "market / banish",
            file: "src/core/run.ts", symbol: "Run.rollOffers",
            expected: "a banished relic is gone from the pool for the rest of the run",
            observed: `${victim} was offered again after ${i + 1} rerolls`,
          };
        }
      }
      return null;
    },
  },
  {
    name: "a Disruptor unravelling the loom mid-battle leaves it consistent",
    steps: [
      'run = new Run("hunter", 55); play to wave 15 (the Disruptor wave)',
      "fight it out and inspect the loom every 30 ticks",
    ],
    check() {
      const run = new Run("hunter", 55);
      for (let guard = 0; guard < 60 && run.wave < 15 && run.phase !== "over"; guard++) {
        if (run.phase === "market") playOneWave(run);
        else if (run.phase === "buff") { run.takeBuff(run.buffChoices()[0]!); run.settlePhase(); }
        else if (run.phase === "expansion") {
          const c = run.expandableCells()[0];
          if (c) run.expandInto(c[0], c[1]); else run.pendingExpansionCells = 0;
          run.settlePhase();
        } else break;
      }
      if (run.phase !== "market" || run.wave !== 15) return null;
      playMarket(run, "competent");
      const b = run.startBattle();
      for (let t = 0; t < 600 * 30 && !b.finished; t++) {
        playUlt(b, "competent");
        b.tick();
        if (t % 30 === 0) {
          const bad = inspect(snapshotRun(run, null), null)[0];
          if (bad) return bad;
        }
      }
      return inspect(snapshotRun(run, null), null)[0] ?? null;
    },
  },
];

export interface ProbeOutcome {
  name: string;
  steps: string[];
  violation: Violation | null;
  threw: string | null;
}

export function runProbes(): ProbeOutcome[] {
  return PROBES.map((p) => {
    try {
      return { name: p.name, steps: p.steps, violation: p.check(), threw: null };
    } catch (err) {
      return { name: p.name, steps: p.steps, violation: null, threw: String(err).slice(0, 300) };
    }
  });
}
