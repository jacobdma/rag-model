"""This script implements the Retrieval-Augmented Generation (RAG) pipeline for interactive question answering."""

# Standard library imports
import time
import yaml

# Third-party imports
import requests
import torch
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from pydantic import BaseModel

# Local imports
from .chunk_documents import DocumentChunker
from .llm_utils import get_llm_engine
from .hybrid_retriever import HybridRetriever
from .retriever_builder import RetrieverBuilder
from . import config
from .config import ModelConfig

class Message(BaseModel):
    role: str
    content: str

class RAGPipeline:
    def __init__(self):
        self._cached_bm25 = None
        self._cached_vector = None
        engine = get_llm_engine()
        self._prompt = engine.prompt
        self._hybrid_retriever = HybridRetriever()
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        self.folder_paths = config["DOCUMENTS"]

    def _get_retrievers(self) -> tuple[dict[str, BM25Retriever], dict[str, FAISS]]:
        if self._cached_bm25 is None or self._cached_vector is None:
            self._cached_bm25, self._cached_vector = RetrieverBuilder(self.folder_paths).build_retrievers()
        return self._cached_bm25, self._cached_vector

    def _search_bing(self, query: str, max_results: int = 5) -> list[str]:
        headers = {"Ocp-Apim-Subscription-Key": config.BING_API_KEY}
        params = {"q": query, "count": max_results}
        response = requests.get(config.BING_API_URL, headers=headers, params=params)
        data = response.json()
        if "webPages" in data:
            return [item["snippet"] for item in data["webPages"]["value"][:max_results]]
        return []

    def _log_time(self, start: float, message: str) -> None:
        print(f"{message} {time.time() - start:.2f} seconds")

    def _build_history_chain(self, chat_history: list[Message], query: str) -> tuple[list[dict[str, str]], list[Message]]:
        t0 = time.time()
        history_chain = []
        
        for i in range(len(chat_history) - 2, -1, -2):
            if chat_history[i].role == "user" and chat_history[i + 1].role == "assistant":
                relevance = self._prompt(
                    prompt=config.HISTORY_PROMPT_TEMPLATE.format(
                        prev_query=chat_history[i].content,
                        prev_answer=chat_history[i + 1].content,
                        current_query=query
                    ),
                    max_new_tokens=32
                )
                print(f"History Relevance Response: {relevance}")

                if "yes" in relevance.lower():
                    history_chain.insert(0, chat_history[i].model_dump())
                    history_chain.insert(1, chat_history[i + 1].model_dump())
                else:
                    break

        chat_history.append(Message(role="user", content=query))
        self._log_time(t0, "[Pipeline] History relevance chain built")

        return history_chain, chat_history

    def _prompt_final_response(self, combined_context: str, web_context: str, query: str,
        history_chain: list[dict[str, str]], chat_history: list[Message]) -> str:
        """Generate the final response using the LLM."""
        t0 = time.time()
        response_prefix = config.RESPONSE_PREFIX
        print("[Final Prompt] Prompting Final Prompt")

        context_str = f"Context:\n{combined_context}" if combined_context else ""
        history_str = ""
        if history_chain:
            history_lines = [f"{entry['role'].capitalize()}: {entry['content']}" for entry in history_chain]
            history_str = "Chat History:\n" + "\n".join(history_lines)

        web_context_str = f"Web Context:\n{web_context}" if web_context else ""

        prompt = config.PROMPT_LLM_TEMPLATE.format(
            prefix=response_prefix.strip(),
            context=context_str.strip(),
            history=history_str.strip() if history_str else "",
            web_context=web_context_str.strip() if web_context else "",
            question=query.strip()
        )

        response = self._prompt(
            prompt=prompt,
            temperature=ModelConfig.TEMPERATURE
        )

        self._log_time(t0, "[Pipeline] Final response took")
        
        # Avoid duplicate assistant responses in chat history
        if not any(entry.content == response for entry in chat_history if entry.role == "assistant"):
            chat_history.append(Message(role="assistant", content=response))
        return response

    def generate(self, query: str,chat_history: list[Message], use_web_search: bool = False) -> str | None:
        """Run the RAG pipeline for interactive question answering."""
        start_total = time.time()

        # Create keyword retriever and vector store
        t0 = time.time()
        bm25_retriever, vector_store = self._get_retrievers()

        hybrid_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever["small"], bm25_retriever["large"], vector_store["small"].as_retriever(), vector_store["large"].as_retriever()],
            weights=[0.35, 0.15, 0.25, 0.25]
        )

        try:
            web_results = None
            # Employ web search if requested
            if use_web_search:
                t0 = time.time()
                web_results = self._search_bing(query)
                web_results = "\n\n".join(web_results)
                self._log_time(t0, "[Pipeline] Bing search took")

            # Builds history chain based on chat history and current query
            history_chain, chat_history = self._build_history_chain(chat_history, query)
            
            # Retrieves and filters context
            results = self._hybrid_retriever.retrieve_context(query, hybrid_retriever, max_results=5)
            results = DocumentChunker(self.folder_paths).clean_paragraphs(results, min_length=50, chunk_size=512, chunk_overlap=50)
            
            # Prompts the LLM for the final response
            torch.cuda.empty_cache()
            response = self._prompt_final_response(results, web_results, query, history_chain, chat_history) 
            self._log_time(start_total, "[Pipeline] Total pipeline time:")
            return response or "No response generated. Please try again."

        except Exception as e:
            print(f"[run_pipeline Exception]: {e}")
            import traceback
            traceback.print_exc()
            return f"Error in pipeline: {e}"