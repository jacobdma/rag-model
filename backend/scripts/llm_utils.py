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
from typing import Iterator, Union

import requests

from . import config

_LLM_ENGINE_INSTANCE = None


def get_llm_engine():
    global _LLM_ENGINE_INSTANCE
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

    def _payload(self, prompt: str, max_new_tokens: int, temperature: float, stream: bool) -> dict:
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
                "top_p": 0.85,
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
                timeout=600,
            )
            resp.raise_for_status()
            print(f"[LLMEngine] Loaded '{self.model}' on {self.host}")
        except requests.RequestException as e:
            print(
                f"[LLMEngine] Could not load '{self.model}' at {self.host}: {e}\n"
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
            print(f"[LLMEngine] Could not list models at {self.host}: {e}")
            return [self.model]

    def prompt(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.2,
        stream: bool = False,
    ) -> Union[str, Iterator[str]]:
        """Prompt the shared model. Returns a string, or an iterator of token
        strings when stream=True."""
        payload = self._payload(prompt, max_new_tokens, temperature, stream)
        if stream:
            return self._stream(payload)
        return self._complete(payload)

    def _complete(self, payload: dict) -> str:
        try:
            resp = requests.post(self._generate_url, json=payload, timeout=600)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except requests.RequestException as e:
            print(f"[LLMEngine] Generation request failed: {e}")
            raise

    def _stream(self, payload: dict) -> Iterator[str]:
        try:
            with requests.post(self._generate_url, json=payload, stream=True, timeout=600) as resp:
                resp.raise_for_status()
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
        except requests.RequestException as e:
            print(f"[LLMEngine] Streaming request failed: {e}")
            raise
