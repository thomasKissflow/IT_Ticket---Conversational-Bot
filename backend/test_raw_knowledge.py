#!/usr/bin/env python3
"""
Test raw knowledge agent responses without humanization.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext


async def test_raw_knowledge():
    """Test raw knowledge agent responses without humanization."""
    
    print("📚 Raw Knowledge Agent Test")
    print("=" * 60)
    
    # Initialize the agent
    agent = KnowledgeAgent()
    context = ConversationContext(session_id="raw_test", user_id="test_user")
    
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
            
            # Show the raw contextual response
            contextual_response = result.data.get('contextual_response', {})
            raw_answer = contextual_response.get('answer', 'No answer generated')
            
            print(f"📝 RAW KNOWLEDGE RESPONSE:")
            print("-" * 40)
            print(raw_answer)
            print("-" * 40)
            
            print(f"\n📊 METADATA:")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Chunks found: {result.data.get('chunks_found', 0)}")
            print(f"   Relevant chunks: {result.data.get('relevant_chunks', 0)}")
            print(f"   Sources: {contextual_response.get('sources', [])}")
            
            # Show individual knowledge chunks with full text
            knowledge_chunks = result.data.get('knowledge_chunks', [])
            if knowledge_chunks:
                print(f"\n📚 INDIVIDUAL KNOWLEDGE CHUNKS:")
                for j, chunk in enumerate(knowledge_chunks, 1):
                    print(f"\n   CHUNK {j}:")
                    print(f"   Score: {chunk.get('relevance_score', 0):.3f}")
                    print(f"   Source: {chunk.get('source', 'Unknown')}")
                    if chunk.get('page_number'):
                        print(f"   Page: {chunk.get('page_number')}")
                    print(f"   Full Text:")
                    print(f"   {chunk.get('text', '')}")
                    print("-" * 30)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_raw_knowledge())