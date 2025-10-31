"""
AWS Call Tracker
Simple global tracker for AWS API calls across the system.
"""

import threading
from typing import Dict, Any
from datetime import datetime

class AWSCallTracker:
    """Thread-safe tracker for AWS API calls."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._calls = {
            'transcribe': 0,
            'polly': 0,
            'bedrock': 0,
            'total': 0
        }
        self._last_reset = datetime.now()
    
    def track_call(self, service: str):
        """Track an AWS API call."""
        with self._lock:
            if service in self._calls:
                self._calls[service] += 1
            self._calls['total'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current call statistics."""
        with self._lock:
            return {
                **self._calls,
                'last_reset': self._last_reset.isoformat()
            }
    
    def reset(self):
        """Reset all counters."""
        with self._lock:
            for key in self._calls:
                self._calls[key] = 0
            self._last_reset = datetime.now()

# Global instance
aws_tracker = AWSCallTracker()

def track_aws_call(service: str):
    """Convenience function to track AWS calls."""
    aws_tracker.track_call(service)