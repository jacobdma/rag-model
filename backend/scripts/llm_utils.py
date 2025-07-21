import torch
import time
from . import config
from .config import ModelConfig

from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.generation.streamers import TextIteratorStreamer
import threading

_LLM_ENGINE_INSTANCE = None

def get_llm_engine():
    global _LLM_ENGINE_INSTANCE
    if _LLM_ENGINE_INSTANCE is None:
        _LLM_ENGINE_INSTANCE = LLMEngine()
    return _LLM_ENGINE_INSTANCE

class LLMEngine:
    def __init__(self):
        self.token = config.MODEL_TOKEN
        self._model = None
        self._tokenizer = None

    def _load_model(self, model_name: str):
        """
        Loads and caches model and tokenizer
        """
        if self._model is None or self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(model_name, token=self.token)
            print(f">>> Loading model {model_name}")
            start = time.time()

            self._model = AutoModelForCausalLM.from_pretrained(
                model_name,
                token=self.token,
                low_cpu_mem_usage=True,
                device_map="cuda" if torch.cuda.is_available() else "cpu",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            print(f">>> Model loaded in {(time.time() - start):.2f}s")
        return self._model, self._tokenizer
    
    def prompt(self, prompt: str, max_new_tokens: int = 384, temperature: float = 0.2, stream: bool = False) -> TextIteratorStreamer | str:
        """
        Prompts cached model and returns output with optional streaming bool
        """
        model, tokenizer = self._load_model(ModelConfig.MODEL)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs.input_ids.to(device)
        attention_mask = inputs.attention_mask.to(device)
        token = tokenizer.eos_token_id
        print(f"Prompt token count: {input_ids.shape[1]}")
        print(f"Model temperature: {temperature}")


        generation_kwargs = dict(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.85,
            eos_token_id=token,
            pad_token_id=token
        )
        if stream:
            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
            thread = threading.Thread(target=lambda: model.generate(streamer=streamer, **generation_kwargs))
            thread.start()
            return streamer
        else:
            outputs = model.generate(**generation_kwargs)
            decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return decoded[len(prompt):].strip()