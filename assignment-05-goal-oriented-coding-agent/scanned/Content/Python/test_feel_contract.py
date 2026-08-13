"""Tests for the CSV-to-struct correspondence check. Stdlib only, no engine.

    python3 -m unittest discover -s Content/Python

The last test runs against the project's real CSV and header, so the suite fails
the moment the two drift apart — which is the whole reason the module exists.
"""

import tempfile
import unittest
from pathlib import Path

import feel_contract as fc

REPO = Path(__file__).resolve().parents[2]
REAL_CSV = REPO / "SourceAssets" / "DT_GameFeel.csv"
REAL_HEADER = REPO / "Source" / "Echoes" / "GameFeelRow.h"

HEADER_TEMPLATE = """
USTRUCT(BlueprintType)
struct FExample : public FTableRowBase
{{
	GENERATED_BODY()
{fields}
}};
"""


def header_with(*names):
    body = "".join(
        f'\n\tUPROPERTY(EditAnywhere, Category = "X")\n\tfloat {n} = 1.0f;\n'
        for n in names
    )
    return HEADER_TEMPLATE.format(fields=body)


class Files(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text)
        return path

    def pair(self, columns, fields):
        csv = self.write("t.csv", "Name," + ",".join(columns) + "\nDefault,"
                         + ",".join("1" for _ in columns) + "\n")
        header = self.write("T.h", header_with(*fields))
        return csv, header


class Parsing(Files):
    def test_row_key_column_is_not_a_field(self):
        csv, _ = self.pair(["A", "B"], ["A", "B"])
        self.assertEqual(fc.csv_fields(csv), ["A", "B"])

    def test_a_csv_without_the_row_key_is_refused(self):
        csv = self.write("t.csv", "A,B\n1,2\n")
        with self.assertRaises(fc.FeelContractError) as c:
            fc.csv_fields(csv)
        self.assertIn("row key", str(c.exception))

    def test_only_uproperty_members_count(self):
        header = self.write("T.h", header_with("Kept") + "\n\tfloat NotExposed = 2.0f;\n")
        self.assertEqual(fc.struct_fields(header), ["Kept"])

    def test_a_header_with_no_fields_is_refused(self):
        header = self.write("T.h", "struct FEmpty {};")
        with self.assertRaises(fc.FeelContractError):
            fc.struct_fields(header)


class Correspondence(Files):
    def test_matching_pair_passes(self):
        csv, header = self.pair(["A", "B"], ["A", "B"])
        self.assertEqual(fc.assert_correspondence(csv, header), ["A", "B"])

    def test_field_without_a_column_would_import_as_zero(self):
        csv, header = self.pair(["A"], ["A", "B"])
        with self.assertRaises(fc.FeelContractError) as c:
            fc.assert_correspondence(csv, header)
        self.assertIn("import as zero", str(c.exception))

    def test_column_without_a_field_would_be_discarded(self):
        csv, header = self.pair(["A", "B"], ["A"])
        with self.assertRaises(fc.FeelContractError) as c:
            fc.assert_correspondence(csv, header)
        self.assertIn("discarded", str(c.exception))

    def test_reordering_is_reported_as_such(self):
        csv, header = self.pair(["A", "B"], ["B", "A"])
        with self.assertRaises(fc.FeelContractError) as c:
            fc.assert_correspondence(csv, header)
        self.assertIn("different order", str(c.exception))


class TheRealTable(unittest.TestCase):
    def test_the_projects_csv_and_struct_agree(self):
        fields = fc.assert_correspondence(REAL_CSV, REAL_HEADER)
        self.assertIn("WalkSpeed", fields)
        self.assertEqual(len(fields), 9)


if __name__ == "__main__":
    unittest.main()
