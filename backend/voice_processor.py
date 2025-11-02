#!/usr/bin/env python3
"""
Unified VoiceProcessor that integrates VoiceInputHandler, VoiceOutputHandler, and InterruptionDetector
for seamless voice interaction with interruption capabilities on macOS.
"""

import asyncio
import logging
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from voice_input_handler import VoiceInputHandler, VoiceInput
from voice_output_handler import VoiceOutputHandler
from interruption_detector import InterruptionDetector, InterruptionEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VoiceProcessorConfig:
    """Configuration for VoiceProcessor"""
    sample_rate: int = 16000
    channels: int = 1
    aws_region: str = 'us-east-2'
    voice_id: str = 'Matthew'
    interruption_word_threshold: int = 3
    interruption_confidence_threshold: float = 0.7
    interruption_audio_threshold: float = 0.05

class VoiceProcessor:
    """
    Unified voice processor that manages voice input, output, and interruption detection.
    Provides a complete voice interaction system with natural conversation flow.
    """
    
    def __init__(self, config: Optional[VoiceProcessorConfig] = None):
        self.config = config or VoiceProcessorConfig()
        
        # Initialize components
        self.input_handler = VoiceInputHandler(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            interruption_threshold=self.config.interruption_word_threshold,
            aws_region=self.config.aws_region
        )
        
        self.output_handler = VoiceOutputHandler(
            aws_region=self.config.aws_region,
            voice_id=self.config.voice_id,
            sample_rate=self.config.sample_rate
        )
        
        self.interruption_detector = InterruptionDetector(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            word_threshold=self.config.interruption_word_threshold,
            confidence_threshold=self.config.interruption_confidence_threshold,
            audio_threshold=self.config.interruption_audio_threshold
        )
        
        # State management
        self.is_active = False
        self.is_listening = False
        self.is_speaking = False
        
        # Callbacks
        self.voice_input_callback = None
        self.interruption_callback = None
        self.audio_level_callback = None
        
    async def initialize(self) -> bool:
        """Initialize all voice processing components"""
        try:
            logger.info("Initializing voice processor...")
            
            # Test microphone
            if not await self.input_handler.test_microphone():
                logger.error("Microphone test failed")
                return False
            
            # Test speaker
            if not await self.output_handler.test_speaker():
                logger.error("Speaker test failed")
                return False
            
            logger.info("✅ Voice processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize voice processor: {e}")
            return False
    
    async def start_voice_interaction(self,
                                    voice_input_callback: Callable[[VoiceInput], None],
                                    interruption_callback: Optional[Callable[[InterruptionEvent], None]] = None,
                                    audio_level_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
        """Start complete voice interaction system"""
        
        if self.is_active:
            logger.warning("Voice processor already active")
            return False
        
        try:
            # Store callbacks
            self.voice_input_callback = voice_input_callback
            self.interruption_callback = interruption_callback or self._default_interruption_handler
            self.audio_level_callback = audio_level_callback
            
            # Start interruption detector
            if not await self.interruption_detector.start_monitoring(
                self.interruption_callback,
                self.audio_level_callback
            ):
                logger.error("Failed to start interruption detector")
                return False
            
            # Start voice input handler
            if not await self.input_handler.start_listening(
                self._handle_voice_input,
                listening_during_playback=True
            ):
                logger.error("Failed to start voice input handler")
                await self.interruption_detector.stop_monitoring()
                return False
            
            self.is_active = True
            self.is_listening = True
            
            logger.info("🎤 Voice interaction system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start voice interaction: {e}")
            await self.stop_voice_interaction()
            return False
    
    async def stop_voice_interaction(self):
        """Stop voice interaction system"""
        try:
            self.is_active = False
            self.is_listening = False
            
            # Stop all components
            await self.input_handler.stop_listening()
            await self.output_handler.stop_speaking()
            await self.interruption_detector.stop_monitoring()
            
            logger.info("🔇 Voice interaction system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping voice interaction: {e}")
    
    def _handle_voice_input(self, voice_input: VoiceInput):
        """Handle voice input from the input handler"""
        try:
            # Update interruption detector with transcript
            if voice_input.transcript.strip():
                self.interruption_detector.process_transcript_update(
                    voice_input.transcript,
                    voice_input.confidence
                )
            
            # Forward to main callback
            if self.voice_input_callback:
                self.voice_input_callback(voice_input)
                
        except Exception as e:
            logger.error(f"Error handling voice input: {e}")
    
    def _default_interruption_handler(self, event: InterruptionEvent):
        """Default interruption handler"""
        try:
            logger.info(f"Interruption detected: {event.transcript} ({event.word_count} words)")
            
            # Stop current speech
            asyncio.create_task(self.output_handler.stop_speaking())
            
        except Exception as e:
            logger.error(f"Error in default interruption handler: {e}")
    
    async def speak(self, text: str, interruptible: bool = True) -> bool:
        """Speak text with interruption support"""
        try:
            # CRITICAL: Stop listening during speech to prevent feedback loop
            self.is_listening = False
            self.input_handler.set_interruption_mode(False)
            
            # Set playback state for interruption detection
            self.interruption_detector.set_playback_active(True)
            self.is_speaking = True
            
            # Speak the text
            success = await self.output_handler.speak_text(text, interruptible)
            
            return success
            
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False
        
        finally:
            # Clear playback state and resume listening
            self.is_speaking = False
            self.interruption_detector.set_playback_active(False)
            
            # Resume listening after speech
            self.is_listening = True
            self.input_handler.set_interruption_mode(True)
            self.interruption_detector.set_playback_active(False)
            self.is_speaking = False
    
    async def play_thinking_sound(self) -> bool:
        """Play thinking sound during processing"""
        try:
            return await self.output_handler.play_thinking_sound()
        except Exception as e:
            logger.error(f"Error playing thinking sound: {e}")
            return False
    
    async def stop_speaking(self):
        """Stop current speech output"""
        try:
            await self.output_handler.stop_speaking()
            self.interruption_detector.set_playback_active(False)
            self.is_speaking = False
            
            # Resume listening after stopping speech
            self.is_listening = True
            if hasattr(self.input_handler, 'set_interruption_mode'):
                self.input_handler.set_interruption_mode(True)
                
        except Exception as e:
            logger.error(f"Error stopping speech: {e}")
    
    async def handle_interruption_immediately(self):
        """Immediately handle interruption with proper state management"""
        try:
            logger.info("🚨 Handling interruption immediately")
            
            # Stop speech immediately
            await self.stop_speaking()
            
            # Brief pause to let audio settle
            await asyncio.sleep(0.1)
            
            # Ensure we're ready to listen
            self.is_listening = True
            self.is_speaking = False
            
            logger.info("✅ Ready for new input after interruption")
            return True
            
        except Exception as e:
            logger.error(f"Error handling immediate interruption: {e}")
            return False
    
    def is_currently_speaking(self) -> bool:
        """Check if currently speaking"""
        return self.output_handler.is_currently_speaking()
    
    def is_currently_listening(self) -> bool:
        """Check if currently listening"""
        return self.is_listening and self.is_active
    
    def get_audio_level(self) -> float:
        """Get current audio input level"""
        return self.interruption_detector.get_current_audio_level()
    
    def is_voice_detected(self) -> bool:
        """Check if voice is currently detected"""
        return self.interruption_detector.is_voice_detected()
    
    async def handle_interruption_gracefully(self) -> bool:
        """Handle interruption with graceful acknowledgment"""
        try:
            # Stop current speech
            await self.stop_speaking()
            
            # Brief pause
            await asyncio.sleep(0.3)
            
            # Acknowledge interruption
            return await self.output_handler.handle_interruption_acknowledgment()
            
        except Exception as e:
            logger.error(f"Error handling interruption gracefully: {e}")
            return False
    
    async def generate_conversational_response(self, data: str, context: str = "") -> str:
        """Generate natural conversational response"""
        try:
            return await self.output_handler.generate_conversational_response(data, context)
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            return data

# Example usage and comprehensive testing
async def main():
    """Comprehensive test of the VoiceProcessor"""
    
    def on_voice_input(voice_input: VoiceInput):
        """Handle voice input events"""
        status = "🚨 INTERRUPTION" if voice_input.is_interruption else "🎤 INPUT"
        final_status = "FINAL" if voice_input.is_final else "PARTIAL"
        
        print(f"{status} [{final_status}] ({voice_input.word_count} words, "
              f"confidence: {voice_input.confidence:.2f}): {voice_input.transcript}")
    
    def on_interruption(event: InterruptionEvent):
        """Handle interruption events"""
        print(f"🚨 INTERRUPTION: '{event.transcript}' "
              f"({event.word_count} words, level: {event.audio_level:.3f})")
    
    def on_audio_level(info: Dict[str, Any]):
        """Handle audio level updates"""
        if info['is_voice_detected']:
            print(f"🔊 Voice level: {info['rms_level']:.3f}")
    
    # Create voice processor
    config = VoiceProcessorConfig(
        interruption_word_threshold=3,
        voice_id='Matthew'
    )
    processor = VoiceProcessor(config)
    
    try:
        # Initialize
        print("Initializing voice processor...")
        if not await processor.initialize():
            print("❌ Initialization failed")
            return
        
        # Start voice interaction
        print("Starting voice interaction system...")
        if not await processor.start_voice_interaction(
            on_voice_input,
            on_interruption,
            on_audio_level
        ):
            print("❌ Failed to start voice interaction")
            return
        
        print("🎉 Voice processor ready!")
        print()
        
        # Test sequence
        print("=== Testing Voice Processor ===")
        
        # Test 1: Simple greeting
        print("Test 1: Simple greeting")
        await processor.speak("Hello! I'm your voice assistant. How can I help you today?")
        await asyncio.sleep(2)
        
        # Test 2: Thinking sound
        print("Test 2: Thinking sound")
        await processor.play_thinking_sound()
        await asyncio.sleep(1)
        
        # Test 3: Conversational response
        print("Test 3: Conversational response")
        response = await processor.generate_conversational_response(
            "The system is working correctly and all components are functioning properly.",
            "confident"
        )
        await processor.speak(response)
        await asyncio.sleep(3)
        
        # Test 4: Interruptible speech
        print("Test 4: Interruptible speech (speak to interrupt)")
        long_text = ("This is a longer message that you can interrupt at any time. "
                    "Just start speaking when you hear this, and I should stop talking "
                    "and listen to what you have to say. This demonstrates the real-time "
                    "interruption capabilities of the voice processing system.")
        
        await processor.speak(long_text, interruptible=True)
        
        # Continue listening
        print("Listening for voice input... (Press Ctrl+C to stop)")
        await asyncio.sleep(20)
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping voice processor...")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    
    finally:
        await processor.stop_voice_interaction()
        print("Voice processor stopped.")

if __name__ == "__main__":
    asyncio.run(main())