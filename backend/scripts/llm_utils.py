"""LLM engine backed by a shared Ollama inference server.

The model no longer lives in this process. Ollama owns the GPU and serves the
(quantized) model once; every backend instance is a thin HTTP client, so prod
and dev can share a single model copy concurrently instead of each trying to
load ~14 GB of weights into a 16 GB card.

The public surface is intentionally unchanged so callers in rag.py / handler.py
/ main.py need no edits:

    engine = get_llm_engine()
    text   = engine.prompt(prompt, temperature=...)               # -> str
    stream = engine.prompt(prompt, stream=True, temperature=...)  # -> Iterator[str]
    engine._load_model(...)   # warmup: loads the model into VRAM
    engine.cleanup()          # no-op, kept for compatibility
"""
import json
import logging
import threading
from typing import Iterator, Union

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from . import config

logger = logging.getLogger(__name__)

_LLM_ENGINE_INSTANCE = None
_LLM_ENGINE_LOCK = threading.Lock()


def get_llm_engine():
    global _LLM_ENGINE_INSTANCE
    if _LLM_ENGINE_INSTANCE is None:
        with _LLM_ENGINE_LOCK:
            if _LLM_ENGINE_INSTANCE is None:
                _LLM_ENGINE_INSTANCE = LLMEngine()
    return _LLM_ENGINE_INSTANCE


class LLMEngine:
    def __init__(self):
        self.host = config.OLLAMA_HOST.rstrip("/")
        self.model = config.OLLAMA_MODEL
        self.num_ctx = config.OLLAMA_NUM_CTX
        # Keep the model resident in VRAM instead of letting Ollama unload it
        # after its default idle timeout.
        self.keep_alive = config.OLLAMA_KEEP_ALIVE
        self._generate_url = f"{self.host}/api/generate"

    def _payload(self, prompt: str, max_new_tokens: int, temperature: float, stream: bool, top_p: float) -> dict:
        return {
            "model": self.model,
            "prompt": prompt,
            # raw=True sends the prompt verbatim (no chat template applied) and
            # returns only the completion. This matches the previous transformers
            # behavior, where we tokenized the raw prompt string and stripped the
            # echoed prompt off the front of the output.
            "raw": True,
            "stream": stream,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_new_tokens,
                "num_ctx": self.num_ctx,
            },
        }

    def _load_model(self, model_name: str = None):
        """Warm the configured model into VRAM so the first real request isn't
        slow. model_name is accepted for call-site compatibility; the served
        model is set via OLLAMA_MODEL."""
        try:
            resp = requests.post(
                self._generate_url,
                json={"model": self.model, "keep_alive": self.keep_alive},
                timeout=(10, 600),
            )
            resp.raise_for_status()
            logger.info(f"Loaded '{self.model}' on {self.host}")
        except requests.RequestException as e:
            logger.error(
                f"Could not load '{self.model}' at {self.host}: {e}\n"
                f"            Is Ollama running, and has the model been pulled? "
                f"(ollama pull {self.model})"
            )

    def cleanup(self):
        """No local GPU state to free; kept for interface compatibility."""
        pass

    def set_model(self, model_name: str):
        """Switch the model used for subsequent prompt() calls."""
        if model_name and model_name != self.model:
            self.model = model_name

    def list_models(self) -> list[str]:
        """Query Ollama for the models currently pulled on the host."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=10)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except requests.RequestException as e:
            logger.error(f"Could not list models at {self.host}: {e}")
            return [self.model]

    def prompt(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.2,
        stream: bool = False,
        top_p: float = 0.85,
    ) -> Union[str, Iterator[str]]:
        """Prompt the shared model. Returns a string, or an iterator of token
        strings when stream=True."""
        payload = self._payload(prompt, max_new_tokens, temperature, stream, top_p)
        if stream:
            return self._stream(payload)
        return self._complete(payload)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10), reraise=True)
    def _post(self, payload: dict, stream: bool = False) -> requests.Response:
        resp = requests.post(self._generate_url, json=payload, stream=stream, timeout=(10, 600))
        resp.raise_for_status()
        return resp

    def _complete(self, payload: dict) -> str:
        try:
            resp = self._post(payload)
            return resp.json().get("response", "").strip()
        except requests.RequestException:
            logger.exception("Generation request failed")
            raise

    def _stream(self, payload: dict) -> Iterator[str]:
        try:
            resp = self._post(payload, stream=True)
        except requests.RequestException:
            logger.exception("Streaming request failed")
            raise
        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                chunk = obj.get("response", "")
                if chunk:
                    yield chunk
                if obj.get("done"):
                    break
        finally:
            resp.close()
