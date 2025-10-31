#!/usr/bin/env python3
"""
Test script to verify response humanizer fixes.
"""

import asyncio
from services.response_humanizer import ResponseHumanizer

async def test_response_humanizer():
    """Test the improved response humanizer."""
    print("🧪 Testing Response Humanizer Fixes")
    print("=" * 50)
    
    humanizer = ResponseHumanizer()
    
    # Test 1: Ticket Query Response
    print("1. Testing Ticket Query Response...")
    ticket_results = [{
        'agent_name': 'TicketAgent',
        'data': {
            'type': 'specific_ticket',
            'found': True,
            'ticket': {
                'id': 'IT-001',
                'title': 'Probe installation failed on Windows',
                'status': 'Resolved',
                'priority': 'High',
                'category': 'Probe Setup',
                'resolution': 'Added /QN and LicenseAccepted=yes to the MSI command; reinstalled successfully.'
            }
        },
        'confidence': 0.95,
        'requires_escalation': False
    }]
    
    response = await humanizer.humanize_response(
        ticket_results, 
        "What is the status of my ticket IT-001?"
    )
    print(f"Response: {response}")
    print()
    
    # Test 2: Escalation Request
    print("2. Testing Escalation Request...")
    escalation_results = [{
        'agent_name': 'SupervisorAgent',
        'data': {
            'intent': type('Intent', (), {'intent_type': type('IntentType', (), {'value': 'escalation'})()})(),
            'routing_decision': []
        },
        'confidence': 0.90,
        'requires_escalation': True
    }]
    
    response = await humanizer.humanize_response(
        escalation_results,
        "Can you escalate to a human?"
    )
    print(f"Response: {response}")
    print()
    
    # Test 3: Greeting
    print("3. Testing Greeting...")
    greeting_results = []
    
    response = await humanizer.humanize_response(
        greeting_results,
        "Hello how are you?"
    )
    print(f"Response: {response}")
    print()
    
    # Test 4: Knowledge Query
    print("4. Testing Knowledge Query...")
    knowledge_results = [{
        'agent_name': 'KnowledgeAgent',
        'data': {
            'type': 'knowledge_search',
            'contextual_response': {
                'answer': 'A probe in SuperOps is a crucial tool used for scanning devices within a network.',
                'confidence': 0.93,
                'sources': ['product-documentation.pdf']
            },
            'knowledge_chunks': [
                {
                    'text': 'Adding a probe in SuperOps What is a probe? A probe in SuperOps is a crucial tool...',
                    'relevance_score': 0.85,
                    'source': 'product-documentation.pdf'
                }
            ]
        },
        'confidence': 0.95,
        'requires_escalation': False
    }]
    
    response = await humanizer.humanize_response(
        knowledge_results,
        "What is a probe in SuperOps?"
    )
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_response_humanizer())