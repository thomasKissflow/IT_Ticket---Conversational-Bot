#!/usr/bin/env python3
"""
Test script for KnowledgeAgent with specific queries about SuperOps.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext


async def test_knowledge_agent():
    """Test the KnowledgeAgent with specific SuperOps queries."""
    
    print("🧪 Testing KnowledgeAgent")
    print("=" * 50)
    
    # Initialize the agent
    try:
        agent = KnowledgeAgent()
        print("✅ KnowledgeAgent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize KnowledgeAgent: {e}")
        return
    
    # Health check
    try:
        health_ok = await agent.health_check()
        if health_ok:
            print("✅ Health check passed")
        else:
            print("⚠️ Health check failed, but continuing...")
    except Exception as e:
        print(f"⚠️ Health check error: {e}, but continuing...")
    
    # Create a conversation context
    context = ConversationContext(session_id="test_session", user_id="test_user")
    
    # Test queries
    test_queries = [
        "what is a probe in superops",
        "give step by step info to create a subnet manually in superops"
    ]
    
    print(f"\n🎯 Testing {len(test_queries)} queries:")
    print("-" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 30)
        
        try:
            # Process the query
            start_time = datetime.now()
            result = await agent.process_query(query, context)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Display results
            print(f"⏱️ Processing time: {processing_time:.2f}s")
            print(f"🎯 Confidence: {result.confidence:.2f}")
            print(f"🚨 Requires escalation: {result.requires_escalation}")
            
            # Show the data
            data = result.data
            print(f"\n📊 Results:")
            print(f"   - Chunks found: {data.get('chunks_found', 0)}")
            print(f"   - Relevant chunks: {data.get('relevant_chunks', 0)}")
            
            # Show contextual response
            contextual_response = data.get('contextual_response', {})
            if contextual_response:
                print(f"\n💬 Response:")
                print(f"   Answer: {contextual_response.get('answer', 'No answer')}")
                print(f"   Sources: {contextual_response.get('sources', [])}")
                print(f"   Response confidence: {contextual_response.get('confidence', 0):.2f}")
            
            # Show knowledge chunks (first few)
            knowledge_chunks = data.get('knowledge_chunks', [])
            if knowledge_chunks:
                print(f"\n📚 Top knowledge chunks:")
                for j, chunk in enumerate(knowledge_chunks[:3], 1):
                    print(f"   {j}. Score: {chunk.get('relevance_score', 0):.3f}")
                    print(f"      Source: {chunk.get('source', 'Unknown')}")
                    if chunk.get('page_number'):
                        print(f"      Page: {chunk.get('page_number')}")
                    
                    # Show first 100 characters of text
                    text = chunk.get('text', '')
                    preview = text[:100] + "..." if len(text) > 100 else text
                    print(f"      Text: {preview}")
                    print()
            else:
                print("   No relevant chunks found")
            
            # Overall assessment
            print(f"\n🔍 Assessment:")
            if result.confidence >= 0.7:
                print("   ✅ High confidence - Good response expected")
            elif result.confidence >= 0.5:
                print("   ⚠️ Medium confidence - Acceptable response")
            elif result.confidence >= 0.3:
                print("   ⚠️ Low confidence - May need clarification")
            else:
                print("   ❌ Very low confidence - Likely needs escalation")
            
            if result.requires_escalation:
                print("   🚨 Escalation recommended")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 50)
    
    print("\n🏁 Testing complete!")


if __name__ == "__main__":
    try:
        asyncio.run(test_knowledge_agent())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()