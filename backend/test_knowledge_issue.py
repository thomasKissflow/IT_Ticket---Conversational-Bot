#!/usr/bin/env python3
"""
Test to reproduce the exact knowledge base issue from the main application.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VoiceAssistantOrchestrator
from agents.base_agent import ConversationContext, Message
from datetime import datetime

async def test_knowledge_issue():
    """Test the knowledge base issue by simulating the main application flow."""
    
    print("🔍 Testing Knowledge Base Issue...")
    
    # Create orchestrator like in main application
    orchestrator = VoiceAssistantOrchestrator()
    
    # Initialize agents like in main application
    from agents.supervisor_agent import SupervisorAgent
    from agents.ticket_agent import TicketAgent
    from agents.knowledge_agent import KnowledgeAgent
    
    orchestrator.supervisor_agent = SupervisorAgent()
    orchestrator.ticket_agent = TicketAgent()
    orchestrator.knowledge_agent = KnowledgeAgent()
    
    # Create a session like in main application
    orchestrator.current_session = ConversationContext(
        session_id="test_session",
        user_id="test_user"
    )
    
    # Test the exact query from the logs
    query = "how do I install a probe"
    print(f"🎤 User: {query}")
    
    # Add the query to conversation history like in main app
    orchestrator.current_session.add_message(query, "user")
    
    # Process through supervisor agent (like in main app)
    supervisor_result = await orchestrator.supervisor_agent.process_query(query, orchestrator.current_session)
    
    # Debug supervisor result
    intent_data = supervisor_result.data.get('intent')
    routing = supervisor_result.data.get('routing_decision', [])
    if intent_data:
        print(f"🧠 Intent: {intent_data.intent_type.value} → Routing: {routing}")
    
    # Route to appropriate agents (like in main app)
    agent_results = await orchestrator._coordinate_agents_simple(supervisor_result, query)
    
    # Debug agent results
    agent_names = [r.agent_name for r in agent_results]
    print(f"🤖 Agents called: {agent_names}")
    
    # Generate response (like in main app)
    response = await orchestrator._generate_response(agent_results)
    
    print(f"🗣️ Final response: {response}")
    
    # Check if response is generic (indicating LLM fallback)
    if len(response) > 200 or "involves" in response.lower():
        print("⚠️ Response appears to be LLM-generated (long/generic)")
    else:
        print("✅ Response appears to be template-based (concise/specific)")

if __name__ == "__main__":
    asyncio.run(test_knowledge_issue())