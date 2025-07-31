import re
import ast
import sympy as sp

from .utils import Message
from . import config

class ResponseFormatter:
    """Handles formatting of technical responses with proper code blocks"""
    
    @staticmethod
    def format_code_blocks(text: str) -> str:
        """Convert plain text code markers to proper code blocks"""
        # Pattern for ```language code blocks
        pattern = r'```(\w+)?\n?(.*?)```'
        
        def format_block(match):
            language = match.group(1) if match.group(1) else 'text'
            code = match.group(2).strip()
            return f'\n```{language}\n{code}\n```\n'
        
        # Replace code blocks
        formatted = re.sub(pattern, format_block, text, flags=re.DOTALL)
        
        # Handle inline code with backticks
        formatted = re.sub(r'`([^`]+)`', r'`\1`', formatted)
        
        return formatted
    
    @staticmethod
    def format_math_expressions(text: str) -> str:
        """Format mathematical expressions for better readability"""
        # Add spacing around operators
        text = re.sub(r'([a-zA-Z0-9])([\+\-\*/=])([a-zA-Z0-9])', r'\1 \2 \3', text)
        
        # Format common mathematical notation
        replacements = {
            'sqrt(': '√(',
            '^2': '²',
            '^3': '³',
            '+-': '±',
            '<=': '≤',
            '>=': '≥',
            '!=': '≠'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        return text

class QueryDecomposer:
    """Handles query decomposition for mixed queries"""
    
    def __init__(self, llm_engine):
        self.engine = llm_engine
    
    def decompose_query(self, query: str) -> list[tuple[str, str]]:
        """
        Decompose query into components
        Returns: List of (component_type, component_query) tuples
        """
        try:
            decomp_prompt = config.QUERY_DECOMPOSITION_TEMPLATE.format(query=query)
            response = self.engine.prompt(decomp_prompt, temperature=0.1)
            
            if "SIMPLE" in response:
                return [("simple", query)]
            
            components = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('→'):
                    continue
                    
                if ':' in line:
                    comp_type, comp_query = line.split(':', 1)
                    comp_type = comp_type.strip().lower()
                    comp_query = comp_query.strip()
                    
                    if comp_type in ['retrieve_context', 'calculate', 'code', 'chat']:
                        components.append((comp_type, comp_query))
            
            return components if components else [("simple", query)]
            
        except Exception as e:
            print(f"[DEBUG] Decomposition error: {e}")
            return [("simple", query)]

class TechnicalHandler():
    """Streaming version of TechnicalHandler for integration with your pipeline"""
    def __init__(self, llm_engine, hybrid_retriever=None):
        self.engine = llm_engine
        self.hybrid_retriever = hybrid_retriever
        self.decomposer = QueryDecomposer(self.engine)
        self.formatter = ResponseFormatter()

    def handle_technical_query_stream(self, query: str, category: str, chat_history: list[Message] = None):
        """Generator version for streaming responses"""
        if category == "math":
            yield from self._handle_math(query)
        elif category == "coding":
            yield from self._handle_coding(query)
        elif category == "mixed":
            yield from self._handle_mixed(query, chat_history)
        else:
            yield f"Unknown technical category: {category}"
    
    def _handle_math(self, query: str):
        """Streaming math handler"""
        try:
            math_prompt = config.MATH_HANDLER_TEMPLATE.format(query=query)
            streamer = self.engine.prompt(math_prompt, temperature=0.2, stream=True)
            
            response_parts = []
            for token in streamer:
                response_parts.append(token)
                yield token
            
            # Post-process for calculations after streaming completes
            full_response = "".join(response_parts)
            processed = self._process_calculations(full_response)
            formatted = self.formatter.format_math_expressions(processed)

            
            # If calculations were processed, yield the processed parts
            if formatted != full_response:
                calc_results = formatted[len(full_response):]
                yield calc_results
                
        except Exception as e:
            yield f"\n[Math Error]: {str(e)}\n"
    
    def _handle_coding(self, query: str):
        """Streaming coding handler"""
        try:
            coding_prompt = config.CODING_HANDLER_TEMPLATE.format(query=query)
            streamer = self.engine.prompt(coding_prompt, temperature=0.3, stream=True)
            
            response_parts = []
            for token in streamer:
                response_parts.append(token)
                yield token
            
            # Post-process for validation after streaming completes
            full_response = "".join(response_parts)
            processed = self._process_code_validation(full_response)
            formatted = self.formatter.format_code_blocks(processed)
            
            # If validation was processed, yield the validation results
            if formatted != full_response:
                validation_results = formatted[len(full_response):]
                yield validation_results
                
        except Exception as e:
            yield f"\n[Coding Error]: {str(e)}\n"
    
    def _handle_mixed(self, query: str, chat_history: list[Message] = None, retriever=None):
        """Handle mixed queries with proper decomposition"""
        try:
            # Decompose the query
            components = self.decomposer.decompose_query(query)
            
            if len(components) == 1 and components[0][0] == "simple":
                # Treat as general inquiry
                yield "This appears to be a general inquiry. Processing..."
                return
            
            yield f"Processing {len(components)} components:\n\n"
            
            # Process each component sequentially
            for i, (comp_type, comp_query) in enumerate(components, 1):
                yield f"**Step {i}: {comp_type.title().replace('_', ' ')}**\n"
                
                if comp_type == "retrieve_context":
                    yield from self._handle_context_retrieval(comp_query, retriever)
                elif comp_type == "calculate":
                    yield from self._handle_math(comp_query)
                elif comp_type == "code":
                    yield from self._handle_coding(comp_query)
                elif comp_type == "chat":
                    yield from self._handle_chat(comp_query)
                
                yield "\n---\n\n"
                
        except Exception as e:
            yield f"Mixed processing error: {str(e)}"
    
    def _handle_chat(self, query: str):
        """Handle conversational component"""
        try:
            chat_prompt = f"Provide a clear, helpful explanation for: {query}"
            streamer = self.engine.prompt(chat_prompt, temperature=0.4, stream=True)
            
            for token in streamer:
                yield token
                
        except Exception as e:
            yield f"\n[Chat Error]: {str(e)}\n"

    def _process_calculations(self, response: str) -> str:
        """Process [CALCULATE: expression] markers using SymPy"""
        pattern = r'\[CALCULATE:\s*([^\]]+)\]'
        
        def calculate_expression(match):
            expr_str = match.group(1).strip()
            try:
                # Parse and evaluate with SymPy
                expr = sp.sympify(expr_str)
                result = expr.evalf()
                return f"{expr_str} = {result}"
            except Exception as e:
                return f"{expr_str} = [Calculation Error: {str(e)}]"
        
        return re.sub(pattern, calculate_expression, response)
    
    def _process_code_validation(self, response: str) -> str:
        """Process [VALIDATE: code_block] markers for syntax checking"""
        pattern = r'\[VALIDATE:\s*([^\]]+)\]'
        
        def validate_code(match):
            code_str = match.group(1).strip()
            try:
                # Basic Python syntax validation
                ast.parse(code_str)
                return f"✓ Syntax Valid"
            except SyntaxError as e:
                return f"✗ Syntax Error: {str(e)}"
            except Exception as e:
                return f"✗ Validation Error: {str(e)}"
        
        return re.sub(pattern, validate_code, response)
    
    def _fallback_math(self, query: str) -> str:
        """Fallback math handling without external tools"""
        fallback_prompt = f"""
        Solve this mathematical problem step by step using basic reasoning:
        
        {query}
        
        Show your work clearly and provide a final answer.
        """
        return self.engine.prompt(fallback_prompt, temperature=0.2)
    
    def _fallback_coding(self, query: str) -> str:
        """Fallback coding handling without validation"""
        fallback_prompt = f"""
        Help with this coding request:
        
        {query}
        
        Provide clear code and explanation.
        """
        return self.engine.prompt(fallback_prompt, temperature=0.3)
    
    def _handle_context_retrieval(self, query: str, retriever):
        """Handle context retrieval component"""
        try:
                
            docs = self.hybrid_retriever.retrieve_context(query, retriever)
            
            if not docs:
                yield "No relevant documentation found.\n"
                return
            
            yield f"Found {len(docs)} relevant sources:\n\n"
            
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get('source', 'Unknown')
                content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                yield f"{i}. **{source}**\n{content_preview}\n\n"
                
        except Exception as e:
            yield f"Context retrieval error: {str(e)}\n"