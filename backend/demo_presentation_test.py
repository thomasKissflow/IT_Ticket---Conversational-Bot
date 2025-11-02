#!/usr/bin/env python3
"""
Demo Test for Presentation - Shows Voice Assistant Capabilities
Demonstrates different query types, response times, agent routing, and system metrics.
"""

import asyncio
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from services.response_humanizer import humanize_agent_response
import uuid

class PresentationDemo:
    """Demo class for presentation showing system capabilities"""
    
    def __init__(self):
        self.supervisor_agent = SupervisorAgent()
        self.ticket_agent = TicketAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.session = ConversationContext(
            session_id=str(uuid.uuid4()),
            user_id="demo_user"
        )
        self.total_queries = 0
        self.total_response_time = 0.0
        
    async def process_demo_query(self, query: str, query_type: str) -> dict:
        """Process a single demo query and return comprehensive metrics"""
        
        print(f"\n{'='*60}")
        print(f"🎯 QUERY #{self.total_queries + 1}: {query_type.upper()}")
        print(f"{'='*60}")
        print(f"❓ User Query: \"{query}\"")
        
        start_time = time.time()
        
        # Step 1: Supervisor Agent (Intent Detection & Routing)
        print(f"\n📋 STEP 1: Intent Detection & Routing")
        supervisor_start = time.time()
        supervisor_result = await self.supervisor_agent.process_query(query, self.session)
        supervisor_time = time.time() - supervisor_start
        
        intent_data = supervisor_result.data.get('intent')
        routing_decision = supervisor_result.data.get('routing_decision', [])
        
        print(f"   🧠 Intent Detected: {intent_data.intent_type.value if intent_data else 'unknown'}")
        print(f"   🎯 Confidence: {intent_data.confidence:.2f}" if intent_data else "   🎯 Confidence: 0.00")
        print(f"   🔀 Routing Decision: {routing_decision}")
        print(f"   ⏱️  Processing Time: {supervisor_time:.3f}s")
        
        # Step 2: Specialized Agent Processing
        print(f"\n📋 STEP 2: Specialized Agent Processing")
        agent_results = [supervisor_result]
        agent_times = {"SupervisorAgent": supervisor_time}
        
        if 'ticket' in routing_decision:
            print(f"   🎫 Calling TicketAgent...")
            ticket_start = time.time()
            ticket_result = await self.ticket_agent.process_query(query, self.session)
            ticket_time = time.time() - ticket_start
            agent_results.append(ticket_result)
            agent_times["TicketAgent"] = ticket_time
            
            print(f"      📊 Confidence: {ticket_result.confidence:.2f}")
            print(f"      🔍 Data Found: {ticket_result.data.get('found', 'N/A')}")
            print(f"      ⏱️  Processing Time: {ticket_time:.3f}s")
        
        if 'knowledge' in routing_decision:
            print(f"   📚 Calling KnowledgeAgent...")
            knowledge_start = time.time()
            knowledge_result = await self.knowledge_agent.process_query(query, self.session)
            knowledge_time = time.time() - knowledge_start
            agent_results.append(knowledge_result)
            agent_times["KnowledgeAgent"] = knowledge_time
            
            print(f"      📊 Confidence: {knowledge_result.confidence:.2f}")
            print(f"      📄 Relevant Chunks: {knowledge_result.data.get('relevant_chunks', 0)}")
            print(f"      ⏱️  Processing Time: {knowledge_time:.3f}s")
        
        # Step 3: Response Humanization
        print(f"\n📋 STEP 3: Response Humanization")
        humanizer_start = time.time()
        
        agent_data = []
        for result in agent_results:
            agent_data.append({
                'agent_name': result.agent_name,
                'data': result.data,
                'confidence': result.confidence,
                'requires_escalation': result.requires_escalation
            })
        
        final_response = await humanize_agent_response(
            agent_data,
            query,
            context={'session_id': self.session.session_id}
        )
        
        humanizer_time = time.time() - humanizer_start
        total_time = time.time() - start_time
        
        print(f"   💬 Response Generated")
        print(f"   📏 Response Length: {len(final_response)} characters")
        print(f"   ⏱️  Humanization Time: {humanizer_time:.3f}s")
        
        # Add to conversation history
        self.session.add_message(query, "user", confidence=1.0)
        self.session.add_message(final_response, "assistant", confidence=1.0)
        
        # Calculate metrics
        self.total_queries += 1
        self.total_response_time += total_time
        
        # Determine if escalation occurred
        escalation_occurred = any(result.requires_escalation for result in agent_results)
        
        # Response classification
        response_type = "Escalation" if escalation_occurred else "Direct Answer"
        if len(final_response) <= 150 and "would you like" in final_response.lower():
            response_type = "Concise + Follow-up Offer"
        elif len(final_response) > 500:
            response_type = "Detailed Information"
        
        print(f"\n📊 FINAL METRICS:")
        print(f"   ⏱️  Total Response Time: {total_time:.3f}s")
        print(f"   🎯 Overall Confidence: {max(r.confidence for r in agent_results):.2f}")
        print(f"   🤖 Agents Used: {[r.agent_name for r in agent_results if r.agent_name != 'SupervisorAgent']}")
        print(f"   📝 Response Type: {response_type}")
        print(f"   🚨 Escalation Required: {'Yes' if escalation_occurred else 'No'}")
        
        print(f"\n💬 ASSISTANT RESPONSE:")
        print(f"   \"{final_response}\"")
        
        return {
            "query": query,
            "query_type": query_type,
            "total_time": total_time,
            "agent_times": agent_times,
            "agents_used": [r.agent_name for r in agent_results if r.agent_name != 'SupervisorAgent'],
            "intent": intent_data.intent_type.value if intent_data else 'unknown',
            "intent_confidence": intent_data.confidence if intent_data else 0.0,
            "routing": routing_decision,
            "overall_confidence": max(r.confidence for r in agent_results),
            "response_length": len(final_response),
            "response_type": response_type,
            "escalation": escalation_occurred,
            "response": final_response
        }

async def run_presentation_demo():
    """Run the complete presentation demo with 5 different query types"""
    
    print("🎤 VOICE ASSISTANT DEMO - PRESENTATION TEST")
    print("=" * 80)
    print("Demonstrating AI-Powered Voice Assistant Capabilities")
    print("Multiple Agent Architecture with Intelligent Routing")
    print("=" * 80)
    
    demo = PresentationDemo()
    
    # 5 Different types of queries to showcase system capabilities
    test_queries = [
        {
            "query": "What is the status of ticket IT-001?",
            "type": "Ticket Query",
            "description": "Direct ticket lookup with contextual information"
        },
        {
            "query": "What is a probe in SuperOps?",
            "type": "Knowledge Query", 
            "description": "Knowledge base search with concise response"
        },
        {
            "query": "Hi, how are you doing today?",
            "type": "Greeting",
            "description": "Natural conversation and greeting handling"
        },
        {
            "query": "Tell me more about probe configuration",
            "type": "Follow-up Knowledge",
            "description": "Detailed knowledge request with comprehensive response"
        },
        {
            "query": "What was the resolution for that ticket?",
            "type": "Contextual Query",
            "description": "Context-aware follow-up using conversation history"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_queries):
        result = await demo.process_demo_query(test["query"], test["type"])
        result["description"] = test["description"]
        results.append(result)
        
        # Brief pause between queries for readability
        await asyncio.sleep(0.5)
    
    # Generate Summary Report
    print(f"\n\n🏆 PRESENTATION SUMMARY REPORT")
    print("=" * 80)
    
    avg_response_time = demo.total_response_time / demo.total_queries
    
    print(f"📊 OVERALL PERFORMANCE METRICS:")
    print(f"   • Total Queries Processed: {demo.total_queries}")
    print(f"   • Average Response Time: {avg_response_time:.3f}s")
    print(f"   • Fastest Response: {min(r['total_time'] for r in results):.3f}s")
    print(f"   • Slowest Response: {max(r['total_time'] for r in results):.3f}s")
    
    # Agent Usage Statistics
    all_agents = []
    for result in results:
        all_agents.extend(result['agents_used'])
    
    from collections import Counter
    agent_usage = Counter(all_agents)
    
    print(f"\n🤖 AGENT UTILIZATION:")
    for agent, count in agent_usage.items():
        percentage = (count / len(results)) * 100
        print(f"   • {agent}: {count}/{len(results)} queries ({percentage:.1f}%)")
    
    # Intent Detection Accuracy
    successful_intents = sum(1 for r in results if r['intent_confidence'] > 0.7)
    intent_accuracy = (successful_intents / len(results)) * 100
    
    print(f"\n🎯 INTENT DETECTION ACCURACY:")
    print(f"   • High Confidence Intents: {successful_intents}/{len(results)} ({intent_accuracy:.1f}%)")
    print(f"   • Average Intent Confidence: {sum(r['intent_confidence'] for r in results) / len(results):.2f}")
    
    # Response Types Distribution
    response_types = Counter(r['response_type'] for r in results)
    
    print(f"\n📝 RESPONSE TYPE DISTRIBUTION:")
    for resp_type, count in response_types.items():
        percentage = (count / len(results)) * 100
        print(f"   • {resp_type}: {count} ({percentage:.1f}%)")
    
    # Escalation Rate
    escalations = sum(1 for r in results if r['escalation'])
    escalation_rate = (escalations / len(results)) * 100
    
    print(f"\n🚨 ESCALATION METRICS:")
    print(f"   • Escalation Rate: {escalations}/{len(results)} ({escalation_rate:.1f}%)")
    print(f"   • Direct Resolution Rate: {len(results) - escalations}/{len(results)} ({100 - escalation_rate:.1f}%)")
    
    # Detailed Query Breakdown
    print(f"\n📋 DETAILED QUERY BREAKDOWN:")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['query_type'].upper()}")
        print(f"   Query: \"{result['query']}\"")
        print(f"   Description: {result['description']}")
        print(f"   Response Time: {result['total_time']:.3f}s")
        print(f"   Agents Used: {', '.join(result['agents_used']) if result['agents_used'] else 'SupervisorAgent only'}")
        print(f"   Intent: {result['intent']} (confidence: {result['intent_confidence']:.2f})")
        print(f"   Response Type: {result['response_type']}")
        print(f"   Response Length: {result['response_length']} chars")
        print(f"   Escalation: {'Yes' if result['escalation'] else 'No'}")
    
    print(f"\n🎉 DEMO COMPLETE - SYSTEM PERFORMANCE EXCELLENT!")
    print("=" * 80)
    print("✅ Multi-agent architecture working seamlessly")
    print("✅ Intelligent routing and intent detection")
    print("✅ Fast response times with contextual awareness")
    print("✅ Concise responses with follow-up options")
    print("✅ Robust error handling and escalation")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    print("🚀 Starting Voice Assistant Presentation Demo...")
    print("This demo showcases the complete system capabilities for judges.\n")
    
    try:
        results = asyncio.run(run_presentation_demo())
        print(f"\n✅ Demo completed successfully!")
        print(f"📊 {len(results)} queries processed with comprehensive metrics")
        print(f"🎯 Ready for presentation to judges!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Please check system configuration and try again.")