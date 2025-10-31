#!/usr/bin/env python3
"""
Simple test to verify the complete flow without orchestrator complexity.
"""

import asyncio
from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response
from logging_config import setup_clean_logging

async def test_simple_flow():
    """Test the complete flow with clean debug output."""
    setup_clean_logging()
    
    print("🧪 Testing Simple Flow")
    print("=" * 40)
    
    # Initialize components
    supervisor = SupervisorAgent()
    ticket_agent = TicketAgent()
    knowledge_agent = KnowledgeAgent()
    context = ConversationContext("test_session")
    
    # Test queries
    queries = [
        "What is the status of my IT ticket 001",
        "How to add a probe, and are there any similar tickets currently open",
        "What is the resolution time of IT 001"
    ]
    
    for query in queries:
        print(f"\n🎤 User: {query}")
        print("-" * 40)
        
        try:
            # Step 1: Intent analysis
            intent = await supervisor.analyze_intent(query, context)
            
            # Step 2: Routing
            supervisor_result = await supervisor.process_query(query, context)
            routing = supervisor_result.data.get('routing_decision', [])
            
            # Step 3: Execute agents
            agent_results = [supervisor_result]
            
            if 'ticket' in routing:
                print("📋 Calling TicketAgent")
                ticket_result = await ticket_agent.process_query(query, context)
                agent_results.append(ticket_result)
            
            if 'knowledge' in routing:
                print("📚 Calling KnowledgeAgent")
                knowledge_result = await knowledge_agent.process_query(query, context)
                agent_results.append(knowledge_result)
            
            # Step 4: Generate response
            agent_data = []
            for result in agent_results:
                if result.agent_name != 'SupervisorAgent':  # Skip supervisor for response
                    agent_data.append({
                        'agent_name': result.agent_name,
                        'data': result.data,
                        'confidence': result.confidence,
                        'requires_escalation': result.requires_escalation
                    })
            
            if agent_data:
                response = await humanize_agent_response(agent_data, query)
                print(f"🗣️ Response: {response}")
            else:
                print("⚠️ No agent data for response")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_flow())