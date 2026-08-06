#!/usr/bin/env python3
"""Tests for the IP term guard. Stdlib only.

    python3 -m unittest discover -s agents

The rule under test is decided in `vault/00-core/terminology-guard.md`: a banned
term is banned in its capitalised form, because the capital is what marks the word
as the proper noun rather than the vocabulary. These tests exist mostly to pin the
cases the rule was chosen to allow — a guard that rejects "the light in the
corridor died" trains people to ignore it, which is worse than a guard that misses
something.
"""

import unittest
from pathlib import Path

import validators as v

GUARD_DOC = (Path(__file__).resolve().parent.parent
             / "vault" / "00-core" / "terminology-guard.md")
BANNED = v.load_banned_and_approved()["banned"]


def hits(text):
    certain, ambiguous = v.ip_term_hits(text, BANNED)
    return set(certain), set(ambiguous)


class TheCapitalIsWhatIsBanned(unittest.TestCase):
    def test_the_placeholder_is_caught(self):
        certain, _ = hits("The Light of the Traveler reached this hall.")
        self.assertEqual({"Light", "Traveler"}, certain)

    def test_the_ordinary_word_is_allowed(self):
        """The case the rule was changed to permit."""
        self.assertEqual((set(), set()), hits("The light in the corridor died long before we did."))

    def test_a_lowercase_ghost_is_a_ghost_and_not_a_Beacon(self):
        self.assertEqual((set(), set()), hits("a ghost of a signal, nothing more"))
        self.assertEqual({"Ghost"}, hits("her Ghost answered first")[0])

    def test_case_is_the_only_difference(self):
        for term in ("Light", "Ghost", "Guardians"):
            self.assertIn(term, BANNED, f"{term} is no longer in the table; update this test")
            self.assertEqual({term}, hits(f"and then the {term} moved")[0])
            self.assertEqual((set(), set()), hits(f"and then the {term.lower()} moved"))


class WhereTheCapitalSaysNothing(unittest.TestCase):
    """At the start of a sentence the capital is mandatory, so it carries no signal."""

    def test_a_sentence_opening_term_is_a_warning_not_a_failure(self):
        certain, ambiguous = hits("Light dies here.")
        self.assertEqual(set(), certain)
        self.assertEqual({"Light"}, ambiguous)

    def test_the_same_word_mid_sentence_is_a_failure(self):
        certain, ambiguous = hits("Nothing but Light dies here.")
        self.assertEqual({"Light"}, certain)
        self.assertEqual(set(), ambiguous)

    def test_after_a_full_stop_counts_as_a_sentence_opening(self):
        _, ambiguous = hits("The hall is silent. Light dies here.")
        self.assertEqual({"Light"}, ambiguous)

    def test_after_a_line_break_or_an_opening_quote_counts_too(self):
        self.assertEqual({"Light"}, hits("The hall is silent.\nLight dies here.")[1])
        self.assertEqual({"Light"}, hits('She wrote: "Light dies here."')[1])

    def test_a_warning_does_not_fail_the_gate(self):
        record = {"node_id": "n", "room_id": "r", "node_type": "Mural",
                  "text_en": "Light dies here.", "text_es": "Aquí muere la lumbre.",
                  "tags": []}
        errors = v.validate_text(record)
        self.assertTrue(any(e["code"] == "WARN_IP_SENTENCE_INITIAL" for e in errors))
        self.assertEqual([], [e for e in errors if e["code"].startswith("ERR_")])


class TheLowercaseRowsAreUnaffected(unittest.TestCase):
    """A term written lowercase has no proper-noun signal to lose."""

    def test_a_region_adjective_is_caught_in_any_casing(self):
        self.assertIsNotNone(v.ur.region_leak("a mexicano hall"))
        self.assertIsNotNone(v.ur.region_leak("a Mexicano hall"))

    def test_the_country_is_caught_wherever_it_sits(self):
        self.assertIsNotNone(v.ur.region_leak("México"))
        self.assertIsNotNone(v.ur.region_leak("built in Mexico, long ago"))


class TheNoteStillDocumentsTheRule(unittest.TestCase):
    def test_the_decision_is_written_where_the_agents_read_it(self):
        text = GUARD_DOC.read_text(encoding="utf-8")
        self.assertIn("banned **only in its capitalised form**", text)
        self.assertIn("start of a sentence", text)

    def test_the_known_gap_is_still_recorded(self):
        """The Spanish side of the IP table is unguarded; the note must say so."""
        self.assertIn("Spanish side of the first table is unguarded",
                      GUARD_DOC.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
