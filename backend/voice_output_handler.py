#!/usr/bin/env python3
"""
Enhanced VoiceOutputHandler for interruptible text-to-speech with thinking sounds.
Supports macOS Core Audio through sounddevice with async streaming.
"""

import asyncio
import sounddevice as sd
import numpy as np
import boto3
import io
import threading
import queue
import random
from typing import Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AudioPlayback:
    """Represents an audio playback session"""
    text: str
    audio_data: np.ndarray
    sample_rate: int
    is_interruptible: bool
    start_time: datetime
    is_playing: bool = False
    is_interrupted: bool = False

class VoiceOutputHandler:
    """Enhanced voice output handler with interruptible playback and thinking sounds"""
    
    def __init__(self, 
                 aws_region: str = 'us-east-1',
                 voice_id: str = 'Matthew',
                 sample_rate: int = 16000):
        
        self.aws_region = aws_region
        self.voice_id = voice_id
        self.sample_rate = sample_rate
        
        # AWS Polly client
        self.polly_client = None
        
        # Audio playback
        self.current_playback = None
        self.playback_thread = None
        self.stop_playback_event = threading.Event()
        self.is_speaking = False
        
        # Thinking sounds
        self.thinking_phrases = [
            "hmm",
            "let me see",
            "one moment",
            "let me check that",
            "give me a second",
            "let me think about that",
            "hold on",
            "just a moment"
        ]
        
        # Audio device configuration
        self.output_device = None
        
        # Initialize AWS client
        self._initialize_aws_client()
        self._configure_audio_device()
    
    def _initialize_aws_client(self):
        """Initialize AWS Polly client"""
        try:
            self.polly_client = boto3.client('polly', region_name=self.aws_region)
            logger.info("AWS Polly client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Polly client: {e}")
            raise
    
    def _configure_audio_device(self):
        """Configure macOS audio output device"""
        try:
            # Query available devices
            devices = sd.query_devices()
            default_output = sd.query_devices(kind='output')
            
            logger.info(f"Using default output device: {default_output['name']}")
            
            # Set default output device
            sd.default.device[1] = default_output['index']
            sd.default.samplerate = self.sample_rate
            
            self.output_device = default_output
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure audio device: {e}")
            return False
    
    async def use_polly(self, text: str, interruptible: bool = True) -> bool:
        """
        Enhanced use_polly function with interruption support.
        Converts text to speech using AWS Polly and plays it with interruption capabilities.
        """
        try:
            if self.is_speaking and interruptible:
                # Stop current playback if it's interruptible
                await self.stop_speaking()
            
            # Generate speech using AWS Polly
            logger.info(f"Generating speech for: {text[:50]}...")
            
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='pcm',
                VoiceId=self.voice_id,
                SampleRate=str(self.sample_rate),
                TextType='text'
            )
            
            # Track AWS API call
            try:
                from services.aws_call_tracker import track_aws_call
                track_aws_call('polly')
            except:
                pass  # Don't break if tracker fails
            
            # Read audio data
            audio_data = response['AudioStream'].read()
            
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Create playback session
            playback = AudioPlayback(
                text=text,
                audio_data=audio_array,
                sample_rate=self.sample_rate,
                is_interruptible=interruptible,
                start_time=datetime.now()
            )
            
            # Play audio
            success = await self._play_audio(playback)
            
            return success
            
        except Exception as e:
            logger.error(f"Error in use_polly: {e}")
            return False
    
    async def _play_audio(self, playback: AudioPlayback) -> bool:
        """Play audio with interruption support"""
        try:
            self.current_playback = playback
            self.is_speaking = True
            self.stop_playback_event.clear()
            
            # Create and start playback thread
            self.playback_thread = threading.Thread(
                target=self._audio_playback_worker,
                args=(playback,)
            )
            self.playback_thread.start()
            
            # Wait for playback to complete or be interrupted
            while self.playback_thread.is_alive():
                await asyncio.sleep(0.1)
            
            self.is_speaking = False
            return not playback.is_interrupted
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            self.is_speaking = False
            return False
    
    def _audio_playback_worker(self, playback: AudioPlayback):
        """Worker thread for audio playback with interruption support"""
        try:
            playback.is_playing = True
            
            # Play audio using sounddevice
            def playback_callback(outdata, frames, time, status):
                if status:
                    logger.warning(f"Audio output status: {status}")
                
                # Check for interruption
                if self.stop_playback_event.is_set():
                    playback.is_interrupted = True
                    outdata.fill(0)  # Silence
                    raise sd.CallbackStop()
                
                # Fill output buffer with audio data
                # This is a simplified implementation
                outdata.fill(0)  # Placeholder - in real implementation, stream audio data
            
            # Use sounddevice to play audio
            sd.play(playback.audio_data, self.sample_rate)
            
            # Wait for playback to complete or be interrupted
            while sd.get_stream().active and not self.stop_playback_event.is_set():
                sd.sleep(100)  # Sleep for 100ms
            
            if self.stop_playback_event.is_set():
                sd.stop()
                playback.is_interrupted = True
                logger.info("Audio playback interrupted")
            else:
                logger.info("Audio playback completed")
            
            playback.is_playing = False
            
        except Exception as e:
            logger.error(f"Audio playback worker error: {e}")
            playback.is_playing = False
            playback.is_interrupted = True
    
    async def stop_speaking(self):
        """Stop current audio playback immediately"""
        try:
            if self.is_speaking and self.current_playback:
                logger.info("Stopping audio playback...")
                
                # Signal stop
                self.stop_playback_event.set()
                
                # Wait for playback thread to finish
                if self.playback_thread and self.playback_thread.is_alive():
                    self.playback_thread.join(timeout=1.0)
                
                # Force stop sounddevice
                try:
                    sd.stop()
                except:
                    pass
                
                self.is_speaking = False
                
                if self.current_playback:
                    self.current_playback.is_interrupted = True
                
                logger.info("Audio playback stopped")
                
        except Exception as e:
            logger.error(f"Error stopping audio playback: {e}")
    
    async def play_thinking_sound(self) -> bool:
        """Play a natural thinking sound during processing delays"""
        try:
            # Select random thinking phrase
            thinking_phrase = random.choice(self.thinking_phrases)
            
            logger.info(f"Playing thinking sound: '{thinking_phrase}'")
            
            # Generate and play thinking sound
            return await self.use_polly(thinking_phrase, interruptible=True)
            
        except Exception as e:
            logger.error(f"Error playing thinking sound: {e}")
            return False
    
    async def speak_text(self, text: str, interruptible: bool = True) -> bool:
        """
        Main interface for speaking text with natural conversation flow.
        Includes thinking sounds for longer processing delays.
        """
        try:
            # For longer texts, add a brief thinking sound first
            if len(text) > 100:
                await self.play_thinking_sound()
                await asyncio.sleep(0.5)  # Brief pause
            
            # Speak the main text
            return await self.use_polly(text, interruptible)
            
        except Exception as e:
            logger.error(f"Error in speak_text: {e}")
            return False
    
    def is_currently_speaking(self) -> bool:
        """Check if currently speaking"""
        return self.is_speaking
    
    async def wait_for_completion(self):
        """Wait for current playback to complete"""
        while self.is_speaking:
            await asyncio.sleep(0.1)
    
    async def test_speaker(self) -> bool:
        """Test speaker functionality"""
        try:
            logger.info("Testing speaker access...")
            
            # Test with a simple phrase
            test_text = "Testing speaker functionality"
            success = await self.use_polly(test_text, interruptible=False)
            
            if success:
                logger.info("✅ Speaker test passed")
                return True
            else:
                logger.warning("⚠️ Speaker test: Playback failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Speaker test failed: {e}")
            return False
    
    async def generate_conversational_response(self, data: str, context: str = "") -> str:
        """
        Generate natural, conversational responses with appropriate introductions.
        This method formats responses to sound more human-like.
        """
        try:
            # Conversational introductions
            introductions = [
                "Here's what I found:",
                "Based on the information I have:",
                "Let me share what I discovered:",
                "I found some relevant information:",
                "Here's what came up:",
                "From what I can see:",
                "Looking at the data:"
            ]
            
            # Uncertainty expressions
            uncertainty_phrases = [
                "I'm not completely sure, but",
                "From what I can tell,",
                "It appears that",
                "Based on available information,"
            ]
            
            # Select appropriate introduction based on context
            if "uncertain" in context.lower() or "confidence" in context.lower():
                intro = random.choice(uncertainty_phrases)
            else:
                intro = random.choice(introductions)
            
            # Format the response naturally
            response = f"{intro} {data}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            return data  # Fallback to original data
    
    async def handle_interruption_acknowledgment(self) -> bool:
        """Acknowledge user interruption gracefully"""
        try:
            acknowledgments = [
                "Oh, you have another question?",
                "Yes, what can I help you with?",
                "I'm listening.",
                "What would you like to know?",
                "How can I assist you?"
            ]
            
            acknowledgment = random.choice(acknowledgments)
            return await self.use_polly(acknowledgment, interruptible=True)
            
        except Exception as e:
            logger.error(f"Error handling interruption acknowledgment: {e}")
            return False

# Example usage and testing
async def main():
    """Example usage of VoiceOutputHandler"""
    
    # Create voice output handler
    handler = VoiceOutputHandler()
    
    try:
        # Test speaker
        print("Testing speaker...")
        if not await handler.test_speaker():
            print("Speaker test failed. Check permissions and device.")
            return
        
        await asyncio.sleep(2)
        
        # Test thinking sounds
        print("Testing thinking sounds...")
        await handler.play_thinking_sound()
        
        await asyncio.sleep(2)
        
        # Test conversational response
        print("Testing conversational response...")
        response = await handler.generate_conversational_response(
            "The system is working correctly and all tests have passed.",
            "confident"
        )
        await handler.speak_text(response)
        
        await asyncio.sleep(3)
        
        # Test interruption
        print("Testing interruption (will interrupt after 2 seconds)...")
        long_text = ("This is a longer text that will be interrupted. "
                    "I'm going to keep talking for a while to demonstrate "
                    "the interruption functionality. This should be stopped "
                    "before it finishes playing completely.")
        
        # Start speaking
        speak_task = asyncio.create_task(handler.speak_text(long_text))
        
        # Interrupt after 2 seconds
        await asyncio.sleep(2)
        await handler.stop_speaking()
        
        # Acknowledge interruption
        await asyncio.sleep(0.5)
        await handler.handle_interruption_acknowledgment()
        
        print("All tests completed!")
        
    except KeyboardInterrupt:
        print("\nStopping...")
        await handler.stop_speaking()
    
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    asyncio.run(main())