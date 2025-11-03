#!/usr/bin/env python3
"""
Quick test to verify performance improvements.
"""

import asyncio
import time
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.response_humanizer import humanize_agent_response


async def test_performance_fixes():
    """Test performance improvements in response humanizer."""
    
    print("⚡ Testing Performance Fixes")
    print("=" * 50)
    
    # Test cases that should be fast
    test_cases = [
        {
            "query": "Details about my ticket 001",
            "agent_results": [
                {
                    'agent_name': 'SupervisorAgent',
                    'data': {'intent': {'intent_type': 'ticket_query'}},
                    'confidence': 0.95,
                    'requires_escalation': False
                },
                {
                    'agent_name': 'TicketAgent',
                    'data': {
                        'type': 'specific_ticket',
                        'found': True,
                        'ticket': {
                            'id': 'IT-001',
                            'status': 'Resolved',
                            'title': 'Test ticket',
                            'resolution': 'Fixed the issue'
                        }
                    },
                    'confidence': 0.95,
                    'requires_escalation': False
                }
            ]
        },
        {
            "query": "I have another question",
            "agent_results": [
                {
                    'agent_name': 'SupervisorAgent',
                    'data': {
                        'intent': type('Intent', (), {
                            'intent_type': type('IntentType', (), {'value': 'followup'})(),
                            'entities': {'followup_type': 'new_question'}
                        })()
                    },
                    'confidence': 0.90,
                    'requires_escalation': False
                }
            ]
        },
        {
            "query": "what is a probe in superops",
            "agent_results": [
                {
                    'agent_name': 'SupervisorAgent',
                    'data': {'intent': {'intent_type': 'knowledge_query'}},
                    'confidence': 0.85,
                    'requires_escalation': False
                },
                {
                    'agent_name': 'KnowledgeAgent',
                    'data': {
                        'type': 'knowledge_search',
                        'relevant_chunks': 3,
                        'contextual_response': {
                            'answer': 'A probe is a tool for scanning devices',
                            'sources': ['SuperOps Manual']
                        },
                        'knowledge_chunks': [
                            {'text': 'A probe scans devices', 'relevance_score': 0.9}
                        ]
                    },
                    'confidence': 0.95,
                    'requires_escalation': False
                }
            ]
        }
    ]
    
    total_time = 0
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        agent_results = test_case["agent_results"]
        
        print(f"\n📝 Test {i}: {query}")
        
        start_time = time.time()
        
        try:
            response = await humanize_agent_response(
                agent_results,
                query,
                context={'session_id': 'test_session'}
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            total_time += processing_time
            
            print(f"   ⏱️ Time: {processing_time:.2f}s")
            print(f"   💬 Response: {response[:100]}...")
            
            if processing_time < 1.0:
                print(f"   ✅ FAST (< 1s)")
            elif processing_time < 3.0:
                print(f"   ⚠️ ACCEPTABLE (< 3s)")
            else:
                print(f"   ❌ SLOW (> 3s)")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    avg_time = total_time / len(test_cases)
    print(f"\n📊 Average time: {avg_time:.2f}s")
    
    if avg_time < 1.0:
        print("🎉 Performance is EXCELLENT!")
    elif avg_time < 2.0:
        print("✅ Performance is GOOD")
    else:
        print("⚠️ Performance needs more work")


if __name__ == "__main__":
    asyncio.run(test_performance_fixes())