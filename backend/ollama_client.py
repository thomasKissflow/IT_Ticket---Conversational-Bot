#!/usr/bin/env python3
"""
Ollama client as a fallback for AWS Bedrock.
Simple HTTP client that mimics Bedrock's interface for easy switching.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class OllamaClient:
    """Simple Ollama client that mimics AWS Bedrock interface."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.chat_model = "deepseek-r1:1.5b"  # Fast model for quick responses
        self.embedding_model = "nomic-embed-text"
        
        # Check if Ollama is available
        self.available = self._check_availability()
        if self.available:
            self._ensure_models()
    
    def _check_availability(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _ensure_models(self):
        """Ensure required models are available."""
        try:
            # Check available models
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                # Pull chat model if not available
                if not any(self.chat_model in name for name in model_names):
                    logger.info(f"Pulling chat model: {self.chat_model}")
                    self._pull_model(self.chat_model)
                
                # Pull embedding model if not available
                if not any(self.embedding_model in name for name in model_names):
                    logger.info(f"Pulling embedding model: {self.embedding_model}")
                    self._pull_model(self.embedding_model)
                    
        except Exception as e:
            logger.warning(f"Could not ensure models: {e}")
    
    def _pull_model(self, model_name: str):
        """Pull a model from Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=300  # 5 minutes timeout for model download
            )
            if response.status_code == 200:
                logger.info(f"Successfully pulled model: {model_name}")
            else:
                logger.warning(f"Failed to pull model {model_name}: {response.text}")
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
    
    def invoke_model(self, modelId: str, body: str, contentType: str = "application/json") -> Dict[str, Any]:
        """
        Mimic AWS Bedrock's invoke_model method.
        
        Args:
            modelId: Model identifier (ignored, uses configured model)
            body: JSON string with the request
            contentType: Content type (ignored)
            
        Returns:
            Response in Bedrock-like format
        """
        if not self.available:
            raise Exception("Ollama is not available")
        
        try:
            request_data = json.loads(body)
            
            # Handle different request formats
            if "messages" in request_data:
                # Chat completion format
                return self._handle_chat_completion(request_data)
            elif "inputText" in request_data:
                # Embedding format
                return self._handle_embedding(request_data)
            else:
                # Legacy format - convert to chat
                return self._handle_legacy_format(request_data)
                
        except Exception as e:
            logger.error(f"Ollama invoke_model error: {e}")
            raise
    
    def _handle_chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat completion requests."""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.chat_model,
                    "messages": request_data["messages"],
                    "stream": False,
                    "options": {
                        "temperature": request_data.get("temperature", 0.7),
                        "top_p": request_data.get("top_p", 0.9)
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                ollama_response = response.json()
                
                # Convert to Bedrock-like format
                bedrock_response = {
                    "content": [
                        {
                            "text": ollama_response["message"]["content"]
                        }
                    ],
                    "usage": {
                        "input_tokens": ollama_response.get("prompt_eval_count", 0),
                        "output_tokens": ollama_response.get("eval_count", 0)
                    }
                }
                
                # Create mock response body
                class MockBody:
                    def read(self):
                        return json.dumps(bedrock_response).encode()
                
                return {"body": MockBody()}
            else:
                raise Exception(f"Ollama chat error: {response.text}")
                
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise
    
    def _handle_embedding(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle embedding requests."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": request_data["inputText"]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                ollama_response = response.json()
                
                # Convert to Bedrock-like format
                bedrock_response = {
                    "embedding": ollama_response["embedding"]
                }
                
                # Create mock response body
                class MockBody:
                    def read(self):
                        return json.dumps(bedrock_response).encode()
                
                return {"body": MockBody()}
            else:
                raise Exception(f"Ollama embedding error: {response.text}")
                
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    def _handle_legacy_format(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle legacy Bedrock format by converting to chat."""
        # Extract prompt from various possible formats
        prompt = ""
        if "prompt" in request_data:
            prompt = request_data["prompt"]
        elif "anthropic_version" in request_data:
            # Claude format
            prompt = request_data.get("messages", [{}])[-1].get("content", "")
        
        if not prompt:
            raise Exception("Could not extract prompt from request")
        
        # Convert to chat format
        messages = [{"role": "user", "content": prompt}]
        return self._handle_chat_completion({"messages": messages})
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        
        for text in texts:
            try:
                body = json.dumps({"inputText": text})
                response = self.invoke_model("embedding-model", body)
                
                response_body = json.loads(response["body"].read())
                embedding = response_body["embedding"]
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error generating embedding for text: {e}")
                # Return zero vector as fallback (same dimension as nomic-embed-text)
                embeddings.append([0.0] * 768)
        
        return embeddings


# Global Ollama client instance
ollama_client = None


def get_ollama_client() -> Optional[OllamaClient]:
    """Get global Ollama client instance."""
    global ollama_client
    
    if ollama_client is None:
        ollama_client = OllamaClient()
    
    return ollama_client if ollama_client.available else None


def test_ollama_connection():
    """Test Ollama connection and models."""
    print("Testing Ollama connection...")
    
    client = get_ollama_client()
    if not client:
        print("❌ Ollama is not available")
        print("💡 Make sure Ollama is installed and running:")
        print("   1. Install: https://ollama.ai/")
        print("   2. Run: ollama serve")
        print("   3. Pull models: ollama pull deepseek-r1:1.5b && ollama pull nomic-embed-text")
        return False
    
    print("✅ Ollama is available")
    
    # Test chat completion
    try:
        body = json.dumps({
            "messages": [
                {"role": "user", "content": "Hello, respond with just 'Hi there!'"}
            ]
        })
        response = client.invoke_model("chat-model", body)
        response_data = json.loads(response["body"].read())
        print(f"✅ Chat test: {response_data['content'][0]['text']}")
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        return False
    
    # Test embeddings
    try:
        embeddings = client.generate_embeddings(["test text"])
        print(f"✅ Embedding test: Generated {len(embeddings[0])} dimensions")
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False
    
    print("🎉 All Ollama tests passed!")
    return True


if __name__ == "__main__":
    test_ollama_connection()