#!/usr/bin/env python3
"""
Test script to verify audio feedback loop fixes.
"""

import asyncio
from services.aws_call_tracker import aws_tracker, track_aws_call

def test_aws_tracking():
    """Test AWS call tracking."""
    print("🧪 Testing AWS Call Tracking")
    print("-" * 40)
    
    # Reset tracker
    aws_tracker.reset()
    
    # Simulate some calls
    track_aws_call('polly')
    track_aws_call('transcribe')
    track_aws_call('polly')
    track_aws_call('bedrock')
    
    # Get stats
    stats = aws_tracker.get_stats()
    print(f"Total AWS Calls: {stats['total']}")
    print(f"Polly Calls: {stats['polly']}")
    print(f"Transcribe Calls: {stats['transcribe']}")
    print(f"Bedrock Calls: {stats['bedrock']}")
    print()

def test_feedback_filtering():
    """Test audio feedback filtering."""
    print("🧪 Testing Audio Feedback Filtering")
    print("-" * 40)
    
    # Test phrases that should be filtered
    feedback_phrases = [
        "what else would you like to know",
        "yes i'm listening",
        "sure what did you want to ask",
        "of course go ahead",
        "you have another question"
    ]
    
    filter_phrases = [
        "what else would you like",
        "yes i'm listening",
        "sure what did you want",
        "of course go ahead",
        "you have another question"
    ]
    
    for phrase in feedback_phrases:
        should_filter = any(filter_phrase in phrase.lower() for filter_phrase in filter_phrases)
        status = "🚫 FILTERED" if should_filter else "✅ ALLOWED"
        print(f"{status}: '{phrase}'")
    
    print()
    
    # Test legitimate user input
    user_phrases = [
        "what is the status of my ticket",
        "how do i add a probe",
        "escalate to human",
        "hello how are you"
    ]
    
    print("Legitimate user input:")
    for phrase in user_phrases:
        should_filter = any(filter_phrase in phrase.lower() for filter_phrase in filter_phrases)
        status = "🚫 FILTERED" if should_filter else "✅ ALLOWED"
        print(f"{status}: '{phrase}'")

if __name__ == "__main__":
    test_aws_tracking()
    test_feedback_filtering()