from typing import List, Dict
import logging
import json

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Handles LLM interactions for answering questions
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        
        # Initialize client based on provider
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        elif self.provider == "groq":
            try:
                from groq import Groq
            except ImportError:
                raise ImportError("groq Python package is not installed. Please add it to requirements.txt.")
            self.client = Groq(api_key=settings.groq_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def is_configured(self) -> bool:
        """Check if LLM is configured"""
        return self.client is not None
    
    def generate_answer(
        self,
        question: str,
        documents: List[Dict],
        system_state: Dict
    ) -> str:
        """
        Generate answer using LLM with retrieved context
        
        Args:
            question: User question
            documents: Retrieved documents
            system_state: Current system state (billing, forecast, etc.)
            
        Returns:
            Generated answer
        """
        try:
            # Build context from documents
            docs_context = self._format_documents(documents)
            
            # Build state context
            state_context = self._format_system_state(system_state)
            
            # Build user prompt
            user_prompt = self._build_user_prompt(question, docs_context, state_context)
            
            # Generate answer
            if self.provider == "openai":
                return self._generate_openai(user_prompt)
            elif self.provider == "anthropic":
                return self._generate_anthropic(user_prompt)
            elif self.provider == "groq":
                return self._generate_groq(user_prompt)
                def _generate_groq(self, user_prompt: str) -> str:
                    """Generate answer using Groq"""
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": self._get_system_prompt()},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7,
                            max_tokens=500
                        )
                        return response.choices[0].message.content
                    except Exception as e:
                        logger.error(f"Groq API error: {e}")
                        raise
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"I encountered an error while processing your question: {str(e)}"
    
    def _format_documents(self, documents: List[Dict]) -> str:
        """Format retrieved documents for context"""
        if not documents:
            return "No relevant documents found."
        
        formatted = []
        for doc in documents:
            doc_id = doc.get('id', 'unknown')
            content = doc.get('content', '')
            formatted.append(f"[{doc_id}]\n{content}\n")
        
        return "\n".join(formatted)
    
    def _format_system_state(self, state: Dict) -> str:
        """Format system state for context"""
        lines = ["Current System State:"]
        
        if state.get('billing'):
            billing = state['billing']
            lines.append(f"- Today's cost: ${billing.get('cost_today', 0):.2f}")
            lines.append(f"- Projected monthly: ${billing.get('projected_month', 0):.2f}")
            lines.append(f"- Energy today: {billing.get('energy_today_kwh', 0):.2f} kWh")
            lines.append(f"- Active tariff: {billing.get('tariff', 'unknown')}")
        
        if state.get('forecast'):
            forecast = state['forecast']
            forecast_kwh = forecast.get('forecast_kwh', [])
            forecast_cost = forecast.get('forecast_cost', [])
            if forecast_kwh:
                lines.append(f"- Next 3h forecast: {forecast_kwh} kWh → ${forecast_cost}")
        
        return "\n".join(lines)
    
    def _build_user_prompt(self, question: str, docs_context: str, state_context: str) -> str:
        """Build the complete user prompt"""
        return f"""User Question: {question}

Retrieved Documentation:
{docs_context}

{state_context}

Answer the user's question using the above context. Be specific and cite sources using [doc_id] format when referencing documents. Include units ($ for cost, kWh for energy) and explain calculations when relevant.
"""
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are OikosNomos Assistant, an expert in home energy billing, IoT systems, and utility tariffs.

Your role:
- Explain the user's current and projected energy costs in clear, non-technical language.
- Help the user understand which devices or behaviors contribute most to their bill.
- Suggest actionable scenarios (e.g., removing devices, changing usage patterns) to reduce costs while maintaining comfort.
- Use ONLY the provided context (retrieved documents and live system state). Do not invent numbers or facts.
- When discussing costs, always mention the tariff being applied and any relevant time-of-use periods.
- If you don't have enough information to answer confidently, say so and suggest what data is needed.

Constraints:
- Cite sources using [doc_id] format when referencing retrieved documents.
- Always include units ($, kWh, kg CO₂).
- Be concise: aim for 2-4 sentences per answer unless user asks for details.
- If the user asks a question outside your domain (e.g., "What's the weather tomorrow?"), politely redirect to energy topics.
"""
    
    def _generate_openai(self, user_prompt: str) -> str:
        """Generate answer using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _generate_anthropic(self, user_prompt: str) -> str:
        """Generate answer using Anthropic Claude"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=self._get_system_prompt(),
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
