#!/usr/bin/env python3
"""
Detailed test of KnowledgeAgent responses to see the actual content.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext


async def test_detailed_responses():
    """Test and show detailed responses from KnowledgeAgent."""
    
    print("🔍 Detailed KnowledgeAgent Response Test")
    print("=" * 60)
    
    # Initialize the agent
    agent = KnowledgeAgent()
    context = ConversationContext(session_id="detailed_test", user_id="test_user")
    
    # Test queries
    queries = [
        "what is a probe in superops",
        "give step by step info to create a subnet manually in superops"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n🎯 QUERY {i}: {query}")
        print("=" * 60)
        
        try:
            result = await agent.process_query(query, context)
            
            # Show the contextual response answer
            contextual_response = result.data.get('contextual_response', {})
            answer = contextual_response.get('answer', 'No answer generated')
            
            print(f"📝 GENERATED ANSWER:")
            print("-" * 40)
            print(answer)
            print("-" * 40)
            
            print(f"\n📊 METADATA:")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Chunks found: {result.data.get('chunks_found', 0)}")
            print(f"   Relevant chunks: {result.data.get('relevant_chunks', 0)}")
            print(f"   Sources: {contextual_response.get('sources', [])}")
            
            # Show the raw knowledge chunks
            knowledge_chunks = result.data.get('knowledge_chunks', [])
            if knowledge_chunks:
                print(f"\n📚 RAW KNOWLEDGE CHUNKS:")
                for j, chunk in enumerate(knowledge_chunks[:2], 1):  # Show top 2
                    print(f"\n   CHUNK {j} (Score: {chunk.get('relevance_score', 0):.3f}):")
                    print(f"   Source: {chunk.get('source', 'Unknown')}")
                    if chunk.get('page_number'):
                        print(f"   Page: {chunk.get('page_number')}")
                    print(f"   Text: {chunk.get('text', '')[:300]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_detailed_responses())