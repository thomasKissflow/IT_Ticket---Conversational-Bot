#!/usr/bin/env python3
"""
Test the complete flow from query to response.
"""

import asyncio
from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response

async def test_complete_flow():
    """Test the complete flow for ticket status query."""
    print("🧪 Testing Complete Flow: Ticket Status Query")
    print("=" * 60)
    
    # Initialize components
    supervisor = SupervisorAgent()
    ticket_agent = TicketAgent()
    context = ConversationContext("test_session")
    
    query = "What is the status of that ticket IT 001"
    print(f"Query: '{query}'")
    print()
    
    # Step 1: Supervisor Intent Analysis
    print("1. Supervisor Intent Analysis:")
    intent = await supervisor.analyze_intent(query, context)
    print(f"   Intent: {intent.intent_type.value}")
    print(f"   Confidence: {intent.confidence:.2f}")
    print(f"   Entities: {intent.entities}")
    print()
    
    # Step 2: Supervisor Routing
    print("2. Supervisor Routing:")
    supervisor_result = await supervisor.process_query(query, context)
    routing = supervisor_result.data.get('routing_decision', [])
    print(f"   Routing: {routing}")
    print()
    
    # Step 3: Ticket Agent Processing
    if 'ticket' in routing:
        print("3. Ticket Agent Processing:")
        ticket_result = await ticket_agent.process_query(query, context)
        print(f"   Found: {ticket_result.data.get('found')}")
        
        if ticket_result.data.get('found'):
            ticket = ticket_result.data['ticket']
            print(f"   Ticket: {ticket['id']} - {ticket['status']}")
            print(f"   Title: {ticket['title']}")
        else:
            print(f"   Error: {ticket_result.data.get('message')}")
        print()
        
        # Step 4: Response Humanization
        print("4. Response Humanization:")
        agent_data = [{
            'agent_name': ticket_result.agent_name,
            'data': ticket_result.data,
            'confidence': ticket_result.confidence,
            'requires_escalation': ticket_result.requires_escalation
        }]
        
        response = await humanize_agent_response(agent_data, query)
        print(f"   Response: '{response}'")
        print()
        
        # Verify correctness
        print("5. Verification:")
        if ticket_result.data.get('found'):
            actual_status = ticket_result.data['ticket']['status']
            if actual_status.lower() in response.lower():
                print(f"   ✅ Response correctly mentions status: {actual_status}")
            else:
                print(f"   ❌ Response doesn't mention correct status: {actual_status}")
                print(f"   ❌ Response says: {response}")
        
    else:
        print("3. ❌ No ticket routing - supervisor issue")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())