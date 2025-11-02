#!/usr/bin/env python3
"""
LLM Client abstraction layer.
Uses Bedrock as primary with Ollama fallback.
Uses the converse API for better compatibility.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ollama_client import get_ollama_client

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client that uses Bedrock as primary, falls back to Ollama.
    Uses the converse API for better compatibility with OpenAI GPT models.
    """
    
    def __init__(self, aws_region: str = "us-east-2"):
        self.aws_region = aws_region
        self.bedrock_client = None
        self.ollama_client = None
        self.use_ollama = False
        
        # Primary model configuration
        self.primary_model = 'openai.gpt-oss-120b-1:0'  # Using your working model
        
        # Try to initialize Bedrock first
        self._try_initialize_bedrock()
        
        # If Bedrock fails, try Ollama
        if not self.bedrock_client:
            self._try_initialize_ollama()
    
    def _try_initialize_bedrock(self):
        """Try to initialize AWS Bedrock client with converse API."""
        try:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.aws_region)
            
            # Test with a simple converse call using your working syntax
            test_response = self.bedrock_client.converse(
                modelId=self.primary_model,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": "test"}]
                    }
                ],
                inferenceConfig={
                    "maxTokens": 512,
                    "temperature": 0.1,
                    "topP": 0.5
                }
            )
            
            logger.info("✅ Using AWS Bedrock with OpenAI GPT model")
            self.use_ollama = False
            
        except (ClientError, NoCredentialsError, Exception) as e:
            logger.warning(f"⚠️ Bedrock initialization failed: {e}")
            self.bedrock_client = None
    
    def _try_initialize_ollama(self):
        """Try to initialize Ollama client."""
        try:
            self.ollama_client = get_ollama_client()
            if self.ollama_client:
                logger.info("✅ Using Ollama as fallback")
                self.use_ollama = True
            else:
                logger.error("❌ Neither Bedrock nor Ollama available")
        except Exception as e:
            logger.error(f"Ollama initialization failed: {e}")
    
    def is_available(self) -> bool:
        """Check if any LLM client is available."""
        return self.bedrock_client is not None or (self.ollama_client is not None and self.use_ollama)
    
    def get_provider(self) -> str:
        """Get current provider name."""
        if self.bedrock_client and not self.use_ollama:
            return "bedrock"
        elif self.ollama_client and self.use_ollama:
            return "ollama"
        else:
            return "none"
    
    def invoke_model(self, modelId: str, body: str, contentType: str = "application/json") -> Dict[str, Any]:
        """
        Invoke model with automatic fallback.
        
        Args:
            modelId: Model identifier (ignored for Bedrock, uses primary_model)
            body: JSON request body
            contentType: Content type
            
        Returns:
            Response in consistent format
        """
        # Try Bedrock first if available
        if self.bedrock_client and not self.use_ollama:
            try:
                # Parse the body to extract messages and parameters
                request_data = json.loads(body)
                messages = request_data.get('messages', [])
                
                # Add system context for IT conversational bot
                bedrock_messages = []
                
                # Add system context
                system_context = self._get_system_context()
                bedrock_messages.append({
                    "role": "user",
                    "content": [{"text": system_context}]
                })
                bedrock_messages.append({
                    "role": "assistant", 
                    "content": [{"text": "I understand. I'm your IT support assistant and I'll provide helpful, human-like responses for all your IT questions and support needs."}]
                })
                
                # Convert user messages to Bedrock converse format
                for msg in messages:
                    if isinstance(msg.get('content'), str):
                        # Handle string content
                        bedrock_messages.append({
                            "role": msg["role"],
                            "content": [{"text": msg["content"]}]
                        })
                    elif isinstance(msg.get('content'), list):
                        # Already in correct format
                        bedrock_messages.append(msg)
                    else:
                        # Fallback
                        bedrock_messages.append({
                            "role": msg["role"],
                            "content": [{"text": str(msg.get("content", ""))}]
                        })
                
                # Extract inference parameters
                max_tokens = request_data.get('max_tokens', 1000)
                temperature = request_data.get('temperature', 0.4)
                top_p = request_data.get('top_p', 0.5)
                
                # Call Bedrock converse API
                response = self.bedrock_client.converse(
                    modelId=self.primary_model,
                    messages=bedrock_messages,
                    inferenceConfig={
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                        "topP": top_p
                    }
                )
                
                # Track AWS call
                try:
                    from services.aws_call_tracker import track_aws_call
                    track_aws_call('bedrock')
                except:
                    pass  # Don't break if tracker fails
                
                # Convert response to expected format (skip reasoning content)
                content = response['output']['message']['content']
                response_text = ""
                for item in content:
                    if 'text' in item:
                        response_text = item['text']
                        break
                
                # Return in format expected by existing code
                class MockBody:
                    def __init__(self, content):
                        self.content = content
                    
                    def read(self):
                        return self.content.encode()
                
                return {
                    'body': MockBody(json.dumps({
                        'content': [{'text': response_text}]
                    }))
                }
                
            except Exception as e:
                logger.warning(f"Bedrock call failed, trying Ollama: {e}")
                # Fall back to Ollama for this call
                if self.ollama_client:
                    return self.ollama_client.invoke_model(modelId, body, contentType)
                else:
                    raise Exception("No LLM provider available")
        
        # Use Ollama
        elif self.ollama_client and self.use_ollama:
            return self.ollama_client.invoke_model(modelId, body, contentType)
        
        else:
            raise Exception("No LLM provider available")
    
    def converse(self, messages: List[Dict[str, Any]], max_tokens: int = 1000, temperature: float = 0.4, top_p: float = 0.5, include_system_context: bool = True) -> str:
        """
        Direct converse method for easier usage.
        
        Args:
            messages: List of messages in format [{"role": "user", "content": "text"}]
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            top_p: Top-p for generation
            
        Returns:
            Generated text response
        """
        if self.bedrock_client and not self.use_ollama:
            try:
                # Add system context for IT conversational bot
                bedrock_messages = []
                
                if include_system_context:
                    system_context = self._get_system_context()
                    bedrock_messages.append({
                        "role": "user",
                        "content": [{"text": system_context}]
                    })
                    bedrock_messages.append({
                        "role": "assistant", 
                        "content": [{"text": "I understand. I'm your IT support assistant and I'll provide helpful, human-like responses for all your IT questions and support needs."}]
                    })
                
                # Convert user messages to Bedrock format
                for msg in messages:
                    bedrock_messages.append({
                        "role": msg["role"],
                        "content": [{"text": msg["content"]}]
                    })
                
                # Call Bedrock converse API
                response = self.bedrock_client.converse(
                    modelId=self.primary_model,
                    messages=bedrock_messages,
                    inferenceConfig={
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                        "topP": top_p
                    }
                )
                
                # Track AWS call
                try:
                    from services.aws_call_tracker import track_aws_call
                    track_aws_call('bedrock')
                except:
                    pass  # Don't break if tracker fails
                
                # Extract text response (skip reasoning content)
                content = response['output']['message']['content']
                
                for item in content:
                    if 'text' in item:
                        return item['text']
                
                # If no text found, return empty string
                return ""
                
            except Exception as e:
                logger.warning(f"Bedrock converse failed, trying Ollama: {e}")
                # Fall back to Ollama
                if self.ollama_client:
                    body = json.dumps({
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    })
                    response = self.ollama_client.invoke_model("fallback", body)
                    response_body = json.loads(response['body'].read())
                    return response_body['content'][0]['text']
                else:
                    raise Exception("No LLM provider available")
        
        elif self.ollama_client and self.use_ollama:
            # Use Ollama
            body = json.dumps({
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            })
            response = self.ollama_client.invoke_model("fallback", body)
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        
        else:
            raise Exception("No LLM provider available")
    
    def _get_system_context(self) -> str:
        """Get system context for IT conversational bot."""
        return """You are an intelligent IT support assistant and conversational bot. Your role is to help users with:

1. IT Support Tickets - Check status, provide updates, find resolutions
2. Technical Knowledge - Answer questions about products, features, troubleshooting
3. General IT Help - Provide guidance on technical issues and procedures

IMPORTANT BEHAVIORAL GUIDELINES:
- Be conversational and human-like, not robotic
- Speak naturally as if you're a helpful IT colleague
- Provide complete, useful information for every query
- Be friendly, professional, and approachable
- Use natural language patterns and avoid overly formal responses
- When you don't know something, admit it honestly and offer alternatives
- Keep responses concise but comprehensive
- Use examples when helpful
- Show empathy for user frustrations with technical issues
- Do not make responses long or wordy in the name of being friendly.

RESPONSE STYLE:
- Talk like a knowledgeable human IT support person
- Use contractions and natural speech patterns
- Be warm and helpful, not cold or mechanical
- Do not forget to be Professional
- Provide actionable information whenever possible
- Ask clarifying questions when needed
- Acknowledge user concerns and validate their experience

Remember: You're here to make IT support feel personal and helpful, not automated and frustrating."""
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with automatic fallback."""
        # Try Bedrock first if available
        if self.bedrock_client and not self.use_ollama:
            try:
                embeddings = []
                for text in texts:
                    body = json.dumps({"inputText": text})
                    response = self.bedrock_client.invoke_model(
                        modelId="amazon.titan-embed-text-v2:0",
                        body=body,
                        contentType="application/json"
                    )
                    response_body = json.loads(response['body'].read())
                    embeddings.append(response_body['embedding'])
                return embeddings
                
            except Exception as e:
                logger.warning(f"Bedrock embeddings failed, trying Ollama: {e}")
                # Fall back to Ollama
                if self.ollama_client:
                    return self.ollama_client.generate_embeddings(texts)
                else:
                    # Return zero vectors as last resort
                    return [[0.0] * 1536 for _ in texts]
        
        # Use Ollama
        elif self.ollama_client and self.use_ollama:
            return self.ollama_client.generate_embeddings(texts)
        
        else:
            # Return zero vectors as fallback
            logger.error("No embedding provider available, returning zero vectors")
            return [[0.0] * 1536 for _ in texts]
    
    def health_check(self) -> bool:
        """Perform health check on current provider."""
        try:
            if self.use_ollama and self.ollama_client:
                # Test Ollama
                body = json.dumps({
                    "messages": [{"role": "user", "content": "health check"}]
                })
                response = self.ollama_client.invoke_model("test", body)
                return True
                
            elif self.bedrock_client:
                # Test Bedrock with converse API
                response = self.bedrock_client.converse(
                    modelId=self.primary_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": "health check"}]
                        }
                    ],
                    inferenceConfig={
                        "maxTokens": 512,
                        "temperature": 0.1,
                        "topP": 0.5
                    }
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global LLM client instance
_llm_client = None


def get_llm_client(aws_region: str = "us-east-2") -> LLMClient:
    """Get global LLM client instance."""
    global _llm_client
    
    if _llm_client is None:
        _llm_client = LLMClient(aws_region)
    
    return _llm_client


def force_bedrock():
    """Force using Bedrock (call this when credentials are fixed)."""
    global _llm_client
    _llm_client = None  # Reset to reinitialize
    client = get_llm_client()
    if client.bedrock_client:
        client.use_ollama = False
        logger.info("🔄 Switched back to Bedrock")
    else:
        logger.warning("⚠️ Bedrock still not available")


def force_ollama():
    """Force using Ollama."""
    global _llm_client
    client = get_llm_client()
    if client.ollama_client:
        client.use_ollama = True
        logger.info("🔄 Switched to Ollama")
    else:
        logger.warning("⚠️ Ollama not available")


if __name__ == "__main__":
    # Test the LLM client
    print("Testing LLM Client...")
    
    client = get_llm_client()
    print(f"Provider: {client.get_provider()}")
    print(f"Available: {client.is_available()}")
    
    if client.is_available():
        print(f"Health check: {client.health_check()}")
    
    print("Done!")