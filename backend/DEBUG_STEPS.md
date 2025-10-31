# Debug Steps for Voice Assistant MVP

## 🎯 **Start Here - Test Core AWS Services**

### **Step 1: Test Basic AWS Connection**
```bash
cd backend
python simple_main.py
```
**Expected:** Should show Polly and Transcribe working

### **Step 2: Fix ChromaDB Dimension Issue**
```bash
# Delete existing ChromaDB data
rm -rf ./data/chroma_db

# This forces recreation with correct dimensions
```

### **Step 3: Test Ollama (if Bedrock fails)**
```bash
# Install Ollama
brew install ollama  # or visit https://ollama.ai/

# Start server
ollama serve

# Pull models
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### **Step 4: Test Full System**
```bash
cd backend
python main.py
```

### **Step 5: Test with Frontend**
```bash
cd backend
python main_with_websocket.py

# In another terminal
cd frontend
npm start
```

## 🔧 **Common Issues & Fixes**

### **Issue 1: "Collection expecting embedding with dimension of 1536, got 768"**
**Fix:** `rm -rf ./data/chroma_db`

### **Issue 2: "Authentication failed: Please make sure your API Key is valid"**
**Fix:** Either fix AWS credentials OR let it fall back to Ollama

### **Issue 3: "Ollama is not available"**
**Fix:** Install and start Ollama, pull required models

### **Issue 4: Voice not working**
**Fix:** Check microphone permissions, audio devices

## 🎯 **MVP Success Criteria**

**Minimum Working System:**
1. ✅ Voice input (AWS Transcribe)
2. ✅ Voice output (AWS Polly)  
3. ✅ Basic conversation (LLM working)
4. ✅ WebSocket connection to frontend

**Nice to Have:**
- Knowledge base search
- Ticket system
- Advanced error handling
- Performance optimization

## 🚀 **Quick Win Strategy**

1. **Get `simple_main.py` working** (proves AWS services)
2. **Fix ChromaDB dimensions** (delete data folder)
3. **Get basic LLM working** (Ollama fallback)
4. **Test voice pipeline** (speak → transcribe → LLM → speak)
5. **Connect frontend** (WebSocket)

Focus on getting the basic voice conversation loop working first, then add features!