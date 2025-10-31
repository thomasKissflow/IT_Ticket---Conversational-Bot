#!/usr/bin/env python3
"""
LLM Client abstraction layer.
Automatically falls back to Ollama if Bedrock credentials fail.
Easy to switch back to Bedrock when credentials are fixed.
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
    Unified LLM client that tries Bedrock first, falls back to Ollama.
    Keeps the same interface for easy switching.
    """
    
    def __init__(self, aws_region: str = "us-east-1"):
        self.aws_region = aws_region
        self.bedrock_client = None
        self.ollama_client = None
        self.use_ollama = False
        
        # Try to initialize Bedrock first
        self._try_initialize_bedrock()
        
        # If Bedrock fails, try Ollama
        if not self.bedrock_client:
            self._try_initialize_ollama()
    
    def _try_initialize_bedrock(self):
        """Try to initialize AWS Bedrock client."""
        try:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.aws_region)
            
            # Test with a simple call
            test_body = json.dumps({
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10,
                "temperature": 0.1
            })
            
            # Try a quick test call
            self.bedrock_client.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=test_body,
                contentType='application/json'
            )
            
            logger.info("✅ Using AWS Bedrock")
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
            modelId: Model identifier
            body: JSON request body
            contentType: Content type
            
        Returns:
            Response in consistent format
        """
        # Try Bedrock first if available
        if self.bedrock_client and not self.use_ollama:
            try:
                return self.bedrock_client.invoke_model(
                    modelId=modelId,
                    body=body,
                    contentType=contentType
                )
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
                # Test Bedrock
                body = json.dumps({
                    "messages": [{"role": "user", "content": "health check"}],
                    "max_tokens": 10
                })
                self.bedrock_client.invoke_model(
                    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    body=body,
                    contentType='application/json'
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global LLM client instance
_llm_client = None


def get_llm_client(aws_region: str = "us-east-1") -> LLMClient:
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