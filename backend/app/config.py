"""Configuration file for model settings, prompt templates, and external API URLs."""
import yaml

# === Model & API Settings ===

BING_API_URL = "https://api.bing.microsoft.com/v7.0/search"

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

BING_API_KEY, MODEL_TOKEN = config["BING_API_KEY"], config["MODEL_TOKEN"]

MODEL_LITE = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

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

RERANK_PREFIX = """
Given the following context chunks, return only those that are relevant to the question.

✅ Only include chunk text.  
⛔️ Do not return scores, rankings, commentary, or metadata.

Example:
Question: What is the weight range of the Emperor penguin?
Chunks:
1. Emperor penguins typically weigh between 50 and 100 pounds.
2. The penguin's habitat consists of icy regions in Antarctica.
3. Macaroni penguins weigh between 8 and 14 pounds.

Relevant:
1. Emperor penguins typically weigh between 50 and 100 pounds.

Now do the same for the following input.
"""

RESPONSE_PREFIX = """
Answer the query using only the context below.

Guidelines:
- If the context covers multiple topics, focus only on the most relevant and actionable points related to the query.
- Do not add information not in the context.
- Respond concisely, in 3 bullet points or less or a short paragraph.
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

Respond with YES or NO only.
"""


REFORMULATION_PROMPT_TEMPLATE = """
Rewrite the following query to expand acronyms and add technical synonyms, while preserving the exact meaning and intent.

Do not change the core question. Avoid paraphrasing unless necessary for clarity. Respond ONLY with the Rewritten Query

Original Query: {query}

Rewritten Query:
"""

DIVERSIFY_PROMPT_TEMPLATE = """
Generate 2 alternative versions of this query that ask for the same information but use different phrasing or terminology.

Do not change what the question is fundamentally asking. Avoid vague or irrelevant rewrites.

Original Query: {query}

Alternative Queries (numbered):
"""

RETRIEVAL_PROMPT = """
Estimate how well a keyword-based retriever (like BM25) will perform on the following query, compared to a semantic retriever.

Query: {query}

Use these heuristics:
- Proper nouns or directive verbs (find, list, who, where) → stronger BM25 performance
- Abstract/exploratory phrasing (how, why, compare, describe) → stronger semantic performance
- Short, precise or technical queries → favor BM25
- Longer, open-ended queries → favor semantic

Respond with a float between 0.0 and 1.0 on its own line.
0.0 = all BM25; 1.0 = all semantic.

Include only the float in your answer. Do not explain your answer.

Answer:
"""