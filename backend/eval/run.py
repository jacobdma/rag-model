"""RAG eval runner.

Measures the pipeline against the frozen question set in dataset.jsonl.

From the backend/ directory:
    python -m eval.run                  # retrieval hit-rate only (fast, no LLM)
    python -m eval.run --answers        # also generate + grade answers (needs Ollama)
    python -m eval.run --max-version v1 # reproduce a frozen eval version
    python -m eval.run --index-tag _test
    python -m eval.run --show-misses    # print retrieval misses (and answer misses w/ --answers)

Metrics:
  - retrieval hit-rate: did the expected source doc appear in the retrieved chunks?
    (deterministic; the same retrieve_context the app uses)
  - answer accuracy (rigorous, end-to-end): for questions with a reference `answer`,
    graded as correct/incorrect. grade="exact" -> all `match` tokens present
    (normalized); grade="judge" -> an LLM judge compares the answer to the reference.
  - answer fact-coverage (legacy): for questions with only `expected_facts`.

Results are appended to results.csv with the eval version + pipeline git commit.
"""
import argparse
import csv
import datetime as _dt
import json
import re
import subprocess
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).resolve().parent
DATASET = EVAL_DIR / "dataset.jsonl"
RESULTS = EVAL_DIR / "results.csv"

_NUMWORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
    "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20",
}


def _norm(s: str) -> str:
    """Lowercase, map number words to digits, reduce to space-delimited tokens."""
    s = str(s).lower()
    for w, d in _NUMWORDS.items():
        s = re.sub(rf"\b{w}\b", d, s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return f" {s.strip()} "


def _exact_pass(answer: str, match: list) -> bool:
    na = _norm(answer)
    return all(f" {_norm(t).strip()} " in na for t in match if str(t).strip())


_JUDGE_PROMPT = """You are grading a question-answering system. Decide if the SYSTEM ANSWER is correct, using the REFERENCE ANSWER as ground truth. It is correct if it conveys the same key fact(s) as the reference, even if worded differently. It is incorrect if it contradicts the reference, omits the key fact, or says it cannot find the information.

QUESTION: {q}
REFERENCE ANSWER: {ref}
SYSTEM ANSWER: {ans}

Reply with exactly one word: CORRECT or INCORRECT.
"""


def _judge(engine, question: str, reference: str, answer: str) -> bool:
    out = (engine.prompt(
        _JUDGE_PROMPT.format(q=question, ref=reference, ans=answer),
        temperature=0.0, max_new_tokens=5,
    ) or "").lower()
    if "incorrect" in out:
        return False
    return "correct" in out


def _version_num(v: str) -> int:
    return int(str(v).lower().lstrip("v"))


def load_dataset(max_version):
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


class JointRetriever:
    """Ensemble several index retrievers (e.g. small + large chunks) by fusing
    their ranked results with Reciprocal Rank Fusion."""

    def __init__(self, retrievers: list, rrf_k: int = 60):
        self.retrievers = retrievers
        self.rrf_k = rrf_k

    def retrieve_context(self, query: str, max_results: int = 5):
        scores: dict = {}
        docmap: dict = {}
        for r in self.retrievers:
            ranked = r.retrieve_context(query, max_results=max_results * 2)
            for rank, doc in enumerate(ranked):
                key = doc.page_content
                scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank)
                docmap.setdefault(key, doc)
        top = sorted(scores, key=scores.get, reverse=True)[:max_results]
        return [docmap[k] for k in top]


def _tags_from(spec: str) -> list:
    return ["" if t.strip() in ("prod", "") else t.strip() for t in spec.split(",")]


def _format_block(label: str, content: str) -> str:
    return f"{label}:\n{content.strip()}\n\n" if content else ""


def main():
    ap = argparse.ArgumentParser(description="Run the RAG eval set.")
    ap.add_argument("--max-version", default=None, help="Run questions added up to this version, e.g. v1.")
    ap.add_argument("--k", type=int, default=5, help="Chunks to retrieve per question.")
    ap.add_argument("--answers", action="store_true", help="Generate + grade answers (requires Ollama).")
    ap.add_argument("--show-misses", action="store_true", help="Print retrieval (and answer) misses.")
    ap.add_argument("--index-tag", default="", help="Index variant, e.g. _test (default: prod).")
    ap.add_argument("--joint", default="", help="Ensemble (RRF) several index tags, e.g. 'prod,_test'.")
    args = ap.parse_args()

    items = load_dataset(args.max_version)
    if not items:
        print("No questions matched. Check --max-version.")
        return
    version_label = args.max_version or "all"
    if args.joint:
        index_label = "joint:" + args.joint
        print(f"Loaded {len(items)} questions (version: {version_label}, index: {index_label}). Building retrievers...")
        retriever = JointRetriever([build_retriever(t) for t in _tags_from(args.joint)])
    else:
        index_label = args.index_tag or "prod"
        print(f"Loaded {len(items)} questions (version: {version_label}, index: {index_label}). Building retriever...")
        retriever = build_retriever(args.index_tag)

    engine = cfg = None
    if args.answers:
        from scripts.llm_utils import get_llm_engine
        from scripts import config as cfg  # noqa: F811
        engine = get_llm_engine()

    hits = 0
    graded_correct = graded_total = 0
    fact_cov_sum = legacy_total = 0
    per_cat: dict[str, list[int]] = {}

    for it in items:
        docs = retriever.retrieve_context(it["question"], max_results=args.k)
        sources = [(d.metadata.get("source", "") or "") for d in docs]
        hit = any(it["expected_source"].lower() in s.lower() for s in sources)
        hits += int(hit)
        bucket = per_cat.setdefault(it.get("category", "uncategorized"), [0, 0])
        bucket[0] += int(hit)
        bucket[1] += 1

        if args.show_misses and not hit:
            print(f"  MISS-RETRIEVAL {it['id']}: {it['question']}\n        got: {[s.split(chr(92))[-1] for s in sources] or ['(none)']}")

        if not args.answers:
            continue

        context = "\n\n".join(d.page_content for d in docs)
        prompt = cfg.RESPONSE_PREFIX.format(
            context=_format_block("Context", context), history="", web_context="",
            original_query=_format_block("Original Query", it["question"]),
        )
        answer = engine.prompt(prompt, temperature=0.2) or ""

        if "grade" in it and it.get("answer"):
            graded_total += 1
            if it["grade"] == "exact" and it.get("match"):
                ok = _exact_pass(answer, it["match"])
            else:
                ok = _judge(engine, it["question"], it["answer"], answer)
            graded_correct += int(ok)
            if args.show_misses and not ok:
                print(f"  MISS-ANSWER {it['id']}: {it['question']}\n        want: {it['answer']!r}\n        got:  {answer.strip()[:160]!r}")
        elif it.get("expected_facts"):
            legacy_total += 1
            facts = it["expected_facts"]
            fact_cov_sum += sum(1 for f in facts if f.lower() in answer.lower()) / len(facts)

    n = len(items)
    hit_rate = hits / n
    ans_acc = (graded_correct / graded_total) if graded_total else None
    fact_cov = (fact_cov_sum / legacy_total) if legacy_total else None

    print("\n==== Eval summary ====")
    print(f"version: {version_label}   index: {index_label}   k: {args.k}   questions: {n}")
    print(f"retrieval hit-rate:   {hit_rate:.1%}  ({hits}/{n})")
    if ans_acc is not None:
        print(f"answer accuracy:      {ans_acc:.1%}  ({graded_correct}/{graded_total} graded)")
    if fact_cov is not None:
        print(f"answer fact-coverage: {fact_cov:.1%}  ({legacy_total} legacy, heuristic)")
    print("retrieval by category:")
    for cat in sorted(per_cat):
        h, t = per_cat[cat]
        print(f"  {cat:14s} {h}/{t}  ({h / t:.0%})")

    row = {
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "git_rev": git_rev(),
        "eval_version": version_label,
        "index": index_label,
        "k": args.k,
        "questions": n,
        "retrieval_hit_rate": round(hit_rate, 4),
        "answer_accuracy": round(ans_acc, 4) if ans_acc is not None else "",
        "answer_fact_coverage": round(fact_cov, 4) if fact_cov is not None else "",
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
