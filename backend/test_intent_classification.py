#!/usr/bin/env python3
"""
Test intent classification fixes.
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.fast_intent_classifier import classify_intent_fast


def test_intent_classification():
    """Test intent classification for problematic queries."""
    
    print("🧠 Testing Intent Classification Fixes")
    print("=" * 60)
    
    # Test cases with expected results
    test_cases = [
        {
            "query": "Details about my ticket 14",
            "expected": "ticket_query",
            "description": "Should be ticket query, not followup"
        },
        {
            "query": "Details",
            "expected": "followup", 
            "description": "Should be followup when standalone"
        },
        {
            "query": "how do I add a probe in superops",
            "expected": "knowledge_query",
            "description": "Should be knowledge query for how-to questions"
        },
        {
            "query": "give me more details",
            "expected": "followup",
            "description": "Should be followup for more details request"
        },
        {
            "query": "I have another question",
            "expected": "followup",
            "description": "Should be followup for new question request"
        },
        {
            "query": "what is a probe in superops",
            "expected": "knowledge_query",
            "description": "Should be knowledge query for definition"
        },
        {
            "query": "status of ticket IT-001",
            "expected": "ticket_query",
            "description": "Should be ticket query with ID"
        }
    ]
    
    print(f"Testing {len(test_cases)} queries:")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        description = test_case["description"]
        
        print(f"\n📝 Test {i}: {query}")
        print(f"   Expected: {expected}")
        print(f"   Description: {description}")
        
        # Classify the intent
        intent = classify_intent_fast(query)
        
        if intent:
            actual = intent.intent_type.value
            confidence = intent.confidence
            reasoning = intent.reasoning
            entities = getattr(intent, 'entities', {})
            
            print(f"   Actual: {actual} (confidence: {confidence:.2f})")
            print(f"   Reasoning: {reasoning}")
            if entities:
                print(f"   Entities: {entities}")
            
            if actual == expected:
                print(f"   ✅ PASS")
                passed += 1
            else:
                print(f"   ❌ FAIL - Expected {expected}, got {actual}")
                failed += 1
        else:
            print(f"   ❌ FAIL - No intent classified (would fallback to LLM)")
            failed += 1
        
        print("-" * 30)
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️ {failed} tests failed - need further fixes")


if __name__ == "__main__":
    test_intent_classification()