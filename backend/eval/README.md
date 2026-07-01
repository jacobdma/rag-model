# RAG eval

A frozen, versioned question set for measuring retrieval + answer quality, so
pipeline changes can be judged by a number instead of by vibes.

## Run

From `backend/`:
```
python -m eval.run                   # retrieval hit-rate only (fast, no LLM)
python -m eval.run --answers         # also generate + grade answers (needs Ollama)
python -m eval.run --max-version v1  # reproduce a frozen version
python -m eval.run --show-misses     # show which questions retrieved the wrong doc
```

Each run prints a summary and appends a row to `results.csv`
(`timestamp, git_rev, eval_version, k, questions, retrieval_hit_rate, answer_fact_coverage`).

## Metrics

- **retrieval hit-rate** — did the expected source doc appear in the retrieved
  chunks? Objective and deterministic; the primary signal for bad pulls.
- **answer fact-coverage** — fraction of a question's `expected_facts` found in
  the generated answer. A rough heuristic (paraphrase-sensitive); good enough to
  catch large regressions. Can be swapped for an LLM judge later.

## Dataset format (`dataset.jsonl`)

One JSON object per line; `#` lines are ignored.
```json
{"id":"ihi-001","added_in":"v1","category":"safety","question":"...","expected_source":"IHI-Handbook.pdf","expected_facts":["oil","resistant"]}
```
- `expected_source` — substring matched against retrieved document paths.
- `expected_facts` — distinctive tokens expected in a correct answer.

## Versioning rules (important)

The whole point is comparable scores over time, so:

1. **Append-only.** To grow the set, add new lines with the next version tag
   (`"added_in": "v2"`, then `"v3"`, ...).
2. **Questions are immutable.** Never edit or delete an existing question — that
   silently changes the benchmark and breaks comparability.
3. **Compare within a version.** `--max-version v1` reproduces the exact v1 set
   forever. To prove a pipeline change helped, run the old and new pipeline both
   on the **same** version; the score on that version should go up.
4. A lower score on a *newer* version is not a regression — it's a bigger/harder
   benchmark. `results.csv` records both the eval version and the pipeline
   `git_rev`, giving a (pipeline rev x eval version) score matrix.
