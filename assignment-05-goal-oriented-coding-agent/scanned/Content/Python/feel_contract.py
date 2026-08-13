"""The correspondence between DT_GameFeel.csv and FGameFeelRow, checked as text.

Unreal's DataTable importer matches CSV columns to struct fields by name. A
mismatch is not an error there: the column is dropped and the field imports as
zero. Rename a field in C++ and forget the CSV, and the character silently gets
a walk speed of zero the next time the table is reimported.

The check compares the two files that have to agree, rather than the struct's
reflection data, for one reason: it then runs with the editor closed, so it can
sit in front of a push instead of only inside the editor console. Reflection is
derived from this header anyway.
"""

import re
from pathlib import Path

FIELD = re.compile(r"^\s*(?:float|int32|bool|FString|FName)\s+(\w+)\s*(?:=|;)", re.M)
ROW_KEY = "Name"


class FeelContractError(ValueError):
    """The CSV and the row struct no longer describe the same table."""


def csv_fields(csv_path):
    header = Path(csv_path).read_text().splitlines()[0]
    columns = [c.strip() for c in header.split(",")]
    if not columns or columns[0] != ROW_KEY:
        raise FeelContractError(
            f"{Path(csv_path).name}: first column must be {ROW_KEY!r} (the row key), "
            f"got {columns[0]!r}"
        )
    return columns[1:]


def struct_fields(header_path):
    text = Path(header_path).read_text()
    # Only the UPROPERTY-decorated members participate in the table; anything
    # else in the header is not part of the contract.
    fields = []
    for block in text.split("UPROPERTY(")[1:]:
        match = FIELD.search(block)
        if match:
            fields.append(match.group(1))
    if not fields:
        raise FeelContractError(f"{Path(header_path).name}: no UPROPERTY fields found")
    return fields


def assert_correspondence(csv_path, header_path):
    """Raise unless the columns and the fields match in name and order."""
    columns, fields = csv_fields(csv_path), struct_fields(header_path)
    if columns == fields:
        return columns

    missing = [c for c in columns if c not in fields]
    extra = [f for f in fields if f not in columns]
    problems = []
    if missing:
        problems.append(f"columns with no field (would be discarded): {missing}")
    if extra:
        problems.append(f"fields with no column (would import as zero): {extra}")
    if not problems:
        problems.append(f"same names, different order: CSV {columns} vs struct {fields}")

    raise FeelContractError(
        f"{Path(csv_path).name} and {Path(header_path).name} disagree. "
        + "; ".join(problems)
    )
