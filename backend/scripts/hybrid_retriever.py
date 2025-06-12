# Standard library imports
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
from langchain.retrievers import EnsembleRetriever

class HybridRetriever:
    def retrieve_context(self, query: str, hybrid_retriever: EnsembleRetriever, max_results: int = 20) -> list[str]:
        seen_content = set()
        unique_chunks = []
        try:
            # Parallelize each retriever in the ensemble
            retrievers = hybrid_retriever.retrievers
            weights = getattr(hybrid_retriever, "weights", [1] * len(retrievers))

            def run_retriever(retriever):
                try:
                    return retriever.invoke(query)
                except Exception as e:
                    print(f"[Retrieval] Sub-retriever failed: {e}")
                    traceback.print_exc()
                    return []

            results = []
            with ThreadPoolExecutor() as executor:
                future_to_idx = {executor.submit(run_retriever, retriever): i for i, retriever in enumerate(retrievers)}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        docs = future.result()
                        results.append((docs, weights[idx]))
                    except Exception as e:
                        print(f"[Pipeline] Retriever {idx} failed: {e}")

            # Flatten and merge results, respecting weights (optional: you can implement weighted merging)
            flat_results = []
            for docs, weight in results:
                flat_results.extend(docs)

            for doc in flat_results:
                content = doc.page_content
                if not self._filter_chunk(content):
                    continue
                if content not in seen_content:
                    seen_content.add(content)
                    unique_chunks.append(content)
        except Exception as e:
            print(f"[Retrieval] Query failed: {e}")
            traceback.print_exc()
        return unique_chunks[:max_results]

    @staticmethod
    def _filter_chunk(doc: str) -> bool:
        text = doc.strip().lower()
        if text.endswith(('.pdf', '.docx', '.txt', '.pptx', '.csv')) and "\\" in text:
            return False
        if len(text) < 120:
            return False
        if any(c.isdigit() for c in text[:15]) and " " not in text[:10] and "\\" not in text:
            return False
        return True