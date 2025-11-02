#!/usr/bin/env python3
"""
InterruptionDetector component for real-time monitoring of microphone input during audio playback.
Handles word counting, meaningful speech detection, and audio playback control on macOS.
"""

import asyncio
import sounddevice as sd
import numpy as np
import threading
import queue
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InterruptionEvent:
    """Represents an interruption event"""
    timestamp: datetime
    audio_level: float
    word_count: int
    confidence: float
    transcript: str
    is_meaningful: bool

class AudioLevelMonitor:
    """Monitors audio input levels for voice activity detection"""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_duration: float = 0.1,
                 silence_threshold: float = 0.01,
                 voice_threshold: float = 0.05):
        
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        self.silence_threshold = silence_threshold
        self.voice_threshold = voice_threshold
        
        # Audio level tracking
        self.recent_levels = deque(maxlen=10)  # Keep last 1 second of levels
        self.current_level = 0.0
        self.is_voice_detected = False
        
    def process_audio_chunk(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Process audio chunk and return voice activity information"""
        try:
            # Calculate RMS level
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            self.current_level = rms_level
            self.recent_levels.append(rms_level)
            
            # Determine voice activity
            avg_recent_level = np.mean(self.recent_levels) if self.recent_levels else 0.0
            
            # Voice detected if current level is above threshold and 
            # significantly higher than recent average
            is_voice = (
                rms_level > self.voice_threshold and 
                rms_level > avg_recent_level * 1.5
            )
            
            self.is_voice_detected = is_voice
            
            return {
                'rms_level': rms_level,
                'avg_recent_level': avg_recent_level,
                'is_voice_detected': is_voice,
                'is_silence': rms_level < self.silence_threshold
            }
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return {
                'rms_level': 0.0,
                'avg_recent_level': 0.0,
                'is_voice_detected': False,
                'is_silence': True
            }

class SpeechDetector:
    """Detects meaningful speech patterns and word counting"""
    
    def __init__(self, 
                 word_threshold: int = 3,
                 confidence_threshold: float = 0.7,
                 speech_timeout: float = 2.0):
        
        self.word_threshold = word_threshold
        self.confidence_threshold = confidence_threshold
        self.speech_timeout = speech_timeout
        
        # Speech tracking
        self.current_transcript = ""
        self.word_count = 0
        self.last_speech_time = None
        self.speech_confidence = 0.0
        
    def process_transcript(self, transcript: str, confidence: float) -> Dict[str, Any]:
        """Process transcript and determine if it represents meaningful speech"""
        try:
            # Update current transcript
            self.current_transcript = transcript.strip()
            self.speech_confidence = confidence
            self.last_speech_time = datetime.now()
            
            # Count words (simple whitespace-based counting)
            words = self.current_transcript.split()
            self.word_count = len([word for word in words if word.strip()])
            
            # Determine if speech is meaningful
            is_meaningful = (
                self.word_count >= self.word_threshold and
                confidence >= self.confidence_threshold and
                len(self.current_transcript) > 5  # At least 5 characters
            )
            
            # Filter out common non-meaningful utterances
            non_meaningful_patterns = [
                'um', 'uh', 'ah', 'hmm', 'er', 'oh',
                'yeah', 'yes', 'no', 'okay', 'ok'
            ]
            
            if self.word_count <= 2:
                transcript_lower = self.current_transcript.lower()
                if any(pattern in transcript_lower for pattern in non_meaningful_patterns):
                    is_meaningful = False
            
            return {
                'transcript': self.current_transcript,
                'word_count': self.word_count,
                'confidence': confidence,
                'is_meaningful': is_meaningful,
                'speech_duration': self._get_speech_duration()
            }
            
        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
            return {
                'transcript': '',
                'word_count': 0,
                'confidence': 0.0,
                'is_meaningful': False,
                'speech_duration': 0.0
            }
    
    def _get_speech_duration(self) -> float:
        """Get duration of current speech session"""
        if self.last_speech_time:
            return (datetime.now() - self.last_speech_time).total_seconds()
        return 0.0
    
    def reset(self):
        """Reset speech detection state"""
        self.current_transcript = ""
        self.word_count = 0
        self.last_speech_time = None
        self.speech_confidence = 0.0

class InterruptionDetector:
    """Main interruption detector that coordinates audio monitoring and speech detection"""
    
    def __init__(self,
                 sample_rate: int = 16000,
                 channels: int = 1,
                 word_threshold: int = 3,
                 confidence_threshold: float = 0.7,
                 audio_threshold: float = 0.05):
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.word_threshold = word_threshold
        self.confidence_threshold = confidence_threshold
        self.audio_threshold = audio_threshold
        
        # Components
        self.audio_monitor = AudioLevelMonitor(
            sample_rate=sample_rate,
            voice_threshold=audio_threshold
        )
        self.speech_detector = SpeechDetector(
            word_threshold=word_threshold,
            confidence_threshold=confidence_threshold
        )
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.is_monitoring = False
        self.stream = None
        
        # Callbacks
        self.interruption_callback = None
        self.audio_level_callback = None
        
        # Threading
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # State
        self.is_playback_active = False
        self.last_interruption_time = None
        
    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice audio input during monitoring"""
        if status:
            logger.warning(f"Audio monitoring status: {status}")
        
        if self.is_monitoring and self.is_playback_active:
            # Process audio data for interruption detection
            audio_data = indata[:, 0] if self.channels == 1 else indata
            self.audio_queue.put(audio_data.copy())
    
    def _configure_audio_device(self) -> bool:
        """Configure macOS audio input device for monitoring"""
        try:
            # Query available devices
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            
            logger.info(f"Interruption detector using input device: {default_input['name']}")
            
            # Configure device settings
            sd.default.device[0] = default_input['index']
            sd.default.samplerate = self.sample_rate
            sd.default.channels[0] = self.channels
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure audio device for interruption detection: {e}")
            return False
    
    def _monitoring_worker(self):
        """Worker thread for audio monitoring and interruption detection"""
        try:
            while not self.stop_event.is_set():
                try:
                    # Get audio chunk with timeout
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    
                    # Process audio level
                    audio_info = self.audio_monitor.process_audio_chunk(audio_chunk)
                    
                    # Call audio level callback if provided
                    if self.audio_level_callback:
                        self.audio_level_callback(audio_info)
                    
                    # Check for voice activity during playback
                    if (self.is_playback_active and 
                        audio_info['is_voice_detected'] and
                        audio_info['rms_level'] > self.audio_threshold):
                        
                        # Potential interruption detected
                        self._handle_potential_interruption(audio_info)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in monitoring worker: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Monitoring worker error: {e}")
    
    def _handle_potential_interruption(self, audio_info: Dict[str, Any]):
        """Handle potential interruption based on audio activity"""
        try:
            # Create interruption event
            interruption_event = InterruptionEvent(
                timestamp=datetime.now(),
                audio_level=audio_info['rms_level'],
                word_count=0,  # Will be updated when transcript is available
                confidence=0.0,  # Will be updated when transcript is available
                transcript="",  # Will be updated when transcript is available
                is_meaningful=audio_info['is_voice_detected']
            )
            
            # Trigger interruption based on audio level (more sensitive)
            # Lower threshold for better responsiveness
            if (audio_info['rms_level'] > self.audio_threshold * 1.5 and
                self._should_trigger_interruption()):
                
                logger.info(f"Interruption detected - Audio level: {audio_info['rms_level']:.3f}")
                
                if self.interruption_callback:
                    self.interruption_callback(interruption_event)
                
                self.last_interruption_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error handling potential interruption: {e}")
    
    def _should_trigger_interruption(self) -> bool:
        """Determine if interruption should be triggered based on timing and state"""
        try:
            # Avoid triggering interruptions too frequently (but allow faster interruptions)
            if self.last_interruption_time:
                time_since_last = (datetime.now() - self.last_interruption_time).total_seconds()
                if time_since_last < 0.5:  # Minimum 0.5 seconds between interruptions
                    return False
            
            # Only trigger during active playback
            return self.is_playback_active
            
        except Exception as e:
            logger.error(f"Error checking interruption trigger: {e}")
            return False
    
    async def start_monitoring(self, 
                             interruption_callback: Callable[[InterruptionEvent], None],
                             audio_level_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
        """Start monitoring for interruptions during audio playback"""
        
        if self.is_monitoring:
            logger.warning("Interruption detector already monitoring")
            return False
        
        try:
            # Configure audio device
            if not self._configure_audio_device():
                return False
            
            # Set callbacks
            self.interruption_callback = interruption_callback
            self.audio_level_callback = audio_level_callback
            
            # Start audio stream for monitoring
            self.stream = sd.InputStream(
                callback=self._audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
                dtype=np.float32
            )
            
            self.stream.start()
            self.is_monitoring = True
            
            # Start monitoring worker thread
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(target=self._monitoring_worker)
            self.monitor_thread.start()
            
            logger.info("Interruption detector started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start interruption detector: {e}")
            await self.stop_monitoring()
            return False
    
    async def stop_monitoring(self):
        """Stop monitoring for interruptions"""
        try:
            self.is_monitoring = False
            self.is_playback_active = False
            
            # Stop monitoring worker
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.stop_event.set()
                self.monitor_thread.join(timeout=2.0)
            
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
            
            # Reset state
            self.speech_detector.reset()
            
            logger.info("Interruption detector stopped")
            
        except Exception as e:
            logger.error(f"Error stopping interruption detector: {e}")
    
    def set_playback_active(self, active: bool):
        """Set whether audio playback is currently active"""
        self.is_playback_active = active
        if not active:
            self.speech_detector.reset()
        
        logger.debug(f"Playback active: {active}")
    
    def process_transcript_update(self, transcript: str, confidence: float):
        """Process transcript update for more accurate interruption detection"""
        try:
            if not self.is_playback_active:
                return
            
            # Process transcript through speech detector
            speech_info = self.speech_detector.process_transcript(transcript, confidence)
            
            # Check if this represents a meaningful interruption
            if speech_info['is_meaningful']:
                interruption_event = InterruptionEvent(
                    timestamp=datetime.now(),
                    audio_level=self.audio_monitor.current_level,
                    word_count=speech_info['word_count'],
                    confidence=confidence,
                    transcript=transcript,
                    is_meaningful=True
                )
                
                logger.info(f"Meaningful interruption detected: '{transcript}' "
                           f"({speech_info['word_count']} words, confidence: {confidence:.2f})")
                
                if self.interruption_callback:
                    self.interruption_callback(interruption_event)
                
                self.last_interruption_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error processing transcript update: {e}")
    
    def get_current_audio_level(self) -> float:
        """Get current audio input level"""
        return self.audio_monitor.current_level
    
    def is_voice_detected(self) -> bool:
        """Check if voice is currently detected"""
        return self.audio_monitor.is_voice_detected

# Example usage and testing
async def main():
    """Example usage of InterruptionDetector"""
    
    def on_interruption(event: InterruptionEvent):
        """Callback for interruption events"""
        print(f"🚨 INTERRUPTION DETECTED!")
        print(f"   Time: {event.timestamp}")
        print(f"   Audio Level: {event.audio_level:.3f}")
        print(f"   Word Count: {event.word_count}")
        print(f"   Confidence: {event.confidence:.2f}")
        print(f"   Transcript: '{event.transcript}'")
        print(f"   Meaningful: {event.is_meaningful}")
        print()
    
    def on_audio_level(info: Dict[str, Any]):
        """Callback for audio level updates"""
        if info['is_voice_detected']:
            print(f"🎤 Voice detected - Level: {info['rms_level']:.3f}")
    
    # Create interruption detector
    detector = InterruptionDetector(word_threshold=3)
    
    try:
        # Start monitoring
        print("Starting interruption detector...")
        if await detector.start_monitoring(on_interruption, on_audio_level):
            print("Monitoring for interruptions...")
            print("Simulating audio playback...")
            
            # Simulate audio playback
            detector.set_playback_active(True)
            
            print("Speak into the microphone to test interruption detection...")
            print("Press Ctrl+C to stop")
            
            # Monitor for 30 seconds
            await asyncio.sleep(30)
        else:
            print("Failed to start interruption detector")
    
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        detector.set_playback_active(False)
        await detector.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())