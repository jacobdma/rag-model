# from .rag import RAGPipeline
import sys
import traceback
import logging
from .load_utils import CACHE_DIR, LOG_DIR
import time
from pathlib import Path

# Crash logging
log_dir = LOG_DIR / "crash.log"
logging.basicConfig(filename=log_dir, level=logging.ERROR)

def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error("Uncaught Exception:\n%s", error_msg)
    print("[CRITICAL] Uncaught exception — details logged to crash.log")

sys.excepthook = log_uncaught_exceptions

# Ensure local imports work
sys.path.append(str(Path(__file__).parent))

from .rag import RAGPipeline, Message

def prewarm_pipeline(pipeline):
    print("[INFO] Prewarming pipeline and retrievers...")
    t0 = time.time()
    pipeline._get_retrievers()
    print(f"[INFO] Prewarming complete in {time.time() - t0:.2f} seconds.")

def stream_query(pipeline, query, chat_history=None, use_web_search=False, use_double_retrievers=True):
    if chat_history is None:
        chat_history = []
    print(f"\n[QUERY] {query}\n[RESPONSE]: ", end="", flush=True)
    tokens = pipeline.stream_generate(
        query=query,
        chat_history=chat_history,
        use_web_search=use_web_search,
        use_double_retrievers=use_double_retrievers,
    )
    for token in tokens:
        print(token, end="", flush=True)
    print("\n" + "-"*60)

def main():
    pipeline = RAGPipeline()
    prewarm_pipeline(pipeline)
    chat_history = []

    print("Type your question (or 'exit' to quit):")
    print("Example: In ANSI B92.2M-1980, how do hard metric spline tolerances ensure interchangeability between mating parts, and what design strategies are available when a specific clearance or press fit is required?")
    print("Example: what are teh best practices for safety")
    print("-" * 60)

    while True:
        try:
            query = input("\nYour query: ").strip()
            if query.lower() == "exit":
                print("Exiting.")
                break
            if not query:
                continue

            # Add user message to history
            chat_history.append(Message(role="user", content=query))
            # Stream response
            stream_query(pipeline, query, chat_history)
            # Add assistant message to history (simulate, you may want to capture the full response)
            # For simplicity, not capturing the full assistant response here
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()