"""
SupervisorAgent implementation with AWS Bedrock integration for intent analysis and query routing.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from .base_agent import (
    BaseAgent, AgentType, AgentTask, AgentResult, AgentResponse,
    ConversationContext, Intent, IntentType
)
from llm_client import get_llm_client
from services.fast_intent_classifier import classify_intent_fast


class SupervisorAgent(BaseAgent):
    """
    Main orchestrating agent that receives voice input and routes requests to appropriate agents.
    Uses AWS Bedrock for intent analysis and response synthesis.
    """
    
    def __init__(self, aws_region: str = "us-east-1"):
        super().__init__("SupervisorAgent", AgentType.SUPERVISOR)
        self.aws_region = aws_region
        self.llm_client = get_llm_client(aws_region)
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Using Claude 3.5 Sonnet
        self.escalation_threshold = 0.6
    

    
    async def process_query(self, query: str, context: ConversationContext) -> AgentResult:
        """
        Process a query by analyzing intent and coordinating with other agents.
        """
        start_time = time.time()
        
        try:
            # Analyze intent
            intent = await self.analyze_intent(query, context)
            
            # Route to appropriate agents
            agent_tasks = await self.route_to_agents(intent, query, context)
            
            # For now, return the routing decision as the result
            # In a full implementation, this would coordinate with other agents
            result_data = {
                "intent": intent,
                "routing_decision": [task.agent_type.value for task in agent_tasks],
                "query": query
            }
            
            processing_time = time.time() - start_time
            
            # Determine if escalation is required
            requires_escalation = (
                intent.intent_type == IntentType.ESCALATION or 
                intent.confidence < self.escalation_threshold
            )
            
            return AgentResult(
                agent_name=self.name,
                data=result_data,
                confidence=intent.confidence,
                processing_time=processing_time,
                requires_escalation=requires_escalation,
                metadata={"intent_type": intent.intent_type.value}
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return AgentResult(
                agent_name=self.name,
                data={"error": str(e)},
                confidence=0.0,
                processing_time=processing_time,
                requires_escalation=True,
                metadata={"error": True}
            )
    
    async def analyze_intent(self, query: str, context: ConversationContext) -> Intent:
        """
        Analyze user intent using fast rule-based classifier first, with LLM fallback.
        """
        try:
            # Try fast rule-based classification first
            fast_intent = classify_intent_fast(query)
            if fast_intent:
                print(f"⚡ Fast classifier: {fast_intent.intent_type.value} ({fast_intent.confidence:.2f})")
                return fast_intent
            
            # Fallback to LLM for complex queries
            print(f"🐌 Falling back to LLM for: '{query}'")
            return await self._analyze_intent_with_llm(query, context)
            
        except Exception as e:
            print(f"Intent analysis failed: {e}")
            return Intent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                reasoning=f"Error during intent analysis: {str(e)}"
            )
    
    async def _analyze_intent_with_llm(self, query: str, context: ConversationContext) -> Intent:
        """
        Analyze user intent using LLM (slower but more accurate for complex queries).
        """
        # Build context from conversation history
        conversation_context = self._build_conversation_context(context)
        
        # Create prompt for intent analysis
        prompt = self._create_intent_analysis_prompt(query, conversation_context)
        
        # Call LLM
        response = await self._call_bedrock(prompt)
        
        # Parse response
        intent_data = self._parse_intent_response(response)
        
        return Intent(
            intent_type=IntentType(intent_data.get("intent_type", "unknown")),
            confidence=intent_data.get("confidence", 0.0),
            entities=intent_data.get("entities", {}),
            reasoning=intent_data.get("reasoning")
        )
    
    def _build_conversation_context(self, context: ConversationContext) -> str:
        """Build conversation context string from history."""
        if not context.conversation_history:
            return "No previous conversation history."
        
        # Get last 3 messages for context
        recent_messages = context.conversation_history[-3:]
        context_lines = []
        
        for msg in recent_messages:
            context_lines.append(f"{msg.speaker}: {msg.content}")
        
        return "\n".join(context_lines)
    
    def _create_intent_analysis_prompt(self, query: str, conversation_context: str) -> str:
        """Create prompt for intent analysis."""
        return f"""You are an AI assistant that analyzes user queries for a support voice assistant system. 
Your job is to determine the user's intent and classify it into one of these categories:

1. ticket_query - Questions about existing support tickets, ticket status, or ticket-related data
2. knowledge_query - Questions about product information, documentation, or general knowledge
3. mixed_query - Questions that require both ticket and knowledge information
4. greeting - Greetings, introductions, or conversation starters
5. escalation - Requests to speak with a human or escalate the issue
6. unknown - Unclear or unclassifiable queries

Conversation Context:
{conversation_context}

Current User Query: "{query}"

Analyze this query and respond with a JSON object containing:
- intent_type: one of the categories above
- confidence: a float between 0.0 and 1.0 indicating your confidence
- entities: any specific entities mentioned (ticket IDs, product names, etc.)
- reasoning: brief explanation of your classification

Example response:
{{
    "intent_type": "ticket_query",
    "confidence": 0.9,
    "entities": {{"ticket_id": "12345", "status": "open"}},
    "reasoning": "User is asking about the status of a specific ticket"
}}

Respond only with the JSON object, no additional text."""
    
    async def _call_bedrock(self, prompt: str) -> str:
        """Make async call to LLM (Bedrock or Ollama)."""
        try:
            # Prepare the request body for Claude/Ollama
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            # Make the call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body),
                    contentType='application/json'
                )
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            print(f"LLM API error: {e}")
            raise
    
    def _parse_intent_response(self, response: str) -> Dict:
        """Parse the JSON response from Bedrock."""
        try:
            # Clean up the response (remove any markdown formatting)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse intent response: {e}")
            print(f"Response was: {response}")
            return {
                "intent_type": "unknown",
                "confidence": 0.0,
                "entities": {},
                "reasoning": "Failed to parse response"
            }
    
    async def route_to_agents(self, intent: Intent, query: str, context: ConversationContext) -> List[AgentTask]:
        """
        Determine which agents should handle the query based on intent analysis.
        """
        tasks = []
        
        if intent.intent_type == IntentType.TICKET_QUERY:
            tasks.append(AgentTask(
                agent_type=AgentType.TICKET,
                query=query,
                context=context,
                priority=1,
                metadata={"intent": intent.intent_type.value}
            ))
        
        elif intent.intent_type == IntentType.KNOWLEDGE_QUERY:
            tasks.append(AgentTask(
                agent_type=AgentType.KNOWLEDGE,
                query=query,
                context=context,
                priority=1,
                metadata={"intent": intent.intent_type.value}
            ))
        
        elif intent.intent_type == IntentType.MIXED_QUERY:
            # Route to both agents with different priorities
            tasks.append(AgentTask(
                agent_type=AgentType.TICKET,
                query=query,
                context=context,
                priority=1,
                metadata={"intent": intent.intent_type.value, "mixed": True}
            ))
            tasks.append(AgentTask(
                agent_type=AgentType.KNOWLEDGE,
                query=query,
                context=context,
                priority=1,
                metadata={"intent": intent.intent_type.value, "mixed": True}
            ))
        
        elif intent.intent_type == IntentType.GREETING:
            # Handle greetings directly in supervisor
            pass
        
        elif intent.intent_type == IntentType.ESCALATION:
            # For escalation requests, we don't route to any specific agent
            # The requires_escalation flag will be set in process_query
            # This will be handled by the main orchestrator
            pass
        
        else:  # UNKNOWN
            # Try both agents with lower priority
            tasks.append(AgentTask(
                agent_type=AgentType.KNOWLEDGE,
                query=query,
                context=context,
                priority=2,
                metadata={"intent": intent.intent_type.value, "fallback": True}
            ))
        
        return tasks
    
    async def synthesize_responses(self, agent_results: List[AgentResult], context: ConversationContext) -> str:
        """
        Synthesize responses from multiple agents into a coherent answer.
        """
        if not agent_results:
            return "I'm sorry, I couldn't find any information to help with your request."
        
        # For single agent response
        if len(agent_results) == 1:
            result = agent_results[0]
            if result.requires_escalation:
                return "I'm having trouble with this request. Let me escalate this to a human agent who can better assist you."
            
            # Generate natural response based on agent data
            return await self._generate_natural_response(result, context)
        
        # For multiple agent responses, combine them
        return await self._combine_multiple_responses(agent_results, context)
    
    async def _generate_natural_response(self, result: AgentResult, context: ConversationContext) -> str:
        """Generate a natural language response from agent result."""
        try:
            prompt = f"""Convert this agent result into a natural, conversational response for a voice assistant:

Agent: {result.agent_name}
Data: {json.dumps(result.data, indent=2)}
Confidence: {result.confidence}

Make the response:
- Conversational and natural for voice interaction
- Helpful and informative
- Concise but complete
- Appropriate for the confidence level

Respond with just the natural language response, no additional formatting."""

            response = await self._call_bedrock(prompt)
            return response.strip()
            
        except Exception as e:
            print(f"Failed to generate natural response: {e}")
            return "I found some information, but I'm having trouble presenting it clearly. Could you rephrase your question?"
    
    async def _combine_multiple_responses(self, results: List[AgentResult], context: ConversationContext) -> str:
        """Combine multiple agent responses into a coherent answer."""
        try:
            results_summary = []
            for result in results:
                results_summary.append({
                    "agent": result.agent_name,
                    "data": result.data,
                    "confidence": result.confidence
                })
            
            prompt = f"""Combine these multiple agent responses into a single, coherent voice response:

{json.dumps(results_summary, indent=2)}

Create a natural, conversational response that:
- Integrates information from all agents
- Flows naturally for voice interaction
- Prioritizes higher confidence information
- Is concise but comprehensive

Respond with just the combined response, no additional formatting."""

            response = await self._call_bedrock(prompt)
            return response.strip()
            
        except Exception as e:
            print(f"Failed to combine responses: {e}")
            return "I found information from multiple sources, but I'm having trouble combining it clearly. Could you be more specific about what you need?"
    
    async def should_escalate(self, confidence: float, context: ConversationContext) -> bool:
        """
        Determine if the query should be escalated to a human agent.
        """
        # Check confidence threshold
        if confidence < self.escalation_threshold:
            return True
        
        # Check for explicit escalation requests in recent conversation
        if context.conversation_history:
            recent_messages = context.conversation_history[-2:]
            for msg in recent_messages:
                if any(phrase in msg.content.lower() for phrase in 
                       ["human", "person", "escalate", "supervisor", "manager"]):
                    return True
        
        # Check for repeated low confidence scores
        if len(context.confidence_scores) >= 3:
            recent_scores = context.confidence_scores[-3:]
            if all(score < 0.7 for score in recent_scores):
                return True
        
        return False
    
    async def health_check(self) -> bool:
        """Check if the SupervisorAgent is healthy and ready."""
        try:
            return self.llm_client.health_check()
        except Exception as e:
            print(f"SupervisorAgent health check failed: {e}")
            return False