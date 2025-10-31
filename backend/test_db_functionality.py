#!/usr/bin/env python3
"""
Test script to verify database functionality with specific questions.
Shows exactly what data is retrieved and sent to LLM agents.
"""

import asyncio
import json
from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext
from utils.data_access import DataAccess

async def test_database_functionality():
    """Test database functionality with specific questions."""
    
    print("🧪 Testing Database Functionality")
    print("=" * 80)
    
    # Initialize components
    supervisor = SupervisorAgent()
    ticket_agent = TicketAgent()
    knowledge_agent = KnowledgeAgent()
    data_access = DataAccess()
    context = ConversationContext("test_session")
    
    # Test questions
    test_questions = [
        # "status of my ticket 001",
        # "ticket description of 002", 
        # "resolution for ticket 004",
        # "what is a probe in superops",
        # "how do i add a probe",
        "escalate to human"
    ]
    
    print("📊 Database Health Check:")
    health = data_access.health_check()
    for component, status in health.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {component}: {status}")
    print()
    
    # Test each question
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"🔍 TEST {i}: '{question}'")
        print(f"{'='*80}")
        
        try:
            # Step 1: Supervisor Intent Analysis
            print("\n📋 STEP 1: Supervisor Intent Analysis")
            print("-" * 50)
            
            intent = await supervisor.analyze_intent(question, context)
            print(f"Intent Type: {intent.intent_type.value}")
            print(f"Confidence: {intent.confidence:.2f}")
            print(f"Entities: {json.dumps(intent.entities, indent=2)}")
            print(f"Reasoning: {intent.reasoning}")
            
            # Step 2: Supervisor Routing Decision
            print("\n🚦 STEP 2: Supervisor Routing Decision")
            print("-" * 50)
            
            supervisor_result = await supervisor.process_query(question, context)
            routing_decision = supervisor_result.data.get('routing_decision', [])
            print(f"Routing Decision: {routing_decision}")
            print(f"Requires Escalation: {supervisor_result.requires_escalation}")
            
            # Step 3: Execute Appropriate Agent
            if 'ticket' in routing_decision:
                print("\n🎫 STEP 3: Ticket Agent Processing")
                print("-" * 50)
                
                # Show what the ticket agent will search for
                criteria = ticket_agent._parse_query_criteria(question)
                print(f"Parsed Criteria:")
                print(f"  - Ticket ID: {criteria.ticket_id}")
                print(f"  - Category: {criteria.category}")
                print(f"  - Priority: {criteria.priority}")
                print(f"  - Status: {criteria.status}")
                print(f"  - Keywords: {criteria.keywords}")
                
                # Execute ticket agent
                ticket_result = await ticket_agent.process_query(question, context)
                
                print(f"\nTicket Agent Results:")
                print(f"  - Confidence: {ticket_result.confidence:.2f}")
                print(f"  - Processing Time: {ticket_result.processing_time:.2f}s")
                print(f"  - Requires Escalation: {ticket_result.requires_escalation}")
                
                # Show retrieved data
                data = ticket_result.data
                print(f"\nRetrieved Data:")
                if data.get('type') == 'specific_ticket':
                    if data.get('found'):
                        ticket = data['ticket']
                        print(f"  ✅ Found Ticket: {ticket['id']}")
                        print(f"     Title: {ticket['title']}")
                        print(f"     Status: {ticket['status']}")
                        print(f"     Priority: {ticket['priority']}")
                        print(f"     Category: {ticket['category']}")
                        print(f"     Description: {ticket.get('description', 'N/A')[:100]}...")
                        print(f"     Resolution: {ticket.get('resolution', 'N/A')[:100] if ticket.get('resolution') else 'N/A'}...")
                    else:
                        print(f"  ❌ Ticket Not Found: {data.get('ticket_id')}")
                elif data.get('type') == 'search_results':
                    total = data.get('total_found', 0)
                    print(f"  📊 Search Results: {total} tickets found")
                    
                    combined_results = data.get('combined_results', [])
                    for j, ticket in enumerate(combined_results[:3], 1):
                        print(f"     {j}. {ticket.get('id', 'N/A')}: {ticket.get('title', 'N/A')}")
                        print(f"        Status: {ticket.get('status', 'N/A')}, Priority: {ticket.get('priority', 'N/A')}")
                
                # Show what would be sent to LLM
                print(f"\n📤 Data Sent to LLM for Humanization:")
                llm_data = {
                    'agent_name': ticket_result.agent_name,
                    'data': ticket_result.data,
                    'confidence': ticket_result.confidence,
                    'requires_escalation': ticket_result.requires_escalation
                }
                print(json.dumps(llm_data, indent=2, default=str))
            
            elif 'knowledge' in routing_decision:
                print("\n📚 STEP 3: Knowledge Agent Processing")
                print("-" * 50)
                
                # Execute knowledge agent
                knowledge_result = await knowledge_agent.process_query(question, context)
                
                print(f"Knowledge Agent Results:")
                print(f"  - Confidence: {knowledge_result.confidence:.2f}")
                print(f"  - Processing Time: {knowledge_result.processing_time:.2f}s")
                print(f"  - Requires Escalation: {knowledge_result.requires_escalation}")
                
                # Show retrieved data
                data = knowledge_result.data
                print(f"\nRetrieved Data:")
                chunks_found = data.get('chunks_found', 0)
                relevant_chunks = data.get('relevant_chunks', 0)
                print(f"  📊 Total Chunks Found: {chunks_found}")
                print(f"  📊 Relevant Chunks: {relevant_chunks}")
                
                contextual_response = data.get('contextual_response', {})
                if contextual_response:
                    print(f"  📝 Contextual Answer: {contextual_response.get('answer', 'N/A')[:200]}...")
                    print(f"  📊 Answer Confidence: {contextual_response.get('confidence', 0):.2f}")
                    print(f"  📚 Sources: {contextual_response.get('sources', [])}")
                
                knowledge_chunks = data.get('knowledge_chunks', [])
                if knowledge_chunks:
                    print(f"\n  📄 Knowledge Chunks:")
                    for j, chunk in enumerate(knowledge_chunks[:2], 1):
                        print(f"     {j}. Relevance: {chunk.get('relevance_score', 0):.2f}")
                        print(f"        Source: {chunk.get('source', 'N/A')}")
                        print(f"        Text: {chunk.get('text', 'N/A')[:150]}...")
                
                # Show what would be sent to LLM
                print(f"\n📤 Data Sent to LLM for Humanization:")
                llm_data = {
                    'agent_name': knowledge_result.agent_name,
                    'data': knowledge_result.data,
                    'confidence': knowledge_result.confidence,
                    'requires_escalation': knowledge_result.requires_escalation
                }
                print(json.dumps(llm_data, indent=2, default=str))
            
            else:
                print("\n⚠️  STEP 3: No Agent Routing")
                print("-" * 50)
                print("No specific agent was selected for this query.")
                print("This might be a greeting or unrecognized query type.")
        
        except Exception as e:
            print(f"\n❌ ERROR in test {i}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("🏁 Database Functionality Test Complete")
    print(f"{'='*80}")

async def test_raw_data_access():
    """Test raw data access methods."""
    print("\n🔧 Testing Raw Data Access Methods")
    print("-" * 50)
    
    data_access = DataAccess()
    
    # Test direct ticket lookup
    print("Testing direct ticket lookups:")
    test_ticket_ids = ['IT-001', 'IT-002', 'IT-004', 'IT-999']
    for ticket_id in test_ticket_ids:
        ticket = data_access.get_ticket_by_id(ticket_id)
        if ticket:
            print(f"  ✅ {ticket_id}: {ticket['title'][:50]}...")
        else:
            print(f"  ❌ {ticket_id}: Not found")
    
    # Test ticket search
    print(f"\nTesting ticket search:")
    search_results = await data_access.search_tickets("status", top_k=3)
    print(f"  📊 Search results: {len(search_results)} tickets")
    for result in search_results[:2]:
        metadata = result.get('metadata', {})
        print(f"    - {metadata.get('ticket_id', 'N/A')}: {metadata.get('title', 'N/A')[:40]}...")
    
    # Test knowledge search
    print(f"\nTesting knowledge search:")
    knowledge_results = await data_access.search_knowledge_base("probe", top_k=3)
    print(f"  📊 Knowledge results: {len(knowledge_results)} chunks")
    for result in knowledge_results[:2]:
        metadata = result.get('metadata', {})
        print(f"    - Source: {metadata.get('source', 'N/A')}")
        print(f"      Text: {result.get('text', 'N/A')[:60]}...")
    
    # Test ticket stats
    print(f"\nTesting ticket statistics:")
    stats = data_access.get_ticket_stats()
    print(f"  📊 Total tickets: {stats.get('total', 0)}")
    print(f"  📊 By status: {stats.get('by_status', {})}")
    print(f"  📊 By priority: {stats.get('by_priority', {})}")

if __name__ == "__main__":
    asyncio.run(test_database_functionality())
    asyncio.run(test_raw_data_access())