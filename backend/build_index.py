"""Build a (optionally tagged) retriever index.

From backend/:
    EMBED_DEVICE=cuda python build_index.py --chunk-size 2048 --chunk-overlap 200 --tag _test

Writes bm25{tag}.dill, faiss{tag}.dill, chunked_docs{tag}.json, and
faiss_embeddings{tag}.pkl. With a tag, prod (untagged) files are left untouched,
so a test build can be A/B'd and reverted. The parsed-text cache is shared
(parsing is chunk-size independent), so only chunking + embedding re-run.
"""
import argparse
import yaml

from scripts.retriever_builder import RetrieverBuilder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-size", type=int, default=None)
    ap.add_argument("--chunk-overlap", type=int, default=None)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    builder = RetrieverBuilder(
        cfg["DOCUMENTS"],
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        tag=args.tag,
    )
    print(f"[build_index] tag={args.tag!r} chunk_size={builder.chunk_size} overlap={builder.chunk_overlap}")
    builder.build_retrievers()
    print("[build_index] Done.")


if __name__ == "__main__":
    main()
