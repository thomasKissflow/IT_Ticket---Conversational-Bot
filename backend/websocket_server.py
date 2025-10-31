#!/usr/bin/env python3
"""
WebSocket server for real-time communication with the React frontend.
Provides status updates, conversation history, and system monitoring.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from main import VoiceAssistantOrchestrator
from error_handler import error_handler

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            'connected_at': datetime.now(),
            'last_activity': datetime.now()
        }
        logger.info(f"WebSocket client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_metadata[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
                self.connection_metadata[client_id]['last_activity'] = datetime.now()
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
                self.connection_metadata[client_id]['last_activity'] = datetime.now()
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


class VoiceAssistantWebSocketServer:
    """WebSocket server for the Voice Assistant with real-time updates."""
    
    def __init__(self, orchestrator: VoiceAssistantOrchestrator):
        self.app = FastAPI(title="Voice Assistant WebSocket Server")
        self.orchestrator = orchestrator
        self.websocket_manager = WebSocketManager()
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up routes
        self._setup_routes()
        
        # State tracking for real-time updates
        self.last_conversation_state = {}
        self.last_system_status = {}
        
        # Start background tasks
        self._setup_background_tasks()
    
    def _setup_routes(self):
        """Set up FastAPI routes."""
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self.websocket_manager.connect(websocket, client_id)
            
            # Send initial state
            await self._send_initial_state(client_id)
            
            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self._handle_websocket_message(message, client_id)
                    
            except WebSocketDisconnect:
                self.websocket_manager.disconnect(client_id)
            except Exception as e:
                logger.error(f"WebSocket error for client {client_id}: {e}")
                self.websocket_manager.disconnect(client_id)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "connections": self.websocket_manager.get_connection_count(),
                "orchestrator_running": self.orchestrator.is_running if self.orchestrator else False
            }
        
        @self.app.get("/status")
        async def get_status():
            """Get current system status."""
            if not self.orchestrator:
                return {"error": "Orchestrator not available"}
            
            try:
                stats = await self.orchestrator.get_performance_stats()
                return {
                    "system_status": "running" if self.orchestrator.is_running else "stopped",
                    "processing_query": self.orchestrator.processing_query,
                    "session_id": stats.get('current_session_id'),
                    "performance": stats.get('performance_metrics', {}),
                    "connections": self.websocket_manager.get_connection_count()
                }
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return {"error": str(e)}
    
    def _setup_background_tasks(self):
        """Set up background tasks for real-time updates."""
        asyncio.create_task(self._status_update_loop())
        asyncio.create_task(self._conversation_monitor_loop())
    
    async def _send_initial_state(self, client_id: str):
        """Send initial state to a newly connected client."""
        try:
            # Send connection confirmation
            await self.websocket_manager.send_personal_message({
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
            # Send current system status
            if self.orchestrator:
                stats = await self.orchestrator.get_performance_stats()
                await self.websocket_manager.send_personal_message({
                    "type": "system_status",
                    "data": {
                        "connection_status": "connected" if self.orchestrator.is_running else "disconnected",
                        "agent_status": "Ready" if not self.orchestrator.processing_query else "Processing",
                        "session_id": stats.get('current_session_id'),
                        "performance_metrics": stats.get('performance_metrics', {})
                    },
                    "timestamp": datetime.now().isoformat()
                }, client_id)
            
            # Send conversation history if available
            if self.orchestrator and self.orchestrator.current_session:
                messages = []
                for msg in self.orchestrator.current_session.conversation_history:
                    messages.append({
                        "id": str(uuid.uuid4()),
                        "type": "assistant" if msg.speaker == "assistant" else "user",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "confidence": msg.confidence
                    })
                
                await self.websocket_manager.send_personal_message({
                    "type": "conversation_history",
                    "data": {"messages": messages},
                    "timestamp": datetime.now().isoformat()
                }, client_id)
            
        except Exception as e:
            logger.error(f"Error sending initial state to {client_id}: {e}")
    
    async def _handle_websocket_message(self, message: dict, client_id: str):
        """Handle incoming WebSocket messages from clients."""
        try:
            message_type = message.get("type")
            
            if message_type == "ping":
                await self.websocket_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, client_id)
            
            elif message_type == "request_status":
                if self.orchestrator:
                    stats = await self.orchestrator.get_performance_stats()
                    await self.websocket_manager.send_personal_message({
                        "type": "system_status",
                        "data": {
                            "connection_status": "connected" if self.orchestrator.is_running else "disconnected",
                            "agent_status": "Ready" if not self.orchestrator.processing_query else "Processing",
                            "session_id": stats.get('current_session_id'),
                            "performance_metrics": stats.get('performance_metrics', {})
                        },
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
            
            elif message_type == "manual_escalation":
                # Handle manual escalation request
                logger.info(f"Manual escalation requested by client {client_id}")
                await self.websocket_manager.broadcast({
                    "type": "escalation_alert",
                    "data": {
                        "message": "Manual escalation requested by user",
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_id
                    },
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
    
    async def _status_update_loop(self):
        """Background loop for sending status updates."""
        while True:
            try:
                await asyncio.sleep(2)  # Update every 2 seconds
                
                if not self.orchestrator or self.websocket_manager.get_connection_count() == 0:
                    continue
                
                # Get current status
                stats = await self.orchestrator.get_performance_stats()
                current_status = {
                    "connection_status": "connected" if self.orchestrator.is_running else "disconnected",
                    "agent_status": "Ready" if not self.orchestrator.processing_query else "Processing",
                    "session_id": stats.get('current_session_id'),
                    "performance_metrics": stats.get('performance_metrics', {})
                }
                
                # Only send if status changed
                if current_status != self.last_system_status:
                    await self.websocket_manager.broadcast({
                        "type": "system_status",
                        "data": current_status,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.last_system_status = current_status
                
            except Exception as e:
                logger.error(f"Error in status update loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _conversation_monitor_loop(self):
        """Background loop for monitoring conversation changes."""
        while True:
            try:
                await asyncio.sleep(1)  # Check every second
                
                if not self.orchestrator or not self.orchestrator.current_session:
                    continue
                
                if self.websocket_manager.get_connection_count() == 0:
                    continue
                
                # Check for new messages in conversation history
                session = self.orchestrator.current_session
                current_message_count = len(session.conversation_history)
                last_message_count = self.last_conversation_state.get('message_count', 0)
                
                if current_message_count > last_message_count:
                    # New messages added
                    new_messages = session.conversation_history[last_message_count:]
                    
                    for msg in new_messages:
                        await self.websocket_manager.broadcast({
                            "type": "new_message",
                            "data": {
                                "id": str(uuid.uuid4()),
                                "type": "assistant" if msg.speaker == "assistant" else "user",
                                "content": msg.content,
                                "timestamp": msg.timestamp.isoformat(),
                                "confidence": msg.confidence
                            },
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    self.last_conversation_state['message_count'] = current_message_count
                
                # Monitor voice processor state changes
                if hasattr(self.orchestrator, 'voice_processor') and self.orchestrator.voice_processor:
                    vp = self.orchestrator.voice_processor
                    current_voice_state = {
                        "is_listening": getattr(vp, 'is_listening', False),
                        "is_processing": self.orchestrator.processing_query,
                        "is_playing": getattr(vp, 'is_playing_audio', False),
                        "current_transcript": getattr(vp, 'current_transcript', '')
                    }
                    
                    last_voice_state = self.last_conversation_state.get('voice_state', {})
                    
                    if current_voice_state != last_voice_state:
                        await self.websocket_manager.broadcast({
                            "type": "voice_state_update",
                            "data": current_voice_state,
                            "timestamp": datetime.now().isoformat()
                        })
                        self.last_conversation_state['voice_state'] = current_voice_state
                
            except Exception as e:
                logger.error(f"Error in conversation monitor loop: {e}")
                await asyncio.sleep(2)  # Wait on error
    
    async def send_escalation_alert(self, message: str, confidence: float = 0.0):
        """Send escalation alert to all connected clients."""
        await self.websocket_manager.broadcast({
            "type": "escalation_alert",
            "data": {
                "message": message,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_agent_routing_update(self, agent_name: str, status: str):
        """Send agent routing status update."""
        await self.websocket_manager.broadcast({
            "type": "agent_routing",
            "data": {
                "agent_name": agent_name,
                "status": status,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })
    
    def run(self, host: str = "localhost", port: int = 8000):
        """Run the WebSocket server."""
        logger.info(f"Starting WebSocket server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="info")


# Global server instance
websocket_server: Optional[VoiceAssistantWebSocketServer] = None


async def start_websocket_server(orchestrator: VoiceAssistantOrchestrator, host: str = "localhost", port: int = 8000):
    """Start the WebSocket server with the orchestrator."""
    global websocket_server
    
    websocket_server = VoiceAssistantWebSocketServer(orchestrator)
    
    # Run the server
    config = uvicorn.Config(
        websocket_server.app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    # For testing the WebSocket server independently
    from main import orchestrator
    
    async def test_server():
        await orchestrator.initialize()
        await start_websocket_server(orchestrator)
    
    asyncio.run(test_server())