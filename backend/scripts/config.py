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
- Prioritize including all key points from the context that directly answer the query, in order of relevance. If multiple sources or domains are represented in the context, select the most relevant points across them.
- Prefer quoting or paraphrasing the most relevant sections of the retrieved context when answering, especially when multiple domains or technical details are present.
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

templates = {
        "Rewrite": """
You are a precise query rewriting system.

Your task is to slightly rewrite user queries to make them clearer, well-formed, and suitable for search. Do not add assumptions. Preserve original intent exactly. Maintain all keywords.
If a query is vague and the domain is not explicitly specified, assume the user is referring to a mechanical or engineering context.
Informal or misspelled language should be expanded and clarified to reflect likely intent (e.g. 'parts r rubbin' -> 'parts are rubbing', 'u can get 2 hot' -> 'you can get too hot')
If a query is a vague or objective statement, infer the likely intent and rewrite it as a precise, standalone question that expresses what the user is trying to learn or solve.
It is acceptable to expand the query slightly to clarify the intended domain or make implicit assumptions explicit.

Examples:
Original: How tall is the Eiffel Tower? It looked so high when I was there last year?
Rewritten: What is the height of the Eiffel Tower?

Original: 1 oz is 28 trams, how many cm is 1 inch?
Rewritten: Convert 1 inch to cm

Original: What's the main point of the article? What did the author try to convey?
Rewritten: What is the main key point of this article?

Original: parts r rubbin
Rewritten: What causes excessive rubbing between mechanical parts, and how can it be prevented?

If you do not recognize a word or acronym, do not try to rewrite it.
Only rewrite the user's question. Do not insert, remove, or hallucinate content. 
Do not repeat examples. Do not respond conversationally. Each rewrite must be a single sentence.

USER QUERY: {query}
Rewritten:""",
        "Condense": """
From the following rewritten queries, find the common question and condense it into a singular, one-sentence question that addresses all major points of the subquestions.

If you don't recognize a word or acronym, do not try to rewrite it. Preserve all original meaning and intent.

SUB QUESTIONS: {query}
Response:""",
        "Subquery Decomposition": """
You are a helpful assistant that generates search queries based on a single input query. 

Perform query decomposition. Given a short or vague user query, break it into high-quality, atomic, distinct sub-questions that clarify the information need. 

Do not invent context. If domain is unspecified, keep questions general.
If the USER QUERY includes a relationship between two or more subjects (e.g., differences, similarities, dependencies, tradeoffs), include one or more sub-questions that explicitly address the relationship.
If the USER QUERY includes numeric ranges, tolerances, or measurement units, include sub-questions that clarify definitions, measurement methods, influencing factors, and relevant standards — not just the numeric constraint itself.

Format: List sub-questions in numbered format.

Examples (for context only):
Query: How does reinforcement learning apply to autonomous driving, and what models are most effective?
Sub-questions:
1. How is reinforcement learning used in autonomous driving?
2. What reinforcement learning models are most effective for autonomous vehicles?

Query: What is the minimum clearance required?
Sub-questions:
1. How does clearance differ across applications?
2. Are there any applicable standards that define minimum clearance for this case?
3. What are the risks of insufficient clearance?

Now decompose the following:

USER QUERY: {query}
Sub-questions:"""}