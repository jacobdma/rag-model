import torch
import time
import re
from . import config
from .config import ModelConfig
from sentence_transformers import SentenceTransformer

from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
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
    
    def prompt(
        self, 
        prompt: str, 
        max_new_tokens: int = 384, 
        temperature: float = 0.2, 
        stream: bool = True
    ) -> str | list[str]:
        model, tokenizer = self._load_model(ModelConfig.MODEL)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs.input_ids.to(device)
        print(f"Prompt token count: {input_ids.shape[1]}")
        print(f"Model temperature: {temperature}")

        if stream:
            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
            generation_kwargs = dict(
                input_ids=input_ids,
                attention_mask=inputs.attention_mask.to(device),
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.85,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
                streamer=streamer
            )
            thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
            thread.start()
            return streamer  # This is an iterator over generated tokens

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
    
    @staticmethod
    def load_bge_large_fp16():
        model_name = "BAAI/bge-large-en-v1.5"
        if torch.cuda.is_available():
            model = SentenceTransformer(model_name, device="cuda")
            model = model.half()
        else:
            model = SentenceTransformer(model_name, device="cpu")
        return lambda x, **kwargs: model.encode(x, **kwargs) if isinstance(x, list) else model.encode([x], **kwargs)[0]

