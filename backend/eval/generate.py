"""Grounded eval-question generator.

For each source document, extract its text and have the LLM draft specific
factual Q/A pairs *strictly from that text*, keeping only ones whose answer is
grounded in the source (anti-hallucination check). Output -> candidates.jsonl
for human curation into dataset.jsonl.

From backend/:
    python -m eval.generate --per-doc 3 --max-docs 80 --out eval/candidates.jsonl

Each candidate:
    {"question","answer","grade":"exact|judge","match":[...]|null,
     "expected_source": <filename>, "category": <department>}
- grade "exact": answer is a number/short value; `match` lists key tokens that
  must all appear in a correct answer (graded deterministically).
- grade "judge": answer is a phrase/description; graded by an LLM judge.
"""
import argparse
import json
import random
import re
from pathlib import Path

import requests

from scripts import config

DL = Path("downloaded_files")
EXTS = (".docx", ".pdf", ".txt")

GEN_PROMPT = """You are writing precise test questions for a company document Q&A system. Using ONLY the document text below, write up to {k} SPECIFIC factual questions, each with a SHORT correct answer that is stated in the text.

Requirements:
- Target a concrete fact: a number, measurement, name, threshold, requirement, code, or exact value.
- The answer must be SHORT (ideally under 12 words). NEVER a paragraph.
- Do NOT ask generic or meta questions ("what is the purpose", "what does this describe", "what is the responsibility of", "what happens prior to"). Only specific lookups.
- The answer must appear in the text. Do not infer or invent. Ignore signature/boilerplate lines.
- grade="exact" when the answer is a number/name/code/short value; set "match" to 1-4 key tokens that must appear, e.g. ["200","pounds"].
- grade="judge" when the answer is a short phrase; omit match.

Good examples:
{{"question": "What is the minimum weight rating for low assembly chairs?", "answer": "200 pounds", "grade": "exact", "match": ["200","pounds"]}}
{{"question": "Who issues parts to the assembler?", "answer": "the assembly supervisor", "grade": "judge"}}

Output ONLY JSON objects, one per line, nothing else:

DOCUMENT ({name}):
{text}

JSON:"""

_GENERIC_RE = re.compile(
    r"\b(purpose|describe[sd]?|responsibilit|this (procedure|document|work instruction|policy|memo|form)|what happens|overview)\b",
    re.I,
)
_BOILERPLATE = ("read, understand", "fully agree", "uncontrolled if printed", "all rights reserved")
_META_RE = re.compile(
    r"\b(document id|acronym|revision (number|of|#)|version (number|#|date)|"
    r"what is the (date|title|file ?name|document)|page \d)\b",
    re.I,
)


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            import docx2txt
            return docx2txt.process(str(path)) or ""
        if ext == ".pdf":
            import fitz
            d = fitz.open(str(path))
            return "\n".join(d[i].get_text() for i in range(min(len(d), 8)))
        if ext == ".txt":
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return ""


def generate_for_doc(path: Path, k: int) -> list[dict]:
    text = extract_text(path).strip()[:6000]
    if len(text) < 250:
        return []
    prompt = GEN_PROMPT.format(k=k, name=path.name, text=text)
    try:
        r = requests.post(
            f"{config.OLLAMA_HOST.rstrip('/')}/api/generate",
            json={
                "model": config.OLLAMA_MODEL, "prompt": prompt, "raw": True, "stream": False,
                "options": {"temperature": 0.3, "num_predict": 800, "num_ctx": 8192},
            },
            timeout=300,
        )
        r.raise_for_status()
        out = r.json().get("response", "")
    except requests.RequestException:
        return []

    low_text = text.lower()
    items = []
    for blob in re.findall(r"\{[^{}]*\}", out):
        try:
            obj = json.loads(blob)
        except json.JSONDecodeError:
            continue
        q = str(obj.get("question", "")).strip()
        a = str(obj.get("answer", "")).strip()
        if not q or not a or len(a) > 160:           # reject empty or paragraph answers
            continue
        if _GENERIC_RE.search(q) or _META_RE.search(q):  # reject vague / document-metadata questions
            continue
        if any(b in a.lower() for b in _BOILERPLATE):  # reject signature/boilerplate
            continue
        # Anti-hallucination: most of the answer's content tokens must appear in the source.
        toks = [t for t in re.findall(r"[a-z0-9]+", a.lower()) if len(t) > 2]
        if toks and (sum(t in low_text for t in toks) / len(toks)) < 0.6:
            continue
        grade = obj.get("grade") if obj.get("grade") in ("exact", "judge") else "judge"
        match = obj.get("match") if isinstance(obj.get("match"), list) else None
        if grade == "exact" and (not match or len(match) > 5):  # exact needs a few clean tokens
            grade, match = "judge", None
        items.append({
            "question": q, "answer": a, "grade": grade, "match": match,
            "expected_source": path.name, "category": path.parent.name,
        })
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-doc", type=int, default=3)
    ap.add_argument("--max-docs", type=int, default=80)
    ap.add_argument("--out", default="eval/candidates.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    docs = [p for p in DL.rglob("*") if p.suffix.lower() in EXTS]
    random.seed(args.seed)
    random.shuffle(docs)
    docs = docs[:args.max_docs]

    out = Path(args.out)
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for i, p in enumerate(docs, 1):
            items = generate_for_doc(p, args.per_doc)
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                f.flush()
            n += len(items)
            print(f"[{i}/{len(docs)}] {p.name}: +{len(items)} (total {n})", flush=True)
    print(f"Done. {n} candidates -> {out}", flush=True)


if __name__ == "__main__":
    main()
