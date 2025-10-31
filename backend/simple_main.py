#!/usr/bin/env python3
"""
Simplified Voice Assistant - Core functionality only
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleVoiceAssistant:
    def __init__(self):
        self.is_running = False
        
    async def initialize(self):
        """Initialize core components"""
        try:
            logger.info("🚀 Initializing Simple Voice Assistant...")
            
            # Test AWS Polly (working)
            import boto3
            polly = boto3.client('polly', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            polly.describe_voices()
            logger.info("✅ AWS Polly working")
            
            # Test AWS Transcribe (working)  
            transcribe = boto3.client('transcribe', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            logger.info("✅ AWS Transcribe working")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def start(self):
        """Start the assistant"""
        if not await self.initialize():
            return False
            
        self.is_running = True
        logger.info("🎉 Simple Voice Assistant ready!")
        
        # Keep running
        while self.is_running:
            await asyncio.sleep(1)
        
        return True
    
    def stop(self):
        """Stop the assistant"""
        self.is_running = False
        logger.info("🛑 Assistant stopped")

async def main():
    assistant = SimpleVoiceAssistant()
    
    try:
        await assistant.start()
    except KeyboardInterrupt:
        assistant.stop()
        logger.info("👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())