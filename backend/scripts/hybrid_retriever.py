# Standard library imports
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document

# Local imports
from .config import templates

class HybridRetriever:

    @staticmethod
    def query_reform(query: str, prompt) -> str:
        """
        Rewrites query through a three stage process
        """
        # 1. Rewrites and cleans up query
        rewrite_prompt = templates["Rewrite"].format(query=query)
        rewrite_output = prompt(rewrite_prompt)

        # 2. Decomposes the query into sub queries
        subquery_prompt = templates["Subquery Decomposition"].format(query=rewrite_output)
        subquery_output = prompt(subquery_prompt)

        # 3. Condenses sub queries into searchable final query
        condensed_prompt = templates["Condense"].format(query=subquery_output)
        condensed_output = prompt(condensed_prompt)

        return condensed_output
    
    def retrieve_context(self, query: str, hybrid_retriever: EnsembleRetriever, max_results: int = 5) -> list[Document]:
        """
        Retrieves content by invoking retrievers in EnsembleRetriever
        """
        seen_content = set()
        unique_chunks = []
        try:
            # Parallelize each retriever in the ensemble
            retrievers = hybrid_retriever.retrievers
            results = []
            with ThreadPoolExecutor() as executor:
                future_to_retriever = {
                    executor.submit(retriever.invoke, query): retriever
                    for retriever in retrievers
                }
                for future in as_completed(future_to_retriever):
                    retriever = future_to_retriever[future]
                    try:
                        docs = future.result()  # Documents
                        results.extend(docs)
                    except Exception as e:
                        print(f"[Pipeline] Retriever {retriever} failed: {e}")

            for doc in results:
                content = doc.page_content
                if not self._filter_chunk(content):
                    continue
                if content not in seen_content:
                    seen_content.add(content)
                    unique_chunks.append(doc)
                
            filtered_docs = self._filter_by_relevance(query, unique_chunks)

        except Exception as e:
            print(f"[Retrieval] Query failed: {e}")
            traceback.print_exc()

        return filtered_docs[:max_results]

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
            if score > 0.1:  # Minimum relevance threshold
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