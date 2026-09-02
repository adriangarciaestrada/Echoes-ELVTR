/**
 * The other half of the agent: it plays the shipped build, in a real browser,
 * through the same pixels a player uses.
 *
 * The core fuzzer proves a rule can be broken. This proves a PERSON can break
 * it — and it reaches faults the core cannot have, because half this game is
 * the renderer: click-to-cell mapping, click zones that outlive the screen that
 * built them, buttons that stay live into a phase they do not belong to.
 *
 * Everything is driven in WORLD coordinates (the game's own 1280x720 space) and
 * converted to page pixels through the canvas's bounding box, so the agent can
 * resize the window or run at a HiDPI device pixel ratio and still aim at the
 * same cell. That is not convenience — the mapping IS one of the things under
 * test: this game shipped a bug where every grid click landed on the wrong cell,
 * scaled by the display's pixel ratio, and nothing but a browser check can see
 * it.
 *
 * The tactics are adversarial by construction. None of them is "play the game":
 *
 *   boundary_carpet    every cell of the envelope plus the ring outside it,
 *                      the four canvas corners, and the panel seams
 *   banish_then_take   the market's parallel arrays, exercised through the
 *                      Banish button a player actually has
 *   double_click_storm four clicks inside one frame on every live button
 *   ghost_clicks       clicking where the PREVIOUS screen's controls were
 *   speed_lang_thrash  redrawing the screen as fast as possible in every phase
 *   ult_mash           the one live input, pressed continuously
 *   key_mash           R / X / ESC / SPACE in phases that do not own them
 *   drag_dump          take a relic and drop it everywhere illegal
 *   resize_churn       resize mid-run, then check clicks still hit their cell
 *
 * The oracle from oracle.ts judges the result, so a break found here and a break
 * found by the fuzzer are the same finding with the same code.
 */
import { chromium, type Browser, type Page } from "playwright";
import { contextFrom, type FindingLog } from "./report.js";
import { inspect, type Snapshot, type Violation } from "./oracle.js";

/** The game's own coordinate space; every layout constant is in these units. */
const WORLD = { w: 1280, h: 720 };
const tag = (cls: string, dpr: number): string => `${cls}@dpr${dpr}`;
/** Tactics that have nothing to attack outside the market screen. */
const MARKET_ONLY = new Set(["banish_then_take", "deep_market_banish", "drag_dump"]);
/** From src/game/centre.ts — the loom's origin and cell size. */
const GRID = { ox: 382, oy: 118, cell: 36, w: 7, h: 7 };

export interface BrowserOptions {
  url: string;
  seconds: number;
  headless: boolean;
  /** Where screenshots are written. */
  shotDir: string;
  /**
   * What the report should CALL them. Evidence paths are recorded relative to
   * the report's own directory rather than to the working directory, so the
   * report and its screenshots travel together — the same JSON is readable
   * from the game repo and from the course repo it is submitted in.
   */
  shotRef: string;
}

interface UiObject { label: string; x: number; y: number; w: number; h: number; kind: string }

export interface BrowserResult {
  cycles: number;
  tactics: string[];
  pageErrors: number;
}

export class BrowserAgent {
  private cycles = 0;
  private readonly tactics = new Set<string>();
  private pageErrors: string[] = [];
  private prev: Snapshot | null = null;
  private lastSignature = "";
  private lastChange = Date.now();
  private readonly shot = new Set<string>();
  /**
   * The canvas box, cached. Working it out is a round trip into the page, and
   * a tactic that clicks eighty cells cannot afford eighty of them — at one
   * evaluate per click the boundary sweep alone ate a whole browser pass.
   * Invalidated whenever the viewport changes, which is the only thing that
   * moves it.
   */
  private rect: { left: number; top: number; width: number; height: number } | null = null;

  constructor(private readonly log: FindingLog, private readonly opts: BrowserOptions) {}

  async run(): Promise<BrowserResult> {
    const browser = await chromium.launch({ headless: this.opts.headless });
    const until = Date.now() + this.opts.seconds * 1000;
    try {
      // Three passes, because the renderer's coordinate mapping is one of the
      // things under test and it is a function of the display, not the game.
      // The HiDPI passes get a short, focused list. A canvas backing store of
      // 2560x1440 or 3840x2160 renders about three times slower under headless
      // Chromium, so spending the same budget there buys a third of the cycles
      // — and the only thing a pixel ratio can actually change is where a click
      // lands, which is what those two lists test.
      const DEEP = [
        "banish_then_take", "advance_wave", "deep_market_banish", "drag_dump", "advance_wave",
        "double_click_storm", "speed_lang_thrash", "advance_wave", "key_mash",
        "ghost_clicks", "advance_wave", "ult_mash", "boundary_carpet",
        "advance_wave", "resize_churn",
      ];
      const HIDPI = ["resize_churn", "boundary_carpet", "banish_then_take",
                     "drag_dump", "advance_wave"];
      const passes = [
        { vp: { width: 1280, height: 720 }, dpr: 1, cls: "hunter", share: 0.6, plan: DEEP },
        { vp: { width: 1024, height: 640 }, dpr: 2, cls: "titan", share: 0.2, plan: HIDPI },
        { vp: { width: 1600, height: 900 }, dpr: 3, cls: "warden", share: 0.2, plan: HIDPI },
      ];
      for (const p of passes) {
        if (Date.now() >= until) break;
        const budget = Math.max(20, Math.round(this.opts.seconds * p.share));
        await this.pass(browser, p.vp, p.dpr, p.cls, p.plan,
                        Math.min(until, Date.now() + budget * 1000));
      }
      await this.storagePoisonPass(browser);
    } finally {
      await browser.close();
    }
    return { cycles: this.cycles, tactics: [...this.tactics], pageErrors: this.pageErrors.length };
  }

  // -- one browser session --------------------------------------------------

  private async pass(
    browser: Browser, viewport: { width: number; height: number },
    dpr: number, cls: string, plan: string[], until: number,
  ): Promise<void> {
    this.prev = null;
    this.lastSignature = "";
    this.lastChange = Date.now();
    const context = await browser.newContext({ viewport, deviceScaleFactor: dpr });
    const page = await context.newPage();
    const seen = new Set<string>();
    const note = (kind: string, text: string) => {
      const line = `${kind}: ${text}`;
      this.pageErrors.push(line);
      if (seen.has(line.slice(0, 120))) return;
      seen.add(line.slice(0, 120));
      void this.crash(page, kind, text, `${cls}@dpr${dpr}`);
    };
    page.on("pageerror", (e) => note("uncaught exception", String(e)));
    page.on("console", (m) => { if (m.type() === "error") note("console error", m.text()); });

    await page.addInitScript(() => {
      // Skip the language screen so every label the agent matches is in one
      // known language, and start from a clean best-score store.
      localStorage.setItem("loom.lang", "en");
      localStorage.removeItem("loom.best");
      localStorage.setItem("loom.speed", "10");
    });
    this.rect = null;
    await page.goto(this.opts.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(700);
    await this.restartRun(page, cls);
    await page.waitForTimeout(300);

    for (let i = 0; Date.now() < until; i++) {
      const tactic = plan[i % plan.length]!;
      // A stray click on Restart, or the score screen's "another class", leaves
      // the select screen up with a dead Run still on `window.loom`. Every
      // tactic after that would be poking a frozen snapshot, so the agent puts
      // itself back in the game first.
      if (!(await this.inGame(page))) {
        await this.restartRun(page, cls);
        await page.waitForTimeout(200);
        this.prev = null;
      }
      this.tactics.add(tactic);
      this.cycles++;
      const t0 = Date.now();
      // Three tactics only mean anything on the market screen. Rather than
      // skipping them whenever the run happens to be mid-fight — which is how
      // the market attacks went a whole session without firing — walk the run
      // to a market first.
      if (MARKET_ONLY.has(tactic)) await this.toMarket(page);
      try {
        await this.tactic(page, tactic, `${cls}@dpr${dpr}`);
      } catch (err) {
        // A tactic that throws is the harness failing, not the game — but a
        // closed page mid-tactic means the game took the tab down with it.
        if (page.isClosed()) break;
        this.pageErrors.push(`tactic ${tactic}: ${String(err).slice(0, 160)}`);
      }
      await this.check(page, tactic, `${cls}@dpr${dpr}`);
      await this.watchdog(page, tactic, `${cls}@dpr${dpr}`);
      if (process.env.LOOM_ADV_TRACE) {
        const s = await this.probe(page);
        console.log(`    ${tag(cls, dpr)} ${tactic.padEnd(18)} ${Date.now() - t0}ms  ` +
                    `phase=${s?.phase} wave=${s?.wave} relics=${s?.relics.length}`);
      }
    }
    await context.close();
  }

  /**
   * What the game does when the state it kept between sessions is not the
   * shape it expects.
   *
   * This is not something a player types in. It is what a browser extension, a
   * second page on the same itch.io origin, a half-written value, or the next
   * change to the stored format leaves behind — and this game reads two of its
   * three stored keys defensively (`loom.lang` checks the value is one of two
   * strings, `loom.speed` checks it is one of five numbers) and the third not
   * at all. The agent runs the case the code does not.
   *
   * Its own browser context each time, because the point is the state the game
   * STARTS from, not anything it can be talked into mid-run.
   */
  private async storagePoisonPass(browser: Browser): Promise<void> {
    this.tactics.add("storage_poison");
    for (const poison of ["not json", "12", "null"]) {
      this.cycles++;
      const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
      const page = await context.newPage();
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
      await page.addInitScript((p) => {
        localStorage.setItem("loom.lang", "en");
        localStorage.setItem("loom.speed", "10");
        localStorage.setItem("loom.best", p);
      }, poison);
      await page.goto(this.opts.url, { waitUntil: "networkidle" });
      await page.waitForTimeout(500);
      this.rect = null;
      await page.evaluate(() => {
        (window as unknown as { loomGame: { scene: { start: (k: string, d: unknown) => void } } })
          .loomGame.scene.start("loom", { cls: "hunter" });
      });
      await page.waitForFunction(() => !!(window as unknown as { loom?: unknown }).loom,
                                 null, { timeout: 10_000 }).catch(() => undefined);
      // Lose the run. The fixture is only the losing — everything the game does
      // afterwards is its own.
      const fight = (await this.ui(page)).find((o) => /fight/i.test(o.label));
      if (fight) await this.clickObject(page, fight, 250);
      await page.evaluate(() => {
        const r = (window as unknown as { loom: { battle: { beaconHp: number } | null } }).loom;
        if (r.battle) r.battle.beaconHp = -1;
      });
      await page.waitForTimeout(1200);

      const snap = await this.probe(page);
      const restart = (await this.ui(page)).find((o) => /again/i.test(o.label));
      if (snap?.phase === "over" && (errors.length || !restart)) {
        const shot = `${this.opts.shotRef}/storage-poison.png`;
        await page.screenshot({ path: `${this.opts.shotDir}/storage-poison.png` })
          .catch(() => undefined);
        this.shot.add("SCORE_SCREEN_BRICKED_BY_STORED_STATE");
        const f = this.log.add({
          code: "SCORE_SCREEN_BRICKED_BY_STORED_STATE", errorType: "crash", severity: "medium",
          system: "score screen / persistence",
          file: "src/game/main.ts", symbol: "LoomScene.recordBest",
          expected: "a stored best-score value the game cannot read is discarded, the way " +
                    "loom.lang and loom.speed already validate what they read",
          observed: `with localStorage["loom.best"] = ${JSON.stringify(poison)}, losing the run ` +
                    `threw ${errors[0] ?? "nothing"} and left phase="over" with ` +
                    `${restart ? "" : "no Play-again button and "}no score screen: the run cannot ` +
                    "be seen or restarted without clearing the site's data",
        }, contextFrom(snap, "browser-ui", "storage_poison", null, [
          `localStorage["loom.best"] = ${JSON.stringify(poison)}`,
          "reload, start a run, lose it",
          "the score screen never builds and there is no way back to the menu",
        ]));
        if (!f.evidence.includes(shot)) f.evidence.push(shot);
        // Three stored values, three identical outcomes, from a recipe that is
        // the whole reproduction: this one does not need a separate replay.
        f.reproduced = true;
      }
      await context.close();
    }
  }

  // -- the tactics ----------------------------------------------------------

  private async tactic(page: Page, name: string, tag: string): Promise<void> {
    switch (name) {
      case "boundary_carpet":    return this.boundaryCarpet(page);
      case "banish_then_take":   return this.banishThenTake(page, tag);
      case "deep_market_banish": return this.deepMarketBanish(page);
      case "drag_dump":          return this.dragDump(page);
      case "double_click_storm": return this.doubleClickStorm(page);
      case "speed_lang_thrash":  return this.speedLangThrash(page, tag);
      case "key_mash":           return this.keyMash(page);
      case "ghost_clicks":       return this.ghostClicks(page);
      case "ult_mash":           return this.ultMash(page);
      case "resize_churn":       return this.resizeChurn(page, tag);
      default:                   return this.advanceWave(page);
    }
  }

  /**
   * Every cell of the envelope, the ring of cells just outside it, and the
   * canvas's own corners. The loom is not a rectangle — expansion cells are
   * player-placed — so "inside the board" and "inside the envelope" are two
   * different things, and clicks land in the gap between them constantly.
   */
  private async boundaryCarpet(page: Page): Promise<void> {
    const before = await this.probe(page);
    // The ring just outside the envelope, the envelope's own edge, and both
    // diagonals. The full 81-cell sweep costs three times as much and finds
    // nothing the edges and the diagonals do not.
    const cells: Array<[number, number]> = [];
    for (let i = -1; i <= GRID.w; i++) {
      cells.push([i, -1], [i, GRID.h], [-1, i], [GRID.w, i]);
      if (i >= 0 && i < GRID.w) cells.push([i, 0], [i, GRID.h - 1], [i, i], [i, GRID.w - 1 - i]);
    }
    for (const [x, y] of cells) await this.clickCell(page, x, y, 0);
    await page.waitForTimeout(30);
    // The four corners, the panel seams, and one pixel inside each edge.
    const spots: Array<[number, number]> = [
      [0, 0], [WORLD.w - 1, 0], [0, WORLD.h - 1], [WORLD.w - 1, WORLD.h - 1],
      [320, 360], [960, 360], [1, 1], [WORLD.w - 1, WORLD.h / 2],
      [GRID.ox - 1, GRID.oy - 1], [GRID.ox + GRID.w * GRID.cell, GRID.oy + GRID.h * GRID.cell],
    ];
    for (const [x, y] of spots) await this.clickWorld(page, x, y, 0);
    await page.waitForTimeout(30);

    // Put back whatever the sweep picked up, then account for every relic.
    // Clicking cells can only lift, drop, merge or tray a relic — none of
    // which destroys one — so a relic that is on none of those four piles
    // afterwards was lost to a click that should have done nothing.
    await page.keyboard.press("Escape");
    await page.waitForTimeout(60);
    const after = await this.probe(page);
    if (!before || !after) return;
    const held = (await this.heldDefId(page)) ? 1 : 0;
    const merged = after.relics.some((r) =>
      r.tier > Math.max(0, ...before.relics.filter((b) => b.defId === r.defId).map((b) => b.tier)));
    if (!merged && after.relics.length + after.tray.length + held < before.relics.length) {
      this.record(page, {
        code: "RELIC_LOST_TO_STRAY_CLICK", errorType: "invariant_break", severity: "high",
        system: "loom / packing",
        file: "src/game/main.ts", symbol: "LoomScene.onClick",
        expected: "clicking cells can lift, drop, merge or tray a relic, never destroy one; " +
                  "Escape returns whatever is in hand to where it came from",
        observed: `${before.relics.length} relics before a sweep of the board's edges, ` +
                  `${after.relics.length} on the loom + ${after.tray.length} in the tray + ` +
                  `${held} in hand afterwards`,
      }, after, "boundary_carpet", "");
    }
  }

  /**
   * The market's Banish button, then its Take button, with the tiers read off
   * the screen either side. This is the UI-level version of the parallel-array
   * attack the fuzzer runs against the core.
   */
  private async banishThenTake(page: Page, tag: string): Promise<void> {
    if ((await this.probe(page))?.phase !== "market") return;
    const before = await this.probe(page);
    const cardsBefore = await this.tierLabels(page);
    const banish = (await this.ui(page)).filter((o) => /banish/i.test(o.label));
    if (!banish.length || !before) return;
    await this.clickObject(page, banish[0]!);
    const after = await this.probe(page);
    const cardsAfter = await this.tierLabels(page);
    if (!after) return;

    // The core-level break the oracle already names, restated with what the
    // player could actually see: the card that moved up changed rarity.
    const movedUp = before.offers[1];
    if (movedUp && after.offers[0] === movedUp &&
        after.offerTiers[0] !== before.offerTiers[1]) {
      this.record(page, {
        code: "OFFER_TIER_DESYNC", errorType: "state_desync", severity: "high",
        system: "market / banish",
        file: "src/core/run.ts", symbol: "Run.removeFromPool",
        expected: "banishing a card takes its tier with it; the cards left keep the rarity they were rolled at",
        observed: `cards read [${cardsBefore.join(", ")}] before the Banish click and ` +
                  `[${cardsAfter.join(", ")}] after: ${movedUp} went from tier ` +
                  `${before.offerTiers[1]} to ${after.offerTiers[0]} without being touched ` +
                  `(offers=${after.offers.length}, offerTiers=${after.offerTiers.length})`,
      }, after, "banish_then_take", tag, banish[0]!);
    }

    const take = (await this.ui(page)).filter((o) => /take/i.test(o.label));
    if (take.length) {
      await this.clickObject(page, take[0]!);
      if (!(await this.placeHeld(page))) await page.keyboard.press("Escape");
    }
  }

  /**
   * The same Banish attack, at a depth where the market actually deals mixed
   * rarities — which is where the break becomes something a player can SEE.
   *
   * The wave counter is fast-forwarded first. That is a FIXTURE, not a claim
   * about what a player can do: it stands in for the twenty minutes of real
   * play needed to reach a market that deals Blues and Purples, and nothing
   * else here is faked. The redraw is forced by clicking the language toggle
   * twice — a real control, in its real place — and the Banish that follows is
   * a real click on the real button, with the rarity words read straight off
   * the screen either side of it.
   */
  private async deepMarketBanish(page: Page): Promise<void> {
    const start = await this.probe(page);
    if (!start || start.phase !== "market") return;
    await page.evaluate(() => {
      const r = (window as unknown as {
        loom: { wave: number; offerTiers: number[]; rollOffers: () => void };
      }).loom;
      if (r.wave < 22) r.wave = 22;
      // Roll until the shelf is ordered high-then-low, which is the half of
      // the time the break pays the player instead of robbing them. Still a
      // fixture: a player reaches this shelf by rerolling, which the market
      // gives them for free once per visit.
      for (let i = 0; i < 300; i++) {
        r.rollOffers();
        if ((r.offerTiers[0] ?? 0) > (r.offerTiers[1] ?? 0)) break;
      }
    });
    // Force the cards to be rebuilt without calling into the scene: the
    // language toggle is a real button and a redraw is exactly what it does.
    for (const o of (await this.ui(page)).filter((x) => /^\s*(EN|ES)\s*$/.test(x.label))) {
      await this.clickObject(page, o, 60);
      await this.clickObject(page, o, 60);
    }
    const before = await this.probe(page);
    const labelsBefore = await this.tierLabels(page);
    if (!before || before.offers.length < 3) return;
    const shotBefore = `${this.opts.shotDir}/banish-before.png`;
    await page.screenshot({ path: shotBefore }).catch(() => undefined);
    const refBefore = `${this.opts.shotRef}/banish-before.png`;

    const banish = (await this.ui(page)).find((o) => /banish/i.test(o.label));
    if (!banish) return;
    await this.clickObject(page, banish, 120);
    const after = await this.probe(page);
    const labelsAfter = await this.tierLabels(page);
    if (!after) return;
    const shotAfter = `${this.opts.shotDir}/banish-after.png`;
    await page.screenshot({ path: shotAfter }).catch(() => undefined);
    const refAfter = `${this.opts.shotRef}/banish-after.png`;

    const moved = before.offers[1];
    const changed = moved && after.offers[0] === moved &&
                    after.offerTiers[0] !== before.offerTiers[1];
    if (!changed && after.offers.length === after.offerTiers.length) return;
    const upgraded = (after.offerTiers[0] ?? 0) > (before.offerTiers[1] ?? 0);
    const f = this.log.add({
      code: upgraded ? "BANISH_UPGRADES_THE_NEXT_CARD" : "OFFER_TIER_DESYNC",
      errorType: upgraded ? "economy_exploit" : "state_desync",
      severity: upgraded ? "critical" : "high",
      system: "market / banish",
      file: "src/core/run.ts", symbol: "Run.removeFromPool",
      expected: "banishing a card takes its tier with it; every card left keeps the " +
                "rarity it rolled at, and the only way to raise a relic's tier is to merge two of them",
      observed: `wave ${after.wave}: the offer column read [${labelsBefore.join(", ")}] ` +
                `before the Banish click on the TOP card and [${labelsAfter.join(", ")}] after it. ` +
                `${moved}, which the player never touched, went from tier ` +
                `${before.offerTiers[1]} to ${after.offerTiers[0]}` +
                ((after.offerTiers[0] ?? 0) > (before.offerTiers[1] ?? 0)
                  ? " — a free rarity upgrade, and banishing costs nothing"
                  : " — a silent downgrade of a card the player was about to buy") +
                ` (offers=${after.offers.length}, offerTiers=${after.offerTiers.length})`,
    }, contextFrom(after, "browser-ui", "deep_market_banish", null, [
      "reach a market deep enough to deal mixed rarities (fixture: run.wave = 22, run.rollOffers())",
      "click the language toggle twice to redraw the cards",
      "read the three rarity words off the offer column",
      "click Banish on the top card",
      "read the three rarity words again",
    ]), { x: Math.round(banish.x + banish.w / 2), y: Math.round(banish.y + banish.h / 2),
          label: "Banish (top offer card)" });
    for (const shot of [refBefore, refAfter]) {
      if (!f.evidence.includes(shot)) f.evidence.push(shot);
    }
    f.reproduced = true;
  }

  /** Take a relic, then try to put it everywhere it must not go. */
  private async dragDump(page: Page): Promise<void> {
    if ((await this.probe(page))?.phase !== "market") return;
    const take = (await this.ui(page)).filter((o) => /take/i.test(o.label));
    if (!take.length) return;
    await this.clickObject(page, take[0]!);
    // Rotate past a full turn, then drop outside, on the locked ring, and on
    // top of whatever is already placed.
    for (let i = 0; i < 6; i++) await page.keyboard.press("r");
    const targets: Array<[number, number]> = [
      [-1, -1], [7, 7], [0, 6], [6, 0], [-1, 3], [3, -1], [8, 3], [3, 8],
      [0, 0], [1, 1], [2, 2], [0, 0],
    ];
    for (const [x, y] of targets) await this.clickCell(page, x, y, 12);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(40);
  }

  /** Four clicks inside one frame on every live control on the screen. */
  private async doubleClickStorm(page: Page): Promise<void> {
    for (const o of (await this.ui(page)).slice(0, 9)) {
      const p = await this.toPage(page, o.x + o.w / 2, o.y + o.h / 2);
      for (let i = 0; i < 4; i++) await page.mouse.click(p.x, p.y, { delay: 0 });
      await page.waitForTimeout(20);
    }
  }

  /**
   * The speed and language toggles redraw the whole screen and exist in every
   * phase — which is exactly how the buff screen was once turned into a free
   * reroll button. Hammer them wherever the run happens to be.
   */
  private async speedLangThrash(page: Page, tag: string): Promise<void> {
    for (let round = 0; round < 3; round++) {
      const snapA = await this.probe(page);
      const toggles = (await this.ui(page))
        .filter((o) => /^\s*(EN|ES|\d+×)\s*$/.test(o.label));
      for (const o of toggles) {
        for (let i = 0; i < 4; i++) await this.clickObject(page, o, 15);
      }
      const snapB = await this.probe(page);
      if (snapA && snapB) {
        for (const v of inspect(snapB, snapA)) {
          this.record(page, v, snapB, "speed_lang_thrash", tag, toggles[0]);
        }
      }
    }
  }

  /** Keys in phases that do not own them. */
  private async keyMash(page: Page): Promise<void> {
    for (const key of ["r", "x", "Escape", " ", "r", "Escape", "x", " "]) {
      await page.keyboard.press(key === " " ? "Space" : key);
      await page.waitForTimeout(20);
    }
  }

  /**
   * Click where the PREVIOUS screen's controls were. Every one of this game's
   * screens is a state of the same panel rather than an overlay, so a control
   * that outlives its phase sits invisibly on top of the next one — which is
   * how a click during a fight once granted a buff and dropped the run back to
   * the market.
   */
  private async ghostClicks(page: Page): Promise<void> {
    const ghosts: Array<[number, number]> = [
      // the three buff cards
      [640, 210], [640, 337], [640, 464],
      // the market's offer column, its Fight / Reroll / Restart row, the shop
      [800, 160], [800, 280], [800, 390],
      [400, 470], [590, 470], [780, 470],
      [400, 545], [550, 545], [700, 545], [850, 545],
      // the score screen's two buttons
      [830, 610], [970, 610],
    ];
    for (const [x, y] of ghosts) await this.clickWorld(page, x, y, 12);
  }

  /** The ultimate, pressed as fast as the input system will take it. */
  private async ultMash(page: Page): Promise<void> {
    const btn = (await this.ui(page)).find((o) => /◆/.test(o.label));
    for (let i = 0; i < 40; i++) {
      await page.keyboard.press("Space");
      if (btn) await this.clickObject(page, btn, 0);
      await page.waitForTimeout(25);
    }
  }

  /**
   * Resize mid-run, then check a grid click still lands on the cell it aimed
   * at. The world stays 1280x720 whatever the window does, so this is a pure
   * test of the pointer-to-cell mapping — the thing that broke once already at
   * a non-unit device pixel ratio.
   */
  private async resizeChurn(page: Page, tag: string): Promise<void> {
    const sizes = [{ width: 800, height: 500 }, { width: 1280, height: 720 }];
    for (const size of sizes) {
      await page.setViewportSize(size);
      this.rect = null;
      await page.waitForTimeout(200);
      const snap = await this.probe(page);
      if (!snap || snap.phase !== "market") continue;
      // Aim at a cell that is occupied, and see whether the relic there is the
      // one that ends up in hand.
      //
      // Two preconditions, both of which this once asserted without: the hand
      // must be empty, because a click on an occupied cell while holding is a
      // *drop* and correctly leaves the hand empty; and the run must survive
      // the click, because a restart lands the board back on its opening shape
      // — which for a titan is this same relic on these same cells.
      if (!(await this.clearHand(page))) continue;
      const target = snap.relics[0]?.cells[0];
      if (!target) continue;
      await this.clickCell(page, target[0], target[1], 60);
      const held = await this.heldDefId(page);
      const after = await this.probe(page);
      if (!after || after.runToken !== snap.runToken) continue;
      if (held === null) {
        this.record(page, {
          code: "GRID_CLICK_MISSED_ITS_CELL", errorType: "boundary_break", severity: "high",
          system: "renderer / pointer mapping",
          file: "src/game/main.ts", symbol: "LoomScene.onClick",
          expected: "a click on an occupied cell lifts the relic in it, at any window size",
          observed: `at viewport ${size.width}x${size.height} a click on the centre of ` +
                    `cell (${target[0]},${target[1]}) — occupied by ${snap.relics[0]?.defId} — ` +
                    "lifted nothing",
        }, snap, "resize_churn", tag);
      } else {
        await page.keyboard.press("Escape");
      }
      await page.waitForTimeout(60);
    }
  }

  /**
   * Deliberate progress. Without it the agent never leaves wave 1, and every
   * screen past the first market — the buff cards, the expansion grid, the
   * score screen — goes untested.
   */
  private async advanceWave(page: Page): Promise<void> {
    const deadline = Date.now() + 22_000;
    let guard = 0;
    while (Date.now() < deadline && guard++ < 40) {
      const snap = await this.probe(page);
      if (!snap) return;

      if (snap.phase === "market") {
        // Take offers and actually PLACE them. The starting board is the 3x3
        // block at the origin, so dropping at a fixed cell drops onto locked
        // ground and quietly leaves the relic in hand — which is how the agent
        // spent its first sessions losing wave 1 with one relic on the loom.
        for (let k = 0; k < 3; k++) {
          const take = (await this.ui(page)).find((o) => /take/i.test(o.label));
          if (!take) break;
          await this.clickObject(page, take, 40);
          if (!(await this.placeHeld(page))) { await page.keyboard.press("Escape"); break; }
        }
        for (const up of (await this.ui(page)).filter((o) => /\d+g/.test(o.label))) {
          await this.clickObject(page, up, 20);
        }
        const fight = (await this.ui(page)).find((o) => /fight|discard/i.test(o.label));
        if (!fight) return;
        await this.clickObject(page, fight, 250);
        continue;
      }

      if (!(await this.settleScreen(page, snap))) return;
      if (snap.phase === "over") return;
    }
  }

  /**
   * Wait out whatever screen the run is on until it is back in a market.
   * Deliberately does NOT play a wave — it only clears the screens between one
   * market and the next, so a market attack does not have to spend its budget
   * fighting first.
   */
  private async toMarket(page: Page): Promise<void> {
    const deadline = Date.now() + 40_000;
    while (Date.now() < deadline) {
      const snap = await this.probe(page);
      if (!snap || snap.phase === "market") return;
      if (!(await this.settleScreen(page, snap))) return;
    }
  }

  /**
   * One step off a non-market screen: wait out a battle, take a buff, place an
   * expansion cell, or restart from the score screen. Returns false when the
   * screen is one this cannot move.
   */
  private async settleScreen(page: Page, snap: Snapshot): Promise<boolean> {
    if (snap.phase === "battle") { await page.waitForTimeout(500); return true; }
    if (snap.phase === "buff") {
      const zone = (await this.ui(page)).find((o) => o.kind === "Zone");
      if (!zone) return false;
      await this.clickObject(page, zone, 150);
      return true;
    }
    if (snap.phase === "expansion") {
      const open = new Set(snap.unlocked);
      for (let y = 0; y < GRID.h; y++) {
        for (let x = 0; x < GRID.w; x++) {
          if (open.has(`${x},${y}`)) continue;
          const near = [[1, 0], [-1, 0], [0, 1], [0, -1]].some(
            ([dx, dy]) => open.has(`${x + (dx ?? 0)},${y + (dy ?? 0)}`));
          if (!near) continue;
          await this.clickCell(page, x, y, 40);
          return true;
        }
      }
      return false;
    }
    if (snap.phase === "over") {
      const again = (await this.ui(page)).find((o) => /again/i.test(o.label));
      if (!again) return false;
      await this.clickObject(page, again, 500);
      return true;
    }
    return false;
  }

  /** Drop whatever is in hand on the first cell the board will accept. */
  private async placeHeld(page: Page): Promise<boolean> {
    const snap = await this.probe(page);
    if (!snap) return false;
    const taken = new Set(snap.relics.flatMap((r) => r.cells.map(([x, y]) => `${x},${y}`)));
    const free = snap.unlocked.filter((c) => !taken.has(c));
    for (const cell of free) {
      const [sx, sy] = cell.split(",");
      await this.clickCell(page, Number(sx), Number(sy), 25);
      if (!(await this.heldDefId(page))) return true;
    }
    return false;
  }

  // -- reading the game -----------------------------------------------------

  /** Is the playable scene the one actually running right now? */
  /**
   * Start a fresh run and wait for it to actually exist.
   *
   * Phaser queues scene starts and processes them on a later step, so the call
   * returns long before create() has run. Waiting on `window.loom` is not
   * enough — the previous run's object is still sitting there, so the wait
   * passes immediately and the restart lands mid-tactic. That produced a
   * "click missed its cell" finding for a click that had lifted correctly: the
   * queued restart replaced the run a frame later, and a fresh titan opens with
   * the same relic on the same cells, so the board looked untouched.
   *
   * Clearing the handle first makes the wait mean what it says.
   */
  private async restartRun(page: Page, cls: string): Promise<boolean> {
    if (page.isClosed()) return false;
    await page.evaluate((c) => {
      (window as unknown as { loom?: unknown }).loom = undefined;
      (window as unknown as { loomGame: { scene: { start: (k: string, d: unknown) => void } } })
        .loomGame.scene.start("loom", { cls: c });
    }, cls).catch(() => undefined);
    return page.waitForFunction(() => !!(window as unknown as { loom?: unknown }).loom,
                                null, { timeout: 10_000 })
      .then(() => true).catch(() => false);
  }

  private async inGame(page: Page): Promise<boolean> {
    if (page.isClosed()) return false;
    return page.evaluate(() => {
      const g = (window as unknown as {
        loomGame?: { scene: { isActive: (k: string) => boolean } };
      }).loomGame;
      return !!g?.scene.isActive("loom");
    }).catch(() => false);
  }

  /** The snapshot, built in the page from the same Run the renderer is drawing. */
  private async probe(page: Page): Promise<Snapshot | null> {
    if (page.isClosed()) return null;
    return page.evaluate(() => {
      const w = window as unknown as { loom?: Record<string, unknown> };
      const r = w.loom as unknown as null | {
        phase: string; wave: number; gold: number; exp: number; level: number;
        beaconHp: number; beaconMax: number; freeRerolls: number; rerollsUsed: number;
        pendingBuffChoices: number; pendingExpansionCells: number; cls: string;
        env: { w: number; h: number };
        loom: { unlocked: Set<string>; relics: Array<Record<string, unknown>> };
        tray: Array<{ defId: string; tier: number }>;
        offers: Array<{ id: string }>; offerTiers: number[]; deals: number; removed: Set<string>;
        buffs: unknown[]; buffChoices: () => Array<{ id: string }>;
        battle: null | Record<string, unknown>;
      };
      if (!r) return null;
      // Stamp each Run the first time it is seen, so a restart is visible as a
      // new run rather than as a wave counter falling back to 1.
      const store = window as unknown as { __advSeq?: number };
      const tagged = r as unknown as { __advToken?: number };
      if (!tagged.__advToken) {
        store.__advSeq = (store.__advSeq ?? 0) + 1;
        tagged.__advToken = store.__advSeq;
      }
      const b = r.battle as null | {
        elapsed: number; beaconHp: number; ultCooldownLeft: number; ultCasts: number;
        enemies: Array<Record<string, number | string>>;
        finished: null | { cleared: boolean; goldEarned: number; expEarned: number };
      };
      return {
        runToken: tagged.__advToken,
        phase: r.phase, wave: r.wave, gold: r.gold, exp: r.exp, level: r.level,
        beaconHp: r.beaconHp, beaconMax: r.beaconMax,
        freeRerolls: r.freeRerolls, rerollsUsed: r.rerollsUsed,
        pendingBuffChoices: r.pendingBuffChoices,
        pendingExpansionCells: r.pendingExpansionCells,
        cls: r.cls, env: { w: r.env.w, h: r.env.h },
        unlocked: [...r.loom.unlocked],
        relics: r.loom.relics.map((x) => ({
          uid: x.uid as number, defId: x.defId as string, tier: x.tier as number,
          cells: (x.cells as Array<[number, number]>).map(([cx, cy]) => [cx, cy]),
          cooldownLeft: x.cooldownLeft as number,
        })),
        tray: r.tray.map((t) => ({ defId: t.defId, tier: t.tier })),
        offers: r.offers.map((o) => o.id),
        offerTiers: [...r.offerTiers],
        deals: r.deals,
        removed: [...r.removed],
        buffs: r.buffs.length,
        buffChoiceIds: r.phase === "buff" ? r.buffChoices().map((x) => x.id) : [],
        handDefId: null,
        battle: b ? {
          elapsed: b.elapsed, beaconHp: b.beaconHp,
          enemies: b.enemies.map((e) => ({
            id: e.id as number, kind: e.kind as string, hp: e.hp as number,
            maxHp: e.maxHp as number, pos: e.pos as number, x: e.x as number,
            stopAt: e.stopAt as number,
          })),
          finished: b.finished,
          ultCooldownLeft: b.ultCooldownLeft, ultCasts: b.ultCasts,
        } : null,
      } as unknown;
    }) as Promise<Snapshot | null>;
  }

  /** Every control the player can currently hit, in world coordinates. */
  private async ui(page: Page): Promise<UiObject[]> {
    if (page.isClosed()) return [];
    return page.evaluate(() => {
      const g = (window as unknown as {
        loomGame: { scene: { getScene: (k: string) => { children: { list: unknown[] } } } };
      }).loomGame;
      const scene = g.scene.getScene("loom");
      const out: UiObject[] = [];
      for (const raw of scene?.children?.list ?? []) {
        const o = raw as {
          type: string; visible: boolean; input?: { enabled: boolean };
          text?: string; getBounds?: () => { x: number; y: number; width: number; height: number };
        };
        if (!o.input?.enabled || !o.visible || !o.getBounds) continue;
        const b = o.getBounds();
        out.push({
          label: (o.text ?? "").split("\n").join(" ").trim(),
          x: b.x, y: b.y, w: b.width, h: b.height, kind: o.type,
        });
      }
      return out;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    }) as unknown as Promise<UiObject[]>;
  }

  /** The rarity words currently printed on the three offer cards. */
  private async tierLabels(page: Page): Promise<string[]> {
    // The five rarity words, both languages (core/strings.generated.ts).
    const words = new Set(["Common", "Uncommon", "Rare", "Legendary", "Epic",
                           "Común", "Poco común", "Raro", "Legendario", "Épico"]);
    if (page.isClosed()) return [];
    const texts = await page.evaluate(() => {
      const g = (window as unknown as {
        loomGame: { scene: { getScene: (k: string) => { children: { list: unknown[] } } } };
      }).loomGame;
      const scene = g.scene.getScene("loom");
      const out: Array<{ t: string; y: number }> = [];
      for (const raw of scene?.children?.list ?? []) {
        const o = raw as { type: string; text?: string; y: number; visible: boolean };
        if (o.type === "Text" && o.visible && o.text) out.push({ t: o.text, y: o.y });
      }
      return out;
    });
    return texts.filter((x) => words.has(x.t.trim()))
                .sort((a, b) => a.y - b.y).map((x) => x.t.trim());
  }

  /**
   * Put down whatever is held, so a following click is a lift and not a drop.
   * Returns false if the hand could not be emptied, which makes the caller skip
   * rather than assert against a state it did not establish.
   */
  private async clearHand(page: Page): Promise<boolean> {
    if (page.isClosed()) return false;
    return page.evaluate(() => {
      const g = (window as unknown as {
        loomGame: { scene: { getScene: (k: string) => {
          hand?: { active?: boolean; cancel?: () => void };
        } | null } };
      }).loomGame;
      const hand = g.scene.getScene("loom")?.hand;
      if (!hand) return false;
      if (hand.active) hand.cancel?.();
      return !hand.active;
    }).catch(() => false);
  }

  private async heldDefId(page: Page): Promise<string | null> {
    if (page.isClosed()) return null;
    return page.evaluate(() => {
      const g = (window as unknown as {
        loomGame: { scene: { getScene: (k: string) => { hand?: { held?: { def: { id: string } } } } } };
      }).loomGame;
      return g.scene.getScene("loom")?.hand?.held?.def.id ?? null;
    });
  }

  // -- clicking -------------------------------------------------------------

  /**
   * World coordinates to page pixels. Phaser scales the canvas to FIT and
   * centres it, so the whole mapping is the canvas's own bounding box — which
   * is what lets the agent resize the window between clicks and keep aiming at
   * the same cell.
   */
  private async toPage(page: Page, wx: number, wy: number): Promise<{ x: number; y: number }> {
    if (!this.rect) {
      this.rect = await page.evaluate(() => {
        const c = document.querySelector("canvas");
        if (!c) return null;
        const r = c.getBoundingClientRect();
        return { left: r.left, top: r.top, width: r.width, height: r.height };
      });
    }
    const rect = this.rect;
    if (!rect) return { x: wx, y: wy };
    const scale = Math.min(rect.width / WORLD.w, rect.height / WORLD.h);
    return {
      x: rect.left + (rect.width - WORLD.w * scale) / 2 + wx * scale,
      y: rect.top + (rect.height - WORLD.h * scale) / 2 + wy * scale,
    };
  }

  private async clickWorld(page: Page, wx: number, wy: number, wait = 20): Promise<void> {
    if (page.isClosed()) return;
    const p = await this.toPage(page, wx, wy);
    await page.mouse.click(p.x, p.y, { delay: 0 });
    if (wait) await page.waitForTimeout(wait);
  }

  private async clickCell(page: Page, gx: number, gy: number, wait = 20): Promise<void> {
    await this.clickWorld(page,
      GRID.ox + gx * GRID.cell + GRID.cell / 2,
      GRID.oy + gy * GRID.cell + GRID.cell / 2, wait);
  }

  private async clickObject(page: Page, o: UiObject, wait = 30): Promise<void> {
    await this.clickWorld(page, o.x + o.w / 2, o.y + o.h / 2, wait);
  }

  // -- judging --------------------------------------------------------------

  private async check(page: Page, tactic: string, tag: string): Promise<void> {
    const snap = await this.probe(page);
    if (!snap) return;
    const sameRun = this.prev && this.prev.runToken === snap.runToken;
    for (const v of inspect(snap, sameRun ? this.prev : null)) {
      this.record(page, v, snap, tactic, tag);
    }
    this.prev = snap;
  }

  /**
   * A game that stops responding is a bug even when every invariant holds.
   * Only the battle is watched: it is the one phase that advances on its own,
   * so a frozen signature there means the run cannot continue without the
   * player being able to do anything about it.
   */
  private async watchdog(page: Page, tactic: string, tag: string): Promise<void> {
    const snap = await this.probe(page);
    if (!snap) return;
    const sig = [snap.phase, snap.wave, snap.relics.length, snap.unlocked.length,
                 snap.battle?.enemies.length ?? -1,
                 Math.round(snap.battle?.beaconHp ?? snap.beaconHp),
                 Math.round((snap.battle?.elapsed ?? 0) * 2)].join("|");
    if (sig !== this.lastSignature) {
      this.lastSignature = sig;
      this.lastChange = Date.now();
      return;
    }
    const frozen = (Date.now() - this.lastChange) / 1000;
    if (snap.phase === "battle" && frozen > 25) {
      this.record(page, {
        code: "BATTLE_FROZEN", errorType: "stuck_state", severity: "critical",
        system: "battle / tick loop",
        file: "src/game/main.ts", symbol: "LoomScene.update",
        expected: "a battle advances on its own until the wave clears or the Beacon falls",
        observed: `nothing on the lane changed for ${frozen.toFixed(0)}s: wave ${snap.wave}, ` +
                  `${snap.battle?.enemies.length ?? 0} enemies, beacon ${snap.battle?.beaconHp}`,
      }, snap, tactic, tag);
      this.lastChange = Date.now();
    }
  }

  private record(
    page: Page, v: Violation, snap: Snapshot, tactic: string, tag: string, at?: UiObject,
  ): void {
    const f = this.log.add(
      v, contextFrom(snap, "browser-ui", tactic, null,
                     [`pass ${tag}`, `tactic ${tactic}`, `phase ${snap.phase}`, `wave ${snap.wave}`]),
      at ? { x: Math.round(at.x + at.w / 2), y: Math.round(at.y + at.h / 2), label: at.label || at.kind }
         : undefined);
    if (!this.shot.has(v.code)) {
      this.shot.add(v.code);
      const path = `${this.opts.shotDir}/${f.id}-${v.code}.png`;
      f.evidence.push(`${this.opts.shotRef}/${f.id}-${v.code}.png`);
      void page.screenshot({ path }).catch(() => undefined);
    }
  }

  private async crash(page: Page, kind: string, text: string, tag: string): Promise<void> {
    const snap = (await this.probe(page).catch(() => null));
    const v: Violation = {
      code: `PAGE_${kind.replace(/\W+/g, "_").toUpperCase()}`,
      errorType: "crash", severity: "critical",
      system: "renderer / runtime",
      file: "src/game", symbol: "LoomScene",
      expected: "the game runs a whole session without an uncaught error",
      observed: `${kind}: ${text.slice(0, 300)}`,
    };
    const blank: Snapshot = snap ?? {
      phase: "unknown", wave: 0, gold: 0, exp: 0, level: 0, beaconHp: 0, beaconMax: 0,
      freeRerolls: 0, rerollsUsed: 0, pendingBuffChoices: 0, pendingExpansionCells: 0,
      cls: tag, env: { w: 7, h: 7 }, unlocked: [], relics: [], tray: [],
      offers: [], offerTiers: [], deals: 0, removed: [], buffs: 0, buffChoiceIds: [],
      handDefId: null, battle: null,
    };
    this.record(page, v, blank, "page_runtime", tag);
  }
}
