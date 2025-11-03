"""
Base agent classes and data structures for the STRAND-based agent system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class AgentType(Enum):
    SUPERVISOR = "supervisor"
    TICKET = "ticket"
    KNOWLEDGE = "knowledge"


class IntentType(Enum):
    TICKET_QUERY = "ticket_query"
    KNOWLEDGE_QUERY = "knowledge_query"
    MIXED_QUERY = "mixed_query"
    GREETING = "greeting"
    ESCALATION = "escalation"
    FOLLOWUP = "followup"
    UNKNOWN = "unknown"


@dataclass
class Message:
    content: str
    timestamp: datetime
    speaker: str  # "user" or "assistant"
    confidence: Optional[float] = None


@dataclass
class ConversationContext:
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Message] = field(default_factory=list)
    current_topic: Optional[str] = None
    last_agent_used: Optional[str] = None
    confidence_scores: List[float] = field(default_factory=list)
    last_response_data: Optional[Dict[str, Any]] = None  # Store last response data for follow-ups
    
    def add_message(self, content: str, speaker: str, confidence: Optional[float] = None):
        """Add a message to the conversation history."""
        message = Message(
            content=content,
            timestamp=datetime.now(),
            speaker=speaker,
            confidence=confidence
        )
        self.conversation_history.append(message)
        
        if confidence is not None:
            self.confidence_scores.append(confidence)
    
    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """Get the most recent messages from the conversation."""
        return self.conversation_history[-count:] if self.conversation_history else []
    
    def get_user_messages(self) -> List[Message]:
        """Get all messages from the user."""
        return [msg for msg in self.conversation_history if msg.speaker == "user"]
    
    def get_assistant_messages(self) -> List[Message]:
        """Get all messages from the assistant."""
        return [msg for msg in self.conversation_history if msg.speaker == "assistant"]
    
    def get_average_confidence(self) -> float:
        """Get the average confidence score for the conversation."""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)
    
    def get_conversation_duration(self) -> Optional[float]:
        """Get the duration of the conversation in minutes."""
        if len(self.conversation_history) < 2:
            return None
        
        start_time = self.conversation_history[0].timestamp
        end_time = self.conversation_history[-1].timestamp
        duration = end_time - start_time
        return duration.total_seconds() / 60.0
    
    def has_low_confidence_pattern(self, threshold: float = 0.6, window: int = 3) -> bool:
        """Check if there's a pattern of low confidence scores."""
        if len(self.confidence_scores) < window:
            return False
        
        recent_scores = self.confidence_scores[-window:]
        return all(score < threshold for score in recent_scores)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation context."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "message_count": len(self.conversation_history),
            "current_topic": self.current_topic,
            "last_agent_used": self.last_agent_used,
            "average_confidence": self.get_average_confidence(),
            "conversation_duration_minutes": self.get_conversation_duration(),
            "has_low_confidence_pattern": self.has_low_confidence_pattern()
        }


@dataclass
class Intent:
    intent_type: IntentType
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None


@dataclass
class AgentTask:
    agent_type: AgentType
    query: str
    context: ConversationContext
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_name: str
    data: Any
    confidence: float
    processing_time: float
    requires_escalation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    content: str
    confidence: float
    requires_escalation: bool
    agent_results: List[AgentResult] = field(default_factory=list)
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
    
    @abstractmethod
    async def process_query(self, query: str, context: ConversationContext) -> AgentResult:
        """Process a query and return results."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the agent is healthy and ready to process queries."""
        pass