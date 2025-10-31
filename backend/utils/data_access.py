"""
Data access layer for SQLite and ChromaDB operations.
Provides unified interface for ticket and knowledge base queries.
"""

import sqlite3
import asyncio
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataAccess:
    """
    Unified data access layer for SQLite and ChromaDB operations.
    Provides methods for ticket queries, knowledge base search, and statistics.
    """
    
    def __init__(self, sqlite_db_path: str = "./data/voice_assistant.db", chroma_db_path: str = "./data/chroma_db"):
        self.sqlite_db_path = sqlite_db_path
        self.chroma_db_path = chroma_db_path
        self.chroma_client = None
        self.knowledge_collection = None
        self.ticket_collection = None
        
        # Initialize ChromaDB connection
        self._init_chromadb()
    
    def _init_chromadb(self):
        """Initialize ChromaDB client and get collections."""
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
            
            # Get collections (they should exist after setup)
            try:
                self.knowledge_collection = self.chroma_client.get_collection("knowledge_base")
                logger.info("Connected to knowledge_base collection")
            except Exception as e:
                logger.warning(f"Knowledge base collection not found: {e}")
                self.knowledge_collection = None
            
            try:
                self.ticket_collection = self.chroma_client.get_collection("ticket_summaries")
                logger.info("Connected to ticket_summaries collection")
            except Exception as e:
                logger.warning(f"Ticket summaries collection not found: {e}")
                self.ticket_collection = None
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific ticket by ID from SQLite database."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, description, category, priority, status, 
                       resolution, resolution_time, assigned_team, created_date, updated_date
                FROM tickets 
                WHERE id = ?
            ''', (ticket_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'category': row[3],
                    'priority': row[4],
                    'status': row[5],
                    'resolution': row[6],
                    'resolution_time': row[7],
                    'assigned_team': row[8],
                    'created_date': row[9],
                    'updated_date': row[10]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting ticket by ID {ticket_id}: {e}")
            return None
    
    async def search_tickets(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search tickets using semantic search via ChromaDB."""
        if not self.ticket_collection:
            logger.warning("Ticket collection not available for semantic search")
            return []
        
        try:
            # Import here to avoid circular imports
            from llm_client import get_llm_client
            llm_client = get_llm_client()
            
            # Generate embedding for the query
            query_embeddings = llm_client.generate_embeddings([query])
            
            if not query_embeddings or not query_embeddings[0]:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search in ChromaDB
            results = self.ticket_collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k
            )
            
            # Format results
            formatted_results = []
            if results and 'documents' in results:
                for i in range(len(results['documents'][0])):
                    result = {
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 1.0
                    }
                    
                    # Add summary field for compatibility
                    result['summary'] = result['text']
                    
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in semantic ticket search: {e}")
            return []
    
    async def search_knowledge_base(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base using semantic search via ChromaDB."""
        if not self.knowledge_collection:
            logger.warning("Knowledge collection not available for semantic search")
            return []
        
        try:
            # Import here to avoid circular imports
            from llm_client import get_llm_client
            llm_client = get_llm_client()
            
            # Generate embedding for the query
            query_embeddings = llm_client.generate_embeddings([query])
            
            if not query_embeddings or not query_embeddings[0]:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search in ChromaDB
            results = self.knowledge_collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k
            )
            
            # Format results
            formatted_results = []
            if results and 'documents' in results:
                for i in range(len(results['documents'][0])):
                    result = {
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 1.0
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in knowledge base search: {e}")
            return []
    
    def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics from SQLite database."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM tickets')
            total = cursor.fetchone()[0]
            
            # Get stats by status
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM tickets 
                GROUP BY status
            ''')
            by_status = dict(cursor.fetchall())
            
            # Get stats by priority
            cursor.execute('''
                SELECT priority, COUNT(*) 
                FROM tickets 
                GROUP BY priority
            ''')
            by_priority = dict(cursor.fetchall())
            
            # Get stats by category
            cursor.execute('''
                SELECT category, COUNT(*) 
                FROM tickets 
                GROUP BY category
            ''')
            by_category = dict(cursor.fetchall())
            
            # Get stats by team
            cursor.execute('''
                SELECT assigned_team, COUNT(*) 
                FROM tickets 
                GROUP BY assigned_team
            ''')
            by_team = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total': total,
                'by_status': by_status,
                'by_priority': by_priority,
                'by_category': by_category,
                'by_team': by_team
            }
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            return {
                'total': 0,
                'by_status': {},
                'by_priority': {},
                'by_category': {},
                'by_team': {}
            }
    
    def get_tickets_by_criteria(self, category: str = None, priority: str = None, 
                               status: str = None, assigned_team: str = None, 
                               limit: int = 20) -> List[Dict[str, Any]]:
        """Get tickets by specific criteria from SQLite database."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Build dynamic query
            query_parts = ['''
                SELECT id, title, description, category, priority, status, 
                       resolution, resolution_time, assigned_team, created_date, updated_date
                FROM tickets 
                WHERE 1=1
            ''']
            params = []
            
            if category:
                query_parts.append("AND category = ?")
                params.append(category)
            
            if priority:
                query_parts.append("AND priority = ?")
                params.append(priority)
            
            if status:
                query_parts.append("AND status = ?")
                params.append(status)
            
            if assigned_team:
                query_parts.append("AND assigned_team = ?")
                params.append(assigned_team)
            
            query_parts.append("ORDER BY created_date DESC LIMIT ?")
            params.append(limit)
            
            final_query = " ".join(query_parts)
            cursor.execute(final_query, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            # Format results
            tickets = []
            for row in rows:
                tickets.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'category': row[3],
                    'priority': row[4],
                    'status': row[5],
                    'resolution': row[6],
                    'resolution_time': row[7],
                    'assigned_team': row[8],
                    'created_date': row[9],
                    'updated_date': row[10]
                })
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error getting tickets by criteria: {e}")
            return []
    
    def search_tickets_by_text(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search tickets by text in title and description using SQLite LIKE queries."""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, description, category, priority, status, 
                       resolution, resolution_time, assigned_team, created_date, updated_date
                FROM tickets 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY created_date DESC 
                LIMIT ?
            ''', (f"%{search_text}%", f"%{search_text}%", limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Format results
            tickets = []
            for row in rows:
                tickets.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'category': row[3],
                    'priority': row[4],
                    'status': row[5],
                    'resolution': row[6],
                    'resolution_time': row[7],
                    'assigned_team': row[8],
                    'created_date': row[9],
                    'updated_date': row[10]
                })
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error searching tickets by text: {e}")
            return []
    
    def health_check(self) -> Dict[str, bool]:
        """Check the health of database connections."""
        health = {
            'sqlite': False,
            'chromadb': False,
            'knowledge_collection': False,
            'ticket_collection': False
        }
        
        # Check SQLite
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tickets')
            conn.close()
            health['sqlite'] = True
        except Exception as e:
            logger.error(f"SQLite health check failed: {e}")
        
        # Check ChromaDB
        try:
            if self.chroma_client:
                collections = self.chroma_client.list_collections()
                health['chromadb'] = True
                
                # Check specific collections
                collection_names = [c.name for c in collections]
                health['knowledge_collection'] = 'knowledge_base' in collection_names
                health['ticket_collection'] = 'ticket_summaries' in collection_names
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
        
        return health