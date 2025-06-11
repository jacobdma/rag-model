# from .rag import RAGPipeline
import sys
import traceback
import logging
from .load_utils import CACHE_DIR, LOG_DIR

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


pipeline = None
response = pipeline.generate(
    query="In ANSI B92.2M-1980, how do hard metric spline tolerances ensure interchangeability between mating parts, and what design strategies are available when a specific clearance or press fit is required?",
    # Trial 2 query="what are teh best practices for safety",
    chat_history=[],
    use_web_search=False
)
print(response)