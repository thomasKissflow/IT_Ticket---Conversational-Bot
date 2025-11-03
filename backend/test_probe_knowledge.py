#!/usr/bin/env python3
"""
Test probe knowledge specifically.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext


async def test_probe_knowledge():
    """Test probe-related knowledge queries."""
    
    print("🔍 Testing Probe Knowledge")
    print("=" * 50)
    
    # Initialize the agent
    agent = KnowledgeAgent()
    context = ConversationContext(session_id="probe_test", user_id="test_user")
    
    # Test probe-related queries
    probe_queries = [
        "how do I add a probe in superops",
        "how to add a probe in superops", 
        "steps to add probe",
        "probe installation superops",
        "add probe superops"
    ]
    
    for i, query in enumerate(probe_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 30)
        
        try:
            result = await agent.process_query(query, context)
            
            print(f"⏱️ Processing time: {result.processing_time:.2f}s")
            print(f"🎯 Confidence: {result.confidence:.2f}")
            print(f"📊 Chunks found: {result.data.get('chunks_found', 0)}")
            print(f"📊 Relevant chunks: {result.data.get('relevant_chunks', 0)}")
            
            # Show contextual response
            contextual_response = result.data.get('contextual_response', {})
            if contextual_response:
                print(f"\n💬 Response:")
                answer = contextual_response.get('answer', 'No answer')
                print(f"   {answer[:200]}..." if len(answer) > 200 else f"   {answer}")
                print(f"   Sources: {contextual_response.get('sources', [])}")
            
            # Show top knowledge chunks
            knowledge_chunks = result.data.get('knowledge_chunks', [])
            if knowledge_chunks:
                print(f"\n📚 Top knowledge chunks:")
                for j, chunk in enumerate(knowledge_chunks[:2], 1):
                    print(f"   {j}. Score: {chunk.get('relevance_score', 0):.3f}")
                    print(f"      Source: {chunk.get('source', 'Unknown')}")
                    text = chunk.get('text', '')
                    preview = text[:150] + "..." if len(text) > 150 else text
                    print(f"      Text: {preview}")
                    print()
            
            # Assessment
            if result.confidence >= 0.7:
                print("✅ High confidence - Good response")
            elif result.confidence >= 0.5:
                print("⚠️ Medium confidence - Acceptable")
            else:
                print("❌ Low confidence - May need improvement")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(test_probe_knowledge())