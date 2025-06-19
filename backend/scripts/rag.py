"""This script implements the Retrieval-Augmented Generation (RAG) pipeline for interactive question answering."""

# Standard library imports
import time
import yaml
import json

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
        self.engine = get_llm_engine()
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

    def generate(self, query: str, chat_history: list[Message], use_web_search: bool = False, use_double_retrievers: bool = True):
        """Stream the RAG pipeline for interactive question answering."""
        start_total = time.time()
        bm25_retriever, vector_store = self._get_retrievers()
        if use_double_retrievers:
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever["small"], 
                        bm25_retriever["large"], 
                        vector_store["small"].as_retriever(), 
                        vector_store["large"].as_retriever()]
            )
        else:
            hybrid_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever["medium"], 
                    vector_store["medium"].as_retriever()]
            )

        try:
            web_results = ""
            if use_web_search:
                t0 = time.time()
                web_results_list = self._search_bing(query)
                web_results = "\n\n".join(web_results_list)
                self._log_time(t0, "[Pipeline] Bing search took")

            history_chain = []

            # Iterate over user/assistant pairs in reverse order
            pairs = [
                (chat_history[i], chat_history[i + 1])
                for i in range(len(chat_history) - 2, -1, -2)
                if chat_history[i].role == "user" and chat_history[i + 1].role == "assistant"
            ]
            for user_msg, assistant_msg in pairs:
                history_chain.extend([user_msg.model_dump(), assistant_msg.model_dump()])

            history_chain = history_chain[::-1]
                
            t0 = time.time()
            reformed_query = HybridRetriever.query_reform(query, self.engine.prompt)
            self._log_time(t0, "[Pipeline] Query reformulation took")
            print(f"[DEBUG] Reformulated query: {reformed_query}")
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            context = self._hybrid_retriever.retrieve_context(reformed_query, hybrid_retriever, max_results=5)

            chunker = getattr(self, "chunker", DocumentChunker(self.folder_paths))
            context = chunker.clean_paragraphs(context, min_length=50, chunk_size=512, chunk_overlap=50)
            context_str = "\n".join([doc.page_content for doc in context])

            def format_block(label, content):
                return f"{label}:\n{content.strip()}" if content else ""
 
            history_lines = [f"{entry['role'].capitalize()}: {entry['content']}" for entry in history_chain] if history_chain else []

            prompt = config.PROMPT_LLM_TEMPLATE.format(
                prefix=config.RESPONSE_PREFIX.strip(),
                context=format_block("Context", context_str),
                history=format_block("Chat History", "\n".join(history_lines)),
                web_context=format_block("Web Context", web_results),
                question=query.strip()
            )

            print(f"\n\n\n Prompt:\n{prompt}\n\n")

            # Stream LLM output
            streamer = self.engine.prompt(
                prompt=prompt,
                temperature=ModelConfig.TEMPERATURE,
                stream=True
            )
            for token in streamer:
                yield token

            self._log_time(start_total, "[Pipeline] Total pipeline time:")
        except Exception as e:
            yield f"\n[Error]: {e}\n"