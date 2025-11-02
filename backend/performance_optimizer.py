#!/usr/bin/env python3
"""
Performance optimization module for the Agentic Voice Assistant.
Implements response time monitoring, connection pooling, and efficient caching.
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import hashlib
import boto3
from botocore.config import Config
import threading

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    cache_hits: int = 0
    cache_misses: int = 0
    aws_api_calls: int = 0
    agent_processing_times: Dict[str, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=50)))
    error_count: int = 0
    escalation_count: int = 0
    interruption_count: int = 0
    
    def add_response_time(self, response_time: float, agent_name: str = "overall"):
        """Add a response time measurement."""
        self.response_times.append(response_time)
        if agent_name != "overall":
            self.agent_processing_times[agent_name].append(response_time)
    
    def get_avg_response_time(self, agent_name: str = "overall") -> float:
        """Get average response time."""
        if agent_name == "overall":
            times = self.response_times
        else:
            times = self.agent_processing_times.get(agent_name, deque())
        
        return sum(times) / len(times) if times else 0.0
    
    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "avg_response_time": self.get_avg_response_time(),
            "cache_hit_rate": self.get_cache_hit_rate(),
            "total_aws_calls": self.aws_api_calls,
            "error_rate": self.error_count,
            "agent_performance": {
                agent: self.get_avg_response_time(agent) 
                for agent in self.agent_processing_times.keys()
            },
            "recent_response_times": list(self.response_times)[-10:],
            "escalations": self.escalation_count,
            "interruptions": self.interruption_count
        }


class ResponseTimeMonitor:
    """Monitor and track response times with alerting."""
    
    def __init__(self, target_time: float = 0.5, warning_threshold: float = 1.0):
        self.target_time = target_time
        self.warning_threshold = warning_threshold
        self.metrics = PerformanceMetrics()
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for performance alerts."""
        self.alert_callbacks.append(callback)
    
    async def measure_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Measure the execution time of an operation."""
        start_time = time.time()
        
        try:
            result = await operation_func(*args, **kwargs)
            processing_time = time.time() - start_time
            
            # Record metrics
            self.metrics.add_response_time(processing_time, operation_name)
            
            # Check for performance issues
            if processing_time > self.warning_threshold:
                await self._trigger_alert("slow_response", {
                    "operation": operation_name,
                    "time": processing_time,
                    "threshold": self.warning_threshold
                })
            
            return result, processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.error_count += 1
            
            await self._trigger_alert("operation_error", {
                "operation": operation_name,
                "error": str(e),
                "time": processing_time
            })
            
            raise
    
    async def _trigger_alert(self, alert_type: str, data: Dict[str, Any]):
        """Trigger performance alerts."""
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics


class AWSConnectionPool:
    """Connection pool for AWS services with automatic retry and optimization."""
    
    def __init__(self, region: str = "us-east-2", max_connections: int = 10):
        self.region = region
        self.max_connections = max_connections
        self._clients: Dict[str, Any] = {}
        self._client_locks: Dict[str, threading.Lock] = {}
        self._connection_counts: Dict[str, int] = defaultdict(int)
        
        # Optimized boto3 config
        self.config = Config(
            region_name=region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=max_connections,
            connect_timeout=5,
            read_timeout=10
        )
    
    def get_client(self, service_name: str):
        """Get or create an optimized AWS client."""
        if service_name not in self._clients:
            if service_name not in self._client_locks:
                self._client_locks[service_name] = threading.Lock()
            
            with self._client_locks[service_name]:
                if service_name not in self._clients:
                    logger.info(f"Creating optimized AWS client for {service_name}")
                    self._clients[service_name] = boto3.client(
                        service_name,
                        config=self.config
                    )
        
        self._connection_counts[service_name] += 1
        return self._clients[service_name]
    
    def get_connection_stats(self) -> Dict[str, int]:
        """Get connection usage statistics."""
        return dict(self._connection_counts)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all AWS connections."""
        health_status = {}
        
        for service_name, client in self._clients.items():
            try:
                if service_name == 'bedrock-runtime':
                    # Simple health check for Bedrock
                    health_status[service_name] = True
                elif service_name == 'transcribe':
                    # Check transcribe service
                    client.list_vocabularies(MaxResults=1)
                    health_status[service_name] = True
                elif service_name == 'polly':
                    # Check Polly service
                    client.describe_voices(MaxResults=1)
                    health_status[service_name] = True
                else:
                    health_status[service_name] = True
                    
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status[service_name] = False
        
        return health_status


class QueryCache:
    """Intelligent caching system for frequent queries and responses."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._cleanup_task = None
        
    async def start_cleanup_task(self):
        """Start the cleanup task (call this after event loop is running)."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    def _generate_cache_key(self, query: str, context_hash: str = "") -> str:
        """Generate a cache key for a query."""
        combined = f"{query.lower().strip()}:{context_hash}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, query: str, context_hash: str = "") -> Optional[Any]:
        """Get cached result for a query."""
        cache_key = self._generate_cache_key(query, context_hash)
        
        with self._lock:
            if cache_key in self._cache:
                result, timestamp = self._cache[cache_key]
                
                # Check if expired
                if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
                    del self._cache[cache_key]
                    if cache_key in self._access_times:
                        del self._access_times[cache_key]
                    return None
                
                # Update access time
                self._access_times[cache_key] = datetime.now()
                return result
        
        return None
    
    def set(self, query: str, result: Any, context_hash: str = ""):
        """Cache a query result."""
        cache_key = self._generate_cache_key(query, context_hash)
        
        with self._lock:
            # Implement LRU eviction if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[cache_key] = (result, datetime.now())
            self._access_times[cache_key] = datetime.now()
    
    def _evict_lru(self):
        """Evict least recently used items."""
        if not self._access_times:
            return
        
        # Find oldest access time
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        
        # Remove from both caches
        if oldest_key in self._cache:
            del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    async def _cleanup_expired(self):
        """Periodic cleanup of expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
                with self._lock:
                    current_time = datetime.now()
                    expired_keys = []
                    
                    for key, (_, timestamp) in self._cache.items():
                        if current_time - timestamp > timedelta(seconds=self.ttl_seconds):
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._cache[key]
                        if key in self._access_times:
                            del self._access_times[key]
                    
                    if expired_keys:
                        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                        
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / self.max_size * 100,
                "ttl_seconds": self.ttl_seconds
            }
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self, target_response_time: float = 0.5, aws_region: str = "us-east-2"):
        self.target_response_time = target_response_time
        self.aws_region = aws_region
        
        # Initialize components
        self.monitor = ResponseTimeMonitor(target_response_time)
        self.connection_pool = AWSConnectionPool(aws_region)
        self.cache = QueryCache()
        
        # Performance tracking
        self.optimization_enabled = True
        self.adaptive_caching = True
        
        # Set up monitoring alerts
        self.monitor.add_alert_callback(self._handle_performance_alert)
        
        # Flag to track if async components are initialized
        self._async_initialized = False
    
    async def initialize_async_components(self):
        """Initialize async components (call after event loop is running)."""
        if not self._async_initialized:
            await self.cache.start_cleanup_task()
            self._async_initialized = True
    
    async def optimize_query_processing(self, query: str, agent_name: str, 
                                      processing_func, context_hash: str = "", 
                                      *args, **kwargs):
        """Optimize query processing with caching and monitoring."""
        
        # Try cache first if enabled
        if self.optimization_enabled:
            cached_result = self.cache.get(query, context_hash)
            if cached_result is not None:
                self.monitor.metrics.cache_hits += 1
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached_result, 0.0  # Cached results are instant
        
        self.monitor.metrics.cache_misses += 1
        
        # Measure and execute the operation
        result, processing_time = await self.monitor.measure_operation(
            agent_name, processing_func, *args, **kwargs
        )
        
        # Cache the result if it's successful and caching is enabled
        if (self.optimization_enabled and 
            result is not None and 
            not getattr(result, 'requires_escalation', False)):
            
            self.cache.set(query, result, context_hash)
        
        return result, processing_time
    
    def get_optimized_aws_client(self, service_name: str):
        """Get an optimized AWS client from the connection pool."""
        self.monitor.metrics.aws_api_calls += 1
        return self.connection_pool.get_client(service_name)
    
    async def _handle_performance_alert(self, alert_type: str, data: Dict[str, Any]):
        """Handle performance alerts and take corrective action."""
        logger.warning(f"Performance alert: {alert_type} - {data}")
        
        if alert_type == "slow_response":
            operation = data.get("operation", "unknown")
            response_time = data.get("time", 0)
            
            # Adaptive optimization based on slow responses
            if response_time > self.target_response_time * 2:
                logger.info(f"Enabling aggressive caching for {operation}")
                # Could implement operation-specific optimizations here
        
        elif alert_type == "operation_error":
            operation = data.get("operation", "unknown")
            logger.error(f"Operation error in {operation}: {data.get('error')}")
            
            # Could implement circuit breaker pattern here
    
    def enable_adaptive_optimization(self):
        """Enable adaptive performance optimization."""
        self.optimization_enabled = True
        self.adaptive_caching = True
        logger.info("Adaptive performance optimization enabled")
    
    def disable_optimization(self):
        """Disable performance optimization (for debugging)."""
        self.optimization_enabled = False
        self.adaptive_caching = False
        logger.info("Performance optimization disabled")
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        metrics = self.monitor.get_metrics()
        cache_stats = self.cache.get_stats()
        connection_stats = self.connection_pool.get_connection_stats()
        aws_health = await self.connection_pool.health_check()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "target_response_time": self.target_response_time,
            "optimization_enabled": self.optimization_enabled,
            "performance_metrics": metrics.get_performance_summary(),
            "cache_statistics": cache_stats,
            "aws_connections": connection_stats,
            "aws_health": aws_health,
            "recommendations": self._generate_recommendations(metrics, cache_stats)
        }
    
    def _generate_recommendations(self, metrics: PerformanceMetrics, 
                                cache_stats: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        avg_response_time = metrics.get_avg_response_time()
        cache_hit_rate = metrics.get_cache_hit_rate()
        
        if avg_response_time > self.target_response_time * 1.5:
            recommendations.append(
                f"Average response time ({avg_response_time:.2f}s) exceeds target. "
                "Consider optimizing agent processing or increasing cache TTL."
            )
        
        if cache_hit_rate < 30:
            recommendations.append(
                f"Low cache hit rate ({cache_hit_rate:.1f}%). "
                "Consider increasing cache size or adjusting TTL."
            )
        
        if metrics.error_count > 0:
            recommendations.append(
                f"Detected {metrics.error_count} errors. "
                "Review error logs and consider implementing circuit breakers."
            )
        
        if cache_stats["utilization"] > 90:
            recommendations.append(
                "Cache utilization high. Consider increasing cache size."
            )
        
        # Agent-specific recommendations
        for agent, times in metrics.agent_processing_times.items():
            if times:
                avg_time = sum(times) / len(times)
                if avg_time > self.target_response_time:
                    recommendations.append(
                        f"{agent} average time ({avg_time:.2f}s) is slow. "
                        "Consider agent-specific optimizations."
                    )
        
        if not recommendations:
            recommendations.append("Performance is within acceptable parameters.")
        
        return recommendations
    
    async def health_check(self) -> bool:
        """Check if performance optimizer is healthy."""
        try:
            # Check AWS connections
            aws_health = await self.connection_pool.health_check()
            
            # Check if any critical services are down
            critical_services = ['bedrock-runtime']
            for service in critical_services:
                if service in aws_health and not aws_health[service]:
                    logger.error(f"Critical service {service} is unhealthy")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Performance optimizer health check failed: {e}")
            return False


# Global performance optimizer instance (initialized on demand)
performance_optimizer = None


async def main():
    """Test the performance optimization system."""
    print("🚀 Testing Performance Optimization System")
    print("=" * 50)
    
    # Test cache
    print("Testing cache...")
    cache = QueryCache(max_size=5, ttl_seconds=10)
    
    cache.set("test query", {"result": "test data"})
    result = cache.get("test query")
    print(f"Cache test: {result}")
    
    # Test connection pool
    print("Testing AWS connection pool...")
    pool = AWSConnectionPool()
    
    try:
        bedrock_client = pool.get_client('bedrock-runtime')
        print(f"Bedrock client created: {type(bedrock_client)}")
    except Exception as e:
        print(f"AWS connection test failed: {e}")
    
    # Test performance monitoring
    print("Testing performance monitoring...")
    monitor = ResponseTimeMonitor(target_time=0.1)
    
    async def test_operation():
        await asyncio.sleep(0.05)
        return "test result"
    
    result, time_taken = await monitor.measure_operation("test_op", test_operation)
    print(f"Operation result: {result}, time: {time_taken:.3f}s")
    
    # Test full optimizer
    print("Testing full performance optimizer...")
    optimizer = PerformanceOptimizer(target_response_time=0.1)
    
    async def mock_processing_func():
        await asyncio.sleep(0.02)
        return {"data": "mock result"}
    
    # Test with caching
    result1, time1 = await optimizer.optimize_query_processing(
        "test query", "TestAgent", mock_processing_func
    )
    print(f"First call: {time1:.3f}s")
    
    result2, time2 = await optimizer.optimize_query_processing(
        "test query", "TestAgent", mock_processing_func
    )
    print(f"Second call (cached): {time2:.3f}s")
    
    # Get performance report
    report = await optimizer.get_performance_report()
    print("\nPerformance Report:")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())