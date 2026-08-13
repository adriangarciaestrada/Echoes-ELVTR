# Editor Tooling — verified reference (UE 5.8.1)

What the editor bridge can and cannot do. Facts marked **[verified]** were
observed against a running editor on 2026-08-09; facts marked **[documented]**
come from tool schemas and engine source but have not been executed.

Applies to the 5.8.1 project only. The 5.7.4 project uses a different bridge.

## Connecting

**[verified]** HTTP endpoint `127.0.0.1:8000/mcp`, protocol `2025-06-18`.
Handshake: `initialize` → keep the `Mcp-Session-Id` response header →
`notifications/initialized` → `tools/call`. Responses arrive as SSE frames and
may span multiple lines; a line-by-line JSON parser will fail on them.

Only three tools are listed. Everything else is reached through them:

```
list_toolsets · describe_toolset · call_tool
```

**[verified]** `call_tool` takes `toolset_name` (optional), `tool_name`
(required, no prefix), `arguments`. Guessing these names costs turns.

A working client is committed at `Echoes-58/Scripts/mcp.py`.

## Batching: the tool script sandbox

`ProgrammaticToolset.execute_tool_script` runs a Python script that must define
`run() -> dict`. Inside it, `execute_tool(tool_name, json_input)` reaches any
registered tool, so one round trip can perform many operations with real control
flow. This is the mechanism Layer B of the pipeline is built on.

Four constraints, all **[verified]**, all load-bearing:

1. **Importable modules are `json`, `math`, `datetime`, `copy`, `re`, `time`.**
   There is no `unreal`, no `os`, no `sys`, no `importlib`. Project Python
   (`import_room.py`, `provenance.py`, `import_stringtables.py`) cannot run here.
2. **A failing `execute_tool` aborts the whole script.** The failure is not
   catchable by `except Exception` or `except BaseException`. Scripts must check
   preconditions — `AssetTools.exists` before `create` — rather than rely on
   error handling.
3. **Returned dicts are `_StrictDict`**: `.get(key, default)` raises. Use direct
   key access.
4. Inside `execute_tool`, tool names are fully qualified, e.g.
   `editor_toolset.toolsets.scene.SceneTools.find_actors`.

## Common parameter shapes

**[documented]** `ObjectRef` = `{"refPath": "/Game/Path/Asset.Asset"}` — used
wherever a tool takes an actor, component, class, graph, pin, or asset. For an
actor: `/Game/Maps/L_X.L_X:PersistentLevel.StaticMeshActor_14`.

## Binding text to a String Table

**[verified]** No MCP tool takes a String Table key for a text property — they
all take strings. The binding is still achievable, and by the route Epic
recommends, because `FText` properties accept an import-text form:

```
LOCTABLE("/Game/UI/Text/ST_UI.ST_UI", "HUD.Health")
```

Passed as `propertyValue` to `WidgetService.SetProperty`, this produces a
genuinely string-table-backed `FText`, not a literal.

- The table id of an asset-based String Table is its full asset path.
- **Verification:** read the property back. `GetProperty` returns export text,
  and the `LOCTABLE(...)` form is only emitted when a string-table reference
  exists. An untouched Text Block reads back as
  `NSLOCTEXT("UMG", "TextBlockDefaultValue", "Text Block")`, so the two are
  distinguishable. A literal assignment would not round-trip.
- The runtime alternative, `KismetTextLibrary.text_from_string_table`, exists and
  is exposed to Python, but engine documentation explicitly prefers setting the
  reference on the property. Treat it as a fallback for dynamic content only.

## Design-time versus run-time values

**[documented]** `BlueprintService.GetProperty` and `GetComponentProperty` read
the **class default object** — design-time defaults, not a live instance. Using
them to confirm that values applied during play will always report the design
value regardless of what happened.

For a live actor, `ActorService.GetAllProperties(label)` resolves by name or
label. During play there are two worlds; the label must resolve against the
`UEDPIE_0_` world, not the editor template.

`EditorAppToolset.StartPIE` waits for the session to be up plus a warmup period,
which is more reliable than polling for a process.

## Authoring Blueprint graphs

Two independent text-first paths exist, both **[documented]**:

- `BlueprintTools.write_graph_dsl` / `read_graph_dsl` / `get_graph_dsl_docs` —
  a graph as an editable script.
- `BlueprintService.BuildGraph` — nodes, connections and pin defaults in one
  transaction, with auto-layout and compile-after flags.

Either is preferable to placing nodes individually, which is how the R1
animation graph was built and where several turns were lost.

## Safety net

**[documented]** `TransactionService` wraps the editor undo buffer:
`BeginTransaction(name)` → edits → `CancelTransaction()` rolls the whole group
back. Wrap any multi-step edit that could half-apply.

## Toolsets worth knowing

Use now: `SceneTools`, `ActorTools`, `AssetTools`, `ObjectTools`,
`BlueprintTools`, `EditorAppToolset`, `StringTableTools`, `DataTableTools`,
`UMGToolSet`, `VibeUE.WidgetService`, `VibeUE.BlueprintService`,
`VibeUE.TransactionService`, `VibeUE.ActorService`, `StateTreeService`,
`AnimGraphService`, `AnimMontageService`, `AnimSequenceService`,
`SkeletalMeshTools`.

Not for this project: landscape, foliage, Niagara, MetaSound, PCG, runtime
virtual texturing, UV tools, map blockout, and every GAS toolset. **Never enable
`AllToolsets`** — it pulls GAS in, and GAS stays out of game code.

## What cannot be registered

`AgentSkillToolset` (`ListSkills`, `GetSkills`, `CreateSkill`, `UpdateSkill`)
stores only a description and a free-text instructions string. It has no input
schema and no code payload, so it cannot add a callable tool. It is discoverable
documentation, not tool surface. Registering a real tool is C++ plugin work.
