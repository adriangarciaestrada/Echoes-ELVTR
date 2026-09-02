/**
 * An auto-player. Not clever — deliberately a "competent" reference player, so
 * measurements describe the game rather than the bot. A separate random policy
 * gives the lower bound; the gap between them is the SKILL GRADIENT, which is
 * the band wave-contract.md actually gates on.
 */
import { MID_LANE, patternFor, type Battle } from "../../engine/core/battle.js";
import type { HitPattern } from "../../engine/core/types.js";
import { RELIC_BY_ID } from "../../engine/core/content.js";
import { UPGRADES, type Run } from "../../engine/core/run.js";

/** A/B control: the same curve with the one live input never used. */
const ULT_OFF = typeof process !== "undefined" && !!process.env.LOOM_NO_ULT;

export type PolicyName = "competent" | "random";

/**
 * Expected targets per shot, by hit pattern. Measured over 40 runs and ~1.2M
 * shots, not guessed. [TUNE] — re-measure when reach or spread changes.
 *
 * Without this the bot ranked offers on raw damage-per-cell, which is the value
 * of a shot that hits exactly one enemy. Every area relic was therefore priced
 * as if its area did not exist: the orbiter sweeps 5.81 enemies a shot and was
 * ranked last in the game, evaluated after the space was gone and scrapped first
 * when space ran short. Its 1% pick rate measured this function, not the relic.
 */
const EXPECTED_TARGETS: Record<HitPattern, number> = {
  single: 1.0, line: 1.7, cone: 3.2, ring: 5.8,
};

function damagePerCell(run: Run, defId: string, tier: number): number {
  const s = run.statsFor(defId, tier);
  const def = RELIC_BY_ID.get(defId)!;
  const cells = def.footprint.length;
  return s.damage / s.cooldown / cells * EXPECTED_TARGETS[patternFor(def, s)];
}

/** Merge every legal pair, best-first. Frees cells and unlocks effects. */
function mergeAll(run: Run): void {
  let merged = true;
  while (merged) {
    merged = false;
    const rs = run.loom.relics;
    outer: for (let i = 0; i < rs.length; i++) {
      for (let j = i + 1; j < rs.length; j++) {
        const a = rs[i]!, b = rs[j]!;
        if (a.defId === b.defId && a.tier === b.tier && a.tier < 4) {
          if (run.loom.merge(a.uid, b.uid)) { merged = true; break outer; }
        }
      }
    }
  }
}

/**
 * Spend gold. Unspent gold is wasted gold — it does not survive the run — so a
 * competent player empties the purse every market, repairing when hurt and
 * otherwise buying compounding upgrades.
 */
function spend(run: Run): void {
  for (let guard = 0; guard < 20; guard++) {
    const hurt = run.beaconHp < run.beaconMax * 0.6;
    const order = UPGRADES.slice().sort((a, b) => {
      const rank = (u: typeof a) =>
        u.id === "repair" ? (hurt ? 0 : 9) :
        u.id === "study" ? 1 : u.id === "reroll" ? 2 : 3;
      return rank(a) - rank(b);
    });
    const pick = order.find((u) => run.canBuy(u));
    if (!pick) return;
    run.buy(pick);
  }
}

export function playMarket(run: Run, policy: PolicyName): void {
  if (policy === "random") {
    // Take the first thing that fits, never merge, never reroll.
    for (let i = run.offers.length - 1; i >= 0; i--) run.takeOffer(i);
    return;
  }

  // Competent: spend free rerolls hunting merge partners, take best value,
  // then merge everything possible.
  // LOOM_ONLY=Burst restricts the bot to one category, which is how a
  // single-category strategy gets measured rather than guessed at.
  const only = typeof process !== "undefined" ? process.env.LOOM_ONLY : undefined;
  for (let attempt = 0; attempt < 3; attempt++) {
    const owned = new Set(run.loom.relics.map((r) => `${r.defId}:${r.tier}`));
    const ordered = run.offers
      .map((d, i) => ({ i, d, partner: owned.has(`${d.id}:0`) }))
      .filter((o) => !only || o.d.category === only)
      .sort((a, b) =>
        (Number(b.partner) - Number(a.partner)) ||
        (damagePerCell(run, b.d.id, 0) - damagePerCell(run, a.d.id, 0)));
    let took = false;
    for (const { d } of ordered) {
      const idx = run.offers.findIndex((o) => o.id === d.id);
      if (idx >= 0 && run.takeOffer(idx)) took = true;
    }
    mergeAll(run);
    if (took || run.rerollCost > run.gold) break;
    run.reroll();
  }
  mergeAll(run);
  // Out of space: scrap the least valuable relic so an offer can land. A
  // player who cannot free cells dead-ends on a full board of merged relics.
  if (run.loom.freeCellCount <= 1 && run.loom.relics.length > 3) {
    const worst = run.loom.relics.slice().sort((a, b) =>
      (a.tier - b.tier) || (damagePerCell(run, a.defId, a.tier) - damagePerCell(run, b.defId, b.tier)))[0];
    if (worst) run.scrap(worst.uid);
  }
  spend(run);
}

export function playBuff(run: Run, policy: PolicyName): void {
  const choices = run.buffChoices();
  if (!choices.length) return;
  if (policy === "random") { run.takeBuff(choices[0]!); return; }

  // Competent: back the category holding the most cells; repair when hurt.
  const weight: Record<string, number> = { Bolt: 0, Burst: 0, Construct: 0 };
  for (const r of run.loom.relics) {
    const def = RELIC_BY_ID.get(r.defId)!;
    weight[def.category] = (weight[def.category] ?? 0) + r.cells.length;
  }
  const best = choices.slice().sort((a, b) => {
    const score = (x: typeof a) => {
      const e = x.effect;
      if (e.k === "repair") return run.beaconHp < 55 ? 100 : 0;
      if (e.k === "range") return 5;
      // The ultimate is priced in seconds of the whole loom, so a percentage
      // of it is worth roughly that percentage of every cell on the board.
      if (e.k === "ult_damage" || e.k === "ult_cooldown" || e.k === "ult_size") {
        // A player who never presses the ultimate would not buy buffs for it.
        // Scoring them normally in the no-ult control made the control measure
        // a bot wasting picks as well as one giving up the ability, which
        // overstates what skipping the ultimate actually costs.
        if (ULT_OFF) return -1;
        // Priced against what a category buff is worth, not against the board.
        // A category damage buff lifts every relic of that category — often
        // half the board — while an ultimate buff lifts one cast a wave, worth
        // a few per cent of a wave's damage. Scored at 0.30 the bot preferred
        // ultimate buffs to category buffs and built worse: the no-ultimate
        // control, which skips them, out-ran the bot that had the ability.
        const cells = run.loom.relics.reduce((n, r) => n + r.cells.length, 0);
        return cells * (e.k === "ult_damage" ? 0.12 : e.k === "ult_cooldown" ? 0.10 : 0.06);
      }
      return (weight[e.category] ?? 0) * (e.k === "cooldown" ? 1.3 : 1);
    };
    return score(b) - score(a);
  })[0]!;
  run.takeBuff(best);
}

export function playExpansion(run: Run): void {
  let guard = 0;
  while (run.pendingExpansionCells > 0 && guard++ < 64) {
    const cells = run.expandableCells();
    if (!cells.length) { run.reconcileExpansions(); break; }
    // Grow compactly: prefer cells adjacent to the most unlocked neighbours.
    const scored = cells.map(([x, y]) => {
      const n = [[1,0],[-1,0],[0,1],[0,-1]]
        .filter(([dx, dy]) => run.loom.isUnlocked(x + dx!, y + dy!)).length;
      return { x, y, n };
    }).sort((a, b) => b.n - a.n);
    const pick = scored[0]!;
    if (!run.expandInto(pick.x, pick.y)) break;
  }
}


/**
 * The ultimate is the only live input in a battle, so it is also the only
 * place a bot can be good or bad at PLAYING rather than at shopping. A naive
 * bot fires the instant the button lights up, which in practice means into a
 * nearly empty lane at the top of the wave. A competent one holds it for a
 * crowd, or spends it the moment something is about to reach the Beacon.
 */
export function playUlt(b: Battle, policy: PolicyName): void {
  if (ULT_OFF) return;               // A/B control: the same curve, ult unused.
  if (!b.ultReady || !b.enemies.length) return;
  if (policy === "random") { b.castUltimate(); return; }

  if (!b.ultWouldConnect) return;
  const radius = b.ult ? b.resolveUlt(b.ult).radius : 0.12;
  // A Knot cannot answer something already at the wall, so "spend it, we are
  // in trouble" is not a reason to throw one.
  const threatened = b.ult?.id !== "vortex" && b.enemies.some((e) => e.pos <= 0.30);
  // How many it would actually catch, which is not the same as how many are
  // alive: the wave reaches out from the Beacon, the other two reach anywhere.
  const covered =
    b.ult?.id === "wave"
      // Breaks out from the Beacon: what is already close.
      ? b.enemies.filter((e) => e.pos <= radius).length
      : b.ult?.id === "vortex"
        // Held at a FIXED point mid-lane, so what matters is what is standing
        // in it or will walk into it before it fades — not the thickest crowd
        // wherever it happens to be. Scoring it as a roaming blast made the bot
        // throw the Knot at moments the Knot could not reach.
        ? b.enemies.filter((e) =>
            e.pos >= MID_LANE.pos - radius &&
            e.pos <= MID_LANE.pos + radius + 0.35).length
        : b.enemies.reduce((best, c) => {
            const n = b.enemies.filter((o) => Math.abs(o.pos - c.pos) <= radius).length;
            return n > best ? n : best;
          }, 0);
  // Four is deliberately low. A threshold of six meant the bot never cast at
  // all before wave 4, so every early-wave measurement described a game with
  // the ultimate switched off — which is the opposite of where it should feel
  // strongest.
  if (threatened || covered >= 4) b.castUltimate();
}
