#!/usr/bin/env python3
"""
Test the follow-up question fixes.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VoiceAssistantOrchestrator
from agents.base_agent import ConversationContext


async def test_follow_up_fixes():
    """Test the follow-up question fixes."""
    
    print("🔧 Testing Follow-up Question Fixes")
    print("=" * 60)
    
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
    
    # Test sequence: initial question -> "I have another question" -> "give me more details"
    test_sequence = [
        "what is a probe in superops",
        "I have another question", 
        "give step by step info to create a subnet manually in superops",
        "give me more details"
    ]
    
    print(f"\n🎯 Testing sequence of {len(test_sequence)} queries:")
    print("-" * 50)
    
    for i, query in enumerate(test_sequence, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 30)
        
        try:
            # Process through the full system
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
            
            print(f"🤖 Agents involved: {[r.agent_name for r in agent_results]}")
            
            print(f"\n💬 Response:")
            print("-" * 20)
            print(response)
            print("-" * 20)
            
            # Add to conversation history (simulate what the main system does)
            orchestrator.current_session.add_message(query, "user", confidence=1.0)
            orchestrator.current_session.add_message(
                response, 
                "assistant", 
                confidence=orchestrator._calculate_overall_confidence(agent_results)
            )
            
            # Store response data for follow-up questions
            orchestrator.current_session.last_response_data = {
                'agent_results': [
                    {
                        'agent_name': result.agent_name,
                        'data': result.data,
                        'confidence': result.confidence,
                        'requires_escalation': result.requires_escalation
                    } for result in agent_results
                ],
                'original_query': query,
                'response': response,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # Check escalation
            needs_escalation = any(r.requires_escalation for r in agent_results)
            print(f"🚨 Needs escalation: {needs_escalation}")
            
            # Show if we have stored response data
            if orchestrator.current_session.last_response_data:
                print(f"💾 Stored response data for follow-ups: ✅")
            else:
                print(f"💾 Stored response data for follow-ups: ❌")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 50)
    
    print("\n🏁 Follow-up fixes test complete!")


if __name__ == "__main__":
    try:
        asyncio.run(test_follow_up_fixes())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()