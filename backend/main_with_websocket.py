#!/usr/bin/env python3
"""
Main entry point for the Agentic Voice Assistant with WebSocket server.
Runs both the voice interaction system and the WebSocket server for frontend communication.
"""

import asyncio
import logging
import signal
import sys
from main import VoiceAssistantOrchestrator
from websocket_server import start_websocket_server

# Configure clean logging
from logging_config import setup_clean_logging
setup_clean_logging()
logger = logging.getLogger(__name__)


class VoiceAssistantWithWebSocket:
    """Combined Voice Assistant and WebSocket server."""
    
    def __init__(self):
        self.orchestrator = VoiceAssistantOrchestrator()
        self.websocket_task = None
        self.voice_task = None
        self.is_running = False
    
    async def start(self, websocket_host: str = "localhost", websocket_port: int = 8000):
        """Start both the voice assistant and WebSocket server."""
        try:
            print("🎤 Starting Voice Assistant...")
            
            # Initialize the orchestrator (silent)
            if not await self.orchestrator.initialize():
                print("❌ Failed to initialize")
                return False
            
            # Start WebSocket server in background
            self.websocket_task = asyncio.create_task(
                start_websocket_server(self.orchestrator, websocket_host, websocket_port)
            )
            
            # Give WebSocket server time to start
            await asyncio.sleep(2)
            
            # Start voice interaction
            if not await self.orchestrator.start_voice_interaction():
                print("❌ Failed to start voice interaction")
                return False
            
            self.is_running = True
            print("✅ Ready! Listening for voice input...")
            print(f"   WebSocket: ws://{websocket_host}:{websocket_port}/ws/{{client_id}}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start combined system: {e}")
            return False
    
    async def stop(self):
        """Stop both systems gracefully."""
        try:
            logger.info("🛑 Stopping Voice Assistant and WebSocket server...")
            
            self.is_running = False
            
            # Stop voice assistant
            if self.orchestrator:
                await self.orchestrator.stop()
            
            # Stop WebSocket server
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("✅ Combined system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping combined system: {e}")
    
    async def run_forever(self):
        """Keep the system running until stopped."""
        try:
            # Performance monitoring loop
            performance_check_counter = 0
            
            while self.is_running:
                await asyncio.sleep(1)
                performance_check_counter += 1
                
                # Periodic performance monitoring (every 30 seconds)
                if performance_check_counter >= 30:
                    performance_check_counter = 0
                    
                    try:
                        stats = await self.orchestrator.get_performance_stats()
                        avg_time = stats.get('performance_metrics', {}).get('avg_response_time', 0)
                        cache_hit_rate = stats.get('performance_metrics', {}).get('cache_hit_rate', 0)
                        aws_calls = stats.get('aws_calls', 0)
                        
                        if avg_time > self.orchestrator.response_time_target * 1.5:
                            logger.warning(f"⚠️ Average response time high: {avg_time:.2f}s")
                        
                        if avg_time > 0:  # Only log if we have data
                            logger.info(f"📈 Performance: {avg_time:.2f}s avg, {cache_hit_rate:.1f}% cache hit rate, {aws_calls} AWS calls")
                            
                    except Exception as e:
                        logger.error(f"Error in performance monitoring: {e}")
                
                # Check if WebSocket server is still running
                if self.websocket_task and self.websocket_task.done():
                    exception = self.websocket_task.exception()
                    if exception:
                        logger.error(f"WebSocket server crashed: {exception}")
                        self.is_running = False
                        break
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.is_running = False


# Global instance
combined_system = VoiceAssistantWithWebSocket()


async def main():
    """Main application entry point."""
    print("🎤 Voice Assistant Starting...")
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(combined_system.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the combined system
        if not await combined_system.start():
            logger.error("❌ Failed to start combined system")
            return 1
        
        # Keep running until stopped
        logger.info("🎯 System running. Press Ctrl+C to stop.")
        logger.info("🌐 Frontend should connect to: ws://localhost:8000/ws/{client_id}")
        
        await combined_system.run_forever()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
        await combined_system.stop()
        return 0
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        await combined_system.stop()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)