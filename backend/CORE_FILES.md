# Core Files for MVP Voice Assistant

## 🎯 **Essential Files Only**

### **Core Application**
- `simple_main.py` - Simplified main entry point (start here)
- `main.py` - Full main application (if you want all features)
- `main_with_websocket.py` - With WebSocket server

### **Voice Processing (Working)**
- `voice_input_handler.py` - AWS Transcribe integration
- `voice_output_handler.py` - AWS Polly integration  
- `voice_processor.py` - Voice processing coordinator
- `interruption_detector.py` - Interruption handling

### **LLM Integration (Bedrock + Ollama Fallback)**
- `llm_client.py` - Unified LLM client (auto-fallback)
- `ollama_client.py` - Ollama fallback client

### **Agents (Core Logic)**
- `agents/base_agent.py` - Base agent classes
- `agents/supervisor_agent.py` - Main orchestrating agent
- `agents/ticket_agent.py` - Ticket handling
- `agents/knowledge_agent.py` - Knowledge base queries

### **Services**
- `services/conversation_manager.py` - Natural conversation
- `services/data_processor.py` - ChromaDB + embeddings

### **Performance & Error Handling**
- `performance_optimizer.py` - Performance optimization
- `error_handler.py` - Comprehensive error handling

### **WebSocket (Frontend Integration)**
- `websocket_server.py` - Real-time frontend communication

### **Configuration**
- `.env` - Environment variables
- `agents/base_agent.py` - Data structures

## 🚀 **Quick Start for Debugging**

### **Option 1: Minimal Test**
```bash
cd backend
python simple_main.py
```

### **Option 2: Full System**
```bash
cd backend
python main.py
```

### **Option 3: With Frontend**
```bash
cd backend
python main_with_websocket.py
```

## 🔧 **Key Issues to Debug**

1. **Embedding Dimensions**: ChromaDB expects 1536, Ollama gives 768
   - Fix: Delete `./data/chroma_db` folder
   
2. **AWS Bedrock Credentials**: Authentication failing
   - Fix: Check AWS credentials or use Ollama fallback
   
3. **Model Loading**: Ollama models not available
   - Fix: `ollama pull llama3.2:3b && ollama pull nomic-embed-text`

## 🎯 **MVP Focus**

**Working Components:**
- ✅ AWS Polly (text-to-speech)
- ✅ AWS Transcribe (speech-to-text)
- ✅ Voice processing pipeline
- ✅ WebSocket server
- ✅ Frontend integration

**Debug These:**
- 🔧 LLM integration (Bedrock/Ollama)
- 🔧 ChromaDB embeddings
- 🔧 Agent coordination

Start with `simple_main.py` to test core AWS services, then move to full system.