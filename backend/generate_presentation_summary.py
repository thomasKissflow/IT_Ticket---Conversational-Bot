#!/usr/bin/env python3
"""
Generate a presentation-ready summary from demo test results
Creates formatted output perfect for slides and judge presentations
"""

import json
import sys
from datetime import datetime
from pathlib import Path

def load_test_results():
    """Load the demo test results."""
    report_file = Path("demo_test_report.json")
    
    if not report_file.exists():
        print("❌ No demo test report found. Please run the demo first:")
        print("   python run_demo.py")
        return None
    
    with open(report_file, 'r') as f:
        return json.load(f)

def generate_presentation_summary(data):
    """Generate presentation-ready summary."""
    
    summary = data['summary']
    results = data['detailed_results']
    
    print("=" * 80)
    print("🎯 AGENTIC VOICE ASSISTANT - PRESENTATION SUMMARY")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Executive Summary
    print("📊 EXECUTIVE SUMMARY")
    print("-" * 40)
    print(f"✅ Success Rate: {summary['success_rate']:.1f}%")
    print(f"⚡ Avg Response Time: {summary['average_response_time']:.2f} seconds")
    print(f"🎯 Routing Accuracy: {summary['average_routing_accuracy']*100:.1f}%")
    print(f"📈 Avg Confidence: {summary['average_confidence']:.1%}")
    print(f"🧪 Tests Completed: {summary['successful_tests']}/{summary['total_tests']}")
    print()
    
    # Performance Highlights
    print("🏆 KEY PERFORMANCE HIGHLIGHTS")
    print("-" * 40)
    
    # Find fastest response
    fastest = min(results, key=lambda x: x.get('total_time', float('inf')))
    print(f"⚡ Fastest Response: {fastest['total_time']:.3f}s ({fastest['question_type']})")
    
    # Find highest confidence
    highest_conf = max(results, key=lambda x: x.get('overall_confidence', 0))
    print(f"🎯 Highest Confidence: {highest_conf['overall_confidence']:.1%} ({highest_conf['question_type']})")
    
    # Count multi-agent queries
    multi_agent = [r for r in results if len(r.get('agents_used', [])) > 2]
    print(f"🤖 Multi-Agent Coordination: {len(multi_agent)} complex queries handled")
    
    # Response time categories
    fast = len([r for r in results if r.get('total_time', 0) < 1.0])
    print(f"🟢 Sub-second Responses: {fast}/{len(results)} ({fast/len(results)*100:.1f}%)")
    print()
    
    # Detailed Test Results
    print("📋 DETAILED TEST RESULTS")
    print("-" * 40)
    
    for i, result in enumerate(results, 1):
        if 'error' in result:
            print(f"{i}. ❌ {result['question_type']} - FAILED")
            continue
            
        print(f"{i}. {result['question_type']}")
        print(f"   ❓ Question: {result['question'][:60]}...")
        print(f"   ⏱️  Time: {result['total_time']:.3f}s")
        print(f"   🤖 Agents: {', '.join(result['agents_used'])}")
        print(f"   📈 Confidence: {result['overall_confidence']:.1%}")
        print(f"   🎯 Routing: {result['routing_accuracy']*100:.1f}% accurate")
        
        if result.get('escalation_required'):
            print(f"   🚨 Escalation: Required")
        print()
    
    # Technology Showcase
    print("🔧 TECHNOLOGY SHOWCASE")
    print("-" * 40)
    print("✅ Multi-Agent AI Architecture")
    print("   • Supervisor Agent for intelligent routing")
    print("   • Specialized Ticket and Knowledge agents")
    print("   • Dynamic agent coordination")
    print()
    print("✅ Real-Time Performance")
    print(f"   • Average response: {summary['average_response_time']:.2f}s")
    print("   • Concurrent agent processing")
    print("   • Performance monitoring & optimization")
    print()
    print("✅ Intelligent Query Understanding")
    print(f"   • {summary['average_routing_accuracy']*100:.1f}% routing accuracy")
    print("   • Intent classification and context awareness")
    print("   • Natural language processing")
    print()
    print("✅ Enterprise Integration Ready")
    print("   • AWS Bedrock AI integration")
    print("   • Scalable microservices architecture")
    print("   • Real-time WebSocket communication")
    print()
    
    # Judge Talking Points
    print("🎤 KEY TALKING POINTS FOR JUDGES")
    print("-" * 40)
    print("1. INNOVATION:")
    print("   • Multi-agent architecture enables specialized expertise")
    print("   • Real-time voice interaction with sub-second responses")
    print("   • Intelligent routing reduces query resolution time")
    print()
    print("2. TECHNICAL EXCELLENCE:")
    print(f"   • {summary['success_rate']:.1f}% success rate demonstrates reliability")
    print(f"   • {summary['average_routing_accuracy']*100:.1f}% routing accuracy shows smart decision-making")
    print("   • Scalable cloud-native architecture")
    print()
    print("3. BUSINESS IMPACT:")
    print("   • Reduces support ticket resolution time")
    print("   • Improves customer satisfaction with instant responses")
    print("   • Scales human expertise through AI agents")
    print()
    print("4. MARKET READINESS:")
    print("   • Built on enterprise AWS infrastructure")
    print("   • Real-time performance suitable for production")
    print("   • Extensible agent framework for domain expansion")
    print()

def generate_slide_data(data):
    """Generate data formatted for presentation slides."""
    
    summary = data['summary']
    results = data['detailed_results']
    
    slide_data = {
        "performance_metrics": {
            "success_rate": f"{summary['success_rate']:.1f}%",
            "avg_response_time": f"{summary['average_response_time']:.2f}s",
            "routing_accuracy": f"{summary['average_routing_accuracy']*100:.1f}%",
            "avg_confidence": f"{summary['average_confidence']:.1%}"
        },
        "test_breakdown": [
            {
                "type": r['question_type'],
                "time": f"{r['total_time']:.3f}s",
                "agents": len(r.get('agents_used', [])),
                "confidence": f"{r['overall_confidence']:.1%}"
            }
            for r in results if 'error' not in r
        ],
        "agent_usage": {
            "SupervisorAgent": len([r for r in results if 'SupervisorAgent' in r.get('agents_used', [])]),
            "TicketAgent": len([r for r in results if 'TicketAgent' in r.get('agents_used', [])]),
            "KnowledgeAgent": len([r for r in results if 'KnowledgeAgent' in r.get('agents_used', [])])
        }
    }
    
    # Save slide data
    with open('presentation_slide_data.json', 'w') as f:
        json.dump(slide_data, f, indent=2)
    
    print("💾 Slide data saved to: presentation_slide_data.json")

def main():
    """Main function to generate presentation summary."""
    
    data = load_test_results()
    if not data:
        return
    
    generate_presentation_summary(data)
    generate_slide_data(data)
    
    print("🎉 Presentation summary generated successfully!")
    print("📋 Use this output for your judge presentation")

if __name__ == "__main__":
    main()