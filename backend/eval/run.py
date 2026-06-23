"""RAG eval runner.

Measures the pipeline against the frozen question set in dataset.jsonl.

From the backend/ directory:
    python -m eval.run                  # retrieval hit-rate only (fast, no LLM)
    python -m eval.run --answers        # also generate + grade answers (needs Ollama)
    python -m eval.run --max-version v1 # reproduce a frozen eval version
    python -m eval.run --show-misses    # print which questions retrieved the wrong doc

Two metrics:
  - retrieval hit-rate: did the expected source doc appear in the retrieved chunks?
    (objective, deterministic -- the primary signal for "garbage pulls")
  - answer fact-coverage: fraction of a question's expected_facts present in the
    generated answer (a rough heuristic; swap for an LLM judge later)

Results are appended to results.csv with the eval version AND the pipeline git
commit, so scores stay comparable across pipeline revisions and eval versions.
"""
import argparse
import csv
import datetime as _dt
import json
import subprocess
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).resolve().parent
DATASET = EVAL_DIR / "dataset.jsonl"
RESULTS = EVAL_DIR / "results.csv"


def _version_num(v: str) -> int:
    return int(str(v).lower().lstrip("v"))


def load_dataset(max_version: str | None):
    items = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        obj = json.loads(line)
        if max_version is None or _version_num(obj["added_in"]) <= _version_num(max_version):
            items.append(obj)
    return items


def git_rev() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(EVAL_DIR)
        ).decode().strip()
    except Exception:
        return "unknown"


def build_retriever(tag: str = ""):
    with open("config.yaml", "r") as f:
        doc_cfg = yaml.safe_load(f)
    from scripts.retriever_builder import RetrieverBuilder
    builder = RetrieverBuilder(doc_cfg["DOCUMENTS"], tag=tag)
    retriever, _chunk_dict = builder.build_retrievers()
    return retriever


def _format_block(label: str, content: str) -> str:
    return f"{label}:\n{content.strip()}\n\n" if content else ""


def main():
    ap = argparse.ArgumentParser(description="Run the RAG eval set.")
    ap.add_argument("--max-version", default=None,
                    help="Only run questions added up to this version, e.g. v1.")
    ap.add_argument("--k", type=int, default=5, help="Chunks to retrieve per question.")
    ap.add_argument("--answers", action="store_true",
                    help="Generate answers and score fact coverage (requires Ollama).")
    ap.add_argument("--show-misses", action="store_true",
                    help="Print questions whose retrieval missed the expected source.")
    ap.add_argument("--index-tag", default="",
                    help="Index variant to evaluate, e.g. _test (default: prod index).")
    args = ap.parse_args()

    items = load_dataset(args.max_version)
    if not items:
        print("No questions matched. Check --max-version.")
        return
    version_label = args.max_version or "all"
    index_label = args.index_tag or "prod"
    print(f"Loaded {len(items)} questions (version: {version_label}, index: {index_label}). Building retriever...")
    retriever = build_retriever(args.index_tag)

    engine = None
    cfg = None
    if args.answers:
        from scripts.llm_utils import get_llm_engine
        from scripts import config as cfg  # noqa: F811
        engine = get_llm_engine()

    hits = 0
    fact_cov_sum = 0.0
    per_cat: dict[str, list[int]] = {}  # category -> [hits, total]

    for it in items:
        docs = retriever.retrieve_context(it["question"], max_results=args.k)
        sources = [(d.metadata.get("source", "") or "") for d in docs]
        want = it["expected_source"].lower()
        hit = any(want in s.lower() for s in sources)
        hits += int(hit)

        cat = it.get("category", "uncategorized")
        bucket = per_cat.setdefault(cat, [0, 0])
        bucket[0] += int(hit)
        bucket[1] += 1

        if args.show_misses and not hit:
            shown = [s.split("\\")[-1] for s in sources] or ["(none)"]
            print(f"  MISS {it['id']}: {it['question']}\n        got: {shown}")

        if args.answers:
            context = "\n\n".join(d.page_content for d in docs)
            prompt = cfg.RESPONSE_PREFIX.format(
                context=_format_block("Context", context),
                history="",
                web_context="",
                original_query=_format_block("Original Query", it["question"]),
            )
            answer = (engine.prompt(prompt, temperature=0.2) or "").lower()
            facts = it.get("expected_facts", [])
            cov = (sum(1 for f in facts if f.lower() in answer) / len(facts)) if facts else 0.0
            fact_cov_sum += cov

    n = len(items)
    hit_rate = hits / n
    print("\n==== Eval summary ====")
    print(f"version: {version_label}   k: {args.k}   questions: {n}")
    print(f"retrieval hit-rate: {hit_rate:.1%}  ({hits}/{n})")
    if args.answers:
        print(f"answer fact-coverage: {fact_cov_sum / n:.1%}  (heuristic)")
    print("by category:")
    for cat in sorted(per_cat):
        h, t = per_cat[cat]
        print(f"  {cat:14s} {h}/{t}  ({h / t:.0%})")

    # Append to the results log (build the pipeline-rev x eval-version matrix).
    row = {
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "git_rev": git_rev(),
        "eval_version": version_label,
        "index": index_label,
        "k": args.k,
        "questions": n,
        "retrieval_hit_rate": round(hit_rate, 4),
        "answer_fact_coverage": round(fact_cov_sum / n, 4) if args.answers else "",
    }
    new_file = not RESULTS.exists()
    with open(RESULTS, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new_file:
            w.writeheader()
        w.writerow(row)
    print(f"\nAppended result to {RESULTS.name}")


if __name__ == "__main__":
    main()
