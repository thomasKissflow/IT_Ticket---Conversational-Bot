"""
TicketAgent implementation for structured data queries on support tickets.
"""

import asyncio
import sqlite3
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentType, AgentResult, ConversationContext
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_access import DataAccess


class SearchCriteria:
    """Criteria for ticket searches."""
    
    def __init__(self):
        self.ticket_id: Optional[str] = None
        self.category: Optional[str] = None
        self.priority: Optional[str] = None
        self.status: Optional[str] = None
        self.assigned_team: Optional[str] = None
        self.date_range: Optional[Tuple[datetime, datetime]] = None
        self.keywords: List[str] = []


class TicketDetails:
    """Detailed ticket information."""
    
    def __init__(self, ticket_data: Dict[str, Any]):
        self.id = ticket_data.get('id')
        self.title = ticket_data.get('title')
        self.description = ticket_data.get('description')
        self.category = ticket_data.get('category')
        self.priority = ticket_data.get('priority')
        self.status = ticket_data.get('status')
        self.resolution = ticket_data.get('resolution')
        self.resolution_time = ticket_data.get('resolution_time')
        self.assigned_team = ticket_data.get('assigned_team')
        self.created_date = ticket_data.get('created_date')
        self.updated_date = ticket_data.get('updated_date')


class AnalysisResult:
    """Result of ticket pattern analysis."""
    
    def __init__(self):
        self.total_tickets: int = 0
        self.patterns: Dict[str, Any] = {}
        self.trends: Dict[str, Any] = {}
        self.recommendations: List[str] = []


class TicketAgent(BaseAgent):
    """
    Specialized agent for retrieving and processing support ticket data.
    Handles SQLite queries and semantic search integration.
    """
    
    def __init__(self, sqlite_db_path: str = "./data/voice_assistant.db", chroma_db_path: str = "./data/chroma_db"):
        super().__init__("TicketAgent", AgentType.TICKET)
        self.data_access = DataAccess(sqlite_db_path, chroma_db_path)
        self.sqlite_db_path = sqlite_db_path
    
    async def process_query(self, query: str, context: ConversationContext) -> AgentResult:
        """
        Process a ticket-related query and return structured results.
        """
        start_time = time.time()
        
        try:
            # Parse query to extract search criteria
            criteria = self._parse_query_criteria(query, context)
            
            # Debug: Show what we're searching for
            if criteria.ticket_id:
                print(f"🎫 Searching for ticket: {criteria.ticket_id}")
            
            # Perform search based on criteria
            if criteria.ticket_id:
                # Direct ticket lookup
                result_data = await self._get_specific_ticket(criteria.ticket_id)
                confidence = 0.95 if result_data else 0.1
                
                # Debug: Show result
                if result_data and result_data.get('found'):
                    ticket = result_data['ticket']
                    print(f"✅ Found: {ticket['id']} - {ticket['status']} - {ticket['title'][:50]}...")
                else:
                    print(f"❌ Ticket {criteria.ticket_id} not found")
            else:
                # Semantic search combined with structured filtering
                result_data = await self._search_tickets_comprehensive(query, criteria)
                confidence = self._calculate_confidence(result_data, query)
                
                # Debug: Show search results
                total = result_data.get('total_found', 0)
                print(f"🔍 Search found {total} tickets")
            
            processing_time = time.time() - start_time
            requires_escalation = confidence < 0.6 or not result_data
            
            return AgentResult(
                agent_name=self.name,
                data=result_data,
                confidence=confidence,
                processing_time=processing_time,
                requires_escalation=requires_escalation,
                metadata={
                    "query_type": "specific_ticket" if criteria.ticket_id else "search",
                    "criteria": self._criteria_to_dict(criteria)
                }
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
    
    def _parse_query_criteria(self, query: str, context: Optional[ConversationContext] = None) -> SearchCriteria:
        """Parse natural language query to extract search criteria."""
        criteria = SearchCriteria()
        query_lower = query.lower()
        
        # Extract ticket ID patterns
        import re
        
        # First try to find "IT 001" or "IT-001" patterns specifically
        it_patterns = [
            r'\bit\s+(\d+)\b',  # "IT 001"
            r'\bit-(\d+)\b',    # "IT-001"
        ]
        
        for pattern in it_patterns:
            match = re.search(pattern, query_lower)
            if match:
                number = match.group(1)
                criteria.ticket_id = f"IT-{number.zfill(3)}"
                break
        
        # Check for contextual references like "that ticket", "the ticket", etc.
        if not criteria.ticket_id and context:
            contextual_patterns = [
                r'\b(?:that|the|this)\s+(?:particular\s+)?ticket\b',
                r'\b(?:that|the|this)\s+(?:one|ticket)\b',
                r'\bof\s+(?:that|it)\b'
            ]
            
            for pattern in contextual_patterns:
                if re.search(pattern, query_lower):
                    # Look for the last mentioned ticket ID in conversation history
                    last_ticket_id = self._get_last_ticket_id_from_context(context)
                    if last_ticket_id:
                        criteria.ticket_id = last_ticket_id
                        print(f"🔗 Using contextual ticket ID: {last_ticket_id}")
                        break
        
        # If no IT pattern found, try other patterns
        if not criteria.ticket_id:
            ticket_id_patterns = [
                r'ticket\s+(?:id\s+)?([a-zA-Z0-9\-_]+)',
                r'#([a-zA-Z0-9\-_]+)',
                r'(?:id|ticket)\s+([a-zA-Z0-9\-_]+)',
                r'(?:of|for)\s+(\d{1,4})\b',  # Only match numbers after "of" or "for"
                r'\b(\d{3,4})\b'  # Match 3-4 digit numbers only
            ]
            
            for pattern in ticket_id_patterns:
                matches = re.findall(pattern, query_lower)
                for match in matches:
                    # Skip common words and validate the match
                    if (match.lower() not in ['ticket', 'description', 'resolution', 'status', 'for', 'of', 'my', 'that', 'particular', 'number'] and
                        len(match) >= 1 and 
                        (match.isdigit() or any(c.isalnum() for c in match))):
                        raw_id = match.upper()
                        criteria.ticket_id = self._normalize_ticket_id(raw_id)
                        break
                if criteria.ticket_id:
                    break
        
        # Extract category
        categories = ['hardware', 'software', 'network', 'security', 'account', 'billing']
        for category in categories:
            if category in query_lower:
                criteria.category = category.title()
                break
        
        # Extract priority
        priorities = ['high', 'medium', 'low', 'critical', 'urgent']
        for priority in priorities:
            if priority in query_lower:
                criteria.priority = priority.title()
                break
        
        # Extract status
        statuses = ['open', 'closed', 'pending', 'resolved', 'in progress']
        for status in statuses:
            if status in query_lower:
                criteria.status = status.title()
                break
        
        # Extract team
        teams = ['support', 'engineering', 'sales', 'billing', 'security']
        for team in teams:
            if team in query_lower:
                criteria.assigned_team = team.title()
                break
        
        # Extract keywords (remove common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'show', 'find', 'get', 'ticket', 'tickets'}
        words = query_lower.split()
        criteria.keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return criteria
    
    def _get_last_ticket_id_from_context(self, context: ConversationContext) -> Optional[str]:
        """Extract the last mentioned ticket ID from conversation history."""
        if not context or not context.conversation_history:
            return None
        
        import re
        
        # Look through recent messages for ticket IDs
        for message in reversed(context.conversation_history[-10:]):  # Check last 10 messages
            if message.speaker == "assistant":
                # Look for ticket IDs in assistant responses
                patterns = [
                    r'\b(IT-\d{3})\b',
                    r'\bTicket\s+(IT-\d{3})\b'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, message.content)
                    if match:
                        return match.group(1)
        
        return None
    
    def _normalize_ticket_id(self, raw_id: str) -> str:
        """Normalize ticket ID to IT-XXX format."""
        import re
        
        # Remove any spaces and convert to uppercase
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
        numbers = re.findall(r'\d+', raw_id)
        if numbers:
            return f"IT-{numbers[0].zfill(3)}"
        
        # Return as is if no clear pattern
        return raw_id
    
    def _criteria_to_dict(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Convert SearchCriteria to dictionary for metadata."""
        return {
            "ticket_id": criteria.ticket_id,
            "category": criteria.category,
            "priority": criteria.priority,
            "status": criteria.status,
            "assigned_team": criteria.assigned_team,
            "keywords": criteria.keywords
        }
    
    async def _get_specific_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific ticket by ID."""
        ticket_data = self.data_access.get_ticket_by_id(ticket_id)
        
        if ticket_data:
            return {
                "type": "specific_ticket",
                "ticket": ticket_data,
                "found": True
            }
        else:
            return {
                "type": "specific_ticket",
                "ticket_id": ticket_id,
                "found": False,
                "message": f"No ticket found with ID: {ticket_id}"
            }
    
    async def _search_tickets_comprehensive(self, query: str, criteria: SearchCriteria) -> Dict[str, Any]:
        """Perform comprehensive ticket search using both semantic and structured approaches."""
        results = {
            "type": "search_results",
            "semantic_results": [],
            "structured_results": [],
            "combined_results": [],
            "total_found": 0
        }
        
        # Semantic search using ChromaDB
        semantic_results = await self.data_access.search_tickets(query, top_k=10)
        results["semantic_results"] = semantic_results
        
        # Structured search using SQLite
        structured_results = await self._structured_search(criteria)
        results["structured_results"] = structured_results
        
        # Combine and deduplicate results
        combined_results = self._combine_search_results(semantic_results, structured_results)
        results["combined_results"] = combined_results
        results["total_found"] = len(combined_results)
        
        return results
    
    async def _structured_search(self, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Perform structured search using SQLite with filters."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Build dynamic query
            query_parts = ["SELECT id, title, description, category, priority, status, resolution, assigned_team FROM tickets WHERE 1=1"]
            params = []
            
            if criteria.category:
                query_parts.append("AND category = ?")
                params.append(criteria.category)
            
            if criteria.priority:
                query_parts.append("AND priority = ?")
                params.append(criteria.priority)
            
            if criteria.status:
                query_parts.append("AND status = ?")
                params.append(criteria.status)
            
            if criteria.assigned_team:
                query_parts.append("AND assigned_team = ?")
                params.append(criteria.assigned_team)
            
            # Add keyword search
            if criteria.keywords:
                keyword_conditions = []
                for keyword in criteria.keywords:
                    keyword_conditions.append("(title LIKE ? OR description LIKE ?)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
                
                if keyword_conditions:
                    query_parts.append(f"AND ({' OR '.join(keyword_conditions)})")
            
            query_parts.append("ORDER BY priority DESC, created_date DESC LIMIT 20")
            
            final_query = " ".join(query_parts)
            cursor.execute(final_query, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            # Format results
            tickets = []
            for row in rows:
                tickets.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'category': row[3],
                    'priority': row[4],
                    'status': row[5],
                    'resolution': row[6],
                    'assigned_team': row[7],
                    'source': 'structured_search'
                })
            
            return tickets
            
        except Exception as e:
            print(f"Error in structured search: {e}")
            return []
    
    def _combine_search_results(self, semantic_results: List[Dict], structured_results: List[Dict]) -> List[Dict[str, Any]]:
        """Combine and deduplicate search results from semantic and structured searches."""
        combined = {}
        
        # Add semantic results with scores
        for result in semantic_results:
            if 'metadata' in result and 'ticket_id' in result['metadata']:
                ticket_id = result['metadata']['ticket_id']
                combined[ticket_id] = {
                    'id': ticket_id,
                    'title': result['metadata'].get('title', ''),
                    'category': result['metadata'].get('category', ''),
                    'priority': result['metadata'].get('priority', ''),
                    'status': result['metadata'].get('status', ''),
                    'summary': result.get('summary', ''),
                    'semantic_score': 1.0 - result.get('distance', 1.0),  # Convert distance to similarity
                    'source': 'semantic_search'
                }
        
        # Add structured results (may override semantic results with more complete data)
        for result in structured_results:
            ticket_id = result['id']
            if ticket_id in combined:
                # Merge with existing semantic result
                combined[ticket_id].update(result)
                combined[ticket_id]['source'] = 'both'
            else:
                # Add new structured result
                result['source'] = 'structured_search'
                combined[ticket_id] = result
        
        # Convert to list and sort by relevance
        results_list = list(combined.values())
        
        # Sort by semantic score if available, then by priority
        def sort_key(item):
            semantic_score = item.get('semantic_score', 0.0)
            priority_score = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}.get(item.get('priority', ''), 0)
            return (semantic_score, priority_score)
        
        results_list.sort(key=sort_key, reverse=True)
        
        return results_list[:10]  # Return top 10 results
    
    def _calculate_confidence(self, result_data: Dict[str, Any], query: str) -> float:
        """Calculate confidence score for the search results."""
        if not result_data:
            return 0.0
        
        if result_data.get("type") == "specific_ticket":
            return 0.95 if result_data.get("found") else 0.1
        
        # For search results
        total_found = result_data.get("total_found", 0)
        if total_found == 0:
            return 0.1
        
        # Base confidence on number of results and semantic scores
        combined_results = result_data.get("combined_results", [])
        if not combined_results:
            return 0.3
        
        # Average semantic scores if available
        semantic_scores = [r.get('semantic_score', 0.5) for r in combined_results if 'semantic_score' in r]
        avg_semantic_score = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.5
        
        # Adjust based on result count
        count_factor = min(total_found / 5.0, 1.0)  # Normalize to max of 1.0
        
        confidence = (avg_semantic_score * 0.7) + (count_factor * 0.3)
        return min(confidence, 0.95)  # Cap at 0.95
    
    async def search_tickets(self, query: str, filters: Dict = None) -> List[Dict[str, Any]]:
        """Public method for searching tickets with optional filters."""
        criteria = SearchCriteria()
        
        if filters:
            criteria.category = filters.get('category')
            criteria.priority = filters.get('priority')
            criteria.status = filters.get('status')
            criteria.assigned_team = filters.get('assigned_team')
        
        # Add query keywords
        criteria.keywords = query.lower().split()
        
        result_data = await self._search_tickets_comprehensive(query, criteria)
        return result_data.get("combined_results", [])
    
    async def get_ticket_details(self, ticket_id: str) -> Optional[TicketDetails]:
        """Get detailed information for a specific ticket."""
        ticket_data = self.data_access.get_ticket_by_id(ticket_id)
        
        if ticket_data:
            return TicketDetails(ticket_data)
        return None
    
    async def analyze_ticket_patterns(self, criteria: SearchCriteria) -> AnalysisResult:
        """Analyze ticket patterns and provide insights."""
        analysis = AnalysisResult()
        
        try:
            # Get ticket statistics
            stats = self.data_access.get_ticket_stats()
            analysis.total_tickets = stats.get('total', 0)
            
            # Analyze patterns
            analysis.patterns = {
                'by_status': stats.get('by_status', {}),
                'by_priority': stats.get('by_priority', {}),
                'by_category': stats.get('by_category', {})
            }
            
            # Generate recommendations based on patterns
            analysis.recommendations = self._generate_recommendations(stats)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing ticket patterns: {e}")
            return analysis
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on ticket statistics."""
        recommendations = []
        
        by_status = stats.get('by_status', {})
        by_priority = stats.get('by_priority', {})
        by_category = stats.get('by_category', {})
        
        # Check for high open ticket count
        open_tickets = by_status.get('Open', 0)
        total_tickets = stats.get('total', 1)
        
        if open_tickets / total_tickets > 0.3:
            recommendations.append(f"High number of open tickets ({open_tickets}). Consider reviewing ticket assignment and resolution processes.")
        
        # Check for high priority tickets
        high_priority = by_priority.get('High', 0) + by_priority.get('Critical', 0)
        if high_priority / total_tickets > 0.2:
            recommendations.append(f"Significant number of high/critical priority tickets ({high_priority}). Review escalation procedures.")
        
        # Check for category concentration
        if by_category:
            max_category = max(by_category.items(), key=lambda x: x[1])
            if max_category[1] / total_tickets > 0.4:
                recommendations.append(f"High concentration of {max_category[0]} tickets ({max_category[1]}). Consider specialized training or resources.")
        
        return recommendations
    
    async def health_check(self) -> bool:
        """Check if the TicketAgent is healthy and ready."""
        try:
            # Test database connection
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tickets")
            count = cursor.fetchone()[0]
            conn.close()
            
            # Test ChromaDB connection
            semantic_results = await self.data_access.search_tickets("test", top_k=1)
            
            return count >= 0  # Basic health check
            
        except Exception as e:
            print(f"TicketAgent health check failed: {e}")
            return False