# Standard library imports
import logging
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, bm25: BM25Retriever, faiss_retriever):
        self.bm25 = bm25
        self.faiss_retriever = faiss_retriever

    def retrieve_context(self, query: str, max_results: int = 5) -> list[Document]:
        """
        Retrieves content by invoking retrievers in Hybrid Retriever
        """
        docs = []
        try:
            results = self.get_relevant_documents(query)
            docs = [doc for doc in results if self._filter_chunk(doc.page_content)]
        except Exception:
            logger.exception("[Retrieval] Query failed")

        return docs[:max_results]

    def get_relevant_documents(self, query: str, k: int = 12) -> list[Document]:
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_bm25 = ex.submit(self.bm25.invoke, query)
            f_faiss = ex.submit(self.faiss_retriever.invoke, query)
            bm25_docs, faiss_docs = f_bm25.result(), f_faiss.result()

        # Deduplicate results by content
        seen, merged = set(), []
        for doc in bm25_docs + faiss_docs:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                merged.append(doc)
        return merged[:k]

    @staticmethod
    def _filter_chunk(doc: str) -> bool:
        """
        Filters chunks with unusable content
        """
        text = doc.strip().lower()
        if text.endswith(('.pdf', '.docx', '.txt', '.pptx', '.csv')) and "\\" in text: # Filters file names
            return False
        if len(text) < 120: # Filters chunks with mostly empty space
            return False
        if any(c.isdigit() for c in text[:15]) and " " not in text[:10] and "\\" not in text: # Filters chunks that only contain numbers at the start, directory slashes, or empty white space
            return False
        return True
