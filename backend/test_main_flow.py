#!/usr/bin/env python3
"""
Test the exact flow from the main application to reproduce the knowledge issue.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.supervisor_agent import SupervisorAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response

async def test_main_flow():
    """Test the exact flow that happens in main application."""
    
    print("🔄 Testing Main Application Flow...")
    
    # Create context like in main app
    context = ConversationContext(
        session_id="test_session",
        user_id="test_user"
    )
    
    # Test the exact query from the logs
    query = "how do I install a probe"
    print(f"🎤 User: {query}")
    
    # Step 1: Supervisor agent (like in main app)
    supervisor = SupervisorAgent()
    supervisor_result = await supervisor.process_query(query, context)
    
    # Debug supervisor result
    intent_data = supervisor_result.data.get('intent')
    routing = supervisor_result.data.get('routing_decision', [])
    if intent_data:
        print(f"🧠 Intent: {intent_data.intent_type.value} → Routing: {routing}")
    
    # Step 2: Route to knowledge agent (like in main app)
    agent_results = [supervisor_result]
    
    if 'knowledge' in routing:
        print("📚 Calling KnowledgeAgent")
        knowledge_agent = KnowledgeAgent()
        knowledge_result = await knowledge_agent.process_query(query, context)
        agent_results.append(knowledge_result)
        
        # Debug knowledge result
        print(f"   Knowledge confidence: {knowledge_result.confidence:.2f}")
        print(f"   Knowledge data type: {knowledge_result.data.get('type')}")
        print(f"   Relevant chunks: {knowledge_result.data.get('relevant_chunks', 0)}")
    
    # Step 3: Convert to format for humanizer (like in main app)
    agent_data = []
    for result in agent_results:
        agent_data.append({
            'agent_name': result.agent_name,
            'data': result.data,
            'confidence': result.confidence,
            'requires_escalation': result.requires_escalation
        })
    
    # Debug what's being sent to humanizer
    agent_names = [r['agent_name'] for r in agent_data]
    print(f"🤖 Agents called: {agent_names}")
    
    # Step 4: Humanize response (like in main app)
    response = await humanize_agent_response(
        agent_data, 
        query,
        context={'session_id': context.session_id}
    )
    
    print(f"🗣️ Final response: {response}")

if __name__ == "__main__":
    asyncio.run(test_main_flow())