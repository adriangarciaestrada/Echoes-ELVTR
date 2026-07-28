No hay conectividad MCP con el editor de Unreal en esta sesión (el único tool que apareció fue `DesignSync`, que no aplica), así que esto queda como el entregable de receta — igual que el resto de `production/semana-0-greybox-recetas.md` — para que lo ejecutes tú en el editor. Reusé el patrón de coyote time / dodge ya validado en esa receta (para no reinventar algo que el equipo ya probó), y añadí lo que faltaba: el mesh placeholder Manny, y el script Python de importación del DataTable.

Una corrección de API importante antes de la receta: **`JumpMaxCount` y `JumpCurrentCount` viven en el propio Character**, no en el componente CharacterMovement (es un error común — hasta la receta previa lo da por hecho sin aclararlo).

---

## 1. DataTable schema (`S_GameFeel` / `DT_GameFeel`)

El CSV ya existe en `Echoes/SourceAssets/DT_GameFeel.csv` (fuente de verdad en git):

```csv
Name,WalkSpeed,JumpZVelocity,GravityScale,AirControl,JumpMaxCount,MinJumpFraction,CoyoteTime,InputBufferTime,DodgeSpeed,DodgeDuration,DodgeIFrameDuration
Default,600,700,2.0,0.9,2,0.4,0.12,0.15,1500,0.4,0.25
```

**Struct `S_GameFeel`** (Content Browser → click derecho → Blueprints → **Structure** → guardar en `Content/Data/S_GameFeel`). Los nombres de campo deben ser **idénticos** a los headers del CSV (el import matchea por nombre):

| Campo | Tipo |
|---|---|
| `WalkSpeed` | Float |
| `JumpZVelocity` | Float |
| `GravityScale` | Float |
| `AirControl` | Float |
| `JumpMaxCount` | **Integer** |
| `MinJumpFraction` | Float |
| `CoyoteTime` | Float |
| `InputBufferTime` | Float |
| `DodgeSpeed` | Float |
| `DodgeDuration` | Float |
| `DodgeIFrameDuration` | Float |

Luego: click derecho → Miscellaneous → **Data Table** → elegir row struct `S_GameFeel` → guardar como `Content/Data/DT_GameFeel`. Este `.uasset` es **derivado** del CSV — nunca lo edites a mano en el editor, siempre reimporta.

## 2. Script de importación — `import_datatables.py`

Colócalo en `Echoes/Content/Python/import_datatables.py` (esa carpeta la auto-descubre el plugin Python de UE). Es idempotente: puedes correrlo cada vez que cambie el CSV en vez de darle click a "Reimport" a mano.

```python
"""Editor automation: (re)import DT_GameFeel from the CSV source of truth.
Run from the UE Python console: py import_datatables
Requires: PythonScriptPlugin enabled (already is, see Echoes.uproject).
"""
import os
import unreal

STRUCT_ASSET = "/Game/Data/S_GameFeel.S_GameFeel"
DEST_PATH = "/Game/Data"
DEST_NAME = "DT_GameFeel"


def _csv_path():
    # Content/Python/../../SourceAssets/DT_GameFeel.csv
    content_dir = unreal.Paths.project_content_dir()
    return unreal.Paths.convert_relative_path_to_full(
        os.path.join(content_dir, "..", "SourceAssets", "DT_GameFeel.csv")
    )


def import_game_feel_table():
    struct = unreal.load_object(None, STRUCT_ASSET)
    if struct is None:
        raise RuntimeError(
            f"No se encontró {STRUCT_ASSET}. Crea el struct S_GameFeel primero (paso 1)."
        )

    csv_path = _csv_path()
    if not os.path.isfile(csv_path):
        raise RuntimeError(f"No existe el CSV: {csv_path}")

    factory = unreal.DataTableFactory()
    factory.struct = struct

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
    if unreal.EditorAssetLibrary.does_asset_exist(result_path):
        unreal.log(f"[import_datatables] {DEST_NAME} actualizado desde {csv_path}")
    else:
        unreal.log_error(f"[import_datatables] Falló el import de {DEST_NAME}")


if __name__ == "__main__":
    import_game_feel_table()
```

Verificación de este paso: abre `Content/Data/DT_GameFeel` después de correrlo → la fila `Default` debe mostrar exactamente los 11 valores del CSV.

## 3. Placeholder visual — Manny + Anim BP

1. Content Browser → botón verde **Add** (arriba-izq) → **Add Feature or Content Pack** → pestaña *Blueprint Feature or Content Packs* → **Third Person** → *Add to Project*.
2. Esto copia el esqueleto/mesh/anim BP del maniquí a tu proyecto (la ruta exacta varía un poco por versión — busca "Manny" en el Content Browser después de importar). Anota dos assets: el **Skeletal Mesh** (`SKM_Manny`) y su **Animation Blueprint** (algo como `ABP_Manny`, sobre el skeleton `SK_Mannequin`).
3. Abre `BP_GreyBoxCharacter` → panel **Components** → selecciona **Mesh (Inherited)** → Details:
   - **Skeletal Mesh Asset** = `SKM_Manny`
   - **Anim Class** = `ABP_Manny`
   - **Location** = `(0, 0, -88)`, **Rotation** = `(0, 0, -90)` (yaw) — corrección estándar: el capsule por defecto de Character mide Half Height 88, y el mesh del maniquí exporta con el frente rotado -90° respecto al forward del actor. Esto **no** es un tunable de feel (es una constante de alineación de este mesh específico), así que no va en el DataTable — igual que el `700` del Spring Arm de la receta de cámara.

**Verificación:** dale Play — debes ver el cuerpo de Manny parado en el suelo (no flotando, no hundido), y al moverte, la animación de correr del ThirdPerson template (aunque no sea la definitiva, confirma que el Anim BP y el skeleton están bien enlazados).

## 4. `BP_GreyBoxCharacter` — Components (Details panel, sin nodos)

**Character Movement** component → sección *Planar Movement*:
- ✅ **Constrain to Plane**
- **Plane Constraint Normal** = `(0, 1, 0)`
- ✅ **Snap to Plane at Start**

(Esto es arquitectura fija del vault — regla 4 de `technical-constraints.md` — no un valor de `DT_GameFeel`, por eso se configura aquí y no se lee del DataTable.)

## 5. Variables del Blueprint (My Blueprint → Variables → +)

| Variable | Tipo | Default |
|---|---|---|
| `CachedGameFeel` | Struct `S_GameFeel` | — |
| `FacingDirection` | Float | `1.0` |
| `bCoyoteActive` | Boolean | false |
| `BufferedJumpTimeStamp` | Float | `-1000.0` (centinela: "no hay salto en buffer") |
| `bIsDodging` | Boolean | false |
| `bInvulnerable` | Boolean | false |

## 6. Event Graph

### 6a. BeginPlay — cargar input y feel del DataTable

```
Event BeginPlay
 → Get Controller → Cast To PlayerController
   → Get Enhanced Input Local Player Subsystem
     → Add Mapping Context (Context = IMC_Default, Priority = 0)

 → Get Data Table Row (Data Table = DT_GameFeel, Row Name = "Default")
     [nodo con pin de salida "Out Row" tipo wildcard — al arrastrar
      un "Break S_GameFeel" desde ahí, UE te pide fijar el tipo de struct;
      elige S_GameFeel. Es un detalle que confunde a principiantes.]
   → Set CachedGameFeel = Out Row

 → Break CachedGameFeel
   → Get Character Movement Component
       → Set Max Walk Speed (WalkSpeed)
       → Set Jump Z Velocity (JumpZVelocity)
       → Set Gravity Scale (GravityScale)
       → Set Air Control (AirControl)
   → Self → Set Jump Max Count (JumpMaxCount)   ⚠️ en el Character, NO en CharacterMovement
```

**Verificación:** Print String de `CachedGameFeel.WalkSpeed` en BeginPlay → debe imprimir `600.0`. Si el pin "Out Row" no resolvió a `S_GameFeel`, el Break no aparecerá — es la señal de que falta fijar el struct type.

### 6b. Movimiento lateral (IA_Move, Triggered)

```
IA_Move (Triggered) → Action Value (ya es Float: IA_Move es Axis1D)
 → Add Movement Input (World Direction = (1,0,0), Scale Value = Action Value)
 → Branch (Action Value > 0): Set FacingDirection = 1.0 → Set Actor Rotation (Yaw 0)
 → Branch (Action Value < 0): Set FacingDirection = -1.0 → Set Actor Rotation (Yaw 180)
```

Turnaround instantáneo por construcción (Set Actor Rotation, sin interpolar).

**Verificación:** mover el stick/A-D → el personaje voltea sin frames de giro intermedio, y nunca se desplaza en Y (empújalo en diagonal contra un borde para confirmarlo).

### 6c. Doble salto + salto variable + coyote + buffer (IA_Jump)

**Started:**
```
Branch: (Character Movement → Is Movement Mode == Walking)
        OR (Jump Current Count < Jump Max Count)
 → TRUE: Jump()                     [nativo — cubre suelo + el salto extra en aire]
 → FALSE:
     Branch: bCoyoteActive == true
      → TRUE: Launch Character(Velocity=(0,0,CachedGameFeel.JumpZVelocity),
                                XYOverride=false, ZOverride=true)
               Set bCoyoteActive = false
      → FALSE: Set BufferedJumpTimeStamp = Get Game Time In Seconds
```

**Completed (soltar el botón):**
```
Branch: (Get Velocity → Break Vector → Z) > 0
        AND Z > (CachedGameFeel.JumpZVelocity × CachedGameFeel.MinJumpFraction)
 → TRUE: Launch Character(
            Velocity = (0,0, CachedGameFeel.JumpZVelocity × CachedGameFeel.MinJumpFraction),
            XYOverride=false, ZOverride=true)
```
Esto recorta el arco a ~`MinJumpFraction` (40%) si sueltas temprano.

**On Movement Mode Changed** (evento de Character — buscar en el grafo "Movement Mode Changed"):
```
Branch: New Movement Mode == Falling
        AND Previous Movement Mode == Walking
        AND Jump Current Count == 0        [distingue "se cayó" de "saltó"]
 → TRUE: Set bCoyoteActive = true
         Set Timer By Event (Time = CachedGameFeel.CoyoteTime, Looping=false)
           → on expire: Set bCoyoteActive = false
```

**On Landed** (evento de Character):
```
Branch: (Get Game Time In Seconds − BufferedJumpTimeStamp) < CachedGameFeel.InputBufferTime
        AND BufferedJumpTimeStamp > 0
 → TRUE: Jump()
         Set BufferedJumpTimeStamp = -1000.0
```

Ningún número (0.12, 0.15, 0.4, 700...) va escrito en el grafo — todo sale de `CachedGameFeel`.

**Verificación (por sub-mecánica):**
- Doble salto: exactamente 2 saltos en el aire, se resetea al tocar suelo.
- Salto variable: tap corto del botón ≈ 40% de altura vs. hold completo.
- Coyote: caminar fuera de una saliente y presionar salto ~0.1 s después de dejar el suelo → SÍ salta; espera >120 ms y ya no.
- Buffer: presiona salto ~0.1 s antes de tocar el piso (cayendo de una plataforma) → salta apenas aterriza, sin tener que soltar y volver a presionar.

### 6d. Dodge con i-frames (IA_Defense, Started)

```
Branch: bIsDodging == true
 → TRUE: (salir, no re-trigger)         ← esta rama NO depende de ningún otro estado:
                                            así "defense has priority" queda expresado en
                                            el grafo — nada más puede bloquear el dodge,
                                            solo el propio dodge en curso.
 → FALSE:
     Set bIsDodging = true
     Set bInvulnerable = true
     Launch Character(Velocity=(CachedGameFeel.DodgeSpeed × FacingDirection, 0, 0),
                       XYOverride=true, ZOverride=false)   [XY override = burst limpio,
                                                             Z sin tocar = no cancela caída]

     Set Timer By Event "IFrameTimer" (Time = CachedGameFeel.DodgeIFrameDuration)
       → on expire: Set bInvulnerable = false

     Set Timer By Event "RecoveryTimer" (Time = CachedGameFeel.DodgeDuration)
       → on expire: Set bIsDodging = false
```

`DodgeDuration (0.4) − DodgeIFrameDuration (0.25) = 0.15 s` de recovery: entre que expiran los i-frames y expira `bIsDodging`, el dodge ya no protege pero tampoco se puede re-disparar — ese es el "no frame-one spam".

Como en R1 todavía no hay sistema de daño, `bInvulnerable` no tiene a quién avisarle. Para poder **ver** el i-frame en PIE, añade un Print String temporal: "IFRAME ON" (cian) al activarse, "IFRAME OFF" al desactivarse — es debug, no se shipea.

**Verificación:** presiona dodge → burst lateral hacia el facing actual; mantener presionado o spamear el botón durante los 400 ms no re-dispara nada; el Print confirma que el i-frame dura ~250 ms y luego hay ~150 ms de "quieto pero ya sin protección" antes de poder volver a esquivar.

## 7. Cómo se verificaría (nota de auditoría)

No hay todavía un test harness automatizado para game feel — la verificación de R1 es manual en PIE, checklist arriba por mecánica. Si más adelante quieres un hook determinista (en vez de "se ve bien"), lo natural sería un **Functional Test map** de UE (`FunctionalTest` actor) que dispare inputs sintéticos vía Timeline y assert sobre `Velocity`/`JumpCurrentCount` en cada frame — pero eso es trabajo de una milestone posterior, no de este grey-box.

---

¿Quieres que arme también la Receta 0 (mapa gimnasio) específica para probar coyote time y el doble salto con Manny, o ya la tienes cubierta por `semana-0-greybox-recetas.md`?