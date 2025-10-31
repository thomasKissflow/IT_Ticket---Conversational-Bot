#!/usr/bin/env python3
"""
Test to debug why real-time is slow vs tests.
"""

import asyncio
import time
from agents.supervisor_agent import SupervisorAgent
from agents.base_agent import ConversationContext
from services.fast_intent_classifier import classify_intent_fast

async def test_realtime_vs_fast():
    """Test the difference between real-time and fast classification."""
    
    queries = [
        "What is the status of my ticket IT 001",
        "How to add a probe",
        "Hello how are you",
        "Escalate to human"
    ]
    
    print("🧪 Testing Real-time vs Fast Classification")
    print("=" * 60)
    
    supervisor = SupervisorAgent()
    context = ConversationContext("test")
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        # Test 1: Fast classifier directly
        start_time = time.time()
        fast_result = classify_intent_fast(query)
        fast_time = time.time() - start_time
        
        if fast_result:
            print(f"⚡ Fast: {fast_result.intent_type.value} ({fast_time*1000:.1f}ms)")
        else:
            print(f"❌ Fast: No result ({fast_time*1000:.1f}ms)")
        
        # Test 2: Supervisor (should use fast classifier)
        start_time = time.time()
        supervisor_result = await supervisor.analyze_intent(query, context)
        supervisor_time = time.time() - start_time
        
        print(f"🧠 Supervisor: {supervisor_result.intent_type.value} ({supervisor_time*1000:.1f}ms)")
        
        # Check if supervisor used fast classifier
        if fast_result and supervisor_result.intent_type == fast_result.intent_type:
            print("✅ Supervisor used fast classifier")
        else:
            print("❌ Supervisor fell back to LLM")

if __name__ == "__main__":
    asyncio.run(test_realtime_vs_fast())