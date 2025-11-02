#!/usr/bin/env python3
"""
Simple runner for the demo test - perfect for presentations
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import and run the demo
from demo_test import main

if __name__ == "__main__":
    print("🚀 Starting Agentic Voice Assistant Demo...")
    print("This will test 5 different question types and show performance metrics")
    print("Perfect for your presentation to the judges!")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)