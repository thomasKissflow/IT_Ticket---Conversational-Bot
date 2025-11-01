#!/usr/bin/env python3
"""
Final test of all fixes: ticket parsing, knowledge responses, and contextual understanding.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VoiceAssistantOrchestrator
from agents.base_agent import ConversationContext
from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.knowledge_agent import KnowledgeAgent

async def test_final_fixes():
    """Test all the fixes together."""
    
    print("🔧 Testing Final Fixes...")
    
    # Create orchestrator
    orchestrator = VoiceAssistantOrchestrator()
    
    # Initialize agents
    orchestrator.supervisor_agent = SupervisorAgent()
    orchestrator.ticket_agent = TicketAgent()
    orchestrator.knowledge_agent = KnowledgeAgent()
    
    # Create session
    orchestrator.current_session = ConversationContext(
        session_id="test_session",
        user_id="test_user"
    )
    
    # Test scenario: ticket query followed by contextual queries
    test_scenario = [
        ("What is the status of IT 001?", "ticket"),
        ("What was the resolution time of that particular ticket?", "ticket_contextual"),
        ("How do I install a probe?", "knowledge"),
        ("What is a probe?", "knowledge")
    ]
    
    for query, query_type in test_scenario:
        print(f"\n🎤 User: {query}")
        print(f"   Type: {query_type}")
        
        # Add to conversation history
        orchestrator.current_session.add_message(query, "user")
        
        # Process through supervisor
        supervisor_result = await orchestrator.supervisor_agent.process_query(query, orchestrator.current_session)
        
        # Route to agents
        agent_results = await orchestrator._coordinate_agents_simple(supervisor_result, query)
        
        # Generate response
        response = await orchestrator._generate_response(agent_results)
        
        # Add response to conversation history
        orchestrator.current_session.add_message(response, "assistant")
        
        print(f"🗣️ Response: {response}")
        
        # Validate response
        if query_type == "ticket":
            if "IT-001" in response and ("resolved" in response.lower() or "status" in response.lower()):
                print("   ✅ Correct ticket information")
            else:
                print("   ❌ Incorrect ticket information")
        
        elif query_type == "ticket_contextual":
            if "IT-001" in response or "resolution time" in response.lower():
                print("   ✅ Contextual reference resolved")
            else:
                print("   ❌ Contextual reference failed")
        
        elif query_type == "knowledge":
            if len(response) > 50 and ("probe" in response.lower()):
                print("   ✅ Knowledge base response")
            else:
                print("   ❌ Poor knowledge response")

if __name__ == "__main__":
    asyncio.run(test_final_fixes())