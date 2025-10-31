#!/usr/bin/env python3
"""
Final test of knowledge base functionality.
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

async def test_knowledge_final():
    """Final test of knowledge base functionality."""
    
    print("🧠 Final Knowledge Base Test...")
    
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
    
    # Test different knowledge queries
    test_queries = [
        "how do I install a probe",
        "what is a probe",
        "how to convert an asset to a probe",
        "probe configuration steps"
    ]
    
    for query in test_queries:
        print(f"\n🎤 User: {query}")
        
        # Add to conversation history
        orchestrator.current_session.add_message(query, "user")
        
        # Process through supervisor
        supervisor_result = await orchestrator.supervisor_agent.process_query(query, orchestrator.current_session)
        
        # Route to agents
        agent_results = await orchestrator._coordinate_agents_simple(supervisor_result, query)
        
        # Generate response
        response = await orchestrator._generate_response(agent_results)
        
        print(f"🗣️ Response: {response[:100]}...")
        
        # Check response quality
        if len(response) < 50:
            print("   ⚠️ Very short response")
        elif "I couldn't find" in response or "I'm not confident" in response:
            print("   ❌ No information found")
        elif len(response) > 300:
            print("   ⚠️ Very long response (possible LLM)")
        else:
            print("   ✅ Good response length")

if __name__ == "__main__":
    asyncio.run(test_knowledge_final())