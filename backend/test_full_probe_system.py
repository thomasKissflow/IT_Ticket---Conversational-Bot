#!/usr/bin/env python3
"""
Test the full system with probe query to see what happens in humanization.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from agents.supervisor_agent import SupervisorAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response


async def test_full_probe_system():
    """Test the full system with probe query."""
    
    print("🔧 Testing Full Probe System")
    print("=" * 60)
    
    # Initialize components
    supervisor = SupervisorAgent()
    knowledge_agent = KnowledgeAgent()
    context = ConversationContext(session_id="probe_system_test", user_id="test_user")
    
    query = "how do I add a probe in superops"
    
    print(f"📝 Query: {query}")
    print("-" * 30)
    
    try:
        # Step 1: Supervisor analysis
        print("🧠 Step 1: Supervisor Analysis")
        supervisor_result = await supervisor.process_query(query, context)
        
        intent_data = supervisor_result.data.get('intent')
        routing = supervisor_result.data.get('routing_decision', [])
        
        if intent_data:
            print(f"   Intent: {intent_data.intent_type.value} (confidence: {intent_data.confidence:.2f})")
        print(f"   Routing: {routing}")
        
        # Step 2: Knowledge Agent Processing
        if 'knowledge' in routing:
            print("\n📚 Step 2: Knowledge Agent Processing")
            knowledge_result = await knowledge_agent.process_query(query, context)
            
            print(f"   Confidence: {knowledge_result.confidence:.2f}")
            print(f"   Chunks found: {knowledge_result.data.get('chunks_found', 0)}")
            print(f"   Relevant chunks: {knowledge_result.data.get('relevant_chunks', 0)}")
            
            # Show raw contextual response
            contextual_response = knowledge_result.data.get('contextual_response', {})
            if contextual_response:
                print(f"\n   Raw Contextual Response:")
                raw_answer = contextual_response.get('answer', 'No answer')
                print(f"   {raw_answer}")
            
            # Step 3: Response Humanization
            print("\n🗣️ Step 3: Response Humanization")
            
            # Convert to format expected by humanizer
            agent_results = [
                {
                    'agent_name': 'SupervisorAgent',
                    'data': supervisor_result.data,
                    'confidence': supervisor_result.confidence,
                    'requires_escalation': supervisor_result.requires_escalation
                },
                {
                    'agent_name': 'KnowledgeAgent',
                    'data': knowledge_result.data,
                    'confidence': knowledge_result.confidence,
                    'requires_escalation': knowledge_result.requires_escalation
                }
            ]
            
            # Test humanization
            humanized_response = await humanize_agent_response(
                agent_results, 
                query,
                context={'session_id': context.session_id}
            )
            
            print(f"   Humanized Response:")
            print(f"   {humanized_response}")
            
            # Compare lengths
            print(f"\n📊 Comparison:")
            print(f"   Raw length: {len(raw_answer)} characters")
            print(f"   Humanized length: {len(humanized_response)} characters")
            
            # Check if it's a step-by-step query
            is_step_query = any(word in query.lower() for word in ['how', 'steps', 'step by step', 'guide'])
            print(f"   Detected as step-by-step query: {is_step_query}")
            
        else:
            print("❌ No knowledge routing - unexpected!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_probe_system())