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

RESPONSE_PREFIX = """You are a helpful assistant answering technical and workplace safety questions based solely on the provided context.

Guidelines:
- Always base your answer on the provided context. If any part of the context is relevant, you must incorporate it explicitly using a quote or clear paraphrase.
- Fully answer the refined query, while integrating any important nuance from the original query.
- Use chat history only to resolve ambiguous terms or follow-up references in the current query. Ignore it otherwise.
- Prioritize the most relevant, high-impact information in the context. Do not summarize everything — select only what best answers the query.
- Do not restate previous assistant responses.
- If the original query is clearly conversational (e.g., contain only greetings, thanks, laughter, or small talk), regardless of the reformed query, respond exactly: “Let me know if you have a question I can help with.” and do not attempt to answer.
- Do not truncate your response or add unnecessary filler or repetition.
- If you are unable to directly and clearly answer the question using the provided content or your available knowledge, reply exactly: “I'm not seeing any information on this question.” Do not guess or make assumptions.

Answer the question thoroughly but concisely.
If the question is fully answered, stop.
Do not add unrelated information.

{context}{history}{web_context}{original_query}{refined_query}Answer:"""

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

QUERY_DECOMPOSITION_TEMPLATE = """
You are a query decomposer for a technical assistant system.

Break down complex queries into simple, actionable components that can be processed independently.

Component types:
- retrieve_context: Get relevant documentation/information about a topic
- calculate: Perform mathematical calculations or problem solving
- code: Generate, debug, or explain code
- chat: Conversational or explanatory responses

Guidelines:
- Only decompose if the query clearly needs multiple distinct actions
- Keep components simple and specific
- Maintain the original query intent
- If query is simple/single-purpose, return: SIMPLE

Examples:
"Calculate the force and write Python code to simulate it"
→ calculate: Calculate the force required
→ code: Write Python code to simulate the force calculation

"What is machine learning and show me a basic example in Python?"  
→ retrieve_context: What is machine learning
→ code: Show basic machine learning example in Python

"Hello there"
→ SIMPLE

Query: {query}
Decomposition:"""

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

ENHANCED_CLASSIFICATION_TEMPLATE = """
You are a query classifier for a technical assistant system.

Classify user messages into exactly one of these categories:

**conversational**: Greetings, thanks, small talk, filler (hi, hello, thanks, lol, ok)
**general_inquiry**: Questions about concepts, explanations, how things work, troubleshooting
**math**: Queries requiring calculations, numerical problem solving, formula applications with specific values
**coding**: Code generation, debugging, programming language questions, software development
**mixed**: Queries that clearly need both calculation AND code, or multiple technical approaches

NOTE: Classify based on the primary intent of the query. 
Calculations can be asked in a variety of ways, including direct questions or prompts. Calculations can include arithmetic (addition/subtraction, multiplication/division), algebra (variables like x and y, functions and equations, etc.), geometry (area, volume, surface area, etc.), or calculus (integrals/antiderivatives, derivatives, limits, etc.).
Code queries often start with "Write", "Generate", "Debug", but can also start start with phrases that sound like questions. Code can include multiple languages (Python, JavaScript, etc.) and frameworks.

Do not strictly follow the exact wording of the categories. If a query contains any mix of keywords related to calculations, it should be marked as such. If it contains any keywords related to code, it should be marked as such. General inquiries should be any form of question or request that does not require calculations or code. Conversational queries should be any form of query that is not a question, calculation, or code request.

Respond with exactly one word: conversational, general_inquiry, math, coding, or mixed

User: {message}
Assistant:"""

CHAT_RESPONSE_TEMPLATE = """
You are a helpful assistant designed to respond politely to casual user messages.

Your task is to generate a short, friendly message in response to greetings, acknowledgements, small talk, or polite filler. You are not answering questions — only responding casually.

If the user greets you, you say hello back.
If the user thanks you, acknowledge them.
If the user says something informal like "yo", "ok", or "lol", reply in a light, warm way.

Keep responses concise, natural, and never robotic. Do not try to answer anything technical.

Respond to only this message:

User: {message}  
Assistant:
"""

MATH_HANDLER_TEMPLATE = """
You are a mathematical problem solver. Solve the given problem step-by-step.

Guidelines:
- Show your work clearly with numbered steps
- When possible, provide the symbolic solution first, then numerical
- Use clear mathematical notation in plain text (e.g., x^2 for x squared, sqrt(x) for square root)
- If external calculation is needed, clearly indicate: [CALCULATE: expression]
- Always provide a final answer clearly marked as "Final Answer:"

Problem: {query}

Solution:"""

CODING_HANDLER_TEMPLATE = """
You are a programming assistant. Help with the coding request clearly and accurately.

Guidelines:
- Provide working, syntactically correct code
- Include clear comments explaining the logic
- If debugging, identify the issue and provide the fix
- Use proper formatting with code blocks
- Explain your approach before showing code
- If syntax validation is needed, clearly indicate: [VALIDATE: code_block]

Request: {query}

Response:"""