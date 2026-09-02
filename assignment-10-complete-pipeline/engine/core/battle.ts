/**
 * The battle core. Pure: no Phaser, no DOM, no clock of its own.
 *
 * The renderer subscribes to this and draws; the headless simulator imports
 * the SAME module and runs it flat out. One implementation, two consumers —
 * which is what makes "wave 12 is fair" a measured claim (combat-model.md).
 *
 * Positions are fractions of the lane: 1 = spawn line, 0 = the Beacon.
 */
import { BEACON_HP, ENEMIES, LANE_HALF_WIDTH, RELIC_BY_ID, spawnSpanFor, TICK_HZ } from "./content.js";
import type { Loom } from "./grid.js";
import type { Rng } from "./rng.js";
import type { EnemyKind, HitPattern, RelicDef, TierStats, UltStats, UltimateDef, WaveSpec } from "./types.js";

/**
 * How a relic's stats are resolved at fire time. The run supplies this so
 * buffs apply without the battle knowing what a buff is; the default is the
 * unmodified table, which is what the law tests exercise.
 */
export type StatsResolver = (defId: string, tier: number) => TierStats;

/** Same idea for the ultimate: the run owns the buffs, the battle just asks. */
export type UltResolver = (def: UltimateDef) => UltStats;

export interface Enemy {
  id: number;
  kind: EnemyKind;
  hp: number;
  maxHp: number;
  pos: number;        // 1 -> 0 down the lane
  /** Across the lane, -LANE_HALF_WIDTH .. +LANE_HALF_WIDTH. 0 is the Beacon's line. */
  x: number;
  speed: number;      // lane fractions per second
  stopAt: number;
  damage: number;
  attackInterval: number;
  attackTimer: number;
  slowUntil: number;
  /** Stopped where it stands: no advance, no attack, until this moment. */
  stunUntil: number;
  /** Taking `burnDps` a second until then, credited to `burnBy`. */
  burnUntil: number;
  burnDps: number;
  burnBy: number;
  /** Takes SHRED_BONUS more damage from every source until then. */
  shredUntil: number;
  isBoss: boolean;
}

export type BattleEvent =
  // The shot carries the shape it actually COVERED: the renderer cannot
  // recover it afterwards, because the target is often reaped in the same tick
  // that produced the shot.
  | { t: "shot"; relicUid: number; targetId: number; damage: number; hits: number;
      pos: number; x: number;
      cone: { aim: number; spread: number; range: number } | null }
  | { t: "kill"; enemyId: number; gold: number; exp: number }
  | { t: "beaconHit"; damage: number }
  | { t: "ult"; id: string; pos: number; x: number }
  | { t: "blast"; pos: number; x: number; radius: number }
  | { t: "unravel"; lost: boolean }
  | { t: "waveClear" }
  | { t: "defeat" };

export interface BattleResult {
  cleared: boolean;
  goldEarned: number;
  expEarned: number;
  /** Damage dealt per relic uid — feeds the score screen and the sim. */
  damageByRelic: Map<number, number>;
}

const DT = 1 / TICK_HZ;

/**
 * The bearing of a point as seen from the Beacon, which sits at (0, 0).
 * A Burst cone is an interval of these — tip at the Beacon, widening with
 * distance, the way a shot leaving a barrel does.
 */
export const bearing = (x: number, pos: number): number =>
  Math.atan2(x, Math.max(1e-4, pos));

/**
 * How far a Remnant is from the Beacon. Reach is a RADIUS, not a depth: a cone
 * is a true sector, bounded by an arc, so what decides whether something is in
 * range is its distance from the muzzle and nothing else.
 */
export const distance = (x: number, pos: number): number => Math.hypot(x, pos);

/**
 * The four effects the roster declared and the engine never had.
 *
 * `pierce` and `slow_20` were implemented; `burn`, `knock`, `armor_shred` and
 * `stun_10` were text on a card. Four of nine relics promised something and did
 * nothing, which is a game lying to its player about what it sells.
 *
 * `armor_shred` needed a reading, because enemies have no armour to shred and
 * giving them some would re-balance every relic at once. Its own description
 * offers the other half — "shred armour and weaken defences" — so it lands as
 * vulnerability: the target takes more from every source while it holds. Same
 * fantasy, no new stat.  All [TUNE].
 */
const BURN_SECONDS = 3;
/** Per second, as a fraction of the shot that lit it. */
const BURN_RATE = 0.25;
/** How far up the lane a knock shoves its target. */
const KNOCK_DISTANCE = 0.06;
const STUN_CHANCE = 0.10;
/**
 * 2.5s, not 1s, and the number is load-bearing.
 *
 * `burst_bomb` trades slow for stun at tier 3, so tier 3 has to be worth more
 * than tier 2 or upgrading the relic makes it worse — which is exactly what it
 * did. Slow is 20% off the speed for a second: 0.2 seconds of held ground,
 * every time. A 10% chance of a full stop has to beat that, which needs it to
 * last longer than two seconds. Measured at 2.5s below.
 */
const STUN_SECONDS = 2.5;
const SHRED_SECONDS = 3;
const SHRED_BONUS = 0.25;

/** Half-angle that reads as "a line" rather than a cone. [TUNE] */
const LINE_HALF = 0.05;

/**
 * Who a shot lands on. Category decides it unless the relic says otherwise, and
 * `pierce` earns a line wherever it appears — that is what the word promises.
 */
export function patternFor(def: RelicDef, stats: TierStats): HitPattern {
  if (def.pattern) return def.pattern;
  if (def.category === "Burst") return "cone";
  if (stats.effect === "pierce") return "line";
  return "single";
}

/**
 * The middle of the battlefield: halfway down the lane, dead centre across it.
 * The Knot is thrown HERE, always, rather than onto whatever crowd happens to
 * be thickest — a fixed choke point the Remnants must walk through, not a
 * shot that follows them.
 */
export const MID_LANE = { pos: 0.5, x: 0 } as const;

export class Battle {
  readonly enemies: Enemy[] = [];
  beaconHp: number;
  elapsed = 0;
  private nextId = 1;
  private queue: { at: number; kind: EnemyKind }[] = [];
  private goldEarned = 0;
  private expEarned = 0;
  readonly damageByRelic = new Map<number, number>();
  private unravelTimer = 0;
  finished: null | BattleResult = null;

  /** The ultimate: ready at the start of every wave, then on its cooldown. */
  ultCooldownLeft = 0;
  ultDamage = 0;
  ultCasts = 0;
  /** Blades in the air, each with its own fuse. Read by the renderer. */
  readonly blasts: { at: number; pos: number; x: number; radius: number; damage: number }[] = [];
  /** Knots grinding the lane. Read by the renderer. */
  readonly knots: { until: number; pos: number; x: number; radius: number; pull: number; dps: number }[] = [];

  constructor(
    readonly wave: WaveSpec,
    readonly loom: Loom,
    readonly rng: Rng,
    readonly envelope: { w: number; h: number },
    beaconHp = BEACON_HP,
    readonly onEvent: (e: BattleEvent) => void = () => {},
    readonly resolveStats: StatsResolver =
      (id, tier) => RELIC_BY_ID.get(id)!.tiers[tier]!,
    readonly ult: UltimateDef | null = null,
    readonly resolveUlt: UltResolver = (d) => ({
      cooldown: d.cooldown, worthSeconds: d.worthSeconds,
      radius: d.radius, duration: d.duration ?? 0,
    }),
  ) {
    this.beaconHp = beaconHp;
    for (const g of wave.spawns) {
      for (let i = 0; i < g.count; i++) {
        const at = g.fromS + (g.count === 1 ? 0 : (g.overS * i) / (g.count - 1));
        this.queue.push({ at, kind: g.kind });
      }
    }
    this.queue.sort((a, b) => a.at - b.at);
    for (const r of loom.relics) r.cooldownLeft = 0;
  }

  /** Advance one fixed tick. Speed multipliers call this N times per frame. */
  tick(): void {
    if (this.finished) return;
    this.elapsed += DT;

    while (this.queue.length && this.queue[0]!.at <= this.elapsed) {
      this.spawn(this.queue.shift()!.kind);
    }

    this.moveEnemies();
    this.runUltimate();
    this.fireRelics();
    this.runBossAbilities();

    if (this.beaconHp <= 0) {
      this.onEvent({ t: "defeat" });
      this.finished = { cleared: false, goldEarned: this.goldEarned,
                        expEarned: this.expEarned, damageByRelic: this.damageByRelic };
    } else if (!this.queue.length && !this.enemies.length) {
      this.onEvent({ t: "waveClear" });
      this.finished = { cleared: true, goldEarned: this.goldEarned,
                        expEarned: this.expEarned, damageByRelic: this.damageByRelic };
    }
  }

  private spawn(kind: EnemyKind): void {
    const def = ENEMIES[kind]!;
    const scale = def.isBoss ? this.wave.bossHpScale
      : kind === "gunner" ? this.wave.gunnerHpScale
      : this.wave.hpScale;
    const hp = Math.round(def.hp * scale);
    this.enemies.push({
      id: this.nextId++, kind, hp, maxHp: hp, pos: 1,
      x: (this.rng.next() * 2 - 1) * spawnSpanFor(def.stopAt),
      speed: (1 / def.crossSeconds) * this.wave.speedScale,
      stopAt: def.stopAt, damage: def.damage, attackInterval: def.attackInterval,
      attackTimer: 0, slowUntil: 0, stunUntil: 0, burnUntil: 0, burnDps: 0, burnBy: 0, shredUntil: 0, isBoss: def.isBoss,
    });
  }

  private moveEnemies(): void {
    for (const e of this.enemies) {
      // Burn ticks whether or not the Remnant can move, and is credited to the
      // relic that lit it so damage-per-relic still adds up on the score screen.
      if (this.elapsed < e.burnUntil && e.burnDps > 0) {
        this.applyDamage(e, e.burnDps * DT, e.burnBy);
      }
      // Stunned: it neither advances nor attacks. Checked before movement so a
      // Remnant already at the Beacon stops hitting it too.
      if (this.elapsed < e.stunUntil) continue;
      const slowed = this.elapsed < e.slowUntil ? 0.8 : 1;
      if (e.pos > e.stopAt) {
        e.pos = Math.max(e.stopAt, e.pos - e.speed * slowed * DT);
      } else {
        e.attackTimer -= DT;
        if (e.attackTimer <= 0) {
          e.attackTimer = e.attackInterval;
          this.beaconHp -= e.damage;
          this.onEvent({ t: "beaconHit", damage: e.damage });
        }
      }
    }
  }

  /**
   * What an ultimate is priced in: the loom's raw output per second, from the
   * UNBUFFED table. Cells and tiers only.
   *
   * Pricing it on the buffed arsenal was measured and failed at the thing it
   * was for. Relic buffs inflated the ultimate too, so spending a pick on the
   * ultimate starved the very arsenal it was priced against: taking EVERY
   * ultimate buff offered across a whole run moved its share of a late wave
   * from 10% to 11%. The buffs paid for themselves and nothing else, which is
   * the definition of a pick nobody should take.
   *
   * Raw pricing separates the two. The ultimate grows with the loom, so it is
   * never useless; the arsenal grows with the loom AND with every relic buff,
   * so it steadily outgrows the ultimate; and the three ultimate buffs are the
   * only thing that closes that gap. The ultimate is not weakened on purpose
   * anywhere — its power is held constant and the waves grow around it.
   *
   * Burst relics count once even though they splash: this is a scaling anchor,
   * not a damage model.
   */
  arsenalDps(): number {
    let dps = 0;
    for (const r of this.loom.relics) {
      const st = RELIC_BY_ID.get(r.defId)?.tiers[r.tier];
      if (st) dps += st.damage / Math.max(0.05, st.cooldown);
    }
    return dps;
  }

  /** Whether the button should read as armed. */
  get ultReady(): boolean {
    return !!this.ult && !this.finished && this.ultCooldownLeft <= 0;
  }

  /**
   * Whether a cast right now would touch anything. Not the same as "the lane
   * has enemies": the wave breaks from the Beacon outward and reaches only
   * part of the lane, so early in a wave it can be armed, pressed, and connect
   * with nothing. Burning a twenty-second cooldown on that is a punishment for
   * pressing the only button the game offers, and the browser check caught it
   * doing exactly that on the Titan.
   */
  get ultWouldConnect(): boolean {
    if (!this.ult || !this.enemies.length) return false;
    const st = this.resolveUlt(this.ult);
    if (this.ult.id === "wave") {
      return this.enemies.some((e) => distance(e.x, e.pos) <= st.radius);
    }
    if (this.ult.id === "vortex") {
      // The Knot holds the middle for several seconds, so anything still at or
      // above it will walk into it. Anything already past it never comes back.
      return this.enemies.some((e) => e.pos >= MID_LANE.pos - st.radius);
    }
    return true;
  }

  /**
   * The one live input in a battle. Returns false when it did not fire, which
   * includes an empty lane — a cast into nothing would burn the cooldown for
   * no reason, and the player pressing early should not be punished for it.
   */
  castUltimate(): boolean {
    if (!this.ultReady || !this.ultWouldConnect) return false;
    const def = this.ult!;
    const st = this.resolveUlt(def);
    // The whole cast is worth N seconds of the player's own loom, SHARED by
    // what it catches. Per-target instead of shared would scale with the wave
    // size and delete late waves outright.
    const pool = this.arsenalDps() * st.worthSeconds;
    this.ultCooldownLeft = st.cooldown;
    this.ultCasts++;

    if (def.id === "wave") {
      // Rolls out from the Beacon: hits what is closest, and buys time by
      // throwing it back up the lane. The only ultimate that moves enemies.
      const caught = this.enemies.filter((e) => distance(e.x, e.pos) <= st.radius);
      this.onEvent({ t: "ult", id: def.id, pos: 0, x: 0 });
      if (caught.length) {
        const each = pool / caught.length;
        for (const e of caught) {
          this.applyUltDamage(e, each);
          e.pos = Math.min(1, e.pos + (def.knockback ?? 0));
        }
        this.reap();
      }
      return true;
    }

    if (def.id === "vortex") {
      const at = MID_LANE;
      this.knots.push({
        until: this.elapsed + st.duration, pos: at.pos, x: at.x, radius: st.radius,
        pull: def.pull ?? 0, dps: pool / Math.max(0.1, st.duration),
      });
      this.onEvent({ t: "ult", id: def.id, pos: at.pos, x: at.x });
      return true;
    }

    // barrage: blades spread across separate clusters, each on its own fuse.
    const shots = def.shots ?? 1;
    const spent = new Set<number>();
    this.onEvent({ t: "ult", id: def.id, pos: 1, x: 0 });
    for (let i = 0; i < shots; i++) {
      const at = this.bestCluster(st.radius, spent);
      for (const e of this.enemies)
        if (Math.hypot(e.pos - at.pos, e.x - at.x) <= st.radius) spent.add(e.id);
      this.blasts.push({
        at: this.elapsed + (def.fuse ?? 0) + i * 0.12,
        pos: at.pos, x: at.x, radius: st.radius, damage: pool / shots,
      });
    }
    return true;
  }

  /**
   * The lane point covering the most enemies, ignoring any already claimed by
   * an earlier blade. Ties break toward the Beacon, because the enemy about to
   * arrive is worth more than the one that just spawned.
   */
  private bestCluster(radius: number, claimed: Set<number>): { pos: number; x: number } {
    const pool = this.enemies.filter((e) => !claimed.has(e.id));
    const from = pool.length ? pool : this.enemies;
    if (!from.length) return { pos: 0.5, x: 0 };
    const cover = (p: { pos: number; x: number }) =>
      from.filter((o) => Math.hypot(o.pos - p.pos, o.x - p.x) <= radius).length;
    return from.reduce<{ pos: number; x: number }>((best, c) => {
      const bc = cover(best), cc = cover(c);
      if (cc !== bc) return cc > bc ? { pos: c.pos, x: c.x } : best;
      return c.pos < best.pos ? { pos: c.pos, x: c.x } : best;
    }, { pos: from[0]!.pos, x: from[0]!.x });
  }

  private applyUltDamage(e: Enemy, amount: number): void {
    e.hp -= amount;
    this.ultDamage += amount;
  }

  /** Cooldown, blades landing, and knots grinding. */
  private runUltimate(): void {
    if (this.ultCooldownLeft > 0) this.ultCooldownLeft -= DT;

    for (let i = this.blasts.length - 1; i >= 0; i--) {
      const b = this.blasts[i]!;
      if (b.at > this.elapsed) continue;
      this.blasts.splice(i, 1);
      const hit = this.enemies.filter((e) => Math.hypot(e.pos - b.pos, e.x - b.x) <= b.radius);
      this.onEvent({ t: "blast", pos: b.pos, x: b.x, radius: b.radius });
      if (!hit.length) continue;
      const each = b.damage / hit.length;
      for (const e of hit) this.applyUltDamage(e, each);
      this.reap();
    }

    for (let i = this.knots.length - 1; i >= 0; i--) {
      const k = this.knots[i]!;
      if (k.until <= this.elapsed) { this.knots.splice(i, 1); continue; }
      const inside = this.enemies.filter((e) => Math.hypot(e.pos - k.pos, e.x - k.x) <= k.radius);
      for (const e of this.enemies) {
        // Dragged across the lane, always: that is the gathering, and moving
        // sideways never brings a Remnant closer to the Beacon.
        const dx = k.x - e.x;
        if (Math.abs(dx) > 1e-4) {
          e.x += Math.min(Math.abs(dx), k.pull * DT) * Math.sign(dx);
        }
        // Along the lane the Knot may only ever pull a Remnant BACK, never
        // forward. Thrown at a fixed point mid-lane, most of a young wave is
        // above it, so a symmetric pull hauled the whole lane 0.2 closer to the
        // Beacon every cast — the Warden's own ultimate delivering the wave it
        // was meant to hold. Measured at median depth 4, against 21 for never
        // casting it at all.
        if (e.pos < k.pos) {
          e.pos = Math.min(k.pos, Math.max(e.stopAt, e.pos + k.pull * DT));
        }
      }
      if (inside.length) {
        const each = (k.dps * DT) / inside.length;
        for (const e of inside) this.applyUltDamage(e, each);
        this.reap();
      }
    }
  }

  /** Targeting per category, with the overkill guard (combat-model.md). */
  private fireRelics(): void {
    for (const relic of this.loom.relics) {
      relic.cooldownLeft -= DT;
      if (relic.cooldownLeft > 0) continue;

      const def = RELIC_BY_ID.get(relic.defId);
      if (!def) continue;
      const stats = this.resolveStats(relic.defId, relic.tier);

      // A relic can only reach enemies within `range` of the Beacon.
      // In range means within `range` OF THE BEACON, measured as a distance.
      const reachable = this.enemies.filter((e) => distance(e.x, e.pos) <= stats.range);
      // OVERKILL GUARD: dead enemies are reaped immediately after each relic
      // fires (see the reap() call below), so by the time the next relic in
      // this tick chooses, anything already killed has left the list. That is
      // the guarantee combat-model.md asks for — six relics cannot dump into
      // one dying walker. If projectiles are ever given travel time, this
      // becomes insufficient and damage-in-flight must be tracked per enemy.
      const live = reachable;
      if (!live.length) continue;

      let target: Enemy;
      if (def.category === "Burst") {
        const spread = stats.spread ?? 0.25;
        // Aim the cone where it catches the most; ties to the nearest Remnant,
        // because the one about to arrive is worth more than the one that just
        // spawned.
        const caught = (e: Enemy) =>
          reachable.filter((o) => Math.abs(bearing(o.x, o.pos) - bearing(e.x, e.pos)) <= spread).length;
        target = live.reduce((best, cand) => {
          const bc = caught(best), cc = caught(cand);
          if (cc !== bc) return cc > bc ? cand : best;
          return cand.pos < best.pos ? cand : best;
        }, live[0]!);
      } else {
        // Bolt and turret Constructs: closest to the Beacon.
        target = live.reduce((a, b) => (b.pos < a.pos ? b : a), live[0]!);
      }

      relic.cooldownLeft = stats.cooldown;
      // Everything inside the cone and within reach. There is no target cap
      // any more: the cone's own geometry is the limit, and a cap the player
      // could not see was doing that job invisibly.
      const aim = bearing(target.x, target.pos);
      const pattern = patternFor(def, stats);
      // A cone of half-angle PI is the whole disc, and one of LINE_HALF is a
      // line, so all three area patterns are the same sector test — and the
      // renderer draws all three without knowing they differ.
      const spread = pattern === "ring" ? Math.PI
        : pattern === "line" ? LINE_HALF
        : stats.spread ?? 0.25;
      const hit = pattern === "single"
        ? [target]
        : this.enemies.filter((e) =>
            distance(e.x, e.pos) <= stats.range &&
            Math.abs(bearing(e.x, e.pos) - aim) <= spread);

      for (const e of hit) {
        this.applyDamage(e, stats.damage, relic.uid);
        switch (stats.effect) {
          case "slow_20": e.slowUntil = this.elapsed + 1.0; break;
          case "burn":
            // Refreshes rather than stacks: two Burst relics burning the same
            // Remnant should not multiply, or a category that already hits
            // several targets compounds with itself.
            e.burnUntil = this.elapsed + BURN_SECONDS;
            e.burnDps = Math.max(e.burnDps, stats.damage * BURN_RATE);
            e.burnBy = relic.uid;
            break;
          case "knock":
            // Backwards only, and never past where it came from. A knock that
            // could push a Remnant forward would help it.
            e.pos = Math.min(1, e.pos + KNOCK_DISTANCE);
            break;
          case "armor_shred": e.shredUntil = this.elapsed + SHRED_SECONDS; break;
          case "stun_10":
            if (this.rng.next() < STUN_CHANCE) e.stunUntil = this.elapsed + STUN_SECONDS;
            break;
          default: break;
        }
      }
      this.onEvent({
        t: "shot", relicUid: relic.uid, targetId: target.id, damage: stats.damage,
        hits: hit.length,
        pos: target.pos, x: target.x,
        cone: pattern === "single" ? null : { aim, spread, range: stats.range },
      });
      this.reap();
    }
  }

  private applyDamage(e: Enemy, amount: number, relicUid: number): void {
    // Vulnerability multiplies every source, not just the relic that applied
    // it — that is what makes armor_shred a support effect rather than a
    // private damage bonus, and why the Bolt that carries it is worth bringing
    // alongside others instead of instead of them.
    const dealt = this.elapsed < e.shredUntil ? amount * (1 + SHRED_BONUS) : amount;
    e.hp -= dealt;
    this.damageByRelic.set(relicUid, (this.damageByRelic.get(relicUid) ?? 0) + dealt);
  }

  private reap(): void {
    for (let i = this.enemies.length - 1; i >= 0; i--) {
      const e = this.enemies[i]!;
      if (e.hp > 0) continue;
      const gold = e.isBoss ? 40 : e.kind === "gunner" ? 3 : 2;
      const exp = e.isBoss ? 30 : 2;
      this.goldEarned += gold;
      this.expEarned += exp;
      this.enemies.splice(i, 1);
      this.onEvent({ t: "kill", enemyId: e.id, gold, exp });

      if (e.kind === "splitter") {
        for (let n = 0; n < 3; n++) this.spawnAt("walker", e.pos, e.x);
      }
    }
  }

  private spawnAt(kind: EnemyKind, pos: number, x = 0): void {
    const def = ENEMIES[kind]!;
    const hp = Math.round(def.hp * this.wave.hpScale);
    this.enemies.push({
      id: this.nextId++, kind, hp, maxHp: hp, pos,
      // Spawned beside the parent, not on top of it, so a splitter's brood is
      // a spread rather than one stack a single cone deletes — but never
      // outside where its kind may come to rest and still be shot at.
      x: Math.max(-spawnSpanFor(def.stopAt), Math.min(spawnSpanFor(def.stopAt),
        x + (this.rng.next() * 2 - 1) * 0.22)),
      speed: (1 / def.crossSeconds) * this.wave.speedScale,
      stopAt: def.stopAt, damage: def.damage, attackInterval: def.attackInterval,
      attackTimer: 0, slowUntil: 0, stunUntil: 0, burnUntil: 0, burnDps: 0, burnBy: 0, shredUntil: 0, isBoss: false,
    });
  }

  /** The Disruptor unravels on arrival and every 20 s while it lives. */
  private runBossAbilities(): void {
    const disruptor = this.enemies.find((e) => e.kind === "disruptor" && e.pos <= e.stopAt);
    if (!disruptor) { this.unravelTimer = 0; return; }
    this.unravelTimer -= DT;
    if (this.unravelTimer > 0) return;
    this.unravelTimer = 20;
    const r = this.loom.unravelHighest(this.envelope);
    if (r) this.onEvent({ t: "unravel", lost: r.lost });
  }

  /** Run to completion without a renderer. Used by the simulator. */
  /**
   * `onTick` is where a bot makes the one decision a human makes in a battle.
   * The renderer does not use it — a person presses the button — but the
   * simulator has to, or it measures a game with the ultimate switched off.
   */
  runToEnd(maxSeconds = 600, onTick?: (b: Battle) => void): BattleResult {
    const limit = maxSeconds * TICK_HZ;
    for (let i = 0; i < limit && !this.finished; i++) { onTick?.(this); this.tick(); }
    return this.finished ?? { cleared: false, goldEarned: this.goldEarned,
      expEarned: this.expEarned, damageByRelic: this.damageByRelic };
  }
}
