"""
Audio Handler for Real-time Voice Capture and Playback
Handles microphone input streaming and speaker output with buffering
"""
import pyaudio
import threading
import queue
import time
from typing import Callable, Optional

from config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_BIT_DEPTH,
    AUDIO_CHUNK_SIZE,
    OUTPUT_SAMPLE_RATE,
    OUTPUT_CHANNELS
)


class AudioHandler:
    """
    Handles real-time audio capture and playback.
    
    - Captures microphone input in chunks
    - Buffers and plays back AI audio responses
    - Thread-safe for use with async WebSocket
    """
    
    def __init__(self):
        self.pyaudio = pyaudio.PyAudio()
        
        # Input stream (microphone)
        self.input_stream: Optional[pyaudio.Stream] = None
        self.is_capturing = False
        self._capture_thread: Optional[threading.Thread] = None
        self._on_audio_chunk: Optional[Callable[[bytes], None]] = None
        
        # Output stream (speaker)
        self.output_stream: Optional[pyaudio.Stream] = None
        self.is_playing = False
        self._playback_thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()
        
        # Debug callback
        self._on_debug: Optional[Callable[[str], None]] = None
        
        # Audio format
        self.format = pyaudio.paInt16  # 16-bit
        self.input_channels = AUDIO_CHANNELS
        self.input_rate = AUDIO_SAMPLE_RATE
        self.chunk_size = AUDIO_CHUNK_SIZE
        
        self.output_channels = OUTPUT_CHANNELS
        self.output_rate = OUTPUT_SAMPLE_RATE
    
    def _log(self, message: str):
        """Internal logging"""
        if self._on_debug:
            self._on_debug(f"[Audio] {message}")
        else:
            print(f"[Audio] {message}")
    
    def on_debug(self, callback: Callable[[str], None]):
        """Set debug logging callback"""
        self._on_debug = callback
        return self
    
    def list_devices(self):
        """List available audio devices and print to console"""
        info = self.pyaudio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        # Print header
        print("\n" + "=" * 50)
        print("AUDIO DEVICES")
        print("=" * 50)
        
        # Print defaults
        try:
            default_output = self.pyaudio.get_default_output_device_info()
            print(f"DEFAULT OUTPUT: [{default_output['index']}] {default_output['name']}")
        except:
            print("DEFAULT OUTPUT: None found")
            
        try:
            default_input = self.pyaudio.get_default_input_device_info()
            print(f"DEFAULT INPUT:  [{default_input['index']}] {default_input['name']}")
        except:
            print("DEFAULT INPUT: None found")
        
        print("-" * 50)
        
        devices = []
        for i in range(num_devices):
            device_info = self.pyaudio.get_device_info_by_host_api_device_index(0, i)
            d = {
                'index': i,
                'name': device_info.get('name'),
                'max_input_channels': device_info.get('maxInputChannels'),
                'max_output_channels': device_info.get('maxOutputChannels'),
                'default_sample_rate': device_info.get('defaultSampleRate')
            }
            devices.append(d)
            
            # Print each device
            in_ch = d['max_input_channels']
            out_ch = d['max_output_channels']
            types = []
            if in_ch > 0:
                types.append(f"IN:{in_ch}ch")
            if out_ch > 0:
                types.append(f"OUT:{out_ch}ch")
            print(f"  [{i}] {d['name']} ({', '.join(types)})")
        
        print("=" * 50 + "\n")
        return devices
    
    def get_default_input_device(self) -> int:
        """Get default input device index"""
        try:
            return self.pyaudio.get_default_input_device_info()['index']
        except:
            return 0
    
    def get_default_output_device(self) -> int:
        """Get default output device index"""
        try:
            return self.pyaudio.get_default_output_device_info()['index']
        except:
            return 0
    
    # === Microphone Capture ===
    
    def start_capture(self, on_audio_chunk: Callable[[bytes], None], device_index: Optional[int] = None):
        """
        Start capturing audio from microphone.
        
        Args:
            on_audio_chunk: Callback for each audio chunk (PCM bytes)
            device_index: Optional specific input device
        """
        if self.is_capturing:
            self._log("Already capturing")
            return
            
        self._on_audio_chunk = on_audio_chunk
        
        try:
            self.input_stream = self.pyaudio.open(
                format=self.format,
                channels=self.input_channels,
                rate=self.input_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_capturing = True
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            
            self._log(f"Started capture: {self.input_rate}Hz, {self.input_channels}ch, {self.chunk_size} samples/chunk")
            
        except Exception as e:
            self._log(f"Failed to start capture: {e}")
            raise
    
    def _capture_loop(self):
        """Continuous audio capture loop"""
        while self.is_capturing and self.input_stream:
            try:
                # Read audio chunk
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Send to callback
                if self._on_audio_chunk and data:
                    self._on_audio_chunk(data)
                    
            except Exception as e:
                if self.is_capturing:  # Only log if we're supposed to be capturing
                    self._log(f"Capture error: {e}")
                break
    
    def stop_capture(self):
        """Stop capturing audio from microphone"""
        self.is_capturing = False
        
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except:
                pass
            self.input_stream = None
            
        self._log("Stopped capture")
    
    # === Speaker Playback ===
    
    def start_playback(self, device_index: Optional[int] = None):
        """
        Start audio playback system.
        
        Args:
            device_index: Optional specific output device
        """
        if self.is_playing:
            self._log("Already playing")
            return
            
        try:
            self.output_stream = self.pyaudio.open(
                format=self.format,
                channels=self.output_channels,
                rate=self.output_rate,
                output=True,
                output_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_playing = True
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()
            
            self._log(f"Started playback: {self.output_rate}Hz, {self.output_channels}ch")
            
        except Exception as e:
            self._log(f"Failed to start playback: {e}")
            raise
    
    def _playback_loop(self):
        """Continuous audio playback loop"""
        while self.is_playing and self.output_stream:
            try:
                # Get audio data from queue (blocking with timeout)
                data = self._audio_queue.get(timeout=0.1)
                
                if data and self.output_stream:
                    self.output_stream.write(data)
                    
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_playing:
                    self._log(f"Playback error: {e}")
                break
    
    def play_audio(self, audio_data: bytes):
        """
        Queue audio data for playback.
        
        Args:
            audio_data: PCM audio bytes
        """
        if self.is_playing:
            self._audio_queue.put(audio_data)
    
    def clear_playback_queue(self):
        """Clear any queued audio (useful when interrupting)"""
        cleared = 0
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
                cleared += 1
            except queue.Empty:
                break
        if cleared > 0:
            self._log(f"Cleared {cleared} audio chunks from queue")
    
    def stop_playback(self):
        """Stop audio playback"""
        self.is_playing = False
        self.clear_playback_queue()
        
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except:
                pass
            self.output_stream = None
            
        self._log("Stopped playback")
    
    # === Lifecycle ===
    
    def start(self, on_audio_chunk: Callable[[bytes], None]):
        """Start both capture and playback"""
        self.start_playback()
        self.start_capture(on_audio_chunk)
    
    def stop(self):
        """Stop both capture and playback"""
        self.stop_capture()
        self.stop_playback()
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop()
        self.pyaudio.terminate()
        self._log("Audio handler cleaned up")


class AudioLevelMonitor:
    """
    Monitor audio levels for visualization.
    Calculates RMS (root mean square) of audio chunks.
    """
    
    def __init__(self, smoothing: float = 0.3):
        self.smoothing = smoothing
        self.current_level = 0.0
        self._lock = threading.Lock()
    
    def update(self, audio_data: bytes) -> float:
        """
        Update level with new audio data.
        Returns normalized level (0.0 - 1.0)
        """
        import struct
        import math
        
        # Convert bytes to samples
        sample_count = len(audio_data) // 2  # 16-bit = 2 bytes per sample
        samples = struct.unpack(f'{sample_count}h', audio_data)
        
        # Calculate RMS
        if samples:
            sum_squares = sum(s * s for s in samples)
            rms = math.sqrt(sum_squares / sample_count)
            # Normalize to 0-1 (32768 is max for 16-bit)
            normalized = min(1.0, rms / 16384)
        else:
            normalized = 0.0
        
        # Apply smoothing
        with self._lock:
            self.current_level = (self.smoothing * self.current_level + 
                                  (1 - self.smoothing) * normalized)
            return self.current_level
    
    def get_level(self) -> float:
        """Get current smoothed level"""
        with self._lock:
            return self.current_level
    
    def reset(self):
        """Reset level to zero"""
        with self._lock:
            self.current_level = 0.0
