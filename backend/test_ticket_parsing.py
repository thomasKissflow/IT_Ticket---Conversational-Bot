#!/usr/bin/env python3
"""
Test improved ticket ID parsing with context.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.ticket_agent import TicketAgent
from agents.base_agent import ConversationContext, Message
from datetime import datetime

async def test_ticket_parsing():
    """Test ticket ID parsing with contextual references."""
    
    print("🎫 Testing Ticket ID Parsing...")
    
    # Create ticket agent
    agent = TicketAgent()
    
    # Create context with conversation history
    context = ConversationContext(session_id="test", user_id="test_user")
    
    # Simulate a conversation where a ticket was previously mentioned
    context.add_message("What is the status of IT 001?", "user")
    context.add_message("Good news! Ticket IT-001 has been resolved. Probe installation failed on Windows.", "assistant")
    
    # Test contextual queries
    test_queries = [
        "What was the resolution time of that particular ticket?",
        "The ticket number is 001. What is the resolution time?",
        "IT 001",
        "What is the resolution time of that ticket?"
    ]
    
    for query in test_queries:
        print(f"\n🎤 Query: {query}")
        
        # Parse the query
        criteria = agent._parse_query_criteria(query, context)
        
        print(f"   Extracted ticket ID: {criteria.ticket_id}")
        
        # Test the full process
        result = await agent.process_query(query, context)
        
        if result.data.get('found'):
            ticket = result.data.get('ticket', {})
            print(f"   ✅ Found: {ticket.get('id')} - {ticket.get('status')}")
        else:
            print(f"   ❌ Not found: {result.data.get('ticket_id', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(test_ticket_parsing())