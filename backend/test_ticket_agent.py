#!/usr/bin/env python3
"""
Test script to debug ticket agent functionality.
"""

import asyncio
from agents.ticket_agent import TicketAgent
from agents.base_agent import ConversationContext

async def test_ticket_agent():
    """Test ticket agent with various queries."""
    
    # Create ticket agent
    ticket_agent = TicketAgent()
    
    # Create test context
    context = ConversationContext("test_session")
    
    # Test queries
    test_queries = [
        "What is the status of my ticket ID 001?",
        "Show me ticket 100",
        "I need help with my support ticket",
        "What tickets are open?",
        "Show me high priority tickets"
    ]
    
    print("🧪 Testing Ticket Agent")
    print("=" * 50)
    
    # First check health
    health = await ticket_agent.health_check()
    print(f"Health Check: {health}")
    print()
    
    for query in test_queries:
        print(f"📝 Query: '{query}'")
        print("-" * 40)
        
        try:
            result = await ticket_agent.process_query(query, context)
            print(f"Agent: {result.agent_name}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Processing Time: {result.processing_time:.2f}s")
            print(f"Requires Escalation: {result.requires_escalation}")
            print(f"Data Type: {result.data.get('type', 'unknown')}")
            
            if 'error' in result.data:
                print(f"❌ Error: {result.data['error']}")
            elif result.data.get('type') == 'specific_ticket':
                if result.data.get('found'):
                    ticket = result.data['ticket']
                    print(f"✅ Found ticket: {ticket['id']} - {ticket['title']}")
                else:
                    print(f"❌ Ticket not found: {result.data.get('ticket_id')}")
            elif result.data.get('type') == 'search_results':
                total = result.data.get('total_found', 0)
                print(f"📊 Search results: {total} tickets found")
                
                combined = result.data.get('combined_results', [])
                for i, ticket in enumerate(combined[:3], 1):
                    print(f"  {i}. {ticket.get('id', 'N/A')} - {ticket.get('title', 'N/A')}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print()

if __name__ == "__main__":
    asyncio.run(test_ticket_agent())