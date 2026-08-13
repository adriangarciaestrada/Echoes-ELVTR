#!/usr/bin/env python3
"""Fail when the project references an asset the repository does not carry.

The marketplace character packs are git-ignored in full and their referenced
subset is re-included by exception (see "Marketplace assets" in CLAUDE.md).
That exception list is a maintenance trap: adding one reference to an asset
nobody remembered to un-ignore leaves a clone broken with no warning, and the
break only surfaces when someone opens the editor somewhere else.

This walks the reference graph outward from the project's own tracked assets
and reports every asset that is reachable but not in the repository.

    python3 Scripts/check-asset-closure.py            # report and exit code
    python3 Scripts/check-asset-closure.py --list     # also print the closure
    python3 Scripts/check-asset-closure.py --gitignore-block

Exit codes: 0 nothing to fix, 1 a referenced asset is untracked, 2 usage error.

Stdlib only, no engine required — it reads the package paths stored inside the
`.uasset` binaries rather than asking Unreal.

Scope caveat: this over-approximates on purpose. A text scan cannot tell an
editor-only reference from one the cooker follows, so chains like a skeleton's
preview mesh are counted even though they never ship. That is the right error
for the question being asked — can the project be opened from a clone — but it
makes this a poor predictor of packaged size. Measure the pak for that.
"""

import argparse
import os
import re
import subprocess
import sys

# Package paths as Unreal stores them: /Game/Some/Path/AssetName, optionally
# followed by .ObjectName. Conservative charset — anything looser starts
# matching arbitrary binary noise.
REF = re.compile(rb"/Game/[A-Za-z0-9_]+(?:/[A-Za-z0-9_\-\.]+)+")

ASSET_SUFFIXES = (".uasset", ".umap")


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def repo_root():
    return run("git", "rev-parse", "--show-toplevel").strip()


def tracked_files(root):
    """Every path git tracks, relative to the repository root."""
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    ).stdout
    return {p.decode() for p in out.split(b"\0") if p}


def content_path(root, ref):
    """Resolve /Game/A/B[.Object] to the file that holds it, if it exists."""
    ref = ref.split(".", 1)[0]  # drop the object name; the file is the package
    rel = ref[len("/Game/"):]
    for suffix in ASSET_SUFFIXES:
        candidate = os.path.join(root, "Content", rel + suffix)
        if os.path.isfile(candidate):
            return candidate
    return None


def references_in(path):
    with open(path, "rb") as handle:
        blob = handle.read()
    return {m.group(0).decode() for m in REF.finditer(blob)}


def closure(root, seeds):
    """Every asset reachable from the seeds, plus the refs that resolve nowhere."""
    reached, dangling, queue = {}, set(), list(seeds)
    while queue:
        path = queue.pop()
        rel = os.path.relpath(path, root)
        if rel in reached:
            continue
        reached[rel] = path
        for ref in references_in(path):
            target = content_path(root, ref)
            if target is None:
                dangling.add(ref)
            elif os.path.relpath(target, root) not in reached:
                queue.append(target)
    return reached, dangling


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true",
                        help="print every asset in the closure, largest first")
    parser.add_argument("--gitignore-block", action="store_true",
                        help="emit the .gitignore exception block for the closure")
    args = parser.parse_args()

    try:
        root = repo_root()
    except subprocess.CalledProcessError:
        print("not inside a git repository", file=sys.stderr)
        return 2

    tracked = tracked_files(root)

    # Seeds are the project's own assets: tracked, and not inside a pack. An
    # untracked asset cannot seed the walk, because whether it belongs in the
    # repository at all is a separate question from this check.
    seeds = [
        os.path.join(root, rel)
        for rel in sorted(tracked)
        if rel.startswith("Content/")
        and rel.endswith(ASSET_SUFFIXES)
        and os.path.isfile(os.path.join(root, rel))
    ]
    if not seeds:
        print("no tracked assets under Content/ — nothing to check")
        return 0

    reached, dangling = closure(root, seeds)
    missing = sorted(rel for rel in reached if rel not in tracked)

    if args.gitignore_block:
        # git cannot re-include a file whose parent directory is excluded, so
        # the pack is excluded with `/**` (files) and its directories are
        # re-included before the per-file exceptions. A bare `Pack/` here
        # would make every negation below it silently inert.
        by_pack = {}
        for rel in missing:
            by_pack.setdefault(rel.split("/")[1], []).append(rel)
        for pack, paths in sorted(by_pack.items()):
            print(f"# Referenced subset of Content/{pack} — regenerate with")
            print(f"#   python3 Scripts/check-asset-closure.py --gitignore-block")
            print(f"Content/{pack}/**")
            print(f"!Content/{pack}/**/")
            for rel in sorted(paths):
                print("!" + rel)
            print()
        return 0

    if args.list:
        sized = sorted(((os.path.getsize(p), rel) for rel, p in reached.items()),
                       reverse=True)
        total = sum(size for size, _ in sized)
        for size, rel in sized:
            mark = " " if rel in tracked else "!"
            print(f"{mark} {size / 1048576:7.1f} MB  {rel}")
        print(f"\n{len(sized)} assets, {total / 1048576:.0f} MB total")

    # A reference that resolves to no file on disk is not treated as a failure:
    # on this machine every pack is present, so it is far more likely to be a
    # byte sequence that merely looks like a package path. A clone missing the
    # packs is what the fresh-clone smoke test covers, not this check.
    if dangling:
        print(f"note: {len(dangling)} reference(s) resolve to no file on disk "
              f"(run with --list to inspect the closure)")

    if missing:
        print(f"\nFAIL — {len(missing)} referenced asset(s) are not tracked by git:\n")
        for rel in missing:
            size = os.path.getsize(os.path.join(root, rel)) / 1048576
            print(f"  {size:7.1f} MB  {rel}")
        print("\nEither track them, or drop the reference. To regenerate the "
              "exception block:\n"
              "  python3 Scripts/check-asset-closure.py --gitignore-block")
        return 1

    print(f"OK — {len(reached)} assets in the closure, all tracked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
