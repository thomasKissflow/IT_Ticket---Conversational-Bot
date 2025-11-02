"""
ConversationManager for natural interactions with varied greetings, thinking phrases,
and context-aware response formatting.
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from agents.base_agent import ConversationContext, Message
from llm_client import get_llm_client


class ConversationManager:
    """
    Manages natural conversation flow with human-like responses, greetings,
    thinking sounds, and context-aware formatting.
    """
    
    def __init__(self, aws_region: str = "us-east-2"):
        self.aws_region = aws_region
        self.llm_client = get_llm_client(aws_region)
        
        # Predefined greeting messages for variety
        self.greeting_messages = [
            "Hello! I'm your IT assistant. How can I help you today?",
            "Hi there! I'm here to help with your support questions. What can I do for you?",
            "Good to hear from you! I can help you with tickets and product information. What do you need?",
            "Hello! I'm ready to assist you with any questions you have. How can I help?",
            "Hi! I'm your AI assistant for support and knowledge queries. What would you like to know?",
            "Welcome! I'm here to help you find information and resolve issues. What can I assist you with?",
        ]
        
        # Thinking phrases for processing delays
        self.thinking_phrases = [
            "Let me check that for you",
            "One moment while I look that up", 
            "Let me see what I can find",
            "Give me just a second to search for that",
            "Let me pull up that information",
            "Hmm, let me find that for you",
            "Let me search through the data",
            "One moment, checking our records",
            "Let me look into that",
            "Give me a moment to process that",
        ]
        
        # Natural breathing/thinking sounds
        self.thinking_sounds = [
            "hmm",
            "let me see", 
            "one moment",
            "just a second",
            "hold on",
            "let me think",
            "give me a moment",
            "um, let me check",
            "okay, let me look",
            "alright, checking"
        ]
        
        # Acknowledgment phrases for interruptions
        self.interruption_acknowledgments = [
            "Oh, you have another question?",
            "Yes, what else can I help with?",
            "Sure, what did you want to ask?",
            "Of course, go ahead",
            "What else would you like to know?",
            "Yes, I'm listening",
        ]
        
        # Conversation transition phrases
        self.transition_phrases = [
            "Actually, let me also check",
            "Additionally, I found",
            "Here's something else that might help",
            "I also noticed",
            "Let me add to that",
            "Another thing to mention",
        ]
        
        # Response introduction phrases
        self.response_intros = [
            "Here's what I found",
            "Based on the information I have",
            "According to our records",
            "I found this information",
            "Here's what I can tell you",
            "From what I can see",
        ]
        
        # Uncertainty expressions
        self.uncertainty_phrases = [
            "I'm not completely sure, but",
            "From what I can tell",
            "It appears that",
            "Based on available information",
            "I believe",
            "It seems like",
        ]
        
        # Closing phrases
        self.closing_phrases = [
            "Is there anything else I can help you with?",
            "Do you have any other questions?",
            "What else can I assist you with today?",
            "Is there anything else you'd like to know?",
            "Can I help you with anything else?",
            "Any other questions for me?",
        ]
    

    
    async def generate_greeting(self, context: Optional[ConversationContext] = None) -> str:
        """
        Generate a varied welcome message based on context.
        
        Args:
            context: Optional conversation context for personalized greetings
            
        Returns:
            A natural greeting message
        """
        # Check if this is a returning user
        if context and context.conversation_history:
            # Check if last interaction was recent (within same session)
            last_message = context.conversation_history[-1]
            time_since_last = datetime.now() - last_message.timestamp
            
            if time_since_last.total_seconds() < 300:  # 5 minutes
                return random.choice([
                    "Welcome back! What else can I help you with?",
                    "Hi again! How can I assist you further?",
                    "Good to hear from you again. What do you need?",
                ])
        
        # Time-based greetings
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            time_greetings = [
                "Good morning! I'm your voice assistant. How can I help you today?",
                "Morning! I'm here to help with your support questions. What can I do for you?",
            ]
            return random.choice(time_greetings + self.greeting_messages)
        elif 12 <= current_hour < 17:
            time_greetings = [
                "Good afternoon! I'm ready to assist you. What can I help with?",
                "Afternoon! I'm here for any questions you have. How can I help?",
            ]
            return random.choice(time_greetings + self.greeting_messages)
        elif 17 <= current_hour < 22:
            time_greetings = [
                "Good evening! I'm your AI assistant. What can I help you with?",
                "Evening! I'm here to help with any questions. What do you need?",
            ]
            return random.choice(time_greetings + self.greeting_messages)
        
        # Default to random greeting
        return random.choice(self.greeting_messages)
    
    async def get_thinking_phrase(self) -> str:
        """
        Get a random thinking phrase for processing delays.
        
        Returns:
            A natural thinking phrase
        """
        return random.choice(self.thinking_phrases)
    
    async def get_thinking_sound(self) -> str:
        """
        Get a random thinking sound for natural pauses.
        
        Returns:
            A natural thinking sound
        """
        return random.choice(self.thinking_sounds)
    
    async def format_response(self, data: Any, context: ConversationContext, 
                            confidence: float = 1.0, agent_name: str = "") -> str:
        """
        Format agent data into a natural, conversational response.
        
        Args:
            data: The data to format (from agent results)
            context: Current conversation context
            confidence: Confidence score for the response
            agent_name: Name of the agent that provided the data
            
        Returns:
            A naturally formatted response string
        """
        try:
            # Build conversation context for better response formatting
            conversation_summary = self._build_conversation_summary(context)
            
            # Determine response style based on confidence
            intro_phrase = self._get_response_intro(confidence)
            
            # Create formatting prompt
            prompt = self._create_response_formatting_prompt(
                data, conversation_summary, intro_phrase, confidence, agent_name
            )
            
            # Generate natural response
            response = await self._call_bedrock(prompt)
            
            # Add natural conversation elements
            formatted_response = self._add_conversation_elements(response, confidence, context)
            
            return formatted_response.strip()
            
        except Exception as e:
            print(f"Failed to format response: {e}")
            # Fallback to simple formatting
            return self._fallback_response_formatting(data, confidence)
    
    def _build_conversation_summary(self, context: ConversationContext) -> str:
        """Build a summary of recent conversation for context."""
        if not context.conversation_history:
            return "This is the start of the conversation."
        
        # Get last 2-3 exchanges for context
        recent_messages = context.conversation_history[-4:]  # Last 2 exchanges
        summary_lines = []
        
        for msg in recent_messages:
            summary_lines.append(f"{msg.speaker}: {msg.content[:100]}...")
        
        return "\n".join(summary_lines)
    
    def _get_response_intro(self, confidence: float) -> str:
        """Get appropriate response introduction based on confidence."""
        if confidence < 0.6:
            return random.choice(self.uncertainty_phrases)
        elif confidence < 0.8:
            return random.choice([
                "From what I can see",
                "Based on the information I have",
                "According to our records",
            ])
        else:
            return random.choice(self.response_intros)
    
    def _create_response_formatting_prompt(self, data: Any, conversation_summary: str,
                                         intro_phrase: str, confidence: float, agent_name: str) -> str:
        """Create prompt for natural response formatting."""
        return f"""Convert the following data into a natural, conversational response for voice interaction.

Recent Conversation Context:
{conversation_summary}

Agent Data to Format:
{json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)}

Response Guidelines:
- Start with: "{intro_phrase}"
- Sound natural and human-like, not robotic
- Be conversational and friendly
- Keep it concise but informative
- Confidence level: {confidence:.2f} (adjust certainty accordingly)
- Source: {agent_name}

If confidence is low (< 0.6), express appropriate uncertainty.
If data contains errors, acknowledge limitations gracefully.

Provide just the natural response, no extra formatting."""
    
    async def _call_bedrock(self, prompt: str) -> str:
        """Make async call to LLM client for response generation."""
        try:
            # Use the converse method for better compatibility
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_client.converse(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.6
                )
            )
            
            return response
            
        except Exception as e:
            print(f"LLM call failed in ConversationManager: {e}")
            raise
    
    def _add_conversation_elements(self, response: str, confidence: float, 
                                 context: ConversationContext) -> str:
        """Add natural conversation elements to the response."""
        # Add natural pauses and emphasis markers for TTS
        response = response.replace(". ", "... ")
        response = response.replace("? ", "?... ")
        response = response.replace("! ", "!... ")
        
        # Add closing phrase if this seems like a complete response
        if confidence > 0.7 and len(response) > 50:
            if not any(phrase in response.lower() for phrase in ["anything else", "other questions"]):
                closing = random.choice(self.closing_phrases)
                response += f" {closing}"
        
        return response
    
    def _fallback_response_formatting(self, data: Any, confidence: float) -> str:
        """Fallback response formatting when Bedrock is unavailable."""
        intro = self._get_response_intro(confidence)
        
        if isinstance(data, dict):
            if "error" in data:
                return f"I'm sorry, I encountered an issue: {data['error']}"
            elif "content" in data:
                return f"{intro}, {data['content']}"
            else:
                return f"{intro}, I found some information but I'm having trouble presenting it clearly."
        elif isinstance(data, str):
            return f"{intro}, {data}"
        else:
            return f"{intro}, I found some information for you."
    
    async def handle_interruption(self, new_query: str, context: ConversationContext) -> str:
        """
        Handle user interruptions gracefully with natural acknowledgments.
        
        Args:
            new_query: The new query from the user
            context: Current conversation context
            
        Returns:
            An acknowledgment phrase for the interruption
        """
        # Add the interruption to context
        context.add_message(new_query, "user")
        
        # Choose appropriate acknowledgment
        acknowledgment = random.choice(self.interruption_acknowledgments)
        
        return acknowledgment
    
    async def generate_transition_phrase(self, context: ConversationContext) -> str:
        """
        Generate a natural transition phrase for continuing conversation.
        
        Args:
            context: Current conversation context
            
        Returns:
            A natural transition phrase
        """
        return random.choice(self.transition_phrases)
    
    async def express_uncertainty(self, topic: str) -> str:
        """
        Express uncertainty about a topic naturally.
        
        Args:
            topic: The topic being discussed
            
        Returns:
            A natural uncertainty expression
        """
        uncertainty = random.choice(self.uncertainty_phrases)
        return f"{uncertainty} I don't have complete information about {topic}."
    
    async def generate_followup_question(self, context: ConversationContext) -> Optional[str]:
        """
        Generate a natural follow-up question based on conversation context.
        
        Args:
            context: Current conversation context
            
        Returns:
            A follow-up question or None if not appropriate
        """
        if not context.conversation_history:
            return None
        
        # Analyze recent conversation to suggest relevant follow-ups
        recent_topics = []
        for msg in context.conversation_history[-3:]:
            if msg.speaker == "user":
                # Simple keyword extraction for follow-up suggestions
                if "ticket" in msg.content.lower():
                    recent_topics.append("ticket")
                elif any(word in msg.content.lower() for word in ["product", "feature", "how"]):
                    recent_topics.append("product")
        
        if "ticket" in recent_topics:
            return "Would you like me to check for any related tickets or updates?"
        elif "product" in recent_topics:
            return "Do you need more information about any specific features?"
        
        return None
    
    def create_session_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationContext:
        """
        Create a new conversation context for a session.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            
        Returns:
            A new ConversationContext instance
        """
        return ConversationContext(
            session_id=session_id,
            user_id=user_id,
            conversation_history=[],
            current_topic=None,
            last_agent_used=None,
            confidence_scores=[]
        )
    
    async def health_check(self) -> bool:
        """Check if the ConversationManager is healthy and ready."""
        try:
            return self.llm_client.health_check()
        except Exception as e:
            print(f"ConversationManager health check failed: {e}")
            return False