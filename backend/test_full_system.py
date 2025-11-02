#!/usr/bin/env python3
"""
Test the full system integration with knowledge queries.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VoiceAssistantOrchestrator
from agents.base_agent import ConversationContext


async def test_full_system():
    """Test knowledge queries through the full orchestrator system."""
    
    print("🎤 Testing Full System Integration")
    print("=" * 50)
    
    # Initialize the orchestrator
    orchestrator = VoiceAssistantOrchestrator()
    
    print("🔧 Initializing orchestrator...")
    try:
        success = await orchestrator.initialize()
        if not success:
            print("❌ Failed to initialize orchestrator")
            return
        print("✅ Orchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return
    
    # Test queries through the orchestrator
    test_queries = [
        "what is a probe in superops",
        "give step by step info to create a subnet manually in superops"
    ]
    
    print(f"\n🎯 Testing {len(test_queries)} queries through full system:")
    print("-" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 30)
        
        try:
            # Process through the full system (without voice)
            start_time = asyncio.get_event_loop().time()
            
            # Simulate the query processing that would happen in _process_user_query
            supervisor_result = await orchestrator.supervisor_agent.process_query(
                query, orchestrator.current_session
            )
            
            # Get routing decision
            routing = supervisor_result.data.get('routing_decision', [])
            print(f"🧠 Supervisor routing: {routing}")
            
            # Coordinate agents
            agent_results = await orchestrator._coordinate_agents_simple(supervisor_result, query)
            
            # Generate response
            response = await orchestrator._generate_response(agent_results)
            
            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time
            
            print(f"⏱️ Total processing time: {processing_time:.2f}s")
            print(f"🤖 Agents involved: {[r.agent_name for r in agent_results]}")
            
            print(f"\n💬 Final Response:")
            print("-" * 20)
            print(response)
            print("-" * 20)
            
            # Show confidence scores
            print(f"\n📊 Agent Confidence Scores:")
            for result in agent_results:
                print(f"   {result.agent_name}: {result.confidence:.2f}")
            
            overall_confidence = orchestrator._calculate_overall_confidence(agent_results)
            print(f"   Overall: {overall_confidence:.2f}")
            
            # Check escalation
            needs_escalation = any(r.requires_escalation for r in agent_results)
            print(f"🚨 Needs escalation: {needs_escalation}")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 50)
    
    print("\n🏁 Full system test complete!")


if __name__ == "__main__":
    try:
        asyncio.run(test_full_system())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()