#!/usr/bin/env python3
"""Tests for the UI gate. Stdlib only.

    python3 -m unittest discover -s agents

Two jobs. The first is the usual one: mutate the contract's own worked example and
assert the rules say so — a gate is only worth what it refuses.

The second is drift. `ui_rules.py` holds its numbers as constants, and
`vault/07-ui-and-controls/ui-budgets.md` is where they are decided and argued
about. `TheNoteAndTheCodeAgree` parses the note and fails if the two disagree, so
the note keeps being the source of truth without the module having to parse
markdown at run time. Editing one and not the other breaks the build instead of
quietly changing what ships.

The fixtures are the two JSON blocks inside `vault/07-ui-and-controls/uispec.md`,
read from the document rather than copied here: a contract and an example that can
drift apart teach whichever one the reader happens to open.
"""

import copy
import json
import re
import unittest
from pathlib import Path

import ui_rules as ur

SPEC_DOC = Path(__file__).resolve().parent.parent / "vault" / "07-ui-and-controls" / "uispec.md"
BUDGETS_DOC = SPEC_DOC.parent / "ui-budgets.md"

_BLOCKS = re.findall(r"```json\n(.*?)\n```", SPEC_DOC.read_text(encoding="utf-8"), re.S)
UMG_EXAMPLE = json.loads(_BLOCKS[0])
TABLE_EXAMPLE = json.loads(_BLOCKS[1])
RECORDS = TABLE_EXAMPLE["records"]


def record(key):
    return copy.deepcopy(next(r for r in RECORDS if r["key"].endswith(key)))


class TheContractsOwnExample(unittest.TestCase):
    """Whatever else changes, the document's example must pass its own rules."""

    def test_the_two_artifacts_agree_about_their_keys(self):
        dangling, orphan = ur.cross_reference([UMG_EXAMPLE], RECORDS)
        self.assertEqual(set(), dangling)
        self.assertEqual(set(), orphan)

    def test_every_record_fits_its_class_cap_in_both_languages(self):
        for rec in RECORDS:
            for field in ("text_en", "text_es"):
                self.assertIsNone(
                    ur.over_cap(rec["widget_class"], rec[field]),
                    f"{rec['key']}.{field} exceeds the {rec['widget_class']} cap",
                )

    def test_every_record_fits_the_spanish_allowance(self):
        for rec in RECORDS:
            self.assertTrue(
                ur.es_within_budget(rec["text_en"], rec["text_es"]),
                f"{rec['key']}: es={len(rec['text_es'])} allowance={ur.es_allowance(rec['text_en'])}",
            )

    def test_no_record_carries_a_specifier_mismatch(self):
        for rec in RECORDS:
            self.assertTrue(ur.specifier_parity(rec["text_en"], rec["text_es"]), rec["key"])

    def test_no_record_names_a_cut_feature_or_the_country(self):
        for rec in RECORDS:
            for field in ("text_en", "text_es"):
                self.assertIsNone(ur.cut_feature_in_text(rec[field]), rec["key"])
                self.assertIsNone(ur.region_leak(rec[field]), rec["key"])

    def test_no_record_is_a_placeholder_or_names_a_button(self):
        for rec in RECORDS:
            for field in ("text_en", "text_es"):
                self.assertEqual([], ur.placeholders(rec[field]), rec["key"])
                self.assertEqual([], ur.glyph_literals(rec[field]), rec["key"])

    def test_the_example_says_nothing_twice(self):
        self.assertEqual({}, ur.duplicate_texts(RECORDS))

    def test_the_examples_widgets_name_no_cut_feature(self):
        for widget in UMG_EXAMPLE["widgets"]:
            self.assertIsNone(
                ur.cut_feature_in_identifiers(
                    widget.get("id"), widget.get("type"),
                    widget.get("binding"), widget.get("string_table_key"),
                ),
                widget["id"],
            )


class TheNoteAndTheCodeAgree(unittest.TestCase):
    """The drift guard. ui-budgets.md decides these numbers; ui_rules.py copies them."""

    @classmethod
    def setUpClass(cls):
        cls.text = BUDGETS_DOC.read_text(encoding="utf-8")

    def _figure(self, pattern):
        match = re.search(pattern, self.text)
        self.assertIsNotNone(match, f"ui-budgets.md no longer states: {pattern}")
        return match.group(1)

    def test_the_ratio_matches(self):
        self.assertEqual(ur.ES_OVERFLOW_RATIO, float(self._figure(r"Ratio cap \| \*\*([\d.]+)\*\*")))

    def test_the_floor_matches(self):
        stated = self._figure(r"Absolute floor \| \*\*\+(\d+) characters\*\*")
        self.assertEqual(ur.ES_OVERFLOW_FLOOR, int(stated))

    def test_every_widget_class_cap_matches(self):
        rows = re.findall(r"\|\s*`(\w+)`\s*\|\s*\*\*(\d+)\*\*", self.text)
        stated = {name: int(cap) for name, cap in rows}
        self.assertTrue(stated, "no widget_class rows parsed from ui-budgets.md")
        self.assertEqual(stated, ur.WIDGET_CLASS_CAPS)

    def test_the_per_screen_key_cap_matches(self):
        stated = self._figure(r"Distinct keys per screen \| ≤ \*\*(\d+)\*\*")
        self.assertEqual(ur.MAX_KEYS_PER_SCREEN, int(stated))

    def test_the_safe_area_matches(self):
        self.assertEqual(int(ur.TITLE_SAFE * 100),
                         int(self._figure(r"Title-safe region \| inner \*\*(\d+)%\*\*")))
        self.assertEqual(int(ur.ACTION_SAFE * 100),
                         int(self._figure(r"Action-safe region \| inner \*\*(\d+)%\*\*")))

    def test_the_note_still_documents_the_crossover(self):
        """The floor governs below 20 characters; the ratio above it."""
        crossover = ur.ES_OVERFLOW_FLOOR / (ur.ES_OVERFLOW_RATIO - 1)
        self.assertAlmostEqual(20.0, crossover, places=6)
        self.assertIn("cross at 20 characters", self.text)


class TheSpanishAllowance(unittest.TestCase):
    """The failure that motivated the floor, kept as a test so it cannot come back."""

    def test_the_ratio_alone_would_reject_correct_translations(self):
        for en, es in (("Resume", "Continuar"), ("Retry", "Reintentar"),
                       ("Settings", "Configuración")):
            self.assertGreater(len(es), len(en) * ur.ES_OVERFLOW_RATIO,
                               f"{en}/{es} no longer demonstrates the ratio failure")
            self.assertTrue(ur.es_within_budget(en, es), f"{en}/{es} must pass with the floor")

    def test_the_floor_governs_short_strings_and_the_ratio_governs_long_ones(self):
        self.assertEqual(len("Exit") + ur.ES_OVERFLOW_FLOOR, ur.es_allowance("Exit"))
        long_en = "x" * 100
        self.assertEqual(int(len(long_en) * ur.ES_OVERFLOW_RATIO), ur.es_allowance(long_en))

    def test_genuine_bloat_is_still_refused(self):
        self.assertFalse(ur.es_within_budget("Resume", "Continuar la incursión ahora"))


class TheCaps(unittest.TestCase):
    def test_a_prose_block_may_be_long_and_a_label_may_not(self):
        sentence = "x" * 200
        self.assertIsNone(ur.over_cap("ProseBlock", sentence))
        self.assertEqual(ur.WIDGET_CLASS_CAPS["MenuLabel"], ur.over_cap("MenuLabel", sentence))

    def test_an_unknown_class_is_not_silently_allowed_a_cap(self):
        self.assertIsNone(ur.cap_for("Banner"))
        self.assertIsNone(ur.over_cap("Banner", "x" * 999))


class TheSubstitutions(unittest.TestCase):
    def test_reordering_is_allowed_and_losing_one_is_not(self):
        self.assertTrue(ur.specifier_parity("{0} of {1}", "{1} de {0}"))
        self.assertFalse(ur.specifier_parity("{0} of {1}", "{0} de todo"))
        self.assertEqual(["{1}"], ur.specifier_diff("{0} of {1}", "{0} de todo")["missing_in_es"])

    def test_an_action_token_counts_as_a_substitution(self):
        self.assertTrue(ur.specifier_parity("<Interact> Open", "<Interact> Abrir"))
        self.assertFalse(ur.specifier_parity("<Interact> Open", "Abrir"))

    def test_a_hardcoded_button_is_caught_in_either_language(self):
        self.assertEqual(["[X]"], ur.glyph_literals("[X] Open"))
        self.assertTrue(ur.glyph_literals("Press A to continue"))
        self.assertTrue(ur.glyph_literals("Pulsa A para continuar"))
        self.assertEqual([], ur.glyph_literals("<Interact> Abrir"))

    def test_placeholders_are_caught(self):
        self.assertTrue(ur.placeholders("TODO: write this"))
        self.assertTrue(ur.placeholders("Lorem ipsum"))
        self.assertEqual([], ur.placeholders("Continuar"))


class TheDenylists(unittest.TestCase):
    def test_the_cut_feature_list_parses_and_is_not_empty(self):
        features = ur.load_cut_features()
        self.assertGreaterEqual(len(features), 5)
        self.assertTrue(any("minimap" in tokens for tokens in features.values()))

    def test_a_widget_that_displays_a_cut_feature_is_caught(self):
        self.assertIsNotNone(ur.cut_feature_in_identifiers("bar_boss_health", "ProgressBar"))
        self.assertIsNotNone(ur.cut_feature_in_identifiers("wgt_minimap", "Image"))
        self.assertIsNone(ur.cut_feature_in_identifiers("row_resume", "TextBlock"))

    def test_copy_that_promises_a_cut_feature_is_caught(self):
        self.assertIsNotNone(ur.cut_feature_in_text("Difficulty"))
        self.assertIsNotNone(ur.cut_feature_in_text("Dificultad"))
        self.assertIsNotNone(ur.cut_feature_in_text("damage numbers"))
        self.assertIsNone(ur.cut_feature_in_text("Continuar"))

    def test_a_legitimate_stat_label_is_not_a_cut_feature(self):
        """"Completion time" is a Run-Complete stat; only the percentage was cut."""
        self.assertIsNone(ur.cut_feature_in_text("Completion time"))
        self.assertIsNone(ur.cut_feature_in_text("Tiempo de recorrido"))
        self.assertIsNotNone(ur.cut_feature_in_text("completion percentage"))

    def test_the_country_is_never_named_in_either_language(self):
        self.assertEqual("México", ur.region_leak("Las ruinas de México"))
        self.assertIsNotNone(ur.region_leak("a Mexican golden age"))
        self.assertIsNone(ur.region_leak("Las ruinas de los Arquitectos"))

    def test_a_plural_does_not_evade_the_denylist(self):
        """Caught by writing this test: \\bMayan\\b never matched "Mayans"."""
        self.assertIsNotNone(ur.region_leak("the Mayans built it"))
        self.assertIsNotNone(ur.region_leak("las pirámides"))
        self.assertIsNotNone(ur.cut_feature_in_text("ammo counters"))

    def test_a_region_word_inside_another_word_is_not_a_leak(self):
        self.assertIsNone(ur.region_leak("mayhem in the vault"))
        self.assertIsNone(ur.region_leak("the mayor of nothing"))


class TheSetLevelRules(unittest.TestCase):
    def test_two_keys_with_the_same_text_are_refused(self):
        twice = [record("Pause_Resume"), record("Pause_Resume")]
        twice[1]["key"] = "ST_UI.RunComplete_Resume"
        dupes = ur.duplicate_texts(twice)
        self.assertEqual(1, len(dupes))
        self.assertEqual(["ST_UI.Pause_Resume", "ST_UI.RunComplete_Resume"],
                         next(iter(dupes.values())))

    def test_a_screen_over_its_key_cap_is_named(self):
        many = []
        for i in range(ur.MAX_KEYS_PER_SCREEN + 1):
            rec = record("Pause_Resume")
            rec["key"] = f"ST_UI.Pause_Row{i}"
            many.append(rec)
        self.assertEqual({"Screen_Pause": ur.MAX_KEYS_PER_SCREEN + 1},
                         ur.screens_over_key_cap(many))

    def test_one_concept_spelled_two_ways_is_named(self):
        a, b = record("Pause_Resume"), record("Pause_Language")
        a["text_en"], b["text_en"] = "Beacon reached", "beacon reached again"
        variants = ur.term_variants([a, b], ["Beacon"])
        self.assertEqual({"Beacon", "beacon"}, variants["Beacon"])

    def test_consistent_spelling_raises_nothing(self):
        a, b = record("Pause_Resume"), record("Pause_Language")
        a["text_en"], b["text_en"] = "Beacon reached", "Beacon again"
        self.assertEqual({}, ur.term_variants([a, b], ["Beacon"]))


class TheCrossReference(unittest.TestCase):
    def test_a_widget_pointing_at_nothing_is_dangling(self):
        spec = copy.deepcopy(UMG_EXAMPLE)
        spec["widgets"][0]["string_table_key"] = "ST_UI.Pause_Missing"
        dangling, orphan = ur.cross_reference([spec], RECORDS)
        self.assertEqual({"ST_UI.Pause_Missing"}, dangling)
        self.assertEqual({"ST_UI.Pause_Resume"}, orphan)

    def test_a_record_nobody_shows_is_an_orphan(self):
        extra = record("Pause_Resume")
        extra["key"] = "ST_UI.Pause_Unused"
        extra["text_en"], extra["text_es"] = "Unused", "Sin uso"
        dangling, orphan = ur.cross_reference([UMG_EXAMPLE], RECORDS + [extra])
        self.assertEqual(set(), dangling)
        self.assertEqual({"ST_UI.Pause_Unused"}, orphan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
