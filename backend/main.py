#!/usr/bin/env python3
"""
Main entry point for the Agentic Voice Assistant
Real-time voice interaction with multi-agent processing and interruption handling.
"""

import asyncio
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv

# Import components
from voice_processor import VoiceProcessor, VoiceProcessorConfig
from voice_input_handler import VoiceInput
from interruption_detector import InterruptionEvent
from agents.supervisor_agent import SupervisorAgent
from agents.ticket_agent import TicketAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base_agent import ConversationContext, AgentResult, AgentType
from services.conversation_manager import ConversationManager
from services.response_humanizer import humanize_agent_response
from performance_optimizer import PerformanceOptimizer
from error_handler import error_handler, ErrorContext

# Load environment variables
load_dotenv()

# Configure clean logging
from logging_config import setup_clean_logging
setup_clean_logging()
logger = logging.getLogger(__name__)


class VoiceAssistantOrchestrator:
    """
    Main orchestrator for the Agentic Voice Assistant.
    Manages real-time voice interaction, agent coordination, and conversation flow.
    """
    
    def __init__(self):
        # Core components
        self.voice_processor: Optional[VoiceProcessor] = None
        self.supervisor_agent: Optional[SupervisorAgent] = None
        self.ticket_agent: Optional[TicketAgent] = None
        self.knowledge_agent: Optional[KnowledgeAgent] = None
        self.conversation_manager: Optional[ConversationManager] = None
        
        # Performance optimization
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        
        # State management
        self.is_running = False
        self.current_session: Optional[ConversationContext] = None
        self.processing_query = False
        self.main_event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-east-2')
        self.response_time_target = 0.5  # 500ms target
        self.max_response_time = 3.0  # 3 second timeout
    
    async def initialize(self) -> bool:
        """Initialize all components and verify system readiness."""
        try:
            # Capture the main event loop for thread-safe operations
            try:
                self.main_event_loop = asyncio.get_running_loop()
            except RuntimeError:
                self.main_event_loop = asyncio.get_event_loop()
            
            # Initialize voice processor
            try:
                config = VoiceProcessorConfig(
                    sample_rate=16000,
                    channels=1,
                    aws_region=self.aws_region,
                    voice_id='Matthew',
                    interruption_word_threshold=3,
                    interruption_confidence_threshold=0.7
                )
                self.voice_processor = VoiceProcessor(config)
                
                if not await self.voice_processor.initialize():
                    print("❌ Voice processor failed")
                    return False
            except Exception as e:
                error_result = await handle_voice_error(e, "VoiceAssistantOrchestrator", "initialize_voice_processor")
                print(f"❌ Voice error: {error_result['fallback_response']}")
                return False
            
            # Initialize performance optimizer
            self.performance_optimizer = PerformanceOptimizer(
                target_response_time=self.response_time_target,
                aws_region=self.aws_region
            )
            
            # Set global performance optimizer for agents to use
            import performance_optimizer as perf_module
            perf_module.performance_optimizer = self.performance_optimizer
            
            # Initialize async components
            await self.performance_optimizer.initialize_async_components()
            
            # Initialize agents
            try:
                self.supervisor_agent = SupervisorAgent(self.aws_region)
                self.ticket_agent = TicketAgent()
                self.knowledge_agent = KnowledgeAgent()
            except Exception as e:
                error_result = await handle_agent_error(e, "VoiceAssistantOrchestrator", "initialize_agents")
                logger.warning(f"Agent initialization warning: {error_result['fallback_response']}")
                # Continue with partial initialization
            
            # Initialize conversation manager
            logger.info("Initializing conversation manager...")
            try:
                self.conversation_manager = ConversationManager(self.aws_region)
            except Exception as e:
                error_result = await handle_agent_error(e, "VoiceAssistantOrchestrator", "initialize_conversation_manager")
                logger.warning(f"Conversation manager initialization warning: {error_result['fallback_response']}")
                # Continue without conversation manager
            
            # Health checks
            logger.info("Performing health checks...")
            health_checks = await asyncio.gather(
                self.supervisor_agent.health_check(),
                self.ticket_agent.health_check(),
                self.knowledge_agent.health_check(),
                self.conversation_manager.health_check(),
                self.performance_optimizer.health_check(),
                return_exceptions=True
            )
            
            failed_checks = []
            for i, result in enumerate(health_checks):
                agent_names = ['SupervisorAgent', 'TicketAgent', 'KnowledgeAgent', 'ConversationManager', 'PerformanceOptimizer']
                if isinstance(result, Exception) or not result:
                    failed_checks.append(agent_names[i])
            
            if failed_checks:
                logger.warning(f"⚠️ Health check failures: {', '.join(failed_checks)}")
                logger.info("Continuing with available components...")
            
            # Create initial session
            self.current_session = ConversationContext(
                session_id=str(uuid.uuid4()),
                user_id=None
            )
            
            logger.info("✅ Initialization complete!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def start_voice_interaction(self) -> bool:
        """Start the main voice interaction loop."""
        session_id = self.current_session.session_id if self.current_session else None
        
        try:
            logger.info("🎤 Starting voice interaction system...")
            
            # Start voice processor with callbacks
            success = await self.voice_processor.start_voice_interaction(
                voice_input_callback=self._handle_voice_input,
                interruption_callback=self._handle_interruption,
                audio_level_callback=self._handle_audio_level
            )
            
            if not success:
                logger.error("❌ Failed to start voice interaction")
                return False
            
            # Play greeting with error handling
            try:
                if self.conversation_manager:
                    greeting = await self.conversation_manager.generate_greeting(self.current_session)
                else:
                    greeting = "Hello! I'm your voice assistant. How can I help you today?"
                
                await self.voice_processor.speak(greeting, interruptible=True)
                
                # Add greeting to conversation history
                if self.current_session:
                    self.current_session.add_message(greeting, "assistant", confidence=1.0)
                    
            except Exception as e:
                error_result = await handle_agent_error(e, "VoiceAssistantOrchestrator", "generate_greeting", session_id)
                logger.warning(f"Greeting generation failed: {error_result['fallback_response']}")
                # Continue without greeting
            
            self.is_running = True
            logger.info("🎉 Voice Assistant is ready! Start speaking...")
            
            return True
            
        except Exception as e:
            error_result = await handle_voice_error(e, "VoiceAssistantOrchestrator", "start_voice_interaction", session_id)
            logger.error(f"❌ Failed to start voice interaction: {error_result['fallback_response']}")
            return False
    
    def _handle_voice_input(self, voice_input: VoiceInput):
        """Handle voice input from the user."""
        session_id = self.current_session.session_id if self.current_session else None
        
        try:
            # Only process final transcripts with meaningful content
            if not voice_input.is_final or not voice_input.transcript.strip():
                return
            
            # Skip if already processing a query (but don't queue - this prevents loops)
            if self.processing_query:
                logger.debug(f"Skipping input while processing: {voice_input.transcript}")
                return
            
            # Filter out likely audio feedback (assistant's own voice)
            transcript_lower = voice_input.transcript.lower()
            feedback_phrases = [
                "what else would you like",
                "yes i'm listening",
                "sure what did you want",
                "of course go ahead",
                "what else can i help",
                "you have another question"
            ]
            
            if any(phrase in transcript_lower for phrase in feedback_phrases):
                logger.debug(f"Filtering out likely audio feedback: {voice_input.transcript}")
                return
            
            # Log the input
            print(f"🎤 User: {voice_input.transcript}")
            
            # Add to conversation history
            if self.current_session:
                self.current_session.add_message(
                    voice_input.transcript, 
                    "user", 
                    confidence=voice_input.confidence
                )
            
            # Process the query asynchronously
            asyncio.create_task(self._process_user_query(voice_input.transcript))
            
        except Exception as e:
            # Handle voice input errors asynchronously
            async def handle_error():
                error_result = await handle_voice_error(e, "VoiceAssistantOrchestrator", "handle_voice_input", session_id)
                logger.error(f"Error handling voice input: {error_result['error_id']}")
                
                # Try to provide feedback to user
                try:
                    if self.voice_processor:
                        await self.voice_processor.speak(error_result['fallback_response'], interruptible=True)
                except:
                    pass  # Don't cascade errors
            
            asyncio.create_task(handle_error())
    
    def _handle_interruption(self, event: InterruptionEvent):
        """Handle user interruptions during assistant speech."""
        session_id = self.current_session.session_id if self.current_session else None
        
        try:
            logger.info(f"🚨 Interruption detected: {event.transcript}")
            
            if self.performance_optimizer and self.performance_optimizer.monitor:
                self.performance_optimizer.monitor.metrics.interruption_count += 1
            
            # CRITICAL: Stop all current speech immediately
            if self.voice_processor:
                # Use the improved interruption handling method
                async def handle_interruption_async():
                    try:
                        await self.voice_processor.handle_interruption_immediately()
                        logger.info("✅ Interruption handled successfully")
                    except Exception as stop_error:
                        logger.error(f"Error handling interruption: {stop_error}")
                
                # Schedule the interruption handling in the event loop (thread-safe)
                try:
                    # Use the stored main event loop for thread-safe scheduling
                    if self.main_event_loop and self.main_event_loop.is_running():
                        # Schedule in the main event loop (thread-safe from any thread)
                        asyncio.run_coroutine_threadsafe(handle_interruption_async(), self.main_event_loop)
                    else:
                        # Fallback: create a new thread with its own event loop
                        logger.debug("Creating new thread for interruption handling")
                        def schedule_interruption_handling():
                            try:
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                new_loop.run_until_complete(self.voice_processor.handle_interruption_immediately())
                                new_loop.close()
                            except Exception as thread_error:
                                logger.error(f"Thread-safe interruption handling error: {thread_error}")
                        
                        import threading
                        interruption_thread = threading.Thread(target=schedule_interruption_handling)
                        interruption_thread.daemon = True  # Make it a daemon thread
                        interruption_thread.start()
                        
                except Exception as interruption_error:
                    logger.error(f"Error scheduling interruption handling: {interruption_error}")
            
            # Process meaningful interruptions (even more responsive)
            if len(event.transcript.split()) >= 1 and event.confidence >= 0.5:
                logger.info(f"🎤 Processing interruption: '{event.transcript}'")
                
                # Add interruption to conversation history
                if self.current_session:
                    self.current_session.add_message(
                        event.transcript,
                        "user",
                        confidence=event.confidence
                    )
                
                # Process the interruption as a new query
                async def process_interruption_async():
                    try:
                        # Wait a moment for speech to stop
                        await asyncio.sleep(0.2)
                        
                        # Check if this is a follow-up or addition to previous question
                        follow_up_indicators = [
                            'also', 'and', 'additionally', 'plus', 'furthermore',
                            'what about', 'how about', 'tell me more', 'more details',
                            'can you also', 'what else', 'anything else'
                        ]
                        
                        transcript_lower = event.transcript.lower()
                        is_follow_up = any(indicator in transcript_lower for indicator in follow_up_indicators)
                        
                        if is_follow_up:
                            logger.info(f"🔗 Detected follow-up question: {event.transcript}")
                        
                        await self._process_user_query(event.transcript)
                    except Exception as process_error:
                        logger.error(f"Error processing interruption query: {process_error}")
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(process_interruption_async())
                    else:
                        asyncio.create_task(process_interruption_async())
                except Exception as process_error:
                    logger.error(f"Error scheduling interruption processing: {process_error}")
            else:
                logger.debug(f"Interruption too short or low confidence: '{event.transcript}' "
                           f"({len(event.transcript.split())} words, {event.confidence:.2f} confidence)")
            
        except Exception as e:
            logger.error(f"Error handling interruption: {e}")
            # Don't try to create async tasks in error handling
    
    def _handle_audio_level(self, info: Dict[str, Any]):
        """Handle audio level updates for monitoring."""
        # This could be used for UI updates or monitoring
        pass
    
    async def _process_user_query(self, query: str):
        """Process a user query through the agent system."""
        if self.processing_query:
            return
        
        self.processing_query = True
        start_time = time.time()
        session_id = self.current_session.session_id if self.current_session else None
        
        try:
            # Play thinking sound for longer processing
            thinking_task = None
            if len(query.split()) > 3:  # Most queries get thinking sounds
                # Use shorter thinking sounds for faster feel
                thinking_sound = await self.conversation_manager.get_thinking_sound()
                thinking_task = asyncio.create_task(
                    self.voice_processor.speak(thinking_sound, interruptible=False)
                )
            
            # Generate context hash for caching
            context_hash = self._generate_context_hash(self.current_session)
            
            # Process through supervisor agent (direct call)
            supervisor_result = await self.supervisor_agent.process_query(query, self.current_session)
            
            # Debug: Show intent and routing
            intent_data = supervisor_result.data.get('intent')
            routing = supervisor_result.data.get('routing_decision', [])
            if intent_data:
                print(f"🧠 Intent: {intent_data.intent_type.value} → Routing: {routing}")
            
            # Route to appropriate agents based on supervisor decision
            agent_results = await self._coordinate_agents_simple(supervisor_result, query)
            
            # Debug: Show which agents were actually called
            agent_names = [r.agent_name for r in agent_results]
            print(f"🤖 Agents called: {agent_names}")
            
            # Wait for thinking sound to complete if it was started
            if thinking_task and not thinking_task.done():
                await thinking_task
            
            # Generate response
            response = await self._generate_response(agent_results)
            
            # Add response to conversation history BEFORE speaking (so UI shows it first)
            processing_time = time.time() - start_time
            self.current_session.add_message(
                response,
                "assistant",
                confidence=self._calculate_overall_confidence(agent_results)
            )
            
            # Small delay to ensure UI receives the message before voice starts
            await asyncio.sleep(0.1)
            
            # Speak the response
            await self.voice_processor.speak(response, interruptible=True)
            
            # Store response data for follow-up questions
            self.current_session.last_response_data = {
                'agent_results': [
                    {
                        'agent_name': result.agent_name,
                        'data': result.data,
                        'confidence': result.confidence,
                        'requires_escalation': result.requires_escalation
                    } for result in agent_results
                ],
                'original_query': query,
                'response': response,
                'timestamp': time.time()
            }
            
            # Update performance metrics
            self.performance_optimizer.monitor.metrics.add_response_time(processing_time, "overall")
            
            # Check for escalation
            if any(result.requires_escalation for result in agent_results):
                self.performance_optimizer.monitor.metrics.escalation_count += 1
                await self._handle_escalation(agent_results)
            
            # Performance monitoring
            if processing_time > self.response_time_target:
                logger.warning(f"⚠️ Response time exceeded target: {processing_time:.2f}s")
            
        except asyncio.TimeoutError as e:
            error_result = await error_handler.handle_error(
                e, 
                ErrorContext(
                    error_type=ErrorType.TIMEOUT_ERROR,
                    severity=ErrorSeverity.MEDIUM,
                    component="VoiceAssistantOrchestrator",
                    operation="process_user_query",
                    user_session_id=session_id
                )
            )
            logger.error(f"⏰ Query processing timeout: {error_result['error_id']}")
            await self.voice_processor.speak(error_result['fallback_response'], interruptible=True)
        
        except Exception as e:
            error_result = await handle_agent_error(e, "VoiceAssistantOrchestrator", "process_user_query", session_id)
            logger.error(f"Error processing query: {error_result['error_id']}")
            await self.voice_processor.speak(error_result['fallback_response'], interruptible=True)
            
            # Check if we should escalate
            if error_result['should_escalate']:
                await self._handle_escalation([])  # Empty agent results for error escalation
        
        finally:
            self.processing_query = False
    
    def _generate_context_hash(self, context: ConversationContext) -> str:
        """Generate a hash of the conversation context for caching."""
        import hashlib
        
        # Use recent conversation history for context
        recent_messages = context.get_recent_messages(3)
        context_str = ""
        
        for msg in recent_messages:
            context_str += f"{msg.speaker}:{msg.content[:100]}"
        
        return hashlib.md5(context_str.encode()).hexdigest()[:8]
    
    async def _coordinate_agents_optimized(self, supervisor_result: AgentResult, query: str, context_hash: str) -> List[AgentResult]:
        """Coordinate with appropriate agents using performance optimization."""
        agent_results = [supervisor_result]
        
        try:
            # Extract routing decision from supervisor result
            routing_decision = supervisor_result.data.get('routing_decision', [])
            print(f"🔀 Routing decision: {routing_decision}")
            
            # Create tasks for parallel agent execution with optimization
            agent_tasks = []
            
            if 'ticket' in routing_decision:
                print("📋 Adding TicketAgent task")
                # Bypass performance optimizer for now - direct call
                agent_tasks.append(
                    self.ticket_agent.process_query(query, self.current_session)
                )
            
            if 'knowledge' in routing_decision:
                print("📚 Adding KnowledgeAgent task")
                # Bypass performance optimizer for now - direct call
                agent_tasks.append(
                    self.knowledge_agent.process_query(query, self.current_session)
                )
            
            # Execute agents in parallel
            if agent_tasks:
                print(f"🚀 Executing {len(agent_tasks)} agent tasks")
                additional_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
                
                for i, result in enumerate(additional_results):
                    if isinstance(result, AgentResult):
                        print(f"✅ Task {i+1}: {result.agent_name}")
                        agent_results.append(result)
                    elif isinstance(result, Exception):
                        print(f"❌ Task {i+1}: Exception - {result}")
                    else:
                        print(f"❌ Task {i+1}: Unexpected result type - {type(result)}")
            else:
                print("⚠️ No agent tasks to execute")
            
            return agent_results
            
        except Exception as e:
            print(f"❌ Error coordinating agents: {e}")
            return agent_results
    
    async def _coordinate_agents_simple(self, supervisor_result: AgentResult, query: str) -> List[AgentResult]:
        """Simple agent coordination without performance optimizer."""
        agent_results = [supervisor_result]
        
        try:
            # Extract routing decision
            routing_decision = supervisor_result.data.get('routing_decision', [])
            print(f"🔀 Routing decision: {routing_decision}")
            
            # Execute agents directly
            if 'ticket' in routing_decision:
                print("📋 Calling TicketAgent")
                ticket_result = await self.ticket_agent.process_query(query, self.current_session)
                agent_results.append(ticket_result)
            
            if 'knowledge' in routing_decision:
                print("📚 Calling KnowledgeAgent")
                knowledge_result = await self.knowledge_agent.process_query(query, self.current_session)
                agent_results.append(knowledge_result)
            
            return agent_results
            
        except Exception as e:
            print(f"❌ Error in simple coordination: {e}")
            return agent_results
    
    async def _coordinate_agents(self, supervisor_result: AgentResult, query: str) -> List[AgentResult]:
        """Coordinate with appropriate agents based on supervisor routing (legacy method)."""
        context_hash = self._generate_context_hash(self.current_session)
        return await self._coordinate_agents_optimized(supervisor_result, query, context_hash)
    
    async def _generate_response(self, agent_results: List[AgentResult]) -> str:
        """Generate a natural response from agent results."""
        try:
            # Get the original query from the current session
            original_query = ""
            if self.current_session and self.current_session.conversation_history:
                # Get the last user message
                for msg in reversed(self.current_session.conversation_history):
                    if msg.speaker == "user":
                        original_query = msg.content
                        break
            
            # Convert agent results to dictionaries for the humanizer
            agent_data = []
            for result in agent_results:
                agent_data.append({
                    'agent_name': result.agent_name,
                    'data': result.data,
                    'confidence': result.confidence,
                    'requires_escalation': result.requires_escalation
                })
            
            # Debug: Show what data is being sent to humanizer
            for data in agent_data:
                if data['agent_name'] == 'TicketAgent':
                    ticket_data = data.get('data', {})
                    if ticket_data.get('found'):
                        ticket = ticket_data.get('ticket', {})
                        print(f"📊 Data to humanizer: {ticket.get('id')} - {ticket.get('status')}")
                    else:
                        print(f"📊 Data to humanizer: Ticket not found")
            
            # Use the response humanizer to create a natural response
            context = {
                'session_id': self.current_session.session_id if self.current_session else None,
                'last_response_data': self.current_session.last_response_data if self.current_session else None
            }
            response = await humanize_agent_response(
                agent_data, 
                original_query,
                context=context
            )
            
            print(f"🗣️ Final response: {response[:50]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I found some information, but I'm having trouble presenting it clearly. Could you rephrase your question?"
    
    def _calculate_overall_confidence(self, agent_results: List[AgentResult]) -> float:
        """Calculate overall confidence from multiple agent results."""
        if not agent_results:
            return 0.0
        
        # Weight by agent importance and average
        weights = {'SupervisorAgent': 0.3, 'TicketAgent': 0.4, 'KnowledgeAgent': 0.4}
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for result in agent_results:
            weight = weights.get(result.agent_name, 0.3)
            weighted_confidence += result.confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    # Removed _handle_interruption_gracefully - was causing multiple responses
    # Interruptions are now handled directly in _handle_interruption
    
    async def _handle_escalation(self, agent_results: List[AgentResult]):
        """Handle escalation to human agents."""
        try:
            logger.info("🚨 Escalation triggered")
            
            # Generate escalation summary
            escalation_reasons = []
            for result in agent_results:
                if result.requires_escalation:
                    escalation_reasons.append(f"{result.agent_name}: confidence {result.confidence:.2f}")
            
            logger.info(f"Escalation reasons: {', '.join(escalation_reasons)}")
            
            # In a full implementation, this would:
            # - Create escalation ticket
            # - Notify human agents
            # - Provide conversation context
            # - Transfer the session
            
        except Exception as e:
            logger.error(f"Error handling escalation: {e}")
    
    async def stop(self):
        """Stop the voice assistant gracefully."""
        session_id = self.current_session.session_id if self.current_session else None
        
        try:
            logger.info("🛑 Stopping Voice Assistant...")
            
            self.is_running = False
            
            if self.voice_processor:
                try:
                    await self.voice_processor.stop_voice_interaction()
                except Exception as e:
                    error_result = await handle_voice_error(e, "VoiceAssistantOrchestrator", "stop_voice_processor", session_id)
                    logger.warning(f"Voice processor stop warning: {error_result['fallback_response']}")
            
            # Log final performance and error reports
            try:
                if self.performance_optimizer:
                    logger.info("📊 Final Performance Report:")
                    report = await self.performance_optimizer.get_performance_report()
                    logger.info(f"  Average Response Time: {report['performance_metrics']['avg_response_time']:.2f}s")
                    logger.info(f"  Cache Hit Rate: {report['performance_metrics']['cache_hit_rate']:.1f}%")
                    logger.info(f"  Total AWS Calls: {report['performance_metrics']['total_aws_calls']}")
                    logger.info(f"  Escalations: {report['performance_metrics']['escalations']}")
                    logger.info(f"  Interruptions: {report['performance_metrics']['interruptions']}")
                
                # Log error statistics
                error_stats = error_handler.get_error_statistics()
                if error_stats['total_errors'] > 0:
                    logger.info("🚨 Final Error Report:")
                    logger.info(f"  Total Errors: {error_stats['total_errors']}")
                    logger.info(f"  Recovery Success Rate: {error_stats['recovery_success_rate']:.1f}%")
                    logger.info(f"  Most Common Error Types: {list(error_stats['error_types'].keys())[:3]}")
                
            except Exception as e:
                logger.warning(f"Error generating final reports: {e}")
            
            logger.info("✅ Voice Assistant stopped")
            
        except Exception as e:
            error_result = await error_handler.handle_error(
                e,
                ErrorContext(
                    error_type=ErrorType.UNKNOWN_ERROR,
                    severity=ErrorSeverity.HIGH,
                    component="VoiceAssistantOrchestrator",
                    operation="stop",
                    user_session_id=session_id
                )
            )
            logger.error(f"Error stopping voice assistant: {error_result['error_id']}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        stats = {
            'current_session_id': self.current_session.session_id if self.current_session else None,
            'is_running': self.is_running,
            'processing_query': self.processing_query
        }
        
        if self.performance_optimizer:
            report = await self.performance_optimizer.get_performance_report()
            stats.update(report)
        
        # Add error statistics
        error_stats = error_handler.get_error_statistics()
        stats['error_statistics'] = error_stats
        
        # Add AWS call statistics
        try:
            from services.aws_call_tracker import aws_tracker
            aws_stats = aws_tracker.get_stats()
            stats['aws_calls'] = aws_stats['total']
            stats['aws_call_breakdown'] = {
                'transcribe': aws_stats['transcribe'],
                'polly': aws_stats['polly'],
                'bedrock': aws_stats['bedrock']
            }
        except:
            stats['aws_calls'] = 0
        
        return stats


# Global orchestrator instance
orchestrator = VoiceAssistantOrchestrator()


async def main():
    """Main application entry point"""
    print("Agentic Voice Assistant")
    print("=" * 40)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(orchestrator.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize the orchestrator
        if not await orchestrator.initialize():
            logger.error("❌ Failed to initialize voice assistant")
            return 1
        
        # Start voice interaction
        if not await orchestrator.start_voice_interaction():
            logger.error("❌ Failed to start voice interaction")
            return 1
        
        # Keep running until stopped
        logger.info("🎯 Voice Assistant running. Press Ctrl+C to stop.")
        
        # Performance monitoring loop
        performance_check_counter = 0
        
        while orchestrator.is_running:
            await asyncio.sleep(1)
            performance_check_counter += 1
            
            # Periodic performance monitoring (every 30 seconds)
            if performance_check_counter >= 30:
                performance_check_counter = 0
                
                try:
                    stats = await orchestrator.get_performance_stats()
                    avg_time = stats.get('performance_metrics', {}).get('avg_response_time', 0)
                    cache_hit_rate = stats.get('performance_metrics', {}).get('cache_hit_rate', 0)
                    
                    if avg_time > orchestrator.response_time_target * 1.5:
                        logger.warning(f"⚠️ Average response time high: {avg_time:.2f}s")
                    
                    if avg_time > 0:  # Only log if we have data
                        logger.info(f"📈 Performance: {avg_time:.2f}s avg, {cache_hit_rate:.1f}% cache hit rate")
                        
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
        await orchestrator.stop()
        return 0
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        await orchestrator.stop()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)