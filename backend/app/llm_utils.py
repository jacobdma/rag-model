import torch
import time
import re
from . import config
from .config import ModelConfig

from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, TextIteratorStreamer
import threading

_LLM_ENGINE_INSTANCE = None

def get_llm_engine():
    global _LLM_ENGINE_INSTANCE
    if _LLM_ENGINE_INSTANCE is None:
        _LLM_ENGINE_INSTANCE = LLMEngine(config.MODEL_TOKEN)
    return _LLM_ENGINE_INSTANCE

class LLMEngine:
    def __init__(self, token: str | None = None):
        self.token = token
        self._model_large = None
        self._tokenizer_large = None
        self._pipeline_lite = None

    # Stores tokenizer, model, and pipeline for faster retrieval
    def load_pipeline(self, model_name: str, cache_attr: str):
        if getattr(self, cache_attr) is None:
            tokenizer = AutoTokenizer.from_pretrained(model_name, token=self.token, trust_remote_code=True)
            if torch.cuda.is_available():
                model = AutoModelForCausalLM.from_pretrained(model_name, token=self.token, device_map="cuda", torch_dtype="float16", trust_remote_code=False)
            else:
                model = AutoModelForCausalLM.from_pretrained(model_name, token=self.token, device_map="cpu", torch_dtype="float32", trust_remote_code=False)
            pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, pad_token_id=tokenizer.eos_token_id)
            setattr(self, cache_attr, pipe)
        return getattr(self, cache_attr)

    def _load_model(self, model_name: str):
        if self._model_large is None or self._tokenizer_large is None:
            self._tokenizer_large = AutoTokenizer.from_pretrained(model_name, token=self.token)
            print(f">>> Loading model {model_name}")
            start = time.time()

            self._model_large = AutoModelForCausalLM.from_pretrained(
                model_name,
                token=self.token,
                low_cpu_mem_usage=True,
                device_map="cuda" if torch.cuda.is_available() else "cpu",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            print(f">>> Model loaded in {(time.time() - start):.2f}s")
        return self._model_large, self._tokenizer_large
    
    def prompt(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.2) -> str | list[str]:
        model, tokenizer = self._load_model(ModelConfig.MODEL)
        device="cuda" if torch.cuda.is_available() else "cpu"
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs.input_ids.to(device)
        print("Prompt token count:", input_ids.shape[1])

        output_ids = model.generate(
            input_ids,
            attention_mask=inputs.attention_mask.to(device),
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.85,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )
        output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return output_text[len(prompt):].strip()

    def prompt_lite(self, question: str, prefix: str = "", max_new_tokens: int = 32,
                    temperature: float = 0.1) -> str | list[str]:
        generate = self.load_pipeline(config.MODEL_LITE, "_pipeline_lite")
        prompt_text = f"{prefix.strip()} {question.strip()}".strip()

        output = generate(prompt_text , max_new_tokens=max_new_tokens, do_sample=True, top_p=0.9, temperature=temperature)
        if not output or "generated_text" not in output[0]:
            print("[Warning] LLM output is empty or malformed:", output)
            return None
        content = output[0]["generated_text"].strip()
        match = re.search(r"Answer:\s*(.*)", content, re.DOTALL)
        if match:
            content = match.group(1).strip()
        return content

