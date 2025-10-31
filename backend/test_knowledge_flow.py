#!/usr/bin/env python3
"""
Test the complete knowledge flow including response humanization.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response

async def test_knowledge_flow():
    """Test the complete knowledge flow."""
    
    print("🧠 Testing Complete Knowledge Flow...")
    
    # Test queries
    test_queries = [
        "how do I install a probe",
        "what is a probe",
        "how to convert an asset to a probe",
        "probe installation steps"
    ]
    
    agent = KnowledgeAgent()
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        
        # Create context
        context = ConversationContext(
            session_id="test",
            user_id="test_user"
        )
        
        # Get agent result
        result = await agent.process_query(query, context)
        print(f"   Agent confidence: {result.confidence:.2f}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        print(f"   Requires escalation: {result.requires_escalation}")
        
        # Convert to format expected by humanizer
        agent_results = [{
            'agent_name': result.agent_name,
            'data': result.data,
            'confidence': result.confidence,
            'requires_escalation': result.requires_escalation
        }]
        
        # Humanize response
        human_response = await humanize_agent_response(agent_results, query)
        print(f"   🗣️ Human response: {human_response}")

if __name__ == "__main__":
    asyncio.run(test_knowledge_flow())