"""
Editor automation: build a crew-authored StringTable asset in the project.

Run inside the UE editor. Two consoles, two syntaxes — `py <file> <args>` is a
Cmd-mode command, and typing it in Python mode is a syntax error:

    Python mode:  import import_stringtables as s; s.import_string_table("/path/to/st_ui_hud.json")
    Cmd mode:     py import_stringtables /path/to/st_ui_hud.json

After editing this file, reload it — Python caches modules for the session:

    import importlib, import_stringtables; importlib.reload(import_stringtables)

This is the Import stage for text, and it refuses on the same terms as the room
importer: nothing lands without a provenance record showing the deterministic
gate passed, a review happened, a human approved, and the artifact's hash still
matches what was approved.

Why a script rather than the editor's own String Table tooling: text is content
with a spec, and this project's rule is that such content enters through a gate.
Placing these rows by hand — or through an agent tool that can do it in one call
— would produce the same asset with none of the argument for trusting it.

Idempotent: the table is rebuilt from the artifact each run, so re-importing
after a wording change leaves one table rather than a merge of two.
"""
import json
import os
import sys

import unreal

from provenance import ProvenanceError, check

DEST_PATH = "/Game/UI/Text"

# vault/07-ui-and-controls/uispec.md: the artifact names its own table, and the
# key's prefix must agree with it. Nothing here invents a destination.
VALID_TABLES = {"ST_UI", "ST_Lore"}


def _asset_path(table_name):
    return f"{DEST_PATH}/{table_name}"


def _load_spec(spec_path):
    with open(spec_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_shape(spec):
    """Structural checks the importer must not proceed without.

    The gate has already run — this is not a second opinion on the content. It
    guards the two things that would corrupt an asset rather than merely make it
    wrong: an unknown destination table, and a key that belongs to a different
    one.
    """
    table = spec.get("table")
    if table not in VALID_TABLES:
        raise RuntimeError(
            f"[import_stringtables] table is {table!r}; expected one of {sorted(VALID_TABLES)}")

    records = spec.get("records") or []
    if not records:
        raise RuntimeError("[import_stringtables] the artifact has no records")

    for i, record in enumerate(records):
        key = record.get("key", "")
        if not key.startswith(f"{table}."):
            raise RuntimeError(
                f"[import_stringtables] records[{i}] key {key!r} does not belong to {table}")
        if not record.get("text_en") or not record.get("text_es"):
            raise RuntimeError(
                f"[import_stringtables] records[{i}] ({key}) is missing text in one language")
    return table, records


def import_string_table(spec_path, locale="en"):
    """Build the table named by the artifact. Returns the keys written.

    `locale` selects which authored language is written into the asset. Both are
    authored in origin, so this is a choice of which one ships in the default
    culture, not a translation step.
    """
    if not os.path.isfile(spec_path):
        raise RuntimeError(f"spec not found: {spec_path}")

    # Refuse before creating anything. An unapproved artifact is not a build
    # error to recover from; it is text that has not earned its way in.
    try:
        record = check(spec_path)
    except ProvenanceError as exc:
        raise RuntimeError(f"[import_stringtables] REFUSED — {exc}") from exc

    spec = _load_spec(spec_path)
    table, records = _validate_shape(spec)

    text_field = "text_es" if locale == "es" else "text_en"
    asset_path = _asset_path(table)

    # Rebuild rather than merge: a table assembled from two runs of different
    # artifacts is a table nobody approved.
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.EditorAssetLibrary.delete_asset(asset_path)

    factory = unreal.StringTableFactory()
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=table, package_path=DEST_PATH,
        asset_class=unreal.StringTable, factory=factory)
    if asset is None:
        raise RuntimeError(f"[import_stringtables] could not create {asset_path}")

    library = unreal.StringTableLibrary
    written = []
    for entry in records:
        # The asset is addressed by the key's tail; the table id supplies the rest.
        short_key = entry["key"].split(".", 1)[1]
        library.set_string_table_entry(asset, short_key, entry[text_field])
        written.append(entry["key"])

    unreal.EditorAssetLibrary.save_asset(asset_path)

    # Verify what landed. An asset existing is not the same as an asset holding
    # the rows the artifact carried.
    reloaded = unreal.load_object(None, f"{asset_path}.{table}")
    present = {str(k) for k in library.get_meta_data_ids(reloaded)} if reloaded else set()
    missing = [k for k in written if k.split(".", 1)[1] not in present] if present else []

    approved_at = (record.get("approval") or {}).get("at", "?")
    unreal.log(
        f"[import_stringtables] {table}: {len(written)} record(s) written from "
        f"{os.path.basename(spec_path)} in '{locale}'. Approved {approved_at}."
    )
    if missing:
        unreal.log_warning(
            f"[import_stringtables] could not confirm {len(missing)} key(s) after save: {missing}")
    return written


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: py import_stringtables <st_*.json> [en|es]")
    import_string_table(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "en")
