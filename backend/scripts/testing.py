from .llm_utils import get_llm_engine
import requests
from . import config

def main():
    engine = get_llm_engine()

    while True:
        message = input("Message: ")
        if message == "quit":
            break
        classification_prompt = config.CLASSIFICATION_TEMPLATE.format(message=message)
        classification = engine.prompt(
            prompt=classification_prompt,
            temperature=0.1
        )

        print("===== Classification =====")
        print(classification)

        if "conversational" in classification:
            # 3. Run conversation prompt and skip pipeline
            prompt = config.CHAT_RESPONSE_TEMPLATE.format(message=message)
            print("[DEBUG] Prompt:\n" + prompt)
            streamer = engine.prompt(
                prompt=prompt,
                stream=True
            )

            print("===== LLM Response =====")

            for token in streamer:
                print(token, end="", flush=True)
            
if __name__ == "__main__":
    main()