#!/usr/bin/env python3
"""
Demo Test Script for Agentic Voice Assistant
Tests 5 different question types and measures performance metrics
Perfect for presentation to judges showing system capabilities
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import uuid
from dotenv import load_dotenv

# Import system components
from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext, AgentResult
from services.response_humanizer import humanize_agent_response
from performance_optimizer import PerformanceOptimizer

# Load environment
load_dotenv()

class DemoTestRunner:
    """Runs comprehensive demo tests for presentation purposes."""
    
    def __init__(self):
        self.aws_region = 'us-east-2'
        self.supervisor_agent = None
        self.ticket_agent = None
        self.knowledge_agent = None
        self.performance_optimizer = None
        self.test_results = []
        
    async def initialize(self):
        """Initialize all agents and components."""
        print("🚀 Initializing Demo Test Environment...")
        
        # Initialize agents
        self.supervisor_agent = SupervisorAgent(self.aws_region)
        self.ticket_agent = TicketAgent()
        self.knowledge_agent = KnowledgeAgent()
        
        # Initialize performance optimizer
        self.performance_optimizer = PerformanceOptimizer(
            target_response_time=0.5,
            aws_region=self.aws_region
        )
        await self.performance_optimizer.initialize_async_components()
        
        print("✅ All components initialized successfully!")
        
    async def run_demo_tests(self):
        """Run 5 different types of questions to showcase system capabilities."""
        
        # Test questions covering different scenarios
        test_questions = [
            {
                "id": 1,
                "question": "What's the status of ticket IT 001?",
                "type": "Ticket Lookup",
                "expected_agents": ["SupervisorAgent", "TicketAgent"],
                "description": "Direct ticket status inquiry"
            },
            {
                "id": 2,
                "question": "What is a probe in Super OPS?",
                "type": "Knowledge Base Query",
                "expected_agents": ["SupervisorAgent", "KnowledgeAgent"],
                "description": "General help/documentation question"
            },
            {
                "id": 3,
                "question": "Yes give me more info about that",
                "type": "Follow up question",
                "expected_agents": ["SupervisorAgent", "KnowledgeAgent"],
                "description": "Follow up to previous question"
            },
            {
                "id": 4,
                "question": "What was the category of my ticket and what was its resolution time?",
                "type": "Context based question",
                "expected_agents": ["SupervisorAgent", "TicketAgent"],
                "description": "Previous context based response needed"
            },
            {
                "id": 5,
                "question": "I would like to talk to a human anyways, can you connect to one?",
                "type": "Support Request",
                "expected_agents": ["SupervisorAgent"],
                "description": "Ambiguous query requiring intelligent routing"
            }
        ]
        
        print("\n" + "="*80)
        print("🎯 AGENTIC VOICE ASSISTANT DEMO - PERFORMANCE SHOWCASE")
        print("="*80)
        
        for test_case in test_questions:
            await self._run_single_test(test_case)
            print("\n" + "-"*60)
            
        # Generate summary report
        await self._generate_summary_report()
        
    async def _run_single_test(self, test_case: Dict[str, Any]):
        """Run a single test case and collect metrics."""
        
        print(f"\n🧪 TEST {test_case['id']}: {test_case['type']}")
        print(f"❓ Question: {test_case['question']}")
        print(f"📝 Description: {test_case['description']}")
        
        # Create conversation context
        session = ConversationContext(
            session_id=str(uuid.uuid4()),
            user_id=f"demo_user_{test_case['id']}"
        )
        session.add_message(test_case['question'], "user", confidence=1.0)
        
        # Start timing
        start_time = time.time()
        
        try:
            # Step 1: Supervisor Agent Processing
            print("\n🧠 Step 1: Intent Analysis & Routing...")
            supervisor_start = time.time()
            
            supervisor_result = await self.supervisor_agent.process_query(
                test_case['question'], session
            )
            
            supervisor_time = time.time() - supervisor_start
            
            # Extract routing decision
            intent_data = supervisor_result.data.get('intent')
            routing_decision = supervisor_result.data.get('routing_decision', [])
            
            print(f"   🎯 Intent: {intent_data.intent_type.value if intent_data else 'Unknown'}")
            print(f"   🔀 Routing: {routing_decision}")
            print(f"   ⏱️  Time: {supervisor_time:.3f}s")
            
            # Step 2: Agent Coordination
            print("\n🤖 Step 2: Agent Execution...")
            agent_results = [supervisor_result]
            agent_times = {"SupervisorAgent": supervisor_time}
            
            # Execute routed agents
            if 'ticket' in routing_decision:
                ticket_start = time.time()
                ticket_result = await self.ticket_agent.process_query(test_case['question'], session)
                ticket_time = time.time() - ticket_start
                
                agent_results.append(ticket_result)
                agent_times["TicketAgent"] = ticket_time
                print(f"   📋 TicketAgent: {ticket_time:.3f}s")
                
                # Show ticket data if found
                if ticket_result.data.get('found'):
                    ticket = ticket_result.data.get('ticket', {})
                    print(f"      → Found: {ticket.get('id')} - {ticket.get('status')}")
                else:
                    print(f"      → No tickets found")
            
            if 'knowledge' in routing_decision:
                knowledge_start = time.time()
                knowledge_result = await self.knowledge_agent.process_query(test_case['question'], session)
                knowledge_time = time.time() - knowledge_start
                
                agent_results.append(knowledge_result)
                agent_times["KnowledgeAgent"] = knowledge_time
                print(f"   📚 KnowledgeAgent: {knowledge_time:.3f}s")
                
                # Show knowledge data if found
                if knowledge_result.data.get('found'):
                    print(f"      → Found relevant documentation")
                else:
                    print(f"      → No relevant docs found")
            
            # Step 3: Response Generation
            print("\n💬 Step 3: Response Generation...")
            response_start = time.time()
            
            # Convert to format expected by humanizer
            agent_data = []
            for result in agent_results:
                agent_data.append({
                    'agent_name': result.agent_name,
                    'data': result.data,
                    'confidence': result.confidence,
                    'requires_escalation': result.requires_escalation
                })
            
            response = await humanize_agent_response(
                agent_data,
                test_case['question'],
                context={'session_id': session.session_id}
            )
            
            response_time = time.time() - response_start
            total_time = time.time() - start_time
            
            print(f"   ⏱️  Time: {response_time:.3f}s")
            
            # Calculate metrics
            overall_confidence = sum(r.confidence for r in agent_results) / len(agent_results)
            agents_used = [r.agent_name for r in agent_results]
            
            # Store results
            test_result = {
                'test_id': test_case['id'],
                'question_type': test_case['type'],
                'question': test_case['question'],
                'total_time': total_time,
                'agent_times': agent_times,
                'agents_used': agents_used,
                'expected_agents': test_case['expected_agents'],
                'routing_accuracy': len(set(agents_used) & set(test_case['expected_agents'])) / len(test_case['expected_agents']),
                'overall_confidence': overall_confidence,
                'response_length': len(response),
                'intent_detected': intent_data.intent_type.value if intent_data else 'Unknown',
                'escalation_required': any(r.requires_escalation for r in agent_results),
                'response_preview': response[:100] + "..." if len(response) > 100 else response
            }
            
            self.test_results.append(test_result)
            
            # Display results
            print(f"\n📊 RESULTS:")
            print(f"   ⏱️  Total Time: {total_time:.3f}s")
            print(f"   🤖 Agents Used: {', '.join(agents_used)}")
            print(f"   🎯 Routing Accuracy: {test_result['routing_accuracy']*100:.1f}%")
            print(f"   📈 Confidence: {overall_confidence:.2f}")
            print(f"   🚨 Escalation: {'Yes' if test_result['escalation_required'] else 'No'}")
            print(f"   💬 Response: {test_result['response_preview']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            # Still record the failure
            self.test_results.append({
                'test_id': test_case['id'],
                'question_type': test_case['type'],
                'question': test_case['question'],
                'error': str(e),
                'total_time': time.time() - start_time,
                'agents_used': [],
                'routing_accuracy': 0.0,
                'overall_confidence': 0.0
            })
    
    async def _generate_summary_report(self):
        """Generate comprehensive summary report for presentation."""
        
        print("\n" + "="*80)
        print("📈 PERFORMANCE SUMMARY REPORT")
        print("="*80)
        
        if not self.test_results:
            print("❌ No test results available")
            return
        
        # Calculate aggregate metrics
        successful_tests = [r for r in self.test_results if 'error' not in r]
        total_tests = len(self.test_results)
        success_rate = len(successful_tests) / total_tests * 100
        
        if successful_tests:
            avg_response_time = sum(r['total_time'] for r in successful_tests) / len(successful_tests)
            avg_confidence = sum(r['overall_confidence'] for r in successful_tests) / len(successful_tests)
            avg_routing_accuracy = sum(r['routing_accuracy'] for r in successful_tests) / len(successful_tests)
            
            # Response time breakdown
            fast_responses = len([r for r in successful_tests if r['total_time'] < 1.0])
            medium_responses = len([r for r in successful_tests if 1.0 <= r['total_time'] < 2.0])
            slow_responses = len([r for r in successful_tests if r['total_time'] >= 2.0])
            
            print(f"\n🎯 OVERALL PERFORMANCE:")
            print(f"   ✅ Success Rate: {success_rate:.1f}% ({len(successful_tests)}/{total_tests})")
            print(f"   ⏱️  Average Response Time: {avg_response_time:.3f}s")
            print(f"   📈 Average Confidence: {avg_confidence:.2f}")
            print(f"   🎯 Average Routing Accuracy: {avg_routing_accuracy*100:.1f}%")
            
            print(f"\n⚡ RESPONSE TIME DISTRIBUTION:")
            print(f"   🟢 Fast (<1s): {fast_responses} tests ({fast_responses/len(successful_tests)*100:.1f}%)")
            print(f"   🟡 Medium (1-2s): {medium_responses} tests ({medium_responses/len(successful_tests)*100:.1f}%)")
            print(f"   🔴 Slow (>2s): {slow_responses} tests ({slow_responses/len(successful_tests)*100:.1f}%)")
            
            # Agent usage statistics
            agent_usage = {}
            for result in successful_tests:
                for agent in result['agents_used']:
                    agent_usage[agent] = agent_usage.get(agent, 0) + 1
            
            print(f"\n🤖 AGENT UTILIZATION:")
            for agent, count in sorted(agent_usage.items()):
                percentage = count / len(successful_tests) * 100
                print(f"   {agent}: {count}/{len(successful_tests)} tests ({percentage:.1f}%)")
            
            # Question type performance
            print(f"\n📊 PERFORMANCE BY QUESTION TYPE:")
            type_performance = {}
            for result in successful_tests:
                q_type = result['question_type']
                if q_type not in type_performance:
                    type_performance[q_type] = {'times': [], 'confidence': []}
                type_performance[q_type]['times'].append(result['total_time'])
                type_performance[q_type]['confidence'].append(result['overall_confidence'])
            
            for q_type, data in type_performance.items():
                avg_time = sum(data['times']) / len(data['times'])
                avg_conf = sum(data['confidence']) / len(data['confidence'])
                print(f"   {q_type}:")
                print(f"      ⏱️  Avg Time: {avg_time:.3f}s")
                print(f"      📈 Avg Confidence: {avg_conf:.2f}")
        
        # Generate JSON report for easy integration
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'successful_tests': len(successful_tests),
                'success_rate': success_rate,
                'average_response_time': avg_response_time if successful_tests else 0,
                'average_confidence': avg_confidence if successful_tests else 0,
                'average_routing_accuracy': avg_routing_accuracy if successful_tests else 0
            },
            'detailed_results': self.test_results
        }
        
        # Save report
        with open('demo_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: demo_test_report.json")
        
        # Key takeaways for presentation
        print(f"\n🎤 KEY TAKEAWAYS FOR PRESENTATION:")
        print(f"   • Multi-agent system successfully routes {avg_routing_accuracy*100:.1f}% of queries correctly")
        print(f"   • Average response time of {avg_response_time:.2f}s demonstrates real-time capability")
        print(f"   • {avg_confidence:.1%} average confidence shows reliable AI decision-making")
        print(f"   • System handles diverse query types from simple lookups to complex multi-agent coordination")
        print(f"   • Robust error handling ensures {success_rate:.1f}% success rate")


async def main():
    """Main demo execution function."""
    
    print("🎭 AGENTIC VOICE ASSISTANT - DEMO TEST SUITE")
    print("=" * 50)
    print("This demo showcases the system's multi-agent capabilities")
    print("Perfect for presentation to judges!")
    print()
    
    demo = DemoTestRunner()
    
    try:
        await demo.initialize()
        await demo.run_demo_tests()
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"📋 Check 'demo_test_report.json' for detailed metrics")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())