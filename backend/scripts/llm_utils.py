import threading
import time
import torch
import gc
from queue import Queue
from . import config
from .config import ModelConfig

from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.generation.streamers import TextIteratorStreamer

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
        self._gpu_lock = threading.Lock()
        self._request_queue = Queue(maxsize=15)

    def _load_model(self, model_name: str):
        """
        Loads and caches model and tokenizer
        """
        if self._model is None or self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(model_name, token=self.token, padding_side="left")
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = AutoModelForCausalLM.from_pretrained(
                model_name,
                token=self.token,
                low_cpu_mem_usage=True,
                device_map={"": device},
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                use_cache=True,
                trust_remote_code=True
            )
            self._model = self._model.to(device)
        return self._model, self._tokenizer
    
    def cleanup(self):
        if torch.cuda.is_available():
            gc.collect()
    
    def prompt(self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.2, stream: bool = False) -> TextIteratorStreamer | str:
        """
        Prompts cached model and returns output with optional streaming bool
        """
        with self._gpu_lock:
            try:
                model, tokenizer = self._load_model(ModelConfig.MODEL)
                device = next(model.parameters()).device

                with torch.no_grad():
                    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
                    input_ids = inputs.input_ids.to(device, non_blocking=True)
                    attention_mask = inputs.attention_mask.to(device, non_blocking=True)
                token = tokenizer.eos_token_id

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
                    generation_kwargs["streamer"] = streamer

                    def generate_sync():
                        try:
                            with torch.no_grad():
                                model.eval()
                                outputs = model.generate(**generation_kwargs)
                        except Exception as e:
                            print(f"Error occurred during generation: {e}")
                        finally:
                            if 'input_ids' in locals():
                                del input_ids
                            if 'attention_mask' in locals():
                                del attention_mask
                            self.cleanup()
                    thread = threading.Thread(target=generate_sync)
                    thread.daemon = True
                    thread.start()
                    return streamer
                else:
                    model.eval()
                    outputs = model.generate(**generation_kwargs)
                    if hasattr(outputs, 'sequences'):
                        generated_ids = outputs.sequences[0]
                    else:
                        generated_ids = outputs[0]

                    decoded = tokenizer.decode(generated_ids, skip_special_tokens=True)
                    result =  decoded[len(prompt):].strip()

                    del input_ids, attention_mask, outputs, generated_ids
                    return result
            except Exception as e:
                raise
            finally:
                self.cleanup()