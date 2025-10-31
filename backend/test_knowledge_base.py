#!/usr/bin/env python3
"""
Test script to debug knowledge base issues.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_access import DataAccess
from agents.knowledge_agent import KnowledgeAgent
import chromadb
from chromadb.config import Settings

async def test_knowledge_base():
    """Test knowledge base functionality step by step."""
    
    print("🔍 Testing Knowledge Base...")
    
    # Test 1: Check if ChromaDB files exist
    print("\n1. Checking ChromaDB files...")
    chroma_path = "./data/chroma_db"
    if os.path.exists(chroma_path):
        print(f"✅ ChromaDB directory exists: {chroma_path}")
        files = os.listdir(chroma_path)
        print(f"   Files: {files}")
    else:
        print(f"❌ ChromaDB directory missing: {chroma_path}")
        return
    
    # Test 2: Direct ChromaDB connection
    print("\n2. Testing direct ChromaDB connection...")
    try:
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        collections = client.list_collections()
        print(f"✅ ChromaDB connected. Collections: {[c.name for c in collections]}")
        
        # Check knowledge_base collection
        if any(c.name == "knowledge_base" for c in collections):
            knowledge_collection = client.get_collection("knowledge_base")
            count = knowledge_collection.count()
            print(f"✅ Knowledge base collection found with {count} documents")
            
            # Get a sample document
            if count > 0:
                sample = knowledge_collection.peek(limit=1)
                print(f"   Sample document: {sample['documents'][0][:100]}..." if sample['documents'] else "No documents")
        else:
            print("❌ Knowledge base collection not found")
            
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        return
    
    # Test 3: DataAccess layer
    print("\n3. Testing DataAccess layer...")
    try:
        data_access = DataAccess()
        health = data_access.health_check()
        print(f"✅ DataAccess health: {health}")
        
        # Test knowledge search
        results = await data_access.search_knowledge_base("probe installation", top_k=3)
        print(f"✅ Knowledge search returned {len(results)} results")
        
        if results:
            for i, result in enumerate(results):
                print(f"   Result {i+1}: {result['text'][:100]}... (distance: {result.get('distance', 'N/A')})")
        else:
            print("   No results found")
            
    except Exception as e:
        print(f"❌ DataAccess test failed: {e}")
        return
    
    # Test 4: KnowledgeAgent
    print("\n4. Testing KnowledgeAgent...")
    try:
        from agents.base_agent import ConversationContext
        
        agent = KnowledgeAgent()
        context = ConversationContext(
            session_id="test",
            user_id="test_user"
        )
        
        result = await agent.process_query("how do I install a probe", context)
        print(f"✅ KnowledgeAgent result:")
        print(f"   Confidence: {result.confidence}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        print(f"   Data: {result.data}")
        
    except Exception as e:
        print(f"❌ KnowledgeAgent test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_knowledge_base())