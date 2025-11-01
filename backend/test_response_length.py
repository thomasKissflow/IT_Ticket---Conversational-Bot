#!/usr/bin/env python3
"""
Test to check if responses are being truncated or if they're actually complete.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response

async def test_response_length():
    """Test the full length of knowledge responses."""
    
    print("📏 Testing Response Length...")
    
    # Create knowledge agent
    agent = KnowledgeAgent()
    context = ConversationContext(session_id="test", user_id="test_user")
    
    # Test query
    query = "how do I install a probe"
    print(f"🎤 Query: {query}")
    
    # Get agent result
    result = await agent.process_query(query, context)
    
    # Check the raw knowledge response
    contextual_response = result.data.get('contextual_response', {})
    raw_answer = contextual_response.get('answer', '')
    print(f"\n📊 Raw knowledge answer ({len(raw_answer)} chars):")
    print(f"'{raw_answer}'")
    
    # Convert to format for humanizer
    agent_data = [{
        'agent_name': result.agent_name,
        'data': result.data,
        'confidence': result.confidence,
        'requires_escalation': result.requires_escalation
    }]
    
    # Get humanized response
    response = await humanize_agent_response(agent_data, query)
    print(f"\n🗣️ Final humanized response ({len(response)} chars):")
    print(f"'{response}'")
    
    # Check if they're the same
    if raw_answer in response or response in raw_answer:
        print("✅ Response appears to be using knowledge base data")
    else:
        print("❌ Response appears to be different from knowledge base")

if __name__ == "__main__":
    asyncio.run(test_response_length())