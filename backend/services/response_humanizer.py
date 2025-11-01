"""
Response Humanizer Service
Converts technical agent responses into natural, human-like conversational responses.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from llm_client import get_llm_client

logger = logging.getLogger(__name__)


class ResponseHumanizer:
    """Service to convert technical responses into human-like conversational responses."""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        
        # Response templates for different scenarios
        self.greeting_responses = [
            "Hello! I'm doing great, thank you for asking. How can I help you today?",
            "Hi there! I'm here and ready to assist you. What can I help you with?",
            "Hello! I'm doing well, thanks for asking. What brings you here today?",
            "Hi! I'm doing fantastic and ready to help. What can I do for you?"
        ]
        
        self.error_responses = [
            "I'm sorry, I'm having trouble processing that right now. Could you try rephrasing your question?",
            "Hmm, I'm not quite sure about that. Could you provide a bit more detail?",
            "I apologize, but I'm having difficulty with that request. Can you help me understand what you're looking for?"
        ]
    
    async def humanize_response(self, 
                               agent_results: List[Dict[str, Any]], 
                               original_query: str,
                               context: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert technical agent responses into human-like conversational responses.
        
        Args:
            agent_results: List of agent result data
            original_query: The user's original question
            context: Additional context for response generation
            
        Returns:
            Human-like conversational response
        """
        try:
            # Handle escalation requests FIRST
            if self._is_escalation_request(agent_results, original_query):
                return self._get_escalation_response()
            
            # Handle simple greetings
            if self._is_greeting(original_query):
                return self._get_greeting_response()
            
            # Handle errors
            if self._has_errors(agent_results):
                return self._get_error_response()
            
            # Handle empty results
            if not agent_results or all(not result.get('data') for result in agent_results):
                return "Hmm, I'm not finding anything on that. Could you try asking differently?"
            
            # Generate human-like response using LLM
            return await self._generate_human_response(agent_results, original_query, context)
            
        except Exception as e:
            logger.error(f"Error humanizing response: {e}")
            return "Sorry, I'm having trouble with that. Could you try again?"
    
    def _is_greeting(self, query: str) -> bool:
        """Check if the query is a greeting."""
        greeting_keywords = ['hello', 'hi', 'hey', 'how are you', 'good morning', 'good afternoon', 'good evening']
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in greeting_keywords)
    
    def _get_greeting_response(self) -> str:
        """Get a friendly greeting response."""
        import random
        return random.choice(self.greeting_responses)
    
    def _has_errors(self, agent_results: List[Dict[str, Any]]) -> bool:
        """Check if any agent results contain errors."""
        return any(result.get('data', {}).get('error') for result in agent_results)
    
    def _get_error_response(self) -> str:
        """Get a friendly error response."""
        import random
        return random.choice(self.error_responses)
    
    def _is_escalation_request(self, agent_results: List[Dict[str, Any]], query: str) -> bool:
        """Check if this is an escalation request."""
        # Check if any agent result requires escalation
        for result in agent_results:
            if result.get('requires_escalation'):
                return True
            
            # Check if supervisor detected escalation intent
            if result.get('agent_name') == 'SupervisorAgent':
                data = result.get('data', {})
                intent = data.get('intent')
                if intent and hasattr(intent, 'intent_type') and intent.intent_type.value == 'escalation':
                    return True
        
        # Check query for escalation keywords
        escalation_keywords = ['escalate', 'human', 'person', 'agent', 'transfer', 'supervisor']
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in escalation_keywords)
    
    def _get_escalation_response(self) -> str:
        """Get an escalation response."""
        escalation_responses = [
            "I understand you'd like to speak with someone else. Let me connect you with a human agent who can help you better.",
            "Of course, let me get you connected with one of our support specialists right away.",
            "No problem, I'll transfer you to a human agent who can assist you further.",
            "I hear you - let me get you connected with someone who can provide more personalized help."
        ]
        import random
        return random.choice(escalation_responses)
    
    async def _generate_human_response(self, 
                                     agent_results: List[Dict[str, Any]], 
                                     original_query: str,
                                     context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a human-like response using LLM."""
        try:
            # Prepare the data for the LLM
            response_data = self._prepare_response_data(agent_results)
            
            # For ticket queries, try a simple template first
            if response_data.get('ticket_results'):
                template_response = self._try_template_response(response_data['ticket_results'], original_query)
                if template_response:
                    print(f"📝 Template response: {template_response[:50]}...")
                    return template_response
            
            # For knowledge queries, try a knowledge template first
            if response_data.get('knowledge_results'):
                template_response = self._try_knowledge_template_response(response_data['knowledge_results'], original_query)
                if template_response:
                    print(f"📚 Knowledge template response: {template_response[:50]}...")
                    return template_response
            
            # Create prompt for humanizing the response
            prompt = self._create_humanization_prompt(original_query, response_data, context)
            
            # Generate response using LLM
            response = await self._call_llm(prompt)
            
            # Clean up the response
            return self._clean_response(response)
            
        except Exception as e:
            logger.error(f"Error generating human response: {e}")
            return "I found some information, but I'm having trouble presenting it clearly. Let me know if you'd like me to try again."
    
    def _try_knowledge_template_response(self, knowledge_results: List[Dict[str, Any]], query: str) -> Optional[str]:
        """Try to generate a simple template response for knowledge queries."""
        try:
            for knowledge_data in knowledge_results:
                if knowledge_data.get('type') == 'knowledge_search':
                    contextual_response = knowledge_data.get('contextual_response', {})
                    answer = contextual_response.get('answer', '')
                    confidence = contextual_response.get('confidence', 0.0)
                    
                    if answer and confidence > 0.6:
                        # Clean up the answer for better presentation
                        clean_answer = self._clean_knowledge_answer(answer)
                        return clean_answer
                    elif knowledge_data.get('relevant_chunks', 0) == 0:
                        return "I couldn't find specific information about that in our knowledge base. Could you try rephrasing your question?"
                    else:
                        return "I found some information, but I'm not confident it fully answers your question. Could you be more specific?"
            
            return None
        except Exception as e:
            logger.error(f"Error in knowledge template response: {e}")
            return None
    
    def _clean_knowledge_answer(self, answer: str) -> str:
        """Clean up knowledge base answers for better presentation."""
        # Remove redundant "Based on" prefixes if they're too verbose
        if answer.startswith("Based on ") and ":" in answer:
            parts = answer.split(":", 1)
            if len(parts) > 1:
                content_part = parts[1].strip()
                
                # If the content is substantial, use it directly with better formatting
                if len(content_part) > 50:
                    # Clean up the content
                    cleaned = content_part
                    
                    # Add proper spacing after periods if missing
                    import re
                    cleaned = re.sub(r'\.([A-Z])', r'. \1', cleaned)
                    
                    # Break up long sentences for better readability
                    # Look for natural break points
                    if len(cleaned) > 150:
                        # Try to break at logical points
                        sentences = re.split(r'(?<=[.!?])\s+', cleaned)
                        if len(sentences) > 1:
                            # Take first 2-3 sentences for conciseness
                            cleaned = '. '.join(sentences[:2])
                            if not cleaned.endswith('.'):
                                cleaned += '.'
                    
                    # Ensure it ends with proper punctuation
                    if not cleaned.endswith(('.', '!', '?')):
                        cleaned += '.'
                    
                    return cleaned
                else:
                    # Keep source reference for short content
                    source_part = parts[0].replace("Based on ", "According to ")
                    return f"{source_part}: {content_part}"
        
        # General cleanup for any answer
        import re
        answer = re.sub(r'\.([A-Z])', r'. \1', answer)  # Add space after periods
        answer = re.sub(r'\s+', ' ', answer)  # Normalize whitespace
        
        # Break up very long responses
        if len(answer) > 200:
            sentences = re.split(r'(?<=[.!?])\s+', answer)
            if len(sentences) > 1:
                answer = '. '.join(sentences[:2])
        
        if not answer.endswith(('.', '!', '?')):
            answer += '.'
        
        return answer
    
    def _try_template_response(self, ticket_results: List[Dict[str, Any]], query: str) -> Optional[str]:
        """Try to generate a simple template response for ticket queries."""
        try:
            for ticket_data in ticket_results:
                if ticket_data.get('type') == 'specific_ticket' and ticket_data.get('found'):
                    ticket = ticket_data['ticket']
                    ticket_id = ticket.get('id', 'Unknown')
                    status = ticket.get('status', 'Unknown')
                    title = ticket.get('title', '')
                    
                    # Simple template responses
                    if 'status' in query.lower():
                        if status.lower() == 'resolved':
                            return f"Good news! Ticket {ticket_id} has been resolved. {title}"
                        elif status.lower() == 'open':
                            return f"Ticket {ticket_id} is currently open and being worked on. {title}"
                        elif status.lower() == 'pending':
                            return f"Ticket {ticket_id} is pending - we're waiting for some information. {title}"
                        else:
                            return f"Ticket {ticket_id} status is {status}. {title}"
                    
                    elif 'resolution time' in query.lower():
                        resolution_time = ticket.get('resolution_time', 'Not specified')
                        if resolution_time and resolution_time != 'Not specified':
                            return f"Ticket {ticket_id} was resolved in {resolution_time}. {title}"
                        else:
                            return f"The resolution time for ticket {ticket_id} is not specified in our records."
                    
                    elif 'resolution' in query.lower():
                        resolution = ticket.get('resolution', '')
                        if resolution:
                            return f"The resolution for ticket {ticket_id}: {resolution}"
                        else:
                            return f"No resolution details are available for ticket {ticket_id}."
                    
                    return None  # Let LLM handle other types of queries
                
                elif ticket_data.get('type') == 'specific_ticket' and not ticket_data.get('found'):
                    ticket_id = ticket_data.get('ticket_id', 'that ticket')
                    return f"I couldn't find {ticket_id} in our system. Could you double-check the ticket number?"
            
            return None
        except Exception as e:
            logger.error(f"Error in template response: {e}")
            return None
    
    def _prepare_response_data(self, agent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare agent results data for LLM processing."""
        prepared_data = {
            'ticket_results': [],
            'knowledge_results': [],
            'other_results': []
        }
        
        for result in agent_results:
            agent_name = result.get('agent_name', 'unknown')
            data = result.get('data', {})
            
            # Skip supervisor results - we only want actual data
            if agent_name == 'SupervisorAgent':
                continue
                
            if 'TicketAgent' in agent_name:
                prepared_data['ticket_results'].append(data)
            elif 'KnowledgeAgent' in agent_name:
                prepared_data['knowledge_results'].append(data)
            else:
                prepared_data['other_results'].append(data)
        
        return prepared_data
    
    def _create_humanization_prompt(self, 
                                   original_query: str, 
                                   response_data: Dict[str, Any],
                                   context: Optional[Dict[str, Any]] = None) -> str:
        """Create a concise prompt for humanizing the response."""
        
        # Build data summary
        data_summary = ""
        
        # Add ticket results
        if response_data.get('ticket_results'):
            for ticket_data in response_data['ticket_results']:
                if ticket_data.get('type') == 'specific_ticket':
                    if ticket_data.get('found'):
                        ticket = ticket_data['ticket']
                        data_summary += f"Ticket {ticket['id']}: {ticket['title']}, Status: {ticket['status']}, Priority: {ticket['priority']}"
                        if ticket.get('resolution'):
                            data_summary += f", Resolution: {ticket['resolution']}"
                    else:
                        data_summary += f"Ticket {ticket_data.get('ticket_id', 'unknown')} not found"
                elif ticket_data.get('type') == 'search_results':
                    total = ticket_data.get('total_found', 0)
                    data_summary += f"Found {total} tickets"
        
        # Add knowledge results
        if response_data.get('knowledge_results'):
            for knowledge_data in response_data['knowledge_results']:
                if knowledge_data.get('contextual_response'):
                    answer = knowledge_data['contextual_response'].get('answer', '')
                    if answer:
                        # Take first 100 chars of answer
                        data_summary += answer[:100] + "..." if len(answer) > 100 else answer
        
        # Create concise prompt
        prompt = f"""User asked: "{original_query}"
Data: {data_summary}

Give a brief, natural voice response. Be conversational but direct. Max 2 sentences.

Response:"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM to generate a human-like response."""
        try:
            # Prepare the request body
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            # Make the call in a thread pool to avoid blocking
            import asyncio
            import json
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_client.invoke_model(
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",  # Will fallback to Ollama if needed
                    body=json.dumps(body),
                    contentType='application/json'
                )
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Error calling LLM for humanization: {e}")
            raise
    
    def _clean_response(self, response: str) -> str:
        """Clean up the LLM response."""
        # Remove any unwanted prefixes or suffixes
        response = response.strip()
        
        # Remove common LLM artifacts
        prefixes_to_remove = [
            "Response:",
            "Answer:",
            "Here's a natural response:",
            "Natural response:",
        ]
        
        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Ensure the response doesn't end abruptly
        if response and not response.endswith(('.', '!', '?')):
            response += '.'
        
        return response


# Global instance
response_humanizer = ResponseHumanizer()


async def humanize_agent_response(agent_results: List[Dict[str, Any]], 
                                 original_query: str,
                                 context: Optional[Dict[str, Any]] = None) -> str:
    """
    Convenience function to humanize agent responses.
    
    Args:
        agent_results: List of agent result dictionaries
        original_query: The user's original question
        context: Additional context
        
    Returns:
        Human-like conversational response
    """
    return await response_humanizer.humanize_response(agent_results, original_query, context)