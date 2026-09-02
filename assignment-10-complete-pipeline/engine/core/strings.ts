/**
 * User-facing text, looked up by key.
 *
 * The table itself is generated — `strings.generated.ts`, written by the copy
 * pipeline from records that passed a checker and matched the game's content in
 * both directions. Nothing here is authored; this file only knows how to read it.
 *
 * `core/` stays pure: the language is a value the renderer sets, never something
 * this module reads from the environment.
 *
 * Strings interpolate `{name}` placeholders. That is not decoration: without it
 * a sentence has to be assembled from fragments in code, and the fragments end
 * up as English literals nobody translates — which is exactly how the first
 * version of the score screen shipped the words "relics", "cells" and "level"
 * into a Spanish build.
 */
import { STRINGS, type Lang } from "./strings.generated.js";

export type { Lang };
export { STRINGS_FINGERPRINT } from "./strings.generated.js";

let current: Lang = "en";

export const setLang = (lang: Lang): void => { current = lang; };
export const getLang = (): Lang => current;

/**
 * The string for a key, in the current language.
 *
 * A missing key returns THE KEY ITSELF rather than an empty string. A blank
 * label looks like a layout bug and gets chased for an hour; `relic.x.name` on
 * screen says exactly what is wrong and which table is short of a record.
 */
export function t(key: string, vars?: Record<string, string | number>): string {
  const record = STRINGS[key];
  let out = record ? record[current] : key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      out = out.split(`{${name}}`).join(String(value));
    }
  }
  return out;
}

export const hasString = (key: string): boolean => key in STRINGS;
