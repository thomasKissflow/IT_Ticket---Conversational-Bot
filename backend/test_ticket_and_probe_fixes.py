#!/usr/bin/env python3
"""
Test the ticket and probe query fixes.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import VoiceAssistantOrchestrator
from agents.base_agent import ConversationContext


async def test_ticket_and_probe_fixes():
    """Test the ticket and probe query fixes."""
    
    print("🔧 Testing Ticket and Probe Query Fixes")
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
    
    # Test queries that were problematic
    test_queries = [
        "Details about my ticket 14",
        "Details",  # This should be followup
        "how do I add a probe in superops",
        "give me more details"  # This should be followup after the probe question
    ]
    
    print(f"\n🎯 Testing {len(test_queries)} queries:")
    print("-" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 30)
        
        try:
            # Process through the full system
            supervisor_result = await orchestrator.supervisor_agent.process_query(
                query, orchestrator.current_session
            )
            
            # Get intent and routing decision
            intent_data = supervisor_result.data.get('intent')
            routing = supervisor_result.data.get('routing_decision', [])
            
            if intent_data:
                print(f"🧠 Intent: {intent_data.intent_type.value} (confidence: {intent_data.confidence:.2f})")
                if hasattr(intent_data, 'entities') and intent_data.entities:
                    print(f"   Entities: {intent_data.entities}")
            
            print(f"🔀 Routing: {routing}")
            
            # Coordinate agents
            agent_results = await orchestrator._coordinate_agents_simple(supervisor_result, query)
            
            # Generate response
            response = await orchestrator._generate_response(agent_results)
            
            print(f"🤖 Agents involved: {[r.agent_name for r in agent_results]}")
            
            print(f"\n💬 Response:")
            print("-" * 20)
            print(response[:200] + "..." if len(response) > 200 else response)
            print("-" * 20)
            
            # Add to conversation history for follow-up context
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
            
            # Assessment
            if intent_data:
                expected_intent = None
                if "ticket" in query.lower() and any(char.isdigit() for char in query):
                    expected_intent = "ticket_query"
                elif query.lower() in ["details", "give me more details"]:
                    expected_intent = "followup"
                elif "how do i" in query.lower() or "probe" in query.lower():
                    expected_intent = "knowledge_query"
                
                if expected_intent and intent_data.intent_type.value == expected_intent:
                    print(f"✅ Correct intent classification: {intent_data.intent_type.value}")
                elif expected_intent:
                    print(f"❌ Wrong intent: expected {expected_intent}, got {intent_data.intent_type.value}")
                else:
                    print(f"ℹ️ Intent: {intent_data.intent_type.value}")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 50)
    
    print("\n🏁 Ticket and probe fixes test complete!")


if __name__ == "__main__":
    try:
        asyncio.run(test_ticket_and_probe_fixes())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()