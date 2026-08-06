#!/usr/bin/env python3
"""Retrieval over the design corpus. Stdlib only, deterministic, no API keys.

The knowledge base is this project's own design documents: the vault notes and the
two GDDs. Chunks are cut on markdown headings, so every chunk carries the address
that produced it — `path#heading` — and a generated string can cite what it was
written from.

Ranking is BM25, in about sixty lines. Chosen over embeddings for three reasons
that matter more here than semantic recall: it is deterministic, so the same query
returns the same ranking forever; it needs no paid API; and it runs in a fresh
clone, which the LLM half of this crew cannot. Whether embeddings would earn their
place is a question for the recall measurement below, not for taste.

Usage:
  python3 agents/retriever.py --query "what the run-complete screen must say"
  python3 agents/retriever.py --query "..." --k 5 --context   # a block to paste into a brief
  python3 agents/retriever.py --eval                          # recall@k over the labelled set
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

BASE_DIR = Path(__file__).resolve().parent.parent
CORPUS_DIRS = [BASE_DIR / "vault"]
CORPUS_FILES = [BASE_DIR / "GDD" / "GDD-course-scope.md", BASE_DIR / "GDD" / "GDD.md"]
EVAL_SET = Path(__file__).resolve().parent / "retrieval_eval.json"

# BM25, standard parameters. k1 damps how much a repeated term keeps paying;
# b is how hard a long chunk is penalised for its length.
K1, B = 1.5, 0.75

# The law and the term table are never retrieved. They are pinned: injected on
# every call as jurisdiction rather than as relevant material, so a query that
# happens not to mention them cannot drop them. See 13-ui-copy-writer.md.
PINNED = {
    "vault/07-ui-and-controls/uispec.md",
    "vault/07-ui-and-controls/ui-constraints.md",
    "vault/07-ui-and-controls/ui-budgets.md",
    "vault/00-core/terminology-guard.md",
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
    paths = sorted(p for d in CORPUS_DIRS for p in d.rglob("*.md"))
    paths += [p for p in CORPUS_FILES if p.exists()]
    corpus = [c for p in paths for c in chunk_file(p)]
    if not corpus:
        sys.exit("❌ Empty corpus; refusing to retrieve from nothing.")
    for chunk in corpus:
        # The filename is indexed alongside the text, because in this corpus it is a
        # curated topic label rather than noise: the vault is organised one note per
        # subject, so `titan-kit.md` is the strongest evidence a chunk is about the
        # Titan's kit. Leaving it out cost three of sixteen labelled queries — the
        # ones naming their subject exactly, which is the easy case a retriever has
        # no excuse to miss.
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
           include_pinned: bool = False, tiered: bool = True) -> List[Tuple[float, Dict]]:
    """BM25 ranking. Pinned notes are excluded by default — they are already injected.

    `tiered` puts the vault ahead of the GDDs, and it is on by default because flat
    BM25 measurably fails without it. The two GDDs are long and cover everything, so
    their chunks beat short focused notes on term overlap: asking about the Titan's
    kit returned the scoped GDD instead of `titan-kit.md`, three times out of
    sixteen. Length normalisation dampens that and does not fix it, because the GDD
    sections genuinely do contain more matching words.

    The fix is not a weight to tune, it is a statement about the corpus. The vault
    is the canon this crew is built to read — every agent's context is vault notes.
    The GDDs are where that canon came from, and one of them describes a game three
    campaigns wider than the slice. So the GDD is a fallback tier that fills
    whatever slots the vault could not, never a competitor for the top of the list.
    """
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
    if not tiered:
        return scored[:k]

    vault = [pair for pair in scored if pair[1]["path"].startswith("vault/")]
    rest = [pair for pair in scored if not pair[1]["path"].startswith("vault/")]
    return (vault + rest)[:k]


def context_block(query: str, hits: List[Tuple[float, Dict]]) -> str:
    """The retrieved half of an agent's context, with its addresses attached."""
    lines = [f"RETRIEVED CONTEXT for: {query}",
             "Cite the source of every record you write in its source_chunks field.",
             ""]
    for score, chunk in hits:
        lines += [f"--- {chunk['source']}  (bm25 {score:.2f})", chunk["text"], ""]
    return "\n".join(lines)


def evaluate(k_values=(3, 5), tiered: bool = True) -> Dict:
    """Recall@k over the labelled set, reported as a raw count and not only a rate.

    Labels are at FILE granularity, not chunk: a query is answered if any chunk of
    the expected note appears in the top k. That is the honest granularity for a
    hand-labelled set of this size — labelling exact headings would mean asserting
    which of a note's sections is the right one, which is a judgment the labeller
    would be marking their own homework on.
    """
    cases = json.loads(EVAL_SET.read_text(encoding="utf-8"))["queries"]
    corpus = build_corpus()
    results = {f"recall@{k}": {"hits": 0, "total": len(cases), "misses": []} for k in k_values}

    for case in cases:
        hits = search(case["query"], corpus, k=max(k_values), tiered=tiered)
        ranked = [c["path"] for _, c in hits]
        for k in k_values:
            expected = case["expect_file"]
            if any(path.endswith(expected) for path in ranked[:k]):
                results[f"recall@{k}"]["hits"] += 1
            else:
                results[f"recall@{k}"]["misses"].append(
                    {"query": case["query"], "expected": expected, "got": ranked[:k]})

    for key, res in results.items():
        res["rate"] = round(res["hits"] / res["total"], 3)
    return results


def main():
    parser = argparse.ArgumentParser(description="Echoes design-corpus retriever (BM25)")
    parser.add_argument("--query", help="What the generator needs to know")
    parser.add_argument("--k", type=int, default=5, help="How many chunks to return")
    parser.add_argument("--context", action="store_true",
                        help="Print a pasteable context block instead of JSON")
    parser.add_argument("--eval", action="store_true", help="Report recall@k over the labelled set")
    parser.add_argument("--flat", action="store_true",
                        help="Disable vault-first tiering; reproduces the measurement "
                             "that motivated it")
    parser.add_argument("--stats", action="store_true", help="Describe the corpus")
    args = parser.parse_args()

    if args.eval:
        print(json.dumps(evaluate(tiered=not args.flat), indent=2, ensure_ascii=False))
        return
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
        parser.error("--query is required unless --eval or --stats is given")

    hits = search(args.query, build_corpus(), k=args.k, tiered=not args.flat)
    if args.context:
        print(context_block(args.query, hits))
    else:
        print(json.dumps({"query": args.query, "chunks": [
            {"source": c["source"], "bm25": round(s, 3), "text": c["text"]}
            for s, c in hits]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
