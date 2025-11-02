#!/usr/bin/env python3
"""
Compare raw knowledge responses vs humanized responses.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response


async def test_response_comparison():
    """Compare raw vs humanized responses."""
    
    print("🔄 Response Comparison Test")
    print("=" * 60)
    
    # Initialize the agent
    agent = KnowledgeAgent()
    context = ConversationContext(session_id="comparison_test", user_id="test_user")
    
    # Test queries
    queries = [
        "what is a probe in superops",
        "give step by step info to create a subnet manually in superops"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n🎯 QUERY {i}: {query}")
        print("=" * 60)
        
        try:
            # Get raw knowledge agent response
            result = await agent.process_query(query, context)
            
            # Show raw response
            contextual_response = result.data.get('contextual_response', {})
            raw_answer = contextual_response.get('answer', 'No answer generated')
            
            print(f"📚 RAW KNOWLEDGE RESPONSE:")
            print("-" * 40)
            print(raw_answer)
            print("-" * 40)
            
            # Convert to format expected by humanizer
            agent_results = [{
                'agent_name': 'KnowledgeAgent',
                'data': result.data,
                'confidence': result.confidence,
                'requires_escalation': result.requires_escalation
            }]
            
            # Get humanized response
            humanized_response = await humanize_agent_response(agent_results, query)
            
            print(f"\n🗣️ HUMANIZED RESPONSE:")
            print("-" * 40)
            print(humanized_response)
            print("-" * 40)
            
            print(f"\n📊 COMPARISON:")
            print(f"   Raw length: {len(raw_answer)} characters")
            print(f"   Humanized length: {len(humanized_response)} characters")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Chunks found: {result.data.get('relevant_chunks', 0)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_response_comparison())