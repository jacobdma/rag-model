# Standard library imports
from collections import defaultdict
import os
import time
import yaml

# Third-party imports
import requests
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from pydantic import BaseModel

# Local imports
from .llm_utils import get_llm_engine
from .hybrid_retriever import HybridRetriever
from .retriever_builder import RetrieverBuilder
from .chunk_documents import DocumentChunker
from . import config
from .config import ModelConfig

class Message(BaseModel):
    role: str
    content: str

class RAGPipeline:
    def __init__(self):
        self._cached_bm25 = None
        self._cached_vector = None
        self._chunk_dict = None
        self.engine = get_llm_engine()
        self._hybrid_retriever = HybridRetriever()
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        self.folder_paths = config["DOCUMENTS"]

    def _get_retrievers(self) -> tuple[dict[str, BM25Retriever], dict[str, FAISS], dict[str, dict[str, list[Document]]]]:
        if self._cached_bm25 is None or self._cached_vector is None or self._chunk_dict is None:
            self._cached_bm25, self._cached_vector, self._chunk_dict = RetrieverBuilder(self.folder_paths).build_retrievers()

        return self._cached_bm25, self._cached_vector, self._chunk_dict

    def _search_bing(self, query: str, max_results: int = 5) -> list[str]:
        headers = {"Ocp-Apim-Subscription-Key": config.BING_API_KEY}
        params = {"q": query, "count": max_results}
        response = requests.get(config.BING_API_URL, headers=headers, params=params)
        data = response.json()
        if "webPages" in data:
            return [item["snippet"] for item in data["webPages"]["value"][:max_results]]
        return []
    
    @staticmethod
    def get_surrounding_chunks(doc: Document, chunks_by_source: dict[str, list[Document]], target_chars: int = 1500) -> list[Document]:
        source = doc.metadata.get("source", "")
        source = os.path.normpath(source)
        if not source or source not in chunks_by_source:
            return [doc]
        chunk_list = chunks_by_source[source]
        index = doc.metadata.get("chunk_number", 0)
        print(f"INDEX: {index}")
        selected = [doc]
        total_chars = len(chunk_list[index].page_content)

        left = index - 1
        right = index + 1

        while total_chars < target_chars and (left >= 0 or right < len(chunk_list)):
            if left >= 0:
                chunk = chunk_list[left]
                selected.insert(0, chunk)
                total_chars += len(chunk.page_content)
                left -= 1
            if right < len(chunk_list):
                chunk = chunk_list[right]
                selected.append(chunk)
                total_chars += len(chunk.page_content)
                right += 1
            if total_chars >= target_chars:
                break

        return selected
    
    def _process_chat_documents(self, chat_id: str) -> list[Document]:
        """Process uploaded documents for a specific chat"""
        from .main import CHAT_DOCUMENTS
        
        if chat_id not in CHAT_DOCUMENTS:
            return []
        
        chat_docs = []
        for uploaded_doc in CHAT_DOCUMENTS[chat_id]:
            chunks = DocumentChunker().clean_paragraphs(
                docs=[uploaded_doc.content],
                chunk_size=1024,
                chunk_overlap=100,
                granularity="uploaded",
                min_length=50,
                source=f"{uploaded_doc.filename}"
            )
            chat_docs.extend(chunks)
        
        return chat_docs

    def _log_time(self, start: float, message: str) -> None:
        print(f"{message} {time.time() - start:.2f} seconds")

    def generate(self, query: str, chat_history: list[Message], use_web_search: bool = False, use_double_retrievers: bool = True, chat_id: str = None):
        """Stream the RAG pipeline for interactive question answering."""
        start_total = time.time()
        # 1. Load retrievers
        bm25_retriever, vector_store, chunk_dict = self._get_retrievers()
        if use_double_retrievers:
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever["small"], 
                        bm25_retriever["large"], 
                        vector_store["small"].as_retriever(), 
                        vector_store["large"].as_retriever()],
                weights=[0.25, 0.25, 0.25, 0.25]
            )
        else:
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever["medium"], 
                    vector_store["medium"].as_retriever()],
                weights=[0.5, 0.5]
            )

        # Try to run pipeline
        try:
            # 2. Classify prompt as conversational or inquiry
            classification_prompt = config.CLASSIFICATION_TEMPLATE.format(message=query)
            classification = self.engine.prompt(
                prompt=classification_prompt,
                temperature=0.1
            )

            if "conversational" in classification:
                while True:
                    prompt = config.CHAT_RESPONSE_TEMPLATE.format(message=query).strip() + "\n\nAssistant:"
                    streamer = self.engine.prompt(prompt=prompt, stream=True)

                    tokens = []
                    for token in streamer:
                        tokens.append(token)
                        yield token

                    full_response = "".join(tokens)

                    # Check for hallucinated dialogue format
                    if "User:" in full_response or "Assistant:" in full_response:
                        continue
                    break
                return None

            # 3. Get web search results
            web_results = None
            if use_web_search:
                t0 = time.time()
                web_results_list = self._search_bing(query)
                web_results = "\n\n".join(web_results_list)
                self._log_time(t0, "[Pipeline] Bing search took")

            # 4. Get chat history
            history_chain = []
            pairs = [
                (chat_history[i], chat_history[i + 1])
                for i in range(len(chat_history) - 2, -1, -2)
                if chat_history[i].role == "user" and chat_history[i + 1].role == "assistant"
            ]
            for user_msg, assistant_msg in pairs:
                history_chain.extend([user_msg.model_dump(), assistant_msg.model_dump()])

            history_chain = history_chain[::-1]
            
            # 5. Reform query for better retrieval/response
            t0 = time.time()
            refined_query = HybridRetriever.query_reform(query, self.engine.prompt)
            self._log_time(t0, "[Pipeline] Query reformulation took")
            print(f"[DEBUG] Refined query: {refined_query}")

            # 6. Invokes retrievers to get relevant chunks
            docs = self._hybrid_retriever.retrieve_context(refined_query, hybrid_retriever, max_results=5) 

             # 7. Get uploaded chat documents if chat_id provided
            chat_documents = []
            if chat_id:
                chat_documents = self._process_chat_documents(chat_id)
                print(f"[DEBUG] Found {len(chat_documents)} uploaded documents for chat {chat_id}")

            # 8. Combine regular docs with chat documents
            all_docs = docs + chat_documents

            # 7. Get surrounding documents
            retrieved_info = []
            context_groups = []  # Each group: dict with keys: 'source', 'granularity', 'chunks', 'content_set', 'total_len', 'original_order', 'metadata_list'
            group_counter = 0

            for doc in all_docs:
                if doc.metadata.get("granularity") == "uploaded":
                    context_chunks = [doc]
                else:
                    context_chunks = self.get_surrounding_chunks(doc, chunk_dict[doc.metadata["granularity"]])

                # Group by contiguous chunks from the same source and granularity
                if not context_chunks:
                    continue

                source = os.path.normpath(context_chunks[0].metadata.get("source", ""))
                granularity = context_chunks[0].metadata.get("granularity", "")
                chunk_numbers = [c.metadata.get("chunk_number", 0) for c in context_chunks]
                group_id = (source, min(chunk_numbers), max(chunk_numbers), granularity)
                group_content = "".join([c.page_content for c in context_chunks])

                content_set = set()
                for c in context_chunks:
                    content_set.update(c.page_content.splitlines())

                context_groups.append({
                    "group_id": group_id,
                    "source": source,
                    "granularity": granularity,
                    "chunks": context_chunks,
                    "content": group_content,
                    "content_set": set(group_content),
                    "total_len": len(group_content),
                    "original_order": group_counter,
                    "metadata_list": [c.metadata for c in context_chunks],
                })
                group_counter += 1

            source_to_groups = defaultdict(list)
            for group in context_groups:
                source_to_groups[group["source"]].append(group)

            deduped_groups = []
            for source, groups in source_to_groups.items():
                keep = [True] * len(groups)
                for i, g1 in enumerate(groups):
                    g1_content = set(c.page_content for c in g1["chunks"])
                    union_others = set()
                    for j, g2 in enumerate(groups):
                        if i == j:
                            continue
                        union_others.update(c.page_content for c in g2["chunks"])
                    if g1_content and g1_content.issubset(union_others) and len(union_others) > len(g1_content):
                        keep[i] = False
                filtered_groups = [g for k, g in zip(keep, groups) if k]

                # Step 2: Merge contiguous/overlapping groups
                def min_chunk(g):
                    return min(c.metadata["chunk_number"] for c in g["chunks"])
                filtered_groups.sort(key=min_chunk)
                merged = []
                for group in filtered_groups:
                    group_chunk_numbers = set(c.metadata["chunk_number"] for c in group["chunks"])
                    if not merged:
                        merged.append(group)
                    else:
                        last = merged[-1]
                        last_chunk_numbers = set(c.metadata["chunk_number"] for c in last["chunks"])
                        if last_chunk_numbers & group_chunk_numbers or (
                            max(last_chunk_numbers) + 1 >= min(group_chunk_numbers) and min(group_chunk_numbers) <= max(last_chunk_numbers) + 1
                        ):
                            all_chunks = last["chunks"] + group["chunks"]
                            seen = set()
                            unique_chunks = []
                            for c in sorted(all_chunks, key=lambda c: c.metadata["chunk_number"]):
                                num = c.metadata["chunk_number"]
                                if num not in seen:
                                    unique_chunks.append(c)
                                    seen.add(num)
                            last["chunks"] = unique_chunks
                            last["content"] = ''.join([c.page_content for c in unique_chunks])
                        else:
                            merged.append(group)
                deduped_groups.extend(merged)

            # Sort deduped groups by original order (first chunk's original order)
            deduped_groups.sort(key=lambda g: g["original_order"])

            # Build retrieved_info and context_list from deduped groups
            retrieved_info = []
            context_list = []
            for group in deduped_groups:
                retrieved_info.append({
                    "retrieved_chunk": {
                        "content": group["chunks"][0].page_content,
                        "metadata": group["chunks"][0].metadata
                    },
                    "surrounding_chunks": [
                        {
                            "content": c.page_content,
                            "metadata": c.metadata
                        }
                        for c in group["chunks"]
                    ]
                })
                context_list.append(group["content"])
            context = ''.join(context_list)
            yield retrieved_info

            # 8. Constructs prompt
            def format_block(label, content):
                return f"{label}:\n{content.strip()}\n\n" if content else ""
 
            history_lines = [f"{entry['role'].capitalize()}: {entry['content']}" for entry in history_chain] if history_chain else []
            context = ''.join(context)
            prompt = config.RESPONSE_PREFIX.format(
                context=format_block("Context", context),
                history=format_block("Chat History", "\n".join(history_lines)),
                web_context=format_block("Web Context", web_results),
                original_query=format_block("Original Query", query.strip()),
                refined_query=format_block("Refined Query", refined_query.strip())
            )

            # 9. Prompts LLM with context
            streamer = self.engine.prompt(
                prompt=prompt,
                temperature=ModelConfig.TEMPERATURE,
                stream=True
            )
            for token in streamer:
                yield token

            self._log_time(start_total, "[Pipeline] Total pipeline time:")
            return None
        except Exception as e:
            yield f"\n[Error]: {e}\n"