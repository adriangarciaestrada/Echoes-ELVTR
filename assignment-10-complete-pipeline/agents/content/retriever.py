#!/usr/bin/env python3
"""Retrieval over loom-vault. Stdlib only, deterministic, no API keys.

The knowledge base is this game's own design law. Chunks are cut on markdown
headings, so every chunk carries the address that produced it — `path#heading`
— and a generated string can cite what it was written from.

Ranking is BM25, in about sixty lines. Chosen over embeddings for three
reasons that matter more here than semantic recall: it is deterministic, so
the same query returns the same ranking forever; it needs no paid API; and it
runs in a fresh clone, which the LLM half of a content pipeline cannot.

Ported from the ELVTR metroidvania's assignment-4 retriever — same algorithm,
pointed at loom-vault instead of that game's vault. The generator and gate
that used to sit downstream of this (`build_strings.py`) never made it into
this repo when Loom was split out on its own; this file is the deterministic
half being rebuilt first, since it needs no model and is the part safe to
demo live.

Usage:
  python3 retriever.py --query "what a market reroll button should say"
  python3 retriever.py --query "..." --k 5 --context   # a block to paste into a brief
  python3 retriever.py --stats
"""
import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

# The design law this pipeline is grounded in, vendored into the
# deliverable so the retriever runs from inside this folder.
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "vault"

# BM25, standard parameters. k1 damps how much a repeated term keeps paying;
# b is how hard a long chunk is penalised for its length.
K1, B = 1.5, 0.75

# Jurisdiction, not material: injected on every real generation call rather
# than retrieved, so a query that happens not to mention them cannot drop
# them. Mirrors the metroidvania pipeline's PINNED set, translated to this
# vault's own budget and terminology notes.
PINNED = {
    "ui-and-strings.md",
    "from-echoes/terminology-guard.md",
}


def _fold(text: str) -> str:
    """Lowercase and strip accents, so 'pirámide' and 'piramide' are one term."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


def chunk_file(path: Path) -> List[Dict]:
    """One chunk per heading. The text before the first heading joins the title."""
    rel = str(path.relative_to(BASE_DIR))
    chunks: List[Dict] = []
    heading = path.stem
    body: List[str] = []

    def flush():
        text = "\n".join(body).strip()
        if text:
            chunks.append({"source": f"{rel}#{heading}", "path": rel,
                           "heading": heading, "text": text})

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            body = []
        else:
            body.append(line)
    flush()
    return chunks


def build_corpus() -> List[Dict]:
    paths = sorted(BASE_DIR.rglob("*.md"))
    corpus = [c for p in paths for c in chunk_file(p)]
    if not corpus:
        sys.exit("empty corpus; refusing to retrieve from nothing.")
    for chunk in corpus:
        # The filename is indexed alongside the text, because in this corpus
        # it is a curated topic label rather than noise — the vault is
        # organised one note per subject, so `loom-grid.md` is the strongest
        # evidence a chunk is about grid geometry. Learned from the
        # metroidvania retriever: leaving it out cost three of sixteen
        # labelled queries, the ones naming their subject exactly.
        label = Path(chunk["path"]).stem.replace("-", " ")
        chunk["tokens"] = tokenize(f"{chunk['text']} {chunk['heading']} {label} {label}")
    return corpus


def _idf(corpus: List[Dict]) -> Dict[str, float]:
    n = len(corpus)
    seen: Counter = Counter()
    for chunk in corpus:
        seen.update(set(chunk["tokens"]))
    return {term: math.log(1 + (n - df + 0.5) / (df + 0.5)) for term, df in seen.items()}


def search(query: str, corpus: List[Dict], k: int = 5,
           include_pinned: bool = False) -> List[Tuple[float, Dict]]:
    """BM25 ranking. Pinned notes are excluded by default — they are already injected."""
    idf = _idf(corpus)
    avg_len = sum(len(c["tokens"]) for c in corpus) / len(corpus)
    terms = tokenize(query)

    scored: List[Tuple[float, Dict]] = []
    for chunk in corpus:
        if not include_pinned and chunk["path"] in PINNED:
            continue
        counts = Counter(chunk["tokens"])
        length = len(chunk["tokens"])
        score = 0.0
        for term in terms:
            tf = counts.get(term, 0)
            if not tf:
                continue
            score += idf.get(term, 0.0) * (tf * (K1 + 1)) / (
                tf + K1 * (1 - B + B * length / avg_len))
        if score > 0:
            scored.append((score, chunk))
    # Ties break on source so the ranking is reproducible, not insertion-ordered.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["source"]))
    return scored[:k]


def context_block(query: str, hits: List[Tuple[float, Dict]]) -> str:
    """The retrieved half of a generator's context, with its addresses attached."""
    lines = [f"RETRIEVED CONTEXT for: {query}",
             "Cite the source of every record you write in its source_chunks field.",
             ""]
    for score, chunk in hits:
        lines += [f"--- {chunk['source']}  (bm25 {score:.2f})", chunk["text"], ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="loom-vault retriever (BM25)")
    parser.add_argument("--query", help="What the generator needs to know")
    parser.add_argument("--k", type=int, default=5, help="How many chunks to return")
    parser.add_argument("--context", action="store_true",
                        help="Print a pasteable context block instead of JSON")
    parser.add_argument("--stats", action="store_true", help="Describe the corpus")
    args = parser.parse_args()

    if args.stats:
        corpus = build_corpus()
        print(json.dumps({
            "chunks": len(corpus),
            "files": len({c["path"] for c in corpus}),
            "pinned_files_excluded_from_retrieval": sorted(PINNED),
            "tokens": sum(len(c["tokens"]) for c in corpus),
        }, indent=2))
        return
    if not args.query:
        parser.error("--query is required unless --stats is given")

    hits = search(args.query, build_corpus(), k=args.k)
    if args.context:
        print(context_block(args.query, hits))
    else:
        print(json.dumps({"query": args.query, "chunks": [
            {"source": c["source"], "bm25": round(s, 3), "text": c["text"]}
            for s, c in hits]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
