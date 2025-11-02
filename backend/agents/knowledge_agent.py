"""
KnowledgeAgent implementation for RAG operations on PDF knowledge base.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
import re
from dataclasses import dataclass

from .base_agent import BaseAgent, AgentType, AgentResult, ConversationContext
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_access import DataAccess


@dataclass
class KnowledgeChunk:
    """Represents a chunk of knowledge from the knowledge base."""
    text: str
    metadata: Dict[str, Any]
    relevance_score: float
    source: str
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None


@dataclass
class ContextualResponse:
    """Response with contextual information from knowledge base."""
    answer: str
    supporting_chunks: List[KnowledgeChunk]
    confidence: float
    sources: List[str]


@dataclass
class VerificationResult:
    """Result of information verification against knowledge base."""
    is_verified: bool
    confidence: float
    supporting_evidence: List[KnowledgeChunk]
    contradicting_evidence: List[KnowledgeChunk]


class KnowledgeAgent(BaseAgent):
    """
    Specialized agent for handling RAG operations on PDF knowledge base using ChromaDB.
    Provides semantic search, contextual information retrieval, and relevance scoring.
    """
    
    def __init__(self, sqlite_db_path: str = "./data/voice_assistant.db", chroma_db_path: str = "./data/chroma_db"):
        super().__init__("KnowledgeAgent", AgentType.KNOWLEDGE)
        self.data_access = DataAccess(sqlite_db_path, chroma_db_path)
        self.relevance_threshold = 0.5  # Lower threshold for better recall
        self.max_chunks_per_response = 5
    
    async def process_query(self, query: str, context: ConversationContext) -> AgentResult:
        """
        Process a knowledge-related query using RAG operations.
        """
        start_time = time.time()
        
        try:
            # Perform semantic search
            knowledge_chunks = await self.semantic_search(query, top_k=10)
            
            # Filter by relevance threshold
            relevant_chunks = [
                chunk for chunk in knowledge_chunks 
                if chunk.relevance_score >= self.relevance_threshold
            ]
            
            # Get contextual information
            contextual_response = await self.get_contextual_info(query, relevant_chunks)
            
            # Calculate confidence based on relevance scores and chunk quality
            confidence = self._calculate_confidence(relevant_chunks, query)
            
            # Boost confidence if we have any relevant chunks
            if relevant_chunks and confidence < 0.6:
                confidence = max(confidence, 0.6)  # Minimum confidence for any relevant results
            
            result_data = {
                "type": "knowledge_search",
                "query": query,
                "chunks_found": len(knowledge_chunks),
                "relevant_chunks": len(relevant_chunks),
                "contextual_response": {
                    "answer": contextual_response.answer,
                    "confidence": contextual_response.confidence,
                    "sources": contextual_response.sources
                },
                "knowledge_chunks": [self._chunk_to_dict(chunk) for chunk in relevant_chunks[:self.max_chunks_per_response]]
            }
            
            processing_time = time.time() - start_time
            # Be less aggressive about escalation for follow-up questions
            is_followup = any(word in query.lower() for word in ['it', 'that', 'this', 'smaller', 'shorter', 'more', 'less'])
            requires_escalation = (confidence < 0.4 or len(relevant_chunks) == 0) and not is_followup
            
            return AgentResult(
                agent_name=self.name,
                data=result_data,
                confidence=confidence,
                processing_time=processing_time,
                requires_escalation=requires_escalation,
                metadata={
                    "chunks_found": len(knowledge_chunks),
                    "relevant_chunks": len(relevant_chunks),
                    "avg_relevance": sum(c.relevance_score for c in relevant_chunks) / len(relevant_chunks) if relevant_chunks else 0.0
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return AgentResult(
                agent_name=self.name,
                data={"error": str(e)},
                confidence=0.0,
                processing_time=processing_time,
                requires_escalation=True,
                metadata={"error": True}
            )
    
    def _chunk_to_dict(self, chunk: KnowledgeChunk) -> Dict[str, Any]:
        """Convert KnowledgeChunk to dictionary for serialization."""
        return {
            "text": chunk.text,
            "relevance_score": chunk.relevance_score,
            "source": chunk.source,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "metadata": chunk.metadata
        }
    
    async def semantic_search(self, query: str, top_k: int = 5) -> List[KnowledgeChunk]:
        """
        Perform semantic search on the knowledge base using ChromaDB embeddings.
        """
        try:
            # Preprocess query to handle common transcription errors
            processed_query = self._preprocess_voice_query(query)
            
            # Use the existing data access method
            raw_results = await self.data_access.search_knowledge_base(processed_query, top_k=top_k)
            
            # Convert to KnowledgeChunk objects
            knowledge_chunks = []
            for result in raw_results:
                # Calculate relevance score (convert distance to similarity)
                distance = result.get('distance', 1.0)
                relevance_score = max(0.0, 1.0 - distance)  # Convert distance to similarity score
                
                chunk = KnowledgeChunk(
                    text=result['text'],
                    metadata=result['metadata'],
                    relevance_score=relevance_score,
                    source=result['metadata'].get('source', 'unknown'),
                    page_number=result['metadata'].get('page_number'),
                    chunk_index=result['metadata'].get('chunk_index')
                )
                knowledge_chunks.append(chunk)
            
            # Sort by relevance score
            knowledge_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return knowledge_chunks
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
    
    async def get_contextual_info(self, topic: str, chunks: Optional[List[KnowledgeChunk]] = None) -> ContextualResponse:
        """
        Get contextual information about a topic from the knowledge base.
        """
        if chunks is None:
            chunks = await self.semantic_search(topic, top_k=5)
        
        if not chunks:
            # Check if the query might have unclear terms that need clarification
            unclear_terms = self._detect_unclear_terms(topic)
            if unclear_terms:
                return ContextualResponse(
                    answer=f"I couldn't find information about '{unclear_terms}'. Did you mean something else? Could you clarify?",
                    supporting_chunks=[],
                    confidence=0.1,  # Low confidence to trigger clarification
                    sources=[]
                )
            else:
                return ContextualResponse(
                    answer="I couldn't find relevant information about this topic in the knowledge base.",
                    supporting_chunks=[],
                    confidence=0.0,
                    sources=[]
                )
        
        # Filter high-relevance chunks with more permissive threshold
        high_relevance_chunks = [c for c in chunks if c.relevance_score >= self.relevance_threshold]
        
        # If no high relevance chunks, use medium relevance chunks
        if not high_relevance_chunks:
            medium_relevance_chunks = [c for c in chunks if c.relevance_score >= 0.3]
            if medium_relevance_chunks:
                high_relevance_chunks = medium_relevance_chunks[:3]  # Take top 3 medium relevance
            else:
                return ContextualResponse(
                    answer="I found some information, but it doesn't seem directly relevant to your question.",
                    supporting_chunks=chunks[:2],  # Include top 2 even if low relevance
                    confidence=0.2,
                    sources=list(set(c.source for c in chunks[:2]))
                )
        
        # Generate contextual answer
        answer = self._generate_contextual_answer(topic, high_relevance_chunks)
        
        # Calculate confidence
        avg_relevance = sum(c.relevance_score for c in high_relevance_chunks) / len(high_relevance_chunks)
        confidence = min(avg_relevance * 1.1, 0.95)  # Boost slightly but cap at 0.95
        
        # Get unique sources
        sources = list(set(c.source for c in high_relevance_chunks))
        
        return ContextualResponse(
            answer=answer,
            supporting_chunks=high_relevance_chunks,
            confidence=confidence,
            sources=sources
        )
    
    def _generate_contextual_answer(self, topic: str, chunks: List[KnowledgeChunk]) -> str:
        """
        Generate a contextual answer from relevant knowledge chunks.
        """
        if not chunks:
            return "No relevant information found."
        
        # For now, provide a structured summary of the chunks
        # In a full implementation, this could use an LLM to synthesize the information
        
        answer_parts = []
        
        # Group chunks by source/page for better organization
        chunks_by_source = {}
        for chunk in chunks:
            source_key = f"{chunk.source}"
            if chunk.page_number:
                source_key += f" (page {chunk.page_number})"
            
            if source_key not in chunks_by_source:
                chunks_by_source[source_key] = []
            chunks_by_source[source_key].append(chunk)
        
        # Create structured answer
        if len(chunks_by_source) == 1:
            # Single source
            source_name = list(chunks_by_source.keys())[0]
            answer_parts.append(f"Based on {source_name}:")
            
            for chunk in chunks_by_source[source_name][:3]:  # Top 3 chunks
                # Extract key sentences (simplified approach)
                sentences = self._extract_key_sentences(chunk.text, topic)
                if sentences:
                    answer_parts.extend(sentences)
        else:
            # Multiple sources
            answer_parts.append("Based on the available documentation:")
            
            for source_name, source_chunks in list(chunks_by_source.items())[:2]:  # Top 2 sources
                answer_parts.append(f"\nFrom {source_name}:")
                
                best_chunk = max(source_chunks, key=lambda x: x.relevance_score)
                sentences = self._extract_key_sentences(best_chunk.text, topic)
                if sentences:
                    answer_parts.extend(sentences[:2])  # Top 2 sentences per source
        
        return " ".join(answer_parts) if answer_parts else "Information found but unable to extract relevant details."
    
    def _extract_key_sentences(self, text: str, topic: str) -> List[str]:
        """
        Extract key sentences from text that are most relevant to the topic.
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return []
        
        # Score sentences based on topic relevance (simplified approach)
        topic_words = set(topic.lower().split())
        scored_sentences = []
        
        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            # Simple word overlap scoring
            overlap = len(topic_words.intersection(sentence_words))
            if overlap > 0:
                scored_sentences.append((sentence, overlap))
        
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored_sentences[:3]]
    
    def _calculate_confidence(self, chunks: List[KnowledgeChunk], query: str) -> float:
        """
        Calculate confidence score based on chunk relevance and query match.
        """
        if not chunks:
            return 0.0
        
        # Base confidence on average relevance score
        avg_relevance = sum(c.relevance_score for c in chunks) / len(chunks)
        
        # Boost confidence if we have multiple chunks
        chunk_count_boost = min(len(chunks) * 0.05, 0.15)
        
        # Boost confidence if query terms appear in chunk text
        query_terms = set(query.lower().split())
        term_matches = 0
        total_terms = len(query_terms)
        
        if total_terms > 0:
            for chunk in chunks[:3]:  # Check top 3 chunks
                chunk_words = set(chunk.text.lower().split())
                matches = len(query_terms.intersection(chunk_words))
                term_matches += matches
            
            term_match_ratio = min(term_matches / (total_terms * 3), 1.0)
            term_boost = term_match_ratio * 0.2
        else:
            term_boost = 0.0
        
        # Special boost for SuperOps-related queries
        superops_terms = ['superops', 'probe', 'monitoring', 'network', 'device']
        if any(term in query.lower() for term in superops_terms):
            superops_boost = 0.1
        else:
            superops_boost = 0.0
        
        confidence = avg_relevance + chunk_count_boost + term_boost + superops_boost
        return min(confidence, 0.95)  # Cap at 0.95
    
    def _detect_unclear_terms(self, query: str) -> Optional[str]:
        """Detect potentially unclear or misspelled terms in the query."""
        query_lower = query.lower()
        
        # Common typos or unclear terms
        unclear_mappings = {
            'sulus': 'SuperOps',
            'po': 'probe', 
            'ops': 'SuperOps',
            'super ops': 'SuperOps',
            'superop': 'SuperOps'
        }
        
        for unclear_term, suggested_term in unclear_mappings.items():
            if unclear_term in query_lower:
                return unclear_term
        
        # Check for very short technical terms that might be unclear
        words = query_lower.split()
        for word in words:
            if len(word) <= 2 and word.isalpha() and word not in ['is', 'a', 'an', 'to', 'in', 'on', 'at', 'it']:
                return word
        
        return None
    
    async def verify_information(self, claim: str) -> VerificationResult:
        """
        Verify a claim against the knowledge base.
        """
        try:
            # Search for information related to the claim
            chunks = await self.semantic_search(claim, top_k=10)
            
            if not chunks:
                return VerificationResult(
                    is_verified=False,
                    confidence=0.0,
                    supporting_evidence=[],
                    contradicting_evidence=[]
                )
            
            # Analyze chunks for supporting vs contradicting evidence
            supporting_evidence = []
            contradicting_evidence = []
            
            claim_words = set(claim.lower().split())
            
            for chunk in chunks:
                if chunk.relevance_score >= 0.6:  # Lower threshold for verification
                    chunk_words = set(chunk.text.lower().split())
                    
                    # Simple heuristic: high word overlap suggests support
                    overlap_ratio = len(claim_words.intersection(chunk_words)) / len(claim_words)
                    
                    if overlap_ratio > 0.3:
                        supporting_evidence.append(chunk)
                    elif chunk.relevance_score > 0.7:
                        # High relevance but low overlap might indicate contradiction
                        # This is a simplified approach - in practice, would need NLP analysis
                        pass
            
            # Determine verification result
            is_verified = len(supporting_evidence) > 0
            confidence = min(sum(c.relevance_score for c in supporting_evidence) / max(len(supporting_evidence), 1), 0.9)
            
            return VerificationResult(
                is_verified=is_verified,
                confidence=confidence,
                supporting_evidence=supporting_evidence,
                contradicting_evidence=contradicting_evidence
            )
            
        except Exception as e:
            print(f"Error verifying information: {e}")
            return VerificationResult(
                is_verified=False,
                confidence=0.0,
                supporting_evidence=[],
                contradicting_evidence=[]
            )
    
    async def get_related_topics(self, topic: str, max_topics: int = 5) -> List[Dict[str, Any]]:
        """
        Find topics related to the given topic based on semantic similarity.
        """
        try:
            # Get chunks related to the topic
            chunks = await self.semantic_search(topic, top_k=20)
            
            # Extract potential related topics from chunk metadata and content
            related_topics = {}
            
            for chunk in chunks:
                if chunk.relevance_score >= 0.5:
                    # Extract topics from metadata if available
                    if 'topics' in chunk.metadata:
                        for related_topic in chunk.metadata['topics']:
                            if related_topic.lower() != topic.lower():
                                if related_topic not in related_topics:
                                    related_topics[related_topic] = []
                                related_topics[related_topic].append(chunk.relevance_score)
                    
                    # Extract potential topics from text (simplified approach)
                    # Look for capitalized phrases that might be topics
                    import re
                    potential_topics = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', chunk.text)
                    
                    for potential_topic in potential_topics:
                        if (len(potential_topic.split()) <= 3 and 
                            potential_topic.lower() != topic.lower() and
                            len(potential_topic) > 3):
                            
                            if potential_topic not in related_topics:
                                related_topics[potential_topic] = []
                            related_topics[potential_topic].append(chunk.relevance_score * 0.7)  # Lower weight for extracted topics
            
            # Score and rank related topics
            scored_topics = []
            for topic_name, scores in related_topics.items():
                avg_score = sum(scores) / len(scores)
                frequency = len(scores)
                combined_score = avg_score * 0.7 + min(frequency / 5.0, 1.0) * 0.3
                
                scored_topics.append({
                    'topic': topic_name,
                    'relevance_score': combined_score,
                    'frequency': frequency
                })
            
            # Sort by combined score and return top topics
            scored_topics.sort(key=lambda x: x['relevance_score'], reverse=True)
            return scored_topics[:max_topics]
            
        except Exception as e:
            print(f"Error finding related topics: {e}")
            return []
    
    def _preprocess_voice_query(self, query: str) -> str:
        """Preprocess voice query to handle common transcription errors."""
        import re
        
        processed_query = query.lower()
        
        # Define corrections with word boundaries to avoid partial replacements
        corrections = [
            (r'\bherbs\b', 'probe'),
            (r'\bherb\b', 'probe'), 
            (r'\bprob\b', 'probe'),  # Only replace "prob" as whole word, not "probe"
            (r'\bsuper obs\b', 'superops'),
            (r'\bsuper ops\b', 'superops'),
            (r'\bsuper op\b', 'superops'),
            (r'\bso ops\b', 'superops'),
            (r'\bsuros\b', 'superops'),
            (r'\bsoros\b', 'superops'),
            (r'\bsulus ops\b', 'superops'),  # "Sulus ops" → "SuperOps"
            (r'\bpoloies\b', 'policies'),    # "poloies" → "policies"
            (r'\bpolices\b', 'policies'),    # "polices" → "policies"
            (r'\bgaming\b', 'give me'),      # "Gaming step by step" → "Give me step by step"
        ]
        
        # Apply corrections using regex word boundaries
        original_query = processed_query
        for pattern, replacement in corrections:
            processed_query = re.sub(pattern, replacement, processed_query)
        
        # Only show correction message if something actually changed
        if processed_query != original_query:
            print(f"🔧 Voice query corrected: '{query}' → '{processed_query}'")
            return processed_query
        else:
            return query  # Return original case if no corrections needed
    
    async def health_check(self) -> bool:
        """Check if the KnowledgeAgent is healthy and ready."""
        try:
            # Test ChromaDB connection with a simple search
            test_results = await self.data_access.search_knowledge_base("test", top_k=1)
            return True  # If no exception, connection is working
            
        except Exception as e:
            print(f"KnowledgeAgent health check failed: {e}")
            return False