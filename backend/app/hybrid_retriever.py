# Standard library imports
import time
import traceback

# Third-party imports
from langchain.retrievers import EnsembleRetriever

class HybridRetriever:
    def retrieve_context(self, query: str, hybrid_retriever: EnsembleRetriever, max_results: int = 20) -> list[str]:
        t0 = time.time()
        seen_content = set()
        unique_chunks = []
        try:
            results = hybrid_retriever.invoke(query)
            for doc in results:
                content = doc.page_content
                if not self._filter_chunk(content):
                    continue
                content_hash = hash(content)
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_chunks.append(content)
        except Exception as e:
            print(f"[Retrieval] Query failed: {e}")
            traceback.print_exc()
        print(f"[Pipeline] Query retrieval took {(time.time() - t0):.2f} seconds")
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