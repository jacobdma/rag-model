# Standard library imports
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
from langchain.retrievers import EnsembleRetriever

# Local imports
from .config import templates

class HybridRetriever:
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
    
    def retrieve_context(self, query: str, hybrid_retriever: EnsembleRetriever, max_results: int = 20) -> list[str]:
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
                futures = [executor.submit(retriever.invoke, query) for retriever in retrievers]
                for future in as_completed(futures):
                    try:
                        docs = future.result()
                        results.extend(docs)
                    except Exception as e:
                        print(f"[Pipeline] Retriever failed: {e}")

            for doc in results:
                print(doc)
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