# Standard library imports
import os
import threading
import time
import yaml

# Third-party imports
import requests
from langchain_core.documents import Document

# Local imports
from .llm_utils import get_llm_engine
from .hybrid_retriever import HybridRetriever
from .retriever_builder import RetrieverBuilder
from .chunk_documents import DocumentChunker
from . import config
from .config import ModelConfig
from .handler import TechnicalHandler
from .utils import Message

class RAGPipeline:
    lock = threading.Lock()
    engine = None
    hybrid_retriever = None
    retriever = None
    chunk_dict = None

    def __init__(self):
        with self.lock:
            if RAGPipeline.engine is None:
                RAGPipeline.engine = get_llm_engine()
            if RAGPipeline.hybrid_retriever is None:
                RAGPipeline.hybrid_retriever = HybridRetriever()
        self.engine = RAGPipeline.engine
        self.hybrid_retriever = RAGPipeline.hybrid_retriever

        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        self.folder_paths = config["DOCUMENTS"]

    def _get_retrievers(self) -> tuple[HybridRetriever, dict[str, dict[str, list[Document]]]]:
        with self.lock:
            if self.retriever is None or self.chunk_dict is None:
                builder = RetrieverBuilder(self.folder_paths)
                RAGPipeline.retriever, RAGPipeline.chunk_dict = builder.build_retrievers()

        return RAGPipeline.retriever, RAGPipeline.chunk_dict

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
                chunk_size=512,
                chunk_overlap=50,
                min_length=50,
                source=f"Uploaded"
            )
            chat_docs.extend(chunks)
        
        return chat_docs

    def generate(self, query: str, chat_history: list[Message], use_web_search: bool = False, use_double_retrievers: bool = True, chat_id: str = None):
        """Stream the RAG pipeline for interactive question answering."""
        start_time = time.time()
        # 1. Load retrievers
        t0 = time.time()
        hybrid_retriever, chunk_dict = self._get_retrievers()
        print(f"[1. Retrieval] Loaded retrievers in {time.time() - t0:.2f}s")
        try:
            # Enhanced classification
            t0 = time.time()
            classification_prompt = config.ENHANCED_CLASSIFICATION_TEMPLATE.format(message=query)
            classification = self.engine.prompt(
                prompt=classification_prompt,
                temperature=0.05
            ).strip().lower()
            print(f"Classification: {classification}")
            print(f"[2. Classification] Completed in {time.time() - t0:.2f}s")
            
            # Route based on classification
            if classification == "conversational":
                while True:
                    prompt = config.CHAT_RESPONSE_TEMPLATE.format(message=query).strip() + "\n\nAssistant:"
                    streamer = self.engine.prompt(prompt=prompt, stream=True, temperature=0.7)
                    
                    for token in streamer:
                        yield token
                    return None
            
            elif classification in ["math", "coding", "mixed"]:
                # Route to technical handler
                for token in TechnicalHandler(self.engine, self.hybrid_retriever).handle_technical_query_stream(query, classification, chat_history):
                    yield token
                return None

            # 3. Get web search results
            t0 = time.time()
            web_results = None
            if use_web_search:
                web_results_list = self._search_bing(query)
                web_results = "\n\n".join(web_results_list)
                print(f"[3. Web Search] Retrieved {len(web_results_list)} results in {time.time() - t0:.2f}s")

            # 4. Get chat history
            t0 = time.time()
            history_chain = []
            pairs = [
                (chat_history[i], chat_history[i + 1])
                for i in range(len(chat_history) - 2, -1, -2)
                if chat_history[i].role == "user" and chat_history[i + 1].role == "assistant"
            ]
            for user_msg, assistant_msg in pairs:
                history_chain.extend([user_msg.model_dump(), assistant_msg.model_dump()])

            history_chain = history_chain[::-1]
            print(f"[4. Chat History] Processed {len(history_chain)} pairs in {time.time() - t0:.2f}s")
            
            # 5. Reform query for better retrieval/response
            t0 = time.time()
            # refined_query = HybridRetriever.query_reform(query, self.engine.prompt)
            print(f"[5. Query Reform] Completed in {time.time() - t0:.2f}s")
            # print(f"Refined Query: {refined_query}")

            # 6. Invokes retrievers to get relevant chunks
            t0 = time.time()
            docs = self.hybrid_retriever.retrieve_context(query, hybrid_retriever, max_results=5) 
            print(f"[6. Retrieval] Retrieved {len(docs)} chunks in {time.time() - t0:.2f}s")

             # 7. Get uploaded chat documents if chat_id provided
            t0 = time.time()
            chat_documents = []
            if chat_id:
                chat_documents = self._process_chat_documents(chat_id)
            print(f"[7. Chat Documents] Processed {len(chat_documents)} documents in {time.time() - t0:.2f}s")

            # 8. Combine regular docs with chat documents
            all_docs = docs + chat_documents

            # 7. Get surrounding documents
            retrieved_info = []
            context_list = []
            
            t0 = time.time()
            for doc in all_docs:
                if doc.metadata.get("source") == "Uploaded":
                    context_chunks = [doc]
                else:
                    context_chunks = self.get_surrounding_chunks(doc, chunk_dict)

                retrieved_info.append({
                    "retrieved_chunk": {
                        "content": doc.page_content[:500],  # Truncate content
                        "metadata": doc.metadata
                    },
                    "surrounding_chunks": [
                        {
                            "content": c.page_content[:300],  # Truncate surrounding
                            "metadata": c.metadata
                        }
                        for c in context_chunks[:3]  # Limit surrounding chunks
                    ]
                })
                
                # Combine context with length limit
                combined_content = ''.join([c.page_content for c in context_chunks])
                context_list.append(combined_content[:1000])  # Truncate combined content

            context = '\n\n'.join(context_list)
            yield retrieved_info
            print(f"[7. Context] Processed {len(context_list)} contexts in {time.time() - t0:.2f}s")
    
            # 8. Constructs prompt
            t0 = time.time()
            def format_block(label, content):
                return f"{label}:\n{content.strip()}\n\n" if content else ""
 
            history_lines = [f"{entry['role'].capitalize()}: {entry['content']}" for entry in history_chain] if history_chain else []
            refined_query = None # placeholder
            prompt = config.RESPONSE_PREFIX.format(
                context=format_block("Context", context),
                history=format_block("Chat History", "\n".join(history_lines)),
                web_context=format_block("Web Context", web_results),
                original_query=format_block("Original Query", query),
                refined_query=format_block("Refined Query", refined_query)
            )
            print(f"[8. Prompt] Constructed in {time.time() - t0:.2f}s")

            # 9. Prompts LLM with context
            t0 = time.time()
            streamer = self.engine.prompt(
                prompt=prompt,
                temperature=ModelConfig.TEMPERATURE,
                stream=True
            )
            for token in streamer:
                yield token
            print(f"[9. LLM Response] Generated in {time.time() - t0:.2f}s")
            return None
        except Exception as e:
            yield f"\n[Error]: {e}\n"