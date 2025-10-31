#!/usr/bin/env python3
"""
Enhanced VoiceInputHandler for real-time speech-to-text with interruption detection.
Supports macOS Core Audio through sounddevice with async streaming.
"""

import asyncio
import sounddevice as sd
import numpy as np
import boto3
import json
import threading
import queue
import time
from typing import AsyncGenerator, Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VoiceInput:
    """Represents a voice input with metadata"""
    transcript: str
    confidence: float
    timestamp: datetime
    is_interruption: bool
    word_count: int
    is_final: bool = False

class MyEventHandler:
    """Enhanced event handler for AWS Transcribe streaming with word counting and interruption detection"""
    
    def __init__(self, callback: Callable[[VoiceInput], None], interruption_threshold: int = 3):
        self.callback = callback
        self.interruption_threshold = interruption_threshold
        self.current_transcript = ""
        self.is_listening_during_playback = False
        
    def set_listening_during_playback(self, listening: bool):
        """Set whether we're listening during audio playback for interruption detection"""
        self.is_listening_during_playback = listening
        
    def on_transcript_event(self, transcript_event):
        """Handle transcript events from AWS Transcribe"""
        try:
            results = transcript_event.get('Transcript', {}).get('Results', [])
            
            for result in results:
                if 'Alternatives' in result:
                    transcript = result['Alternatives'][0].get('Transcript', '')
                    confidence = result['Alternatives'][0].get('Confidence', 0.0)
                    is_final = not result.get('IsPartial', True)
                    
                    if transcript.strip():
                        word_count = len(transcript.strip().split())
                        
                        # Determine if this is an interruption (for partial transcripts during playback)
                        is_interruption = (
                            self.is_listening_during_playback and 
                            word_count >= self.interruption_threshold
                        )
                        
                        voice_input = VoiceInput(
                            transcript=transcript,
                            confidence=confidence,
                            timestamp=datetime.now(),
                            is_interruption=is_interruption,
                            word_count=word_count,
                            is_final=is_final
                        )
                        
                        # Only call the callback for final transcripts OR interruptions
                        if is_final or is_interruption:
                            self.callback(voice_input)
                        
                        if is_final:
                            self.current_transcript = ""
                        else:
                            self.current_transcript = transcript
                            
        except Exception as e:
            logger.error(f"Error processing transcript event: {e}")

class VoiceInputHandler:
    """Enhanced voice input handler with real-time transcription and interruption detection"""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 chunk_duration: float = 0.1,
                 interruption_threshold: int = 3,
                 aws_region: str = 'us-east-1'):
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        self.interruption_threshold = interruption_threshold
        self.aws_region = aws_region
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None
        
        # AWS Transcribe
        self.transcribe_client = None
        self.transcribe_stream = None
        
        # Event handling
        self.event_handler = None
        self.voice_input_callback = None
        
        # Threading
        self.transcribe_thread = None
        self.stop_event = threading.Event()
        
        # Initialize AWS client
        self._initialize_aws_client()
        
    def _initialize_aws_client(self):
        """Initialize AWS Transcribe client"""
        try:
            self.transcribe_client = boto3.client('transcribe', region_name=self.aws_region)
            logger.info("AWS Transcribe client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Transcribe client: {e}")
            raise
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice audio input"""
        if status:
            logger.warning(f"Audio input status: {status}")
        
        if self.is_recording:
            # Convert to the format expected by AWS Transcribe
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            self.audio_queue.put(audio_data.tobytes())
    
    def _configure_audio_device(self):
        """Configure macOS audio input device"""
        try:
            # Query available devices
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            
            logger.info(f"Using default input device: {default_input['name']}")
            
            # Set default input device
            sd.default.device[0] = default_input['index']
            sd.default.samplerate = self.sample_rate
            sd.default.channels[0] = self.channels
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure audio device: {e}")
            return False
    
    def _transcribe_worker(self):
        """Worker thread for AWS Transcribe streaming"""
        try:
            # Run the async transcription in this thread
            asyncio.run(self._async_transcribe_worker())
        except Exception as e:
            logger.error(f"Transcribe worker error: {e}")
    
    async def _async_transcribe_worker(self):
        """Async worker for AWS Transcribe streaming"""
        try:
            from amazon_transcribe.client import TranscribeStreamingClient
            from amazon_transcribe.handlers import TranscriptResultStreamHandler
            from amazon_transcribe.model import TranscriptEvent
            
            # Create transcribe streaming client
            client = TranscribeStreamingClient(region=self.aws_region)
            
            # Start transcription stream (this is async)
            stream = await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=self.sample_rate,
                media_encoding="pcm"
            )
            
            # Track AWS API call
            try:
                from services.aws_call_tracker import track_aws_call
                track_aws_call('transcribe')
            except:
                pass  # Don't break if tracker fails
            
            # Create custom handler for transcript events
            class TranscriptHandler(TranscriptResultStreamHandler):
                def __init__(self, transcript_result_stream, voice_handler):
                    super().__init__(transcript_result_stream)
                    self.voice_handler = voice_handler
                
                async def handle_transcript_event(self, transcript_event: TranscriptEvent):
                    try:
                        for result in transcript_event.transcript.results:
                            for alt in result.alternatives:
                                if alt.transcript:
                                    # Convert to the format expected by our event handler
                                    event_data = {
                                        'Transcript': {
                                            'Results': [{
                                                'Alternatives': [{
                                                    'Transcript': alt.transcript,
                                                    'Confidence': getattr(alt, 'confidence', 0.9)
                                                }],
                                                'IsPartial': result.is_partial
                                            }]
                                        }
                                    }
                                    self.voice_handler.on_transcript_event(event_data)
                    except Exception as e:
                        logger.error(f"Error in transcript handler: {e}")
            
            # Create handler
            handler = TranscriptHandler(stream.output_stream, self.event_handler)
            
            # Start handling events in background
            event_task = asyncio.create_task(handler.handle_events())
            
            # Process audio data
            try:
                while not self.stop_event.is_set():
                    try:
                        audio_chunk = self.audio_queue.get(timeout=0.1)
                        # Send audio to transcribe stream
                        await stream.input_stream.send_audio_event(audio_chunk=audio_chunk)
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"Error sending audio to transcribe: {e}")
                        break
            finally:
                # End the stream
                try:
                    await stream.input_stream.end_stream()
                except Exception as e:
                    logger.error(f"Error ending stream: {e}")
                
                # Wait for event handler to finish
                try:
                    await asyncio.wait_for(event_task, timeout=2.0)
                except asyncio.TimeoutError:
                    event_task.cancel()
            
        except Exception as e:
            logger.error(f"Async transcribe worker error: {e}")
    
    async def start_listening(self, 
                            callback: Callable[[VoiceInput], None],
                            listening_during_playback: bool = False) -> bool:
        """Start listening for voice input with real-time transcription"""
        
        if self.is_recording:
            logger.warning("Already recording")
            return False
        
        try:
            # Configure audio device
            if not self._configure_audio_device():
                return False
            
            # Set up callback and event handler
            self.voice_input_callback = callback
            self.event_handler = MyEventHandler(callback, self.interruption_threshold)
            self.event_handler.set_listening_during_playback(listening_during_playback)
            
            # Start audio stream
            self.stream = sd.InputStream(
                callback=self._audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                dtype=np.float32
            )
            
            self.stream.start()
            self.is_recording = True
            
            # Start transcribe worker thread
            self.stop_event.clear()
            self.transcribe_thread = threading.Thread(target=self._transcribe_worker)
            self.transcribe_thread.start()
            
            logger.info("Voice input handler started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start voice input handler: {e}")
            await self.stop_listening()
            return False
    
    async def stop_listening(self):
        """Stop listening for voice input"""
        try:
            self.is_recording = False
            
            # Stop transcribe worker
            if self.transcribe_thread and self.transcribe_thread.is_alive():
                self.stop_event.set()
                self.transcribe_thread.join(timeout=2.0)
            
            # Stop audio stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            # Clear queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            logger.info("Voice input handler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping voice input handler: {e}")
    
    def set_interruption_mode(self, listening_during_playback: bool):
        """Enable/disable interruption detection during audio playback"""
        if self.event_handler:
            self.event_handler.set_listening_during_playback(listening_during_playback)
    
    def get_audio_level(self) -> float:
        """Get current audio input level for visual feedback"""
        try:
            if not self.is_recording or not self.stream:
                return 0.0
            
            # This is a simplified implementation
            # In a real implementation, you'd track recent audio levels
            return 0.5  # Placeholder
            
        except Exception as e:
            logger.error(f"Error getting audio level: {e}")
            return 0.0
    
    async def test_microphone(self) -> bool:
        """Test microphone access and functionality"""
        try:
            logger.info("Testing microphone access...")
            
            # Configure audio device
            if not self._configure_audio_device():
                return False
            
            # Record for 1 second to test
            duration = 1.0
            test_recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32
            )
            sd.wait()
            
            # Check if we got audio data
            max_amplitude = np.max(np.abs(test_recording))
            
            if max_amplitude > 0.001:
                logger.info("✅ Microphone test passed")
                return True
            else:
                logger.warning("⚠️ Microphone test: No audio detected")
                return False
                
        except Exception as e:
            logger.error(f"❌ Microphone test failed: {e}")
            return False

# Example usage and testing
async def main():
    """Example usage of VoiceInputHandler"""
    
    def on_voice_input(voice_input: VoiceInput):
        """Callback for voice input events"""
        status = "INTERRUPTION" if voice_input.is_interruption else "NORMAL"
        final_status = "FINAL" if voice_input.is_final else "PARTIAL"
        
        print(f"[{status}] [{final_status}] ({voice_input.word_count} words, "
              f"confidence: {voice_input.confidence:.2f}): {voice_input.transcript}")
    
    # Create voice input handler
    handler = VoiceInputHandler()
    
    # Test microphone
    if not await handler.test_microphone():
        print("Microphone test failed. Check permissions and device.")
        return
    
    try:
        # Start listening
        print("Starting voice input handler...")
        if await handler.start_listening(on_voice_input):
            print("Listening for voice input. Speak into the microphone...")
            print("Press Ctrl+C to stop")
            
            # Listen for 30 seconds
            await asyncio.sleep(30)
        else:
            print("Failed to start voice input handler")
    
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        await handler.stop_listening()

if __name__ == "__main__":
    asyncio.run(main())