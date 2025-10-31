#!/usr/bin/env python3
"""
Test script to compare fast intent classification vs LLM-based classification.
"""

import asyncio
import time
from agents.supervisor_agent import SupervisorAgent
from agents.base_agent import ConversationContext
from services.fast_intent_classifier import classify_intent_fast

async def test_intent_speed():
    """Test the speed difference between fast and LLM-based intent classification."""
    
    print("🚀 Testing Intent Classification Speed")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "status of my ticket 001",
        "ticket description of 002", 
        "resolution for ticket 004",
        "what is a probe in superops",
        "how do i add a probe",
        "hello how are you",
        "escalate to human"
    ]
    
    supervisor = SupervisorAgent()
    context = ConversationContext("test_session")
    
    print("🏃‍♂️ Fast Rule-Based Classification:")
    print("-" * 40)
    
    fast_total_time = 0
    fast_results = []
    
    for query in test_queries:
        start_time = time.time()
        fast_intent = classify_intent_fast(query)
        end_time = time.time()
        
        processing_time = end_time - start_time
        fast_total_time += processing_time
        
        if fast_intent:
            print(f"✅ '{query}'")
            print(f"   Intent: {fast_intent.intent_type.value}")
            print(f"   Confidence: {fast_intent.confidence:.2f}")
            print(f"   Entities: {fast_intent.entities}")
            print(f"   Time: {processing_time*1000:.1f}ms")
            fast_results.append(True)
        else:
            print(f"❌ '{query}' - No fast classification")
            fast_results.append(False)
        print()
    
    print(f"📊 Fast Classification Summary:")
    print(f"   Total Time: {fast_total_time*1000:.1f}ms")
    print(f"   Average Time: {(fast_total_time/len(test_queries))*1000:.1f}ms per query")
    print(f"   Success Rate: {sum(fast_results)}/{len(test_queries)} ({sum(fast_results)/len(test_queries)*100:.1f}%)")
    
    print("\n" + "="*60)
    print("🐌 Full Supervisor Classification (with fast classifier):")
    print("-" * 40)
    
    supervisor_total_time = 0
    
    for query in test_queries:
        start_time = time.time()
        intent = await supervisor.analyze_intent(query, context)
        end_time = time.time()
        
        processing_time = end_time - start_time
        supervisor_total_time += processing_time
        
        print(f"✅ '{query}'")
        print(f"   Intent: {intent.intent_type.value}")
        print(f"   Confidence: {intent.confidence:.2f}")
        print(f"   Time: {processing_time*1000:.1f}ms")
        print()
    
    print(f"📊 Supervisor Classification Summary:")
    print(f"   Total Time: {supervisor_total_time*1000:.1f}ms")
    print(f"   Average Time: {(supervisor_total_time/len(test_queries))*1000:.1f}ms per query")
    
    print("\n" + "="*60)
    print("🏆 Speed Comparison:")
    print(f"   Fast Classifier: {(fast_total_time/len(test_queries))*1000:.1f}ms avg")
    print(f"   Supervisor (with fast): {(supervisor_total_time/len(test_queries))*1000:.1f}ms avg")
    print(f"   Speed Improvement: {((supervisor_total_time - fast_total_time) / supervisor_total_time * 100):.1f}%")

if __name__ == "__main__":
    asyncio.run(test_intent_speed())