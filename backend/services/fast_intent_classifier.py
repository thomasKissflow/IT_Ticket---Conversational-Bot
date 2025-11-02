"""
Fast Intent Classifier
Rule-based intent classification for common queries to avoid slow LLM calls.
Falls back to LLM only for complex/ambiguous cases.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from agents.base_agent import Intent, IntentType

logger = logging.getLogger(__name__)


class FastIntentClassifier:
    """Fast rule-based intent classifier with LLM fallback."""
    
    def __init__(self):
        # Ticket-related patterns
        self.ticket_patterns = [
            # Direct ticket ID references
            (r'\b(?:ticket|id)\s*(?:id\s*)?(?:#\s*)?([a-zA-Z0-9\-_]+)', 'ticket_id'),
            (r'\b(?:it-\d+|#\d+|\d{3,})\b', 'ticket_id'),
            
            # Ticket status queries
            (r'\b(?:status|state)\s+(?:of|for)?\s*(?:my\s+)?(?:ticket|id)', 'status'),
            (r'\b(?:what|how)\s+(?:is\s+)?(?:the\s+)?status', 'status'),
            
            # Ticket information queries
            (r'\b(?:description|details|info|information)\s+(?:of|for|about)', 'description'),
            (r'\b(?:resolution|solution|fix)\s+(?:of|for|to)', 'resolution'),
            (r'\b(?:show|get|find|lookup)\s+(?:me\s+)?(?:ticket|id)', 'lookup'),
            
            # Team assignment queries
            (r'\b(?:who|which\s+team)\s+(?:was\s+)?(?:it\s+)?(?:assigned\s+to)', 'team_assignment'),
            (r'\b(?:assigned\s+to|assigned\s+team)', 'team_assignment'),
            (r'\b(?:resolution\s+time|how\s+long)', 'resolution_time'),
            
            # General ticket queries
            (r'\b(?:my\s+)?(?:tickets?|issues?|problems?)', 'general_ticket'),
            (r'\b(?:open|closed|pending|resolved)\s+tickets?', 'ticket_search'),
            (r'\b(?:show|list|display|get)\s+(?:me\s+)?(?:all\s+)?(?:my\s+)?(?:high|low|medium|priority|urgent)?\s*(?:priority\s+)?tickets?', 'ticket_search'),
            (r'\b(?:all|high|low|medium)\s+priority\s+tickets?', 'ticket_search'),
        ]
        
        # Knowledge-related patterns
        self.knowledge_patterns = [
            # Direct questions
            (r'\b(?:what|how|why|when|where)\s+(?:is|are|do|does|can|should)', 'question'),
            (r'\b(?:how\s+(?:do\s+i|to|can\s+i))', 'how_to'),
            (r'\b(?:what\s+(?:is|are))\s+(?:a|an|the)?\s*(\w+)', 'definition'),
            
            # Documentation/help queries
            (r'\b(?:help|guide|documentation|docs|manual)', 'help'),
            (r'\b(?:explain|tell\s+me|show\s+me)\s+(?:about|how)', 'explanation'),
            
            # Product-specific terms
            (r'\b(?:probe|superops|network|monitor|scan)', 'product_feature'),
            (r'\b(?:install|setup|configure|add|create)', 'setup_help'),
        ]
        
        # Greeting patterns
        self.greeting_patterns = [
            (r'\b(?:hello|hi|hey|good\s+(?:morning|afternoon|evening))', 'greeting'),
            (r'\b(?:how\s+are\s+you|how\s+do\s+you\s+do)', 'greeting'),
            (r'\b(?:thanks?|thank\s+you)', 'thanks'),
            (r'\b(?:thank\s+you\s+(?:so\s+)?much)', 'thanks'),
            (r'\b(?:perfect.*thank|great.*thank)', 'thanks'),
            (r'\b(?:goodbye|see\s+you|have\s+a\s+good)', 'thanks'),
            (r'\b(?:appreciate\s+it)', 'thanks'),
        ]
        
        # Escalation patterns
        self.escalation_patterns = [
            (r'\b(?:escalate|human|agent|person|representative)', 'escalation'),
            (r'\b(?:speak\s+to|talk\s+to|connect\s+me)', 'escalation'),
            (r'\b(?:transfer|forward|hand\s+over)', 'escalation'),
        ]
        
        # Follow-up patterns
        self.followup_patterns = [
            (r'\b(?:yes|yeah|yep|sure|okay|ok)\b.*(?:show|list|display)', 'followup_show'),
            (r'\b(?:please\s+)?(?:show|list|display)\s+(?:them|those|it)', 'followup_show'),
            (r'\b(?:yes|yeah|yep|sure|okay|ok)\b.*(?:please)', 'followup_confirm'),
            (r'\b(?:go\s+ahead|continue|proceed)', 'followup_confirm'),
            
            # Contextual reference patterns
            (r'\b(?:who|which\s+team)\s+(?:was\s+)?(?:it\s+)?(?:assigned)', 'contextual_team'),
            (r'\b(?:what\s+(?:was\s+)?(?:the\s+)?(?:resolution\s+time|time))', 'contextual_time'),
            (r'\b(?:that\s+(?:particular\s+)?ticket)', 'contextual_ticket'),
        ]
    
    def classify_intent(self, query: str) -> Optional[Intent]:
        """
        Fast rule-based intent classification.
        Returns None if the query is too complex for rule-based classification.
        """
        query_lower = query.lower().strip()
        
        if not query_lower:
            return None
        
        # Check for greetings first (highest priority)
        greeting_match = self._check_patterns(query_lower, self.greeting_patterns)
        if greeting_match:
            return Intent(
                intent_type=IntentType.GREETING,
                confidence=0.95,
                entities={},
                reasoning="Detected greeting pattern"
            )
        
        # Check for escalation requests
        escalation_match = self._check_patterns(query_lower, self.escalation_patterns)
        if escalation_match:
            return Intent(
                intent_type=IntentType.ESCALATION,
                confidence=0.90,
                entities={},
                reasoning="Detected escalation request"
            )
        
        # Check for follow-up queries (should maintain context from previous query)
        followup_match = self._check_patterns(query_lower, self.followup_patterns)
        if followup_match:
            # For follow-ups, we should maintain the same intent as the previous query
            # This will be handled by the supervisor agent with context
            return Intent(
                intent_type=IntentType.TICKET_QUERY,  # Default to ticket for follow-ups
                confidence=0.85,
                entities={'followup': True},
                reasoning="Detected follow-up query"
            )
        
        # Check for ticket-related queries
        ticket_match, ticket_entities = self._check_ticket_patterns(query_lower)
        knowledge_match = self._check_patterns(query_lower, self.knowledge_patterns)
        
        # Specific ticket information queries should be ticket_query, not mixed
        ticket_info_keywords = ['status', 'resolution', 'priority', 'category', 'description', 'assigned', 'created', 'updated']
        has_ticket_info = any(keyword in query_lower for keyword in ticket_info_keywords)
        
        # More precise mixed query detection - only for explicit dual requests
        explicit_mixed_indicators = [
            'can you also' in query_lower and any(kw in query_lower for kw in ['what is', 'how to', 'explain']),
            'and also' in query_lower and ticket_match and knowledge_match,
            'also tell me' in query_lower and (ticket_match or knowledge_match),
            'also explain' in query_lower and (ticket_match or knowledge_match),
            # More specific pattern: "I have a ticket... also explain/tell me"
            'ticket' in query_lower and 'also' in query_lower and any(kw in query_lower for kw in ['explain', 'tell me about', 'what is a', 'how does'])
        ]
        
        # Only classify as mixed if there are explicit indicators for both types
        if any(explicit_mixed_indicators):
            return Intent(
                intent_type=IntentType.MIXED_QUERY,
                confidence=0.90,
                entities=ticket_entities,
                reasoning=f"Detected explicit mixed query with dual request indicators"
            )
        elif ticket_match:
            confidence = 0.95 if ticket_entities.get('ticket_id') else 0.85
            return Intent(
                intent_type=IntentType.TICKET_QUERY,
                confidence=confidence,
                entities=ticket_entities,
                reasoning=f"Detected ticket query pattern: {ticket_match}"
            )
        
        # Check for knowledge-related queries
        knowledge_match = self._check_patterns(query_lower, self.knowledge_patterns)
        if knowledge_match:
            return Intent(
                intent_type=IntentType.KNOWLEDGE_QUERY,
                confidence=0.85,
                entities={},
                reasoning=f"Detected knowledge query pattern: {knowledge_match}"
            )
        
        # If no clear pattern matches, return None for LLM fallback
        return None
    
    def _check_patterns(self, query: str, patterns: List[Tuple[str, str]]) -> Optional[str]:
        """Check if query matches any of the given patterns."""
        for pattern, pattern_type in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return pattern_type
        return None
    
    def _check_ticket_patterns(self, query: str) -> Tuple[Optional[str], Dict[str, str]]:
        """Check for ticket patterns and extract entities."""
        entities = {}
        matched_pattern = None
        
        # Extract ticket ID - prioritize "IT 001" patterns
        it_patterns = [
            r'\bit\s+(\d+)\b',  # "IT 001"
            r'\bit-(\d+)\b',    # "IT-001"
        ]
        
        for pattern in it_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                number = match.group(1)
                entities['ticket_id'] = f"IT-{number.zfill(3)}"
                break
        
        # If no IT pattern found, try other patterns
        if 'ticket_id' not in entities:
            ticket_id_patterns = [
                r'\b(?:ticket|id)\s*(?:id\s*)?(?:#\s*)?([a-zA-Z0-9\-_]+)',
                r'#(\d+)',
                r'\b(\d{3,})\b',
                r'(?:of|for)\s+([a-zA-Z0-9\-_]+)(?:\s|$)',
            ]
            
            for pattern in ticket_id_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    raw_id = match.group(1)
                    # Skip common words and single letters
                    skip_words = ['ticket', 'description', 'resolution', 'status', 'for', 'of', 'my', 'similar', 'current', 'currently', 'open', 'closed']
                    if raw_id.lower() not in skip_words and len(raw_id) > 1:
                        entities['ticket_id'] = self._normalize_ticket_id(raw_id)
                        break
        
        # Check for ticket-related patterns
        for pattern, pattern_type in self.ticket_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                matched_pattern = pattern_type
                break
        
        return matched_pattern, entities
    
    def _normalize_ticket_id(self, raw_id: str) -> str:
        """Normalize ticket ID to IT-XXX format."""
        raw_id = raw_id.strip().upper()
        
        # If it already has IT- prefix, return as is
        if raw_id.startswith('IT-'):
            return raw_id
        
        # If it starts with IT but no dash, add the dash
        if raw_id.startswith('IT') and len(raw_id) > 2:
            number_part = raw_id[2:]
            if number_part.isdigit():
                return f"IT-{number_part.zfill(3)}"
        
        # If it's just a number, add IT- prefix and pad with zeros
        if raw_id.isdigit():
            return f"IT-{raw_id.zfill(3)}"
        
        # If it has other format, try to extract numbers
        import re
        numbers = re.findall(r'\d+', raw_id)
        if numbers:
            return f"IT-{numbers[0].zfill(3)}"
        
        # Return as is if no clear pattern
        return raw_id
    
    def get_classification_stats(self) -> Dict[str, int]:
        """Get statistics about pattern matching."""
        return {
            'ticket_patterns': len(self.ticket_patterns),
            'knowledge_patterns': len(self.knowledge_patterns),
            'greeting_patterns': len(self.greeting_patterns),
            'escalation_patterns': len(self.escalation_patterns)
        }


# Global instance
fast_classifier = FastIntentClassifier()


def classify_intent_fast(query: str) -> Optional[Intent]:
    """
    Fast intent classification using rule-based patterns.
    Returns None if LLM fallback is needed.
    """
    return fast_classifier.classify_intent(query)