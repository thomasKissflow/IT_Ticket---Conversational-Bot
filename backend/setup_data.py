#!/usr/bin/env python3
"""
Setup script for initializing data storage and processing.
Run this script to set up ChromaDB and SQLite databases.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.data_processor import DataProcessor


async def setup_data_storage():
    """Set up all data storage components."""
    print("🚀 Starting data storage setup...")
    
    try:
        # Initialize data processor
        processor = DataProcessor()
        
        # Step 1: Set up SQLite database
        print("📊 Setting up SQLite database...")
        processor.init_sqlite_database()
        print("✅ SQLite database initialized")
        
        # Step 2: Import ticket data
        print("🎫 Importing ticket data...")
        csv_path = Path(__file__).parent.parent / "support-tickets.csv"
        if csv_path.exists():
            processor.import_ticket_data(str(csv_path))
            print("✅ Ticket data imported successfully")
        else:
            print(f"⚠️  Warning: CSV file not found at {csv_path}")
        
        # Step 3: Process knowledge base PDF
        print("📚 Processing knowledge base PDF...")
        pdf_path = Path(__file__).parent.parent / "product-documentation.pdf"
        if pdf_path.exists():
            await processor.process_knowledge_base(str(pdf_path))
            print("✅ Knowledge base processed and stored")
        else:
            print(f"⚠️  Warning: PDF file not found at {pdf_path}")
        
        # Step 4: Generate ticket summaries
        print("🔍 Generating ticket summaries for semantic search...")
        await processor.generate_ticket_summaries()
        print("✅ Ticket summaries generated and stored")
        
        print("\n🎉 Data storage setup completed successfully!")
        print("\nCreated:")
        print(f"  - SQLite database: {processor.sqlite_db_path}")
        print(f"  - ChromaDB collections: {processor.chroma_db_path}")
        print("  - knowledge_base collection (PDF chunks)")
        print("  - ticket_summaries collection (ticket embeddings)")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_data_storage())