"""
Remy - AI Desk Companion
Main application entry point

Real-time voice AI using Coze WebSocket API with animated face display.
"""
import sys
import time
import threading
from typing import Optional

from config import EyeState, DEBUG_MODE
from coze_client import CozeRealtimeClient
from audio_handler import AudioHandler, AudioLevelMonitor
from ui_eyes import RemyUI


class RemyCompanion:
    """
    Main application class that orchestrates:
    - Coze WebSocket client for AI conversation
    - Audio capture and playback
    - Animated UI display
    """
    
    def __init__(self):
        # Core components
        self.ui: Optional[RemyUI] = None
        self.coze: Optional[CozeRealtimeClient] = None
        self.audio: Optional[AudioHandler] = None
        
        # Audio level monitoring for visualization
        self.input_level_monitor = AudioLevelMonitor(smoothing=0.4)
        self.output_level_monitor = AudioLevelMonitor(smoothing=0.3)
        
        # State
        self.is_running = False
        self.is_ready = False
        
    def log(self, message: str):
        """Log to UI and console"""
        try:
            print(message)
        except UnicodeEncodeError:
            # Windows console may not support some Unicode chars
            print(message.encode('ascii', 'replace').decode())
        if self.ui:
            self.ui.log(message)
    
    def _setup_coze_callbacks(self):
        """Configure Coze client callbacks"""
        
        def on_ready():
            self.is_ready = True
            self.log("[OK] Coze connected and ready!")
            self.ui.set_state(EyeState.IDLE)
        
        def on_audio(audio_bytes: bytes):
            """Handle incoming AI audio"""
            if self.audio:
                self.audio.play_audio(audio_bytes)
                # Update output level for visualization
                level = self.output_level_monitor.update(audio_bytes)
                self.ui.set_audio_level(level)
        
        def on_transcript(text: str, is_final: bool):
            """Handle user speech transcription"""
            self.ui.set_user_transcript(text)
            if is_final:
                self.log(f"You: {text}")
        
        def on_ai_transcript(text: str):
            """Handle AI response text"""
            self.ui.set_ai_transcript(text)
        
        def on_emotion(emotion: str):
            """Handle detected user emotion from voice"""
            self.log(f">>> EMOTION CALLBACK: {emotion} <<<")
            # Map Coze emotions to eye states
            emotion_map = {
                "happy": EyeState.HAPPY,
                "sad": EyeState.SAD,
                "angry": EyeState.ANGRY,
                "surprise": EyeState.SURPRISED,
                "surprised": EyeState.SURPRISED,
                "neutral": EyeState.NEUTRAL,
            }
            eye_state = emotion_map.get(emotion.lower(), EyeState.NEUTRAL)
            self.log(f">>> Setting eye state to: {eye_state} <<<")
            self.ui.set_emotion(emotion, eye_state)
        
        def on_state_change(state: str):
            """Handle conversation state changes"""
            state_map = {
                "idle": EyeState.IDLE,
                "listening": EyeState.LISTENING,
                "thinking": EyeState.THINKING,
                "speaking": EyeState.SPEAKING
            }
            eye_state = state_map.get(state, EyeState.IDLE)
            self.ui.set_state(eye_state)
            
            # Clear audio queue when interrupted
            if state == "listening" and self.audio:
                self.audio.clear_playback_queue()
        
        def on_error(error: str):
            """Handle errors"""
            self.log(f"[ERROR] {error}")
        
        def on_debug(message: str):
            """Handle debug messages from Coze client"""
            if DEBUG_MODE:
                self.log(message)
        
        # Wire up callbacks
        self.coze.on_ready(on_ready)
        self.coze.on_audio(on_audio)
        self.coze.on_transcript(on_transcript)
        self.coze.on_ai_transcript(on_ai_transcript)
        self.coze.on_emotion(on_emotion)
        self.coze.on_state_change(on_state_change)
        self.coze.on_error(on_error)
        self.coze.on_debug(on_debug)
    
    def _on_audio_chunk(self, audio_data: bytes):
        """Handle microphone audio chunk"""
        if self.is_ready and self.coze:
            # Send to Coze
            self.coze.send_audio(audio_data)
            
            # Update input level for visualization (optional)
            self.input_level_monitor.update(audio_data)
    
    def init(self):
        """Initialize all components"""
        self.log("=" * 50)
        self.log("  Remy - AI Desk Companion")
        self.log("=" * 50)
        
        # Initialize UI first (needs pygame init)
        self.log("Initializing UI...")
        self.ui = RemyUI()
        self.ui.init()
        self.ui.set_state(EyeState.IDLE)
        self.log("[OK] UI ready")
        
        # Initialize audio handler
        self.log("Initializing audio...")
        self.audio = AudioHandler()
        self.audio.on_debug(lambda msg: self.log(msg))
        
        # List available audio devices
        devices = self.audio.list_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        output_devices = [d for d in devices if d['max_output_channels'] > 0]
        
        self.log(f"Found {len(input_devices)} input, {len(output_devices)} output devices")
        
        # Start audio
        self.audio.start(self._on_audio_chunk)
        self.log("[OK] Audio ready")
        
        # Initialize Coze client
        self.log("Initializing Coze client...")
        self.coze = CozeRealtimeClient()
        self._setup_coze_callbacks()
        self.log("[OK] Coze client ready")
        
        self.is_running = True
        self.log("-" * 50)
        self.log("Connecting to Coze...")
    
    def connect(self):
        """Connect to Coze API"""
        if self.coze:
            self.coze.connect()
    
    def run(self):
        """Main application loop"""
        self.init()
        self.connect()
        
        self.log("Starting main loop...")
        self.log("Press ESC to exit")
        self.log("-" * 50)
        
        try:
            while self.is_running and self.ui.running:
                # Run UI frame (handles events, updates, drawing)
                if not self.ui.run_frame():
                    self.is_running = False
                    break
                    
        except KeyboardInterrupt:
            self.log("Interrupted by user")
        except Exception as e:
            self.log(f"Error in main loop: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of all components"""
        self.log("Shutting down...")
        self.is_running = False
        
        # Stop audio first
        if self.audio:
            self.audio.cleanup()
            self.log("[OK] Audio stopped")
        
        # Disconnect from Coze
        if self.coze:
            self.coze.disconnect()
            self.log("[OK] Coze disconnected")
        
        # Quit UI
        if self.ui:
            self.ui.quit()
            self.log("[OK] UI closed")
        
        self.log("Goodbye!")


def main():
    """Entry point"""
    companion = RemyCompanion()
    
    try:
        companion.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
