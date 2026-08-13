"""
Editor automation: (re)import DT_GameFeel from the CSV source of truth.

Run inside the UE editor Python console:   py import_datatables

Idempotent: run it every time DT_GameFeel.csv changes instead of clicking Reimport.
Re-running replaces the table's rows rather than appending to them.

The row type is the native `FGameFeelRow` in the game module, not an asset. A
DataTable needs a row struct, and one authored in C++ is text a compiler checks
and a diff shows; the editor's struct editor is not reachable from Python anyway,
so the asset route would have meant permanent hand-work in the GUI.

Before importing anything, this checks that the CSV columns and the struct fields
still correspond. Unreal does not treat a mismatch as an error — it drops the
column and leaves the field at zero — so a rename on one side would quietly ship
a character whose walk speed is nothing.
"""
import os

import unreal

from feel_contract import FeelContractError, assert_correspondence

ROW_STRUCT = "/Script/Echoes.GameFeelRow"
DEST_PATH = "/Game/Data"
DEST_NAME = "DT_GameFeel"
CSV_NAME = "DT_GameFeel.csv"
HEADER_RELATIVE = os.path.join("Source", "Echoes", "GameFeelRow.h")


def _project_dir():
    return unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())


def _csv_path():
    return os.path.join(_project_dir(), "SourceAssets", CSV_NAME)


def _load_row_struct():
    struct = unreal.load_object(None, ROW_STRUCT)
    if struct is None:
        raise RuntimeError(
            f"{ROW_STRUCT} not found. The game module is most likely not built, or "
            "the editor is running against an older binary. Close the editor and "
            "rebuild the EchoesEditor target."
        )
    return struct


def _expected_row_names(csv_path):
    with open(csv_path, "r", encoding="utf-8") as handle:
        lines = [line for line in (raw.strip() for raw in handle) if line]
    return [line.split(",")[0] for line in lines[1:]]


def import_game_feel_table():
    csv_path = _csv_path()
    if not os.path.isfile(csv_path):
        raise RuntimeError(f"CSV not found: {csv_path}")

    header_path = os.path.join(_project_dir(), HEADER_RELATIVE)
    try:
        fields = assert_correspondence(csv_path, header_path)
    except FeelContractError as exc:
        # Refuse outright. Importing a table full of silent zeros is worse than
        # not importing at all, because the zeros look like tuning.
        raise RuntimeError(f"[import_datatables] contract check failed: {exc}") from exc

    struct = _load_row_struct()

    # CSVImportFactory, not DataTableFactory. The latter is the content browser's
    # "create an empty DataTable" factory and declares no file extensions, so the
    # import fails with "Unknown extension 'csv'". The row struct travels in the
    # automated settings rather than on the factory itself.
    factory = unreal.CSVImportFactory()
    factory.automated_import_settings.import_row_struct = struct
    factory.automated_import_settings.import_type = unreal.CSVImportType.ECSV_DATA_TABLE

    task = unreal.AssetImportTask()
    task.filename = csv_path
    task.destination_path = DEST_PATH
    task.destination_name = DEST_NAME
    task.replace_existing = True
    task.automated = True
    task.save = True
    task.factory = factory

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    result_path = f"{DEST_PATH}/{DEST_NAME}"
    if not unreal.EditorAssetLibrary.does_asset_exist(result_path):
        raise RuntimeError(f"[import_datatables] import of {DEST_NAME} failed")

    # Verify what landed instead of trusting that the import succeeded: a table
    # that exists is not the same as a table holding the rows the CSV had.
    table = unreal.load_object(None, f"{result_path}.{DEST_NAME}")
    imported = [str(n) for n in
                unreal.DataTableFunctionLibrary.get_data_table_row_names(table)]
    expected = _expected_row_names(csv_path)

    if sorted(imported) != sorted(expected):
        raise RuntimeError(
            f"[import_datatables] row mismatch after import: "
            f"expected {expected}, got {imported}"
        )

    unreal.log(
        f"[import_datatables] {DEST_NAME} updated from {CSV_NAME} — "
        f"{len(imported)} row(s), {len(fields)} field(s)"
    )
    return imported


if __name__ == "__main__":
    import_game_feel_table()
