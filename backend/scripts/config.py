"""Configuration file for model settings, prompt templates, and external API URLs."""
import yaml

# === Model & API Settings ===

BING_API_URL = "https://api.bing.microsoft.com/v7.0/search"

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

BING_API_KEY, MODEL_TOKEN = config["BING_API_KEY"], config["MODEL_TOKEN"]

class ModelConfig:
    TONE: str = "Formal"
    # MODEL: str = "gpt2"
    MODEL: str = "mistralai/Mistral-7B-Instruct-v0.1"
    TEMPERATURE: float = 0.4
    LLM_RERANKING: bool = False

# === Prompt Templates ===

PROMPT_LLM_TEMPLATE = """
{prefix}

{context}

{history}

{web_context}

Query:
{question}

Answer:
"""

RESPONSE_PREFIX = """
Answer the query using only the context below.

Guidelines:
- If the context covers multiple topics, focus only on the most relevant and actionable points needed to answer the query.
- Do not add information not in the context.
- Prioritize including all key points from the context that directly answer the query, in order of relevance.
- Prefer quoting or closely paraphrasing the exact phrasing or structure from the context when possible.
- Prefer a clearly structured bullet list when answering technical or standards-based questions, unless the query explicitly requests a paragraph.
- Do not introduce vague or general statements not supported by the context.
- Do not truncate your response prematurely; complete your answer fully before ending. If answering in bullets, complete the list of key points needed to answer the query.
- Prioritize content that supports answering the query over background references or definitions.
- If not found, reply exactly: "I'm not seeing any information in the database."
- Do not repeat information.
- If the provided context does not clearly answer the query, state that and do not attempt to generalize.
- Respond in a complete sentence. Reference titles, proper nouns, or categories if provided.
"""

HISTORY_PROMPT_TEMPLATE = """
Determine if the Current Question depends on the Previous Interaction for understanding or answering.

Criteria:
- If the Current Question can be fully understood and answered using only the Current Question and context, respond NO.
- If the Previous Interaction provides essential information needed to understand or answer the Current Question, respond YES.

Previous Question: {prev_query}  
Previous Answer: {prev_answer}  
Current Question: {current_query}

Respond ONLY with \"YES\" or \"NO\", no explanations or additional text.
"""