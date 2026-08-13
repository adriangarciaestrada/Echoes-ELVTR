#!/usr/bin/env bash
# Rebuild the UE_MCP_Bridge plugin binaries from the vendored (patched) source.
#
# Binaries/ is git-ignored, so a fresh checkout has source but no compiled .so.
# Run this once after checkout (and after any source change to the plugin).
#
# Prereq: UE 5.7.4 installed at the path below. The produced BuildId must match
# the engine's, or the editor will prompt to recompile on launch.
set -euo pipefail

UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/Linux_Unreal_Engine_5.7.4}"
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PLUGIN="$PROJECT_DIR/Plugins/UE_MCP_Bridge/UE_MCP_Bridge.uplugin"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/ue-mcp-bridge-build.XXXXXX")"

echo "Engine : $UE_ROOT"
echo "Plugin : $PLUGIN"
echo "Staging: $STAGE"

"$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh" BuildPlugin \
  -plugin="$PLUGIN" \
  -package="$STAGE" \
  -TargetPlatforms=Linux

# Copy just the Linux binaries back into the in-tree plugin (leave source as-is).
mkdir -p "$PROJECT_DIR/Plugins/UE_MCP_Bridge/Binaries/Linux"
cp "$STAGE/Binaries/Linux/"* "$PROJECT_DIR/Plugins/UE_MCP_Bridge/Binaries/Linux/"
rm -rf "$STAGE"

echo "Done. BuildId:"
grep -o '"BuildId": *"[^"]*"' "$PROJECT_DIR/Plugins/UE_MCP_Bridge/Binaries/Linux/UnrealEditor.modules"
