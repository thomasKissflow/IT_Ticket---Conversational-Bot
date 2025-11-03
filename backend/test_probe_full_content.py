#!/usr/bin/env python3
"""
Test to see the full probe content.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext


async def test_probe_full_content():
    """Test to see the full probe content."""
    
    print("📚 Full Probe Content Test")
    print("=" * 50)
    
    # Initialize the agent
    agent = KnowledgeAgent()
    context = ConversationContext(session_id="probe_full_test", user_id="test_user")
    
    query = "how do I add a probe in superops"
    
    print(f"📝 Query: {query}")
    print("-" * 30)
    
    try:
        result = await agent.process_query(query, context)
        
        # Show the full knowledge chunks
        knowledge_chunks = result.data.get('knowledge_chunks', [])
        if knowledge_chunks:
            print(f"📚 Full knowledge chunks ({len(knowledge_chunks)} total):")
            for j, chunk in enumerate(knowledge_chunks, 1):
                print(f"\n   CHUNK {j}:")
                print(f"   Score: {chunk.get('relevance_score', 0):.3f}")
                print(f"   Source: {chunk.get('source', 'Unknown')}")
                if chunk.get('page_number'):
                    print(f"   Page: {chunk.get('page_number')}")
                print(f"   Full Text:")
                print(f"   {chunk.get('text', '')}")
                print("-" * 40)
        
        # Show the contextual response
        contextual_response = result.data.get('contextual_response', {})
        if contextual_response:
            print(f"\n💬 Full Contextual Response:")
            answer = contextual_response.get('answer', 'No answer')
            print(answer)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_probe_full_content())