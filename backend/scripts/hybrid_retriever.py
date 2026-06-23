# Standard library imports
import time
import traceback

# Third-party imports
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

# Local imports
from .config import templates

class HybridRetriever:
    def __init__(self, bm25: BM25Retriever, faiss_retriever):
        self.bm25 = bm25
        self.faiss_retriever = faiss_retriever

    @staticmethod
    def query_reform(query: str, prompt) -> str:
        """
        Rewrites query through a three stage process
        """
        # 1. Rewrites and cleans up query
        t0 = time.time()
        rewrite_prompt = templates["Rewrite"].format(query=query)
        rewrite_output = prompt(rewrite_prompt, stream=False, temperature=0.1, max_new_tokens=50)
        print(f"[Query Reform] Rewrite completed in {time.time() - t0:.2f}s")

        return rewrite_output
    
    def retrieve_context(self, query: str, max_results: int = 5) -> list[Document]:
        """
        Retrieves content by invoking retrievers in Hybrid Retriever
        """
        seen_content = set()
        docs = []
        try:
            # Parallelize each retriever in the ensemble
            results = self.get_relevant_documents(query)
            for doc in results:
                content = doc.page_content
                if not self._filter_chunk(content):
                    continue
                if content not in seen_content:
                    seen_content.add(content)
                    docs.append(doc)

        except Exception as e:
            print(f"[Retrieval] Query failed: {e}")
            traceback.print_exc()

        return docs[:max_results]
    
    def get_relevant_documents(self, query: str, k: int = 12) -> list[Document]:
        bm25_docs = self.bm25.invoke(query)
        faiss_docs = self.faiss_retriever.invoke(query)

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

    def _filter_by_relevance(self, query: str, docs: list) -> list[str]:
        """Filter documents based on query keywords and metadata"""
        query_keywords = set(query.lower().split())
        
        scored_docs = []
        for doc in docs:
            score = self._calculate_relevance_score(query_keywords, doc)
            if score > 0.1:
                scored_docs.append((score, doc))
        
        # Sort by relevance score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs]
    
    @staticmethod
    def _calculate_relevance_score(query_keywords: set, doc) -> float:
        """Calculate relevance score for a document"""
        try:
            content = doc.page_content.lower()
            source = doc.metadata.get('source', '').lower()
            
            # Keyword matching in content
            content_words = set(content.split())
            keyword_overlap = len(query_keywords.intersection(content_words))
            content_score = keyword_overlap / len(query_keywords) if query_keywords else 0
            
            # Source relevance (prefer certain file types for technical queries)
            source_score = 0
            if any(ext in source for ext in ['.pdf', '.docx', '.md']):
                source_score = 0.1
            
            return content_score + source_score
            
        except Exception:
            return 0.0