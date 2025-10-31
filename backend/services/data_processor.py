"""
Data processing service for ChromaDB and knowledge base management.
Handles PDF processing, embedding generation, and vector storage.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import sqlite3
import csv
from datetime import datetime

import chromadb
from chromadb.config import Settings
import boto3
import json
from botocore.exceptions import ClientError
import PyPDF2
from io import BytesIO
from llm_client import get_llm_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Handles data storage and processing for the voice assistant."""
    
    def __init__(self, chroma_db_path: str = "./data/chroma_db", sqlite_db_path: str = "./data/voice_assistant.db"):
        self.chroma_db_path = chroma_db_path
        self.sqlite_db_path = sqlite_db_path
        self.chroma_client = None
        self.llm_client = get_llm_client()
        
        # Initialize ChromaDB
        self._init_chromadb()
    

    
    def _init_chromadb(self):
        """Initialize ChromaDB client and create collections."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.chroma_db_path), exist_ok=True)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collections
            self.knowledge_collection = self._get_or_create_collection("knowledge_base")
            self.ticket_collection = self._get_or_create_collection("ticket_summaries")
            
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _get_or_create_collection(self, collection_name: str):
        """Get or create a ChromaDB collection."""
        try:
            collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=None  # Use no embedding function since we provide our own
            )
            logger.info(f"Retrieved existing collection: {collection_name}")
        except Exception:
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=None  # Use no embedding function since we provide our own
            )
            logger.info(f"Created new collection: {collection_name}")
        
        return collection
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using LLM client (Bedrock Titan or Ollama)."""
        try:
            return self.llm_client.generate_embeddings(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Return zero vectors as fallback
            return [[0.0] * 1536 for _ in texts]
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text from PDF with page and section metadata."""
        chunks = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    
                    if text.strip():
                        # Split text into smaller chunks (roughly 500 words each)
                        words = text.split()
                        chunk_size = 500
                        
                        for i in range(0, len(words), chunk_size):
                            chunk_words = words[i:i + chunk_size]
                            chunk_text = ' '.join(chunk_words)
                            
                            if len(chunk_text.strip()) > 50:  # Only store meaningful chunks
                                chunks.append({
                                    'text': chunk_text,
                                    'page_number': page_num,
                                    'chunk_index': i // chunk_size,
                                    'source': os.path.basename(pdf_path)
                                })
        
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
            raise
        
        logger.info(f"Extracted {len(chunks)} chunks from {pdf_path}")
        return chunks
    
    async def process_knowledge_base(self, pdf_path: str):
        """Process PDF knowledge base and store in ChromaDB."""
        logger.info(f"Processing knowledge base: {pdf_path}")
        
        # Extract text chunks from PDF
        chunks = self.extract_text_from_pdf(pdf_path)
        
        if not chunks:
            logger.warning("No text chunks extracted from PDF")
            return
        
        # Generate embeddings for chunks
        texts = [chunk['text'] for chunk in chunks]
        embeddings = await self.generate_embeddings(texts)
        
        # Prepare data for ChromaDB
        ids = [f"kb_{i}" for i in range(len(chunks))]
        metadatas = [{
            'page_number': chunk['page_number'],
            'chunk_index': chunk['chunk_index'],
            'source': chunk['source'],
            'text_length': len(chunk['text'])
        } for chunk in chunks]
        
        # Store in ChromaDB
        try:
            self.knowledge_collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully stored {len(chunks)} knowledge base chunks in ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to store knowledge base in ChromaDB: {e}")
            raise
    
    def init_sqlite_database(self):
        """Initialize SQLite database with required tables."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Create tickets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority TEXT,
                    status TEXT,
                    resolution TEXT,
                    resolution_time TEXT,
                    assigned_team TEXT,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create ticket_interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT,
                    interaction_type TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            ''')
            
            # Create indexes for efficient querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_team ON tickets(assigned_team)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_ticket ON ticket_interactions(ticket_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise
    
    def import_ticket_data(self, csv_path: str):
        """Import ticket data from CSV file."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    cursor.execute('''
                        INSERT OR REPLACE INTO tickets 
                        (id, title, description, category, priority, status, resolution, resolution_time, assigned_team)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['Ticket ID'],
                        row['Ticket Summary'],
                        row['Ticket Description'],
                        row['Category'],
                        row['Priority'],
                        row['Status'],
                        row['Resolution'],
                        row['Resolution Time'],
                        row['Assigned Team']
                    ))
            
            conn.commit()
            
            # Get count of imported tickets
            cursor.execute('SELECT COUNT(*) FROM tickets')
            count = cursor.fetchone()[0]
            
            conn.close()
            
            logger.info(f"Successfully imported {count} tickets from {csv_path}")
            
        except Exception as e:
            logger.error(f"Failed to import ticket data: {e}")
            raise
    
    async def generate_ticket_summaries(self):
        """Generate ticket summaries and store in ChromaDB for semantic search."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Get all tickets
            cursor.execute('''
                SELECT id, title, description, category, priority, status, resolution
                FROM tickets
            ''')
            
            tickets = cursor.fetchall()
            conn.close()
            
            if not tickets:
                logger.warning("No tickets found to generate summaries")
                return
            
            # Create summary texts for embedding
            summary_texts = []
            ticket_ids = []
            metadatas = []
            
            for ticket in tickets:
                ticket_id, title, description, category, priority, status, resolution = ticket
                
                # Create comprehensive summary text
                summary_parts = [
                    f"Title: {title}",
                    f"Category: {category}",
                    f"Priority: {priority}",
                    f"Status: {status}"
                ]
                
                if description:
                    summary_parts.append(f"Description: {description}")
                
                if resolution:
                    summary_parts.append(f"Resolution: {resolution}")
                
                summary_text = " | ".join(summary_parts)
                
                summary_texts.append(summary_text)
                ticket_ids.append(f"ticket_{ticket_id}")
                metadatas.append({
                    'ticket_id': ticket_id,
                    'category': category,
                    'priority': priority,
                    'status': status,
                    'title': title
                })
            
            # Generate embeddings
            embeddings = await self.generate_embeddings(summary_texts)
            
            # Store in ChromaDB
            self.ticket_collection.add(
                embeddings=embeddings,
                documents=summary_texts,
                metadatas=metadatas,
                ids=ticket_ids
            )
            
            logger.info(f"Successfully generated and stored {len(tickets)} ticket summaries")
            
        except Exception as e:
            logger.error(f"Failed to generate ticket summaries: {e}")
            raise


async def main():
    """Main function to set up data storage and processing."""
    # Initialize data processor
    processor = DataProcessor()
    
    # Set up SQLite database
    processor.init_sqlite_database()
    
    # Import ticket data
    processor.import_ticket_data("../support-tickets.csv")
    
    # Process knowledge base PDF
    await processor.process_knowledge_base("../product-documentation.pdf")
    
    # Generate ticket summaries
    await processor.generate_ticket_summaries()
    
    logger.info("Data storage and processing setup complete!")


if __name__ == "__main__":
    asyncio.run(main())