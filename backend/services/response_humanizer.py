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
            
            # Check if this is a request for more information about previous response
            if self._is_more_info_request(original_query):
                print(f"🔍 Detected more info request: {original_query}")
                if context and context.get('last_response_data'):
                    print(f"📚 Found stored response data, generating detailed response")
                    return await self._handle_more_info_request(original_query, context['last_response_data'])
                else:
                    print(f"❌ No stored response data available")
                    return "I'd be happy to provide more details. Could you be more specific about what aspect you'd like me to elaborate on?"
            
            # Handle simple greetings
            if self._is_greeting(original_query):
                return self._get_greeting_response()
            
            # Handle thank you messages
            if self._is_thank_you(original_query):
                return self._get_thank_you_response()
            
            # Handle errors
            if self._has_errors(agent_results):
                return self._get_error_response()
            
            # Handle empty results with clarification
            if not agent_results or all(not result.get('data') for result in agent_results):
                return self._get_clarification_response(original_query)
            
            # Generate human-like response using LLM
            return await self._generate_human_response(agent_results, original_query, context)
            
        except Exception as e:
            logger.error(f"Error humanizing response: {e}")
            return "Sorry, I'm having trouble with that. Could you try again?"
    
    def _is_greeting(self, query: str) -> bool:
        """Check if the query is a greeting."""
        import re
        greeting_patterns = [
            r'\bhello\b',
            r'\bhi\b',
            r'\bhey\b',
            r'\bhow are you\b',
            r'\bgood morning\b',
            r'\bgood afternoon\b',
            r'\bgood evening\b'
        ]
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in greeting_patterns)
    
    def _get_greeting_response(self) -> str:
        """Get a friendly greeting response."""
        import random
        return random.choice(self.greeting_responses)
    
    def _is_thank_you(self, query: str) -> bool:
        """Check if the query is a thank you message."""
        import re
        thank_you_patterns = [
            r'\bthank\s+you\b',
            r'\bthanks\b',
            r'\bthank\s+you\s+(?:so\s+)?much\b',
            r'\bappreciate\s+it\b',
            r'\bperfect.*thank\b',
            r'\bgreat.*thank\b',
            r'\bgoodbye\b',
            r'\bsee\s+you\b',
            r'\bhave\s+a\s+good\b'
        ]
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in thank_you_patterns)
    
    def _get_thank_you_response(self) -> str:
        """Get a friendly thank you response."""
        thank_you_responses = [
            "You're very welcome! Happy to help anytime.",
            "My pleasure! Feel free to reach out if you need anything else.",
            "Glad I could help! Have a great day!",
            "You're welcome! I'm here whenever you need assistance.",
            "Happy to help! Take care!"
        ]
        import random
        return random.choice(thank_you_responses)
    
    def _has_errors(self, agent_results: List[Dict[str, Any]]) -> bool:
        """Check if any agent results contain errors."""
        return any(result.get('data', {}).get('error') for result in agent_results)
    
    def _get_error_response(self) -> str:
        """Get a friendly error response."""
        import random
        return random.choice(self.error_responses)
    
    def _is_escalation_request(self, agent_results: List[Dict[str, Any]], query: str) -> bool:
        """Check if this is an escalation request."""
        # Check if supervisor detected escalation intent
        for result in agent_results:
            if result.get('agent_name') == 'SupervisorAgent':
                data = result.get('data', {})
                intent = data.get('intent')
                if intent and hasattr(intent, 'intent_type') and intent.intent_type.value == 'escalation':
                    return True
        
        # Check for explicit escalation requests only
        explicit_escalation_keywords = ['escalate', 'transfer', 'supervisor', 'speak to human', 'talk to person']
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in explicit_escalation_keywords):
            return True
        
        # Don't escalate for follow-up questions or requests for more info
        follow_up_indicators = [
            'another question', 'next question', 'different question', 'new question',
            'more details', 'more information', 'tell me more', 'continue',
            'yes', 'no', 'ok', 'sure', 'please'
        ]
        
        if any(indicator in query_lower for indicator in follow_up_indicators):
            return False  # These are follow-ups, not escalation requests
        
        # Only escalate if ALL non-supervisor agents require escalation AND we have no useful data
        non_supervisor_results = [r for r in agent_results if r.get('agent_name') != 'SupervisorAgent']
        
        if not non_supervisor_results:
            return False
        
        # Check if all agents require escalation AND we have no useful data
        all_require_escalation = all(r.get('requires_escalation', False) for r in non_supervisor_results)
        has_useful_data = any(
            r.get('data', {}).get('type') in ['specific_ticket', 'search_results', 'knowledge_search'] and
            (r.get('data', {}).get('found') or r.get('data', {}).get('relevant_chunks', 0) > 0)
            for r in non_supervisor_results
        )
        
        # Check if this might be a clarification opportunity instead of escalation
        if all_require_escalation and not has_useful_data:
            # Check if query might need clarification (unclear terms, typos, etc.)
            unclear_indicators = [
                len(query.lower().split()) <= 3,  # Very short queries
                any(word in query.lower() for word in ['po', 'sulus', 'ops']),  # Potential typos/unclear terms
                query.lower().strip() in ['no', 'yes', 'ok', 'fine']  # Single word responses
            ]
            
            if any(unclear_indicators):
                return False  # Don't escalate, let it ask for clarification instead
        
        # Only escalate if all agents failed AND we have no useful data AND it's not a clarification case
        return all_require_escalation and not has_useful_data
    
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
    
    def _get_clarification_response(self, query: str) -> str:
        """Get a clarification response instead of immediate escalation."""
        query_lower = query.lower().strip()
        
        # Handle follow-up question requests
        if 'another question' in query_lower or 'different question' in query_lower or 'new question' in query_lower:
            print(f"🔄 Detected follow-up question request: {query}")
            return "Of course! What would you like to know?"
        
        # Handle requests for more information
        if any(phrase in query_lower for phrase in ['more details', 'more information', 'tell me more', 'continue']):
            return "I'd be happy to provide more details. What specific aspect would you like me to elaborate on?"
        
        # Specific clarification for potential typos or unclear terms
        if 'sulus' in query_lower:
            return "I think you might mean SuperOps? Could you clarify what you're asking about?"
        elif 'po' in query_lower and len(query_lower.split()) <= 4:
            return "I'm not sure what 'po' refers to. Did you mean 'probe'? Could you rephrase your question?"
        elif query_lower in ['no', 'yes', 'ok', 'fine']:
            return "I'm not sure what you're referring to. Could you please ask your question again?"
        elif len(query_lower.split()) <= 2:
            return "Could you provide a bit more detail about what you're looking for?"
        else:
            # General clarification responses
            clarification_responses = [
                "I'm not sure I understood that correctly. Could you rephrase your question?",
                "I didn't quite catch that. Could you try asking in a different way?",
                "I'm having trouble understanding what you're looking for. Could you be more specific?",
                "Could you clarify what you're asking about? I want to make sure I help you with the right information.",
                "I'm not sure I followed that. Could you try rephrasing your question?"
            ]
            import random
            return random.choice(clarification_responses)
    
    async def _generate_human_response(self, 
                                     agent_results: List[Dict[str, Any]], 
                                     original_query: str,
                                     context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a human-like response using LLM."""
        try:
            # Prepare the data for the LLM
            response_data = self._prepare_response_data(agent_results)
            
            # FAST PATH: Try template responses first to avoid LLM calls
            if response_data.get('ticket_results'):
                template_response = self._try_template_response(response_data['ticket_results'], original_query)
                if template_response:
                    print(f"📝 Template response: {template_response[:50]}...")
                    return template_response
            
            # FAST PATH: For knowledge queries, try template response first
            if response_data.get('knowledge_results'):
                template_response = await self._try_knowledge_template_response(response_data['knowledge_results'], original_query)
                if template_response:
                    print(f"📚 Knowledge comprehensive response: {template_response[:50]}...")
                    return template_response
            
            # FAST PATH: For simple cases, use direct responses without LLM
            if len(agent_results) == 1 and agent_results[0].get('agent_name') == 'SupervisorAgent':
                intent_data = agent_results[0].get('data', {}).get('intent')
                if intent_data and hasattr(intent_data, 'intent_type'):
                    if intent_data.intent_type.value == 'followup':
                        entities = getattr(intent_data, 'entities', {})
                        followup_type = entities.get('followup_type', '')
                        if followup_type == 'new_question':
                            return "Of course! What would you like to know?"
                        elif followup_type == 'more_details':
                            return "I'd be happy to provide more details. What specific aspect would you like me to elaborate on?"
                    elif intent_data.intent_type.value == 'escalation':
                        return "I understand you'd like to speak with someone else. Let me connect you with a human agent who can help you better."
            
            # Create prompt for humanizing the response
            prompt = self._create_humanization_prompt(original_query, response_data, context)
            
            # Generate response using LLM with timeout
            try:
                response = await asyncio.wait_for(self._call_llm(prompt), timeout=3.0)  # 3 second timeout
            except asyncio.TimeoutError:
                logger.warning("LLM call timed out, using fallback response")
                return self._create_fallback_response(response_data, original_query)
            
            # Clean up the response
            return self._clean_response(response)
            
        except Exception as e:
            logger.error(f"Error generating human response: {e}")
            return "I found some information, but I'm having trouble presenting it clearly. Let me know if you'd like me to try again."
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM client to generate a response."""
        try:
            # Use the existing LLM client with faster settings
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.llm_client.converse(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,  # Even shorter for speed
                    temperature=0.1  # Lower temperature for faster, more deterministic responses
                )
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _clean_response(self, response: str) -> str:
        """Clean up the LLM response."""
        if not response:
            return ""
        
        # Remove any leading/trailing whitespace
        cleaned = response.strip()
        
        # Remove any markdown formatting that might have been added
        import re
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)  # Remove bold
        cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)      # Remove italic
        
        # Ensure proper sentence ending
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
        
        return cleaned
    
    def _is_more_info_request(self, query: str) -> bool:
        """Check if the user is asking for more information about a previous response."""
        more_info_indicators = [
            'more details', 'more information', 'tell me more', 'explain more',
            'continue', 'more steps', 'remaining steps', 'next steps',
            'elaborate', 'expand', 'detailed', 'in detail', 'further',
            'yes please', 'yes', 'continue with', 'go on', 'keep going',
            'give me more', 'show me more', 'additional info'
        ]
        query_lower = query.lower().strip()
        return any(indicator in query_lower for indicator in more_info_indicators)
    
    async def _handle_more_info_request(self, query: str, last_response_data: Dict[str, Any]) -> str:
        """Handle requests for more information about the previous response."""
        try:
            # Get the previous agent results
            previous_agent_results = last_response_data.get('agent_results', [])
            original_query = last_response_data.get('original_query', '')
            
            # Look for knowledge agent results in the previous response
            for agent_result in previous_agent_results:
                if agent_result.get('agent_name') == 'KnowledgeAgent':
                    knowledge_data = agent_result.get('data', {})
                    if knowledge_data.get('type') == 'knowledge_search':
                        # Generate detailed response from the stored knowledge data
                        return await self._generate_detailed_knowledge_response(knowledge_data, original_query)
            
            # If no knowledge data found, provide a helpful response
            return "I'd be happy to provide more details. Could you be more specific about what aspect you'd like me to elaborate on?"
            
        except Exception as e:
            logger.error(f"Error handling more info request: {e}")
            return "I'd be happy to provide more details, but I'm having trouble accessing the previous information. Could you ask your question again?"

    async def _generate_detailed_knowledge_response(self, knowledge_data: Dict[str, Any], query: str) -> str:
        """Generate a detailed response when user asks for more information."""
        try:
            contextual_response = knowledge_data.get('contextual_response', {})
            answer = contextual_response.get('answer', '')
            knowledge_chunks = knowledge_data.get('knowledge_chunks', [])
            
            if not answer:
                return "I don't have additional details available. Could you ask a more specific question?"
            
            # Create a detailed response using LLM
            prompt = f"""The user asked for more details about this topic. Provide a comprehensive but well-structured response.

Original information:
{answer}

Additional context from knowledge base:
{chr(10).join([chunk.get('text', '')[:200] + '...' for chunk in knowledge_chunks[:3]])}

Instructions:
1. Provide detailed information in a clear, organized way
2. Use bullet points or numbered lists when appropriate
3. Break information into digestible sections
4. Be thorough but not overwhelming
5. Keep it conversational and helpful

Detailed response:"""

            detailed_response = await self._call_llm(prompt)
            return self._clean_response(detailed_response)
            
        except Exception as e:
            logger.error(f"Error generating detailed response: {e}")
            # Fallback to showing more of the original answer
            contextual_response = knowledge_data.get('contextual_response', {})
            answer = contextual_response.get('answer', '')
            return answer if answer else "I don't have additional details available right now."
    
    async def _try_knowledge_template_response(self, knowledge_results: List[Dict[str, Any]], query: str) -> Optional[str]:
        """Generate concise knowledge response with follow-up offers."""
        try:
            for knowledge_data in knowledge_results:
                if knowledge_data.get('type') == 'knowledge_search':
                    relevant_chunks = knowledge_data.get('relevant_chunks', 0)
                    confidence = knowledge_data.get('contextual_response', {}).get('confidence', 0.0)
                    
                    # If we have relevant chunks, generate concise response
                    if relevant_chunks > 0 and confidence > 0.3:
                        return await self._generate_concise_knowledge_response(knowledge_data, query)
                    elif relevant_chunks == 0:
                        return "I couldn't find specific information about that in our knowledge base. Could you try rephrasing your question?"
                    else:
                        return "I found some information, but I'm not confident it fully answers your question. Could you be more specific?"
            
            return None
        except Exception as e:
            logger.error(f"Error in knowledge template response: {e}")
            return None
    
    async def _generate_concise_knowledge_response(self, knowledge_data: Dict[str, Any], query: str) -> str:
        """Generate a concise knowledge response with follow-up offers."""
        try:
            # Check if this is a follow-up request for more information
            if self._is_more_info_request(query):
                return await self._generate_detailed_knowledge_response(knowledge_data, query)
            
            # Get the contextual response
            contextual_response = knowledge_data.get('contextual_response', {})
            answer = contextual_response.get('answer', '')
            knowledge_chunks = knowledge_data.get('knowledge_chunks', [])
            
            if not answer or not knowledge_chunks:
                return "I found some information but couldn't extract the key details. Could you be more specific?"
            
            # FAST PATH: Try to create response without LLM for common patterns
            query_lower = query.lower()
            
            # For "what is" questions
            if query_lower.startswith('what is'):
                topic = query_lower.replace('what is', '').replace('a ', '').replace('an ', '').strip()
                if 'probe' in topic:
                    return "A probe scans devices in your network for monitoring. Would you like more details?"
                elif 'subnet' in topic:
                    return "A subnet is a network segment for organizing devices. Would you like more details?"
            
            # For "how do i" or "how to" questions
            elif any(phrase in query_lower for phrase in ['how do i', 'how to', 'steps to']):
                if 'probe' in query_lower and 'add' in query_lower:
                    return "Go to Modules → Network Monitor → Probes and click +Probe. Would you like more details?"
                elif 'subnet' in query_lower and any(word in query_lower for word in ['add', 'create', 'manual']):
                    return "Go to Modules → Network Monitor → Network Scans, click Add Subnet manually. Would you like more details?"
            
            # Check if this is a step-by-step query
            is_step_query = self._detect_step_by_step_query(query)
            
            if is_step_query:
                # Handle step-by-step queries specially
                steps = self._extract_steps_from_content(answer)
                if len(steps) > 3:
                    # Show first 3 steps and offer to continue
                    step_response = "Here are the first 3 steps:\n\n"
                    for i, step in enumerate(steps[:3], 1):
                        clean_step = step.strip()
                        if not clean_step.startswith(str(i)):
                            step_response += f"{i}. {clean_step}\n"
                        else:
                            step_response += f"{clean_step}\n"
                    
                    step_response += f"\nThere are {len(steps) - 3} more steps. Would you like me to continue with the remaining steps?"
                    return step_response
                elif steps:
                    # Show all steps if 3 or fewer
                    step_response = "Here are the steps:\n\n"
                    for i, step in enumerate(steps, 1):
                        clean_step = step.strip()
                        if not clean_step.startswith(str(i)):
                            step_response += f"{i}. {clean_step}\n"
                        else:
                            step_response += f"{clean_step}\n"
                    return step_response.strip()
            
            # Fallback to simple response without LLM
            return self._create_fallback_concise_response(knowledge_data, query)
            
        except Exception as e:
            logger.error(f"Error generating concise knowledge response: {e}")
            # Fallback to simple response
            return self._create_fallback_concise_response(knowledge_data, query)
    
    def _create_fallback_response(self, response_data: Dict[str, Any], query: str) -> str:
        """Create a fast fallback response when LLM times out."""
        # Check for ticket results
        if response_data.get('ticket_results'):
            return "I found some ticket information. Could you be more specific about what you need?"
        
        # Check for knowledge results
        if response_data.get('knowledge_results'):
            return "I found some information about that. Would you like me to provide more details?"
        
        # Generic fallback
        return "I'm processing your request. Could you rephrase your question?"

    def _create_fallback_concise_response(self, knowledge_data: Dict[str, Any], query: str) -> str:
        """Create a fallback concise response when LLM fails."""
        try:
            contextual_response = knowledge_data.get('contextual_response', {})
            answer = contextual_response.get('answer', '')
            
            if not answer:
                return "I found some information about that. Would you like me to provide more details?"
            
            # Extract first sentence or key information
            import re
            sentences = re.split(r'[.!?]+', answer)
            first_sentence = sentences[0].strip() if sentences else answer
            
            # Clean up "Based on" prefixes
            if first_sentence.startswith("Based on "):
                colon_pos = first_sentence.find(":")
                if colon_pos > 0:
                    first_sentence = first_sentence[colon_pos + 1:].strip()
            
            # Ensure it's not too long
            if len(first_sentence) > 100:
                first_sentence = first_sentence[:97] + "..."
            
            # Add follow-up offer
            if not first_sentence.endswith('.'):
                first_sentence += '.'
            
            return f"{first_sentence} Would you like more details?"
            
        except Exception as e:
            logger.error(f"Error creating fallback response: {e}")
            return "I found information about that topic. Would you like me to provide more details?"
    
    def _detect_step_by_step_query(self, query: str) -> bool:
        """Detect if the user is asking for step-by-step information."""
        step_indicators = [
            'step by step', 'steps', 'how to', 'guide', 'tutorial', 
            'process', 'procedure', 'instructions', 'walkthrough'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in step_indicators)
    
    def _extract_steps_from_content(self, content: str) -> List[str]:
        """Extract steps from content if it contains step-by-step information."""
        import re
        
        # Look for numbered steps
        step_patterns = [
            r'(\d+\.\s+[^.]+\.)',  # "1. Step description."
            r'(Step\s+\d+[:\s]+[^.]+\.)',  # "Step 1: Description."
            r'(\d+\)\s+[^.]+\.)',  # "1) Step description."
        ]
        
        steps = []
        for pattern in step_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                steps.extend(matches)
                break  # Use first pattern that matches
        
        # If no numbered steps, look for bullet points or line breaks
        if not steps:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                    steps.append(line)
        
        return steps[:10]  # Limit to 10 steps max
    
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
    
    async def _generate_comprehensive_knowledge_response(self, knowledge_data: Dict[str, Any], query: str) -> str:
        """Generate comprehensive knowledge response using Bedrock with all relevant data."""
        try:
            # Extract all knowledge chunks
            knowledge_chunks = knowledge_data.get('knowledge_chunks', [])
            contextual_response = knowledge_data.get('contextual_response', {})
            
            if not knowledge_chunks:
                return contextual_response.get('answer', 'I found some information but cannot present it clearly.')
            
            # Prepare comprehensive data for Bedrock
            all_content = []
            sources = set()
            
            for chunk in knowledge_chunks:
                chunk_text = chunk.get('text', '')
                source = chunk.get('source', 'unknown')
                page_num = chunk.get('page_number')
                
                if chunk_text:
                    all_content.append(chunk_text)
                    if page_num:
                        sources.add(f"{source} (page {page_num})")
                    else:
                        sources.add(source)
            
            # Combine all content
            combined_content = "\n\n".join(all_content)
            sources_list = list(sources)
            
            # Determine response type based on query
            response_type = self._determine_response_type(query)
            
            # Create comprehensive prompt for Bedrock
            prompt = self._create_knowledge_synthesis_prompt(query, combined_content, sources_list, response_type)
            
            # Generate response using LLM
            response = await self._call_llm_for_knowledge(prompt)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating comprehensive knowledge response: {e}")
            # Fallback to basic contextual response
            return knowledge_data.get('contextual_response', {}).get('answer', 'I found some information but had trouble processing it.')
    
    def _determine_response_type(self, query: str) -> str:
        """Determine what type of response is needed based on the query."""
        query_lower = query.lower()
        
        # Step-by-step instructions
        if any(phrase in query_lower for phrase in ['how to', 'how do i', 'steps', 'install', 'configure', 'setup', 'create']):
            return "step_by_step"
        
        # Concept explanation
        elif any(phrase in query_lower for phrase in ['what is', 'what are', 'explain', 'define', 'meaning']):
            return "concept_explanation"
        
        # Comparison or features
        elif any(phrase in query_lower for phrase in ['difference', 'compare', 'vs', 'versus', 'features', 'capabilities']):
            return "comparison"
        
        # Troubleshooting
        elif any(phrase in query_lower for phrase in ['problem', 'issue', 'error', 'not working', 'fix', 'troubleshoot']):
            return "troubleshooting"
        
        # General information
        else:
            return "general_info"
    
    def _create_knowledge_synthesis_prompt(self, query: str, content: str, sources: List[str], response_type: str) -> str:
        """Create a comprehensive prompt for knowledge synthesis."""
        
        # Base instruction based on response type
        if response_type == "step_by_step":
            instruction = """Provide clear, numbered step-by-step instructions. Be specific and actionable. Include any prerequisites or important notes."""
        elif response_type == "concept_explanation":
            instruction = """Provide a clear, concise explanation of the concept. Start with a simple definition, then add relevant details. Make it easy to understand."""
        elif response_type == "comparison":
            instruction = """Provide a clear comparison highlighting key differences, similarities, and use cases. Use bullet points if helpful."""
        elif response_type == "troubleshooting":
            instruction = """Provide troubleshooting guidance with potential causes and solutions. Be systematic and helpful."""
        else:
            instruction = """Provide comprehensive, well-organized information that directly answers the question. Be thorough but concise."""
        
        return f"""You are an IT support assistant. Based on the documentation provided, answer the user's question comprehensively.

User Question: "{query}"

Available Documentation:
{content}

Sources: {', '.join(sources)}

Instructions: {instruction}

Requirements:
- Answer directly and completely based on the documentation
- Be conversational and human-like, not robotic
- Use natural language appropriate for voice interaction
- If the documentation contains step-by-step information, present it clearly
- Include relevant details but keep it focused
- Don't mention "based on the documentation" - just provide the answer naturally

Response:"""
    
    async def _call_llm_for_knowledge(self, prompt: str) -> str:
        """Call LLM specifically for knowledge synthesis."""
        try:
            # Use faster settings for knowledge synthesis
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.llm_client.converse(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,  # Reduced for speed
                    temperature=0.3   # Lower temperature for speed
                )
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error calling LLM for knowledge synthesis: {e}")
            raise
    
    def _try_template_response(self, ticket_results: List[Dict[str, Any]], query: str) -> Optional[str]:
        """Try to generate a simple template response for ticket queries."""
        try:
            for ticket_data in ticket_results:
                if ticket_data.get('type') == 'specific_ticket' and ticket_data.get('found'):
                    ticket = ticket_data['ticket']
                    ticket_id = ticket.get('id', 'Unknown')
                    status = ticket.get('status', 'Unknown')
                    title = ticket.get('title', '')
                    
                    # Multi-part template responses - check for multiple questions
                    response_parts = []
                    
                    # Check for status
                    if 'status' in query.lower():
                        if status.lower() == 'resolved':
                            response_parts.append(f"Ticket {ticket_id} has been resolved")
                        elif status.lower() == 'open':
                            response_parts.append(f"Ticket {ticket_id} is currently open and being worked on")
                        elif status.lower() == 'pending':
                            response_parts.append(f"Ticket {ticket_id} is pending")
                        else:
                            response_parts.append(f"Ticket {ticket_id} status is {status}")
                    
                    # Check for resolution time
                    if 'resolution time' in query.lower():
                        resolution_time = ticket.get('resolution_time', 'Not specified')
                        if resolution_time and resolution_time != 'Not specified':
                            formatted_time = self._format_resolution_time(resolution_time)
                            response_parts.append(f"it was resolved in {formatted_time}")
                        else:
                            response_parts.append("resolution time is not specified")
                    
                    # Check for category
                    if 'category' in query.lower():
                        category = ticket.get('category', 'Not specified')
                        response_parts.append(f"it's categorized under {category}")
                    
                    # Check for team assignment
                    if 'team' in query.lower() or 'assigned' in query.lower():
                        assigned_team = ticket.get('assigned_team', 'Not specified')
                        response_parts.append(f"it's assigned to the {assigned_team} team")
                    
                    # Check for priority
                    if 'priority' in query.lower():
                        priority = ticket.get('priority', 'Not specified')
                        if priority and priority != 'Not specified':
                            response_parts.append(f"it has {priority.lower()} priority")
                        else:
                            response_parts.append("priority is not specified")
                    
                    # Check for resolution details
                    if 'resolution' in query.lower() and 'resolution time' not in query.lower():
                        resolution = ticket.get('resolution', '')
                        if resolution:
                            response_parts.append(f"resolution: {resolution}")
                        else:
                            response_parts.append("no resolution details available")
                    
                    # Combine response parts
                    if response_parts:
                        if len(response_parts) == 1:
                            return f"{response_parts[0]}. {title}"
                        else:
                            # Join multiple parts naturally
                            combined = response_parts[0]
                            for i, part in enumerate(response_parts[1:], 1):
                                if i == len(response_parts) - 1:
                                    combined += f", and {part}"
                                else:
                                    combined += f", {part}"
                            return f"{combined}. {title}"
                    
                    # Check if asking for full ticket details (no specific field mentioned)
                    query_lower = query.lower()
                    specific_fields = ['status', 'priority', 'category', 'team', 'assigned', 'resolution time', 'resolution']
                    is_asking_specific_field = any(field in query_lower for field in specific_fields)
                    
                    if not is_asking_specific_field and ('details' in query_lower or 'about' in query_lower or 'information' in query_lower):
                        # Generate concise full ticket details without markdown
                        parts = []
                        parts.append(f"Ticket {ticket_id}")
                        
                        if title:
                            parts.append(f"regarding {title}")
                        
                        if status:
                            parts.append(f"Status is {status}")
                        
                        if ticket.get('priority'):
                            parts.append(f"Priority is {ticket['priority']}")
                        
                        if ticket.get('category'):
                            parts.append(f"Category is {ticket['category']}")
                        
                        if ticket.get('assigned_team'):
                            parts.append(f"Assigned to {ticket['assigned_team']} team")
                        
                        if ticket.get('resolution'):
                            resolution = ticket['resolution']
                            # Keep resolution concise
                            if len(resolution) > 100:
                                resolution = resolution[:97] + "..."
                            parts.append(f"Resolution: {resolution}")
                        
                        # Join parts naturally
                        if len(parts) <= 2:
                            return ". ".join(parts) + "."
                        else:
                            result = parts[0]
                            for i, part in enumerate(parts[1:], 1):
                                if i == len(parts) - 1:
                                    result += f". {part}"
                                else:
                                    result += f". {part}"
                            return result + "."
                    
                    return None  # Let LLM handle other types of queries
                
                elif ticket_data.get('type') == 'specific_ticket' and not ticket_data.get('found'):
                    ticket_id = ticket_data.get('ticket_id', 'that ticket')
                    return f"I couldn't find {ticket_id} in our system. Could you double-check the ticket number?"
                
                elif ticket_data.get('type') == 'search_results':
                    tickets = ticket_data.get('combined_results', [])  # Use combined_results instead of tickets
                    total = len(tickets)

                    
                    if total == 0:
                        criteria = ticket_data.get('criteria', {})
                        category = criteria.get('category')
                        if category:
                            return f"I couldn't find any tickets in the {category} category."
                        else:
                            return "I couldn't find any tickets matching your criteria."
                    
                    elif total <= 5:
                        # List specific tickets
                        ticket_list = []
                        for ticket in tickets:
                            ticket_list.append(f"{ticket.get('id')}: {ticket.get('title')}")
                        
                        return f"Here are the matching tickets: " + ", ".join(ticket_list)
                    
                    else:
                        # Too many to list individually - show first 5
                        ticket_list = []
                        for ticket in tickets[:5]:  # Show first 5
                            ticket_list.append(f"{ticket.get('id')}: {ticket.get('title')}")
                        
                        return f"I found {total} tickets. Here are the first 5: " + ", ".join(ticket_list)
            
            return None
        
        except Exception as e:
            logger.error(f"Error in template response: {e}")
            return None
    
    def _format_resolution_time(self, resolution_time: str) -> str:
        """Format resolution time for TTS to avoid confusion with meters."""
        if not resolution_time:
            return resolution_time
        
        # Convert common abbreviations to full words for TTS
        formatted = resolution_time.lower()
        formatted = formatted.replace('m', ' minutes')
        formatted = formatted.replace('h', ' hours')
        formatted = formatted.replace('d', ' days')
        formatted = formatted.replace('w', ' weeks')
        
        # Clean up multiple spaces
        import re
        formatted = re.sub(r'\s+', ' ', formatted).strip()
        
        return formatted
    
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
        
        # Build conversation context
        conversation_context = ""
        if context and context.get('session_id'):
            conversation_context = "Previous conversation context available."
        
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
                    combined_results = ticket_data.get('combined_results', [])
                    if combined_results:
                        ticket_list = []
                        for ticket in combined_results[:3]:  # Show first 3 in summary
                            ticket_list.append(f"{ticket.get('id')}: {ticket.get('title')}")
                        data_summary += f"Found {total} tickets including: " + ", ".join(ticket_list)
                    else:
                        data_summary += f"Found {total} tickets"
        
        # Add knowledge results
        if response_data.get('knowledge_results'):
            for knowledge_data in response_data['knowledge_results']:
                if knowledge_data.get('contextual_response'):
                    answer = knowledge_data['contextual_response'].get('answer', '')
                    if answer:
                        # Take first 100 chars of answer
                        data_summary += answer[:100] + "..." if len(answer) > 100 else answer
        
        # Create concise prompt - system context is handled by LLM client
        prompt = f"""User asked: "{original_query}"
Available data: {data_summary}

{conversation_context}

Provide a natural, conversational response as an IT support assistant. Be helpful and human-like, not robotic. Keep it concise but complete."""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM to generate a human-like response."""
        try:
            # Use faster settings for speed
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 100,  # Reduced for speed
                "temperature": 0.2  # Lower temperature for speed
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