"""
Coze WebSocket Client for Real-time Voice Conversations
Handles bidirectional streaming with full interruption support
"""
import json
import base64
import threading
import time
import uuid
import re
from typing import Callable, Optional, Dict, Any, Tuple
import websocket

from config import (
    COZE_ACCESS_TOKEN, 
    COZE_WS_URL,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_BIT_DEPTH,
    OUTPUT_SAMPLE_RATE,
    VAD_MODE,
    VAD_SILENCE_DURATION_MS,
    VAD_PREFIX_PADDING_MS
)


class CozeRealtimeClient:
    """
    WebSocket client for Coze's bidirectional streaming voice API.
    
    Supports:
    - Real-time voice streaming (input and output)
    - Server-side VAD (Voice Activity Detection)
    - Interruption handling
    - Automatic reconnection
    """
    
    def __init__(self):
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = False
        self.is_configured = False
        self.conversation_id: Optional[str] = None
        self.current_chat_id: Optional[str] = None
        
        # State tracking
        self.is_user_speaking = False
        self.is_ai_speaking = False
        self.is_processing = False
        self.current_user_emotion: Optional[str] = None  # Last detected user emotion
        
        # Callbacks
        self._on_ready: Optional[Callable] = None
        self._on_audio: Optional[Callable[[bytes], None]] = None
        self._on_transcript: Optional[Callable[[str, bool], None]] = None
        self._on_ai_transcript: Optional[Callable[[str], None]] = None
        self._on_emotion: Optional[Callable[[str], None]] = None  # User emotion detected
        self._on_state_change: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_debug: Optional[Callable[[str], None]] = None
        
        # Threading
        self._ws_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def _log(self, message: str):
        """Internal logging with debug callback"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        if self._on_debug:
            self._on_debug(log_msg)
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID"""
        return str(uuid.uuid4())[:8]
    
    def _detect_emotion_from_text(self, text: str) -> Optional[str]:
        """
        Detect emotion from AI response text using keyword analysis.
        
        Returns: emotion string or None if neutral/unclear
        """
        text_lower = text.lower()
        
        # Happy indicators (Chinese + English)
        happy_keywords = [
            '哈哈', '嘻嘻', '开心', '高兴', '太好了', '棒', '真棒', '厉害',
            '恭喜', '祝贺', '欢迎', '期待', '兴奋', '太棒', '好玩', '有趣',
            '喜欢', '爱', '幸福', '快乐', '嘿嘿', '耶', '哇', '好耶',
            'haha', 'hehe', 'happy', 'great', 'awesome', 'wonderful', 'excited',
            '！！', '~~', '^_^', ':)', '😊', '😄', '🎉'
        ]
        
        # Sad indicators
        sad_keywords = [
            '难过', '伤心', '抱歉', '对不起', '遗憾', '可惜', '唉', '哎',
            '心疼', '同情', '理解你', '不容易', '辛苦', '委屈', '失望',
            'sorry', 'sad', 'unfortunately', 'regret',
            '呜', '...', '😢', '😔'
        ]
        
        # Angry indicators
        angry_keywords = [
            '生气', '愤怒', '讨厌', '烦', '可恶', '气死', '受不了',
            '不行', '不可以', '不允许', '警告', '注意', '严肃',
            'angry', 'annoyed', 'stop', 'warning',
            '！！！', '😠', '😤'
        ]
        
        # Surprised indicators
        surprised_keywords = [
            '哇', '天哪', '真的吗', '不会吧', '居然', '竟然', '没想到',
            '意外', '惊讶', '震惊', '吓', '啊', '诶', '咦',
            'wow', 'really', 'amazing', 'incredible', 'surprised', 'what',
            '？？', '?!', '！？', '😮', '😲', '🤯'
        ]
        
        # Count matches for each emotion
        scores = {
            'happy': sum(1 for kw in happy_keywords if kw in text_lower),
            'sad': sum(1 for kw in sad_keywords if kw in text_lower),
            'angry': sum(1 for kw in angry_keywords if kw in text_lower),
            'surprised': sum(1 for kw in surprised_keywords if kw in text_lower),
        }
        
        # Get emotion with highest score (minimum 1 match required)
        max_emotion = max(scores, key=scores.get)
        if scores[max_emotion] >= 1:
            self._log(f">>> DETECTED EMOTION: {max_emotion} (score: {scores[max_emotion]}) <<<")
            return max_emotion
        
        return None
    
    # === Callback Setters ===
    
    def on_ready(self, callback: Callable):
        """Called when connection is established and configured"""
        self._on_ready = callback
        return self
        
    def on_audio(self, callback: Callable[[bytes], None]):
        """Called when audio data is received from AI"""
        self._on_audio = callback
        return self
    
    def on_transcript(self, callback: Callable[[str, bool], None]):
        """Called when user speech is transcribed (text, is_final)"""
        self._on_transcript = callback
        return self
    
    def on_ai_transcript(self, callback: Callable[[str], None]):
        """Called when AI response text is received"""
        self._on_ai_transcript = callback
        return self
    
    def on_emotion(self, callback: Callable[[str], None]):
        """Called when user emotion is detected (angry, happy, neutral, sad, surprise)"""
        self._on_emotion = callback
        return self
    
    def on_state_change(self, callback: Callable[[str], None]):
        """Called when conversation state changes (idle, listening, thinking, speaking)"""
        self._on_state_change = callback
        return self
    
    def on_error(self, callback: Callable[[str], None]):
        """Called when an error occurs"""
        self._on_error = callback
        return self
    
    def on_debug(self, callback: Callable[[str], None]):
        """Called for debug logging"""
        self._on_debug = callback
        return self
    
    # === Connection Management ===
    
    def connect(self):
        """Establish WebSocket connection to Coze"""
        self._log("Connecting to Coze...")
        
        headers = [f"Authorization: Bearer {COZE_ACCESS_TOKEN}"]
        
        self.ws = websocket.WebSocketApp(
            COZE_WS_URL,
            header=headers,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close
        )
        
        # Run WebSocket in separate thread
        self._ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self._ws_thread.start()
    
    def _run_websocket(self):
        """Run WebSocket connection (blocking)"""
        self.ws.run_forever(ping_interval=30, ping_timeout=10)
    
    def disconnect(self):
        """Close the WebSocket connection"""
        self._log("Disconnecting...")
        if self.ws:
            self.ws.close()
        self.is_connected = False
        self.is_configured = False
    
    # === WebSocket Event Handlers ===
    
    def _on_ws_open(self, ws):
        """Handle WebSocket connection opened"""
        self._log("WebSocket connected!")
        self.is_connected = True
        # Connection will be fully ready after chat.created event
    
    def _on_ws_error(self, ws, error):
        """Handle WebSocket error"""
        error_msg = f"WebSocket error: {error}"
        self._log(error_msg)
        if self._on_error:
            self._on_error(error_msg)
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        self._log(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        self.is_configured = False
    
    def _on_ws_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            event_type = data.get("event_type", "unknown")
            
            # Route to appropriate handler
            handler_name = f"_handle_{event_type.replace('.', '_')}"
            handler = getattr(self, handler_name, None)
            if handler:
                handler(data)
            else:
                self._log(f"Unhandled event: {event_type}")
                
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse message: {e}")
        except Exception as e:
            import traceback
            self._log(f"Error handling message: {e}")
            self._log(traceback.format_exc())
    
    # === Downstream Event Handlers ===
    
    def _handle_chat_created(self, data):
        """Handle chat.created - connection established"""
        self._log("Chat session created")
        # Send initial configuration
        self._send_chat_config()
    
    def _handle_chat_updated(self, data):
        """Handle chat.updated - configuration confirmed"""
        self._log("Chat configuration updated")
        self.is_configured = True
        config = data.get("data", {})
        self.conversation_id = config.get("chat_config", {}).get("conversation_id")
        self._log(f"Conversation ID: {self.conversation_id}")
        
        if self._on_ready:
            self._on_ready()
        if self._on_state_change:
            self._on_state_change("idle")
    
    def _handle_conversation_chat_created(self, data):
        """Handle conversation.chat.created - new conversation turn started"""
        chat_data = data.get("data", {})
        self.current_chat_id = chat_data.get("id")
        self._log(f"Conversation turn started: {self.current_chat_id}")
        self.is_processing = True
        if self._on_state_change:
            self._on_state_change("thinking")
    
    def _handle_conversation_chat_in_progress(self, data):
        """Handle conversation.chat.in_progress - processing"""
        self._log("AI is processing...")
        self.is_processing = True
    
    def _handle_conversation_audio_delta(self, data):
        """Handle conversation.audio.delta - audio chunk received"""
        audio_data = data.get("data", {})
        
        # Audio is in 'content' field, not 'delta' field (Coze API quirk)
        audio_b64 = audio_data.get("content", "") or audio_data.get("delta", "")
        
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                if self._on_audio:
                    self._on_audio(audio_bytes)
            except Exception as e:
                self._log(f"Failed to decode audio: {e}")
        
        if not self.is_ai_speaking:
            self.is_ai_speaking = True
            self._log("AI started speaking")
            if self._on_state_change:
                self._on_state_change("speaking")
    
    def _handle_conversation_audio_sentence_start(self, data):
        """Handle conversation.audio.sentence_start - new sentence starting"""
        sentence_data = data.get("data", {})
        text = sentence_data.get("content", "")
        if text:
            # Detect emotion from AI response content
            emotion = self._detect_emotion_from_text(text)
            
            # Trigger emotion callback if emotion was detected
            if emotion and self._on_emotion:
                self._on_emotion(emotion)
            
            self._log(f"AI: {text}")
            if self._on_ai_transcript:
                self._on_ai_transcript(text)
    
    def _handle_conversation_audio_completed(self, data):
        """Handle conversation.audio.completed - audio finished"""
        self._log("AI audio completed")
        self.is_ai_speaking = False
        self.is_processing = False
        if self._on_state_change:
            self._on_state_change("idle")
    
    def _handle_conversation_message_delta(self, data):
        """Handle conversation.message.delta - text response chunk"""
        msg_data = data.get("data", {})
        content = msg_data.get("content", "")
        if content:
            # Detect emotion from text content
            emotion = self._detect_emotion_from_text(content)
            
            # Trigger emotion callback if emotion was detected
            if emotion and self._on_emotion:
                self._on_emotion(emotion)
            
            self._log(f"AI text: {content}")
    
    def _handle_conversation_message_completed(self, data):
        """Handle conversation.message.completed - full message received"""
        self._log("Message completed")
    
    def _handle_conversation_chat_completed(self, data):
        """Handle conversation.chat.completed - conversation turn finished"""
        self._log("Conversation turn completed")
        self.is_processing = False
        self.is_ai_speaking = False
        if self._on_state_change:
            self._on_state_change("idle")
    
    def _handle_conversation_chat_failed(self, data):
        """Handle conversation.chat.failed - conversation failed"""
        error_info = data.get("data", {})
        error_msg = f"Conversation failed: {error_info}"
        self._log(error_msg)
        self.is_processing = False
        if self._on_error:
            self._on_error(error_msg)
        if self._on_state_change:
            self._on_state_change("idle")
    
    def _handle_conversation_chat_canceled(self, data):
        """Handle conversation.chat.canceled - conversation was interrupted"""
        self._log("Conversation interrupted")
        self.is_ai_speaking = False
        self.is_processing = False
    
    def _handle_error(self, data):
        """Handle error event"""
        error_data = data.get("data", {})
        error_msg = f"Error: {error_data.get('msg', 'Unknown error')} (code: {error_data.get('code')})"
        self._log(error_msg)
        if self._on_error:
            self._on_error(error_msg)
    
    def _handle_input_audio_buffer_completed(self, data):
        """Handle input_audio_buffer.completed - audio submitted"""
        self._log("Audio buffer submitted")
    
    def _handle_input_audio_buffer_cleared(self, data):
        """Handle input_audio_buffer.cleared - buffer cleared"""
        self._log("Audio buffer cleared")
    
    def _handle_input_audio_buffer_speech_started(self, data):
        """Handle input_audio_buffer.speech_started - user started speaking (VAD)"""
        self._log("User started speaking")
        self.is_user_speaking = True
        
        # Interrupt AI if it's speaking
        if self.is_ai_speaking:
            self._log("Interrupting AI...")
            self.cancel_response()
        
        if self._on_state_change:
            self._on_state_change("listening")
    
    def _handle_input_audio_buffer_speech_stopped(self, data):
        """Handle input_audio_buffer.speech_stopped - user stopped speaking (VAD)"""
        self._log("User stopped speaking")
        self.is_user_speaking = False
        if self._on_state_change:
            self._on_state_change("thinking")
    
    def _handle_conversation_audio_transcript_update(self, data):
        """Handle conversation.audio_transcript.update - ASR interim results"""
        transcript_data = data.get("data", {})
        text = transcript_data.get("content", "")
        if text and self._on_transcript:
            self._on_transcript(text, False)
    
    def _handle_conversation_audio_transcript_completed(self, data):
        """Handle conversation.audio_transcript.completed - ASR final result"""
        transcript_data = data.get("data", {})
        text = transcript_data.get("content", "")
        
        # Log all keys in transcript data to see what Coze sends
        self._log(f"ASR data keys: {list(transcript_data.keys())}")
        
        # Try to get emotion from Coze ASR (if available)
        emotion = (transcript_data.get("emotion") or 
                   transcript_data.get("user_emotion") or
                   transcript_data.get("voice_emotion"))
        
        # If Coze didn't provide emotion, detect from user's text
        if not emotion and text:
            emotion = self._detect_emotion_from_text(text)
            if emotion:
                self._log(f">>> USER EMOTION (from text): {emotion} <<<")
        elif emotion:
            self._log(f">>> USER EMOTION (from Coze ASR): {emotion} <<<")
        
        # Update TTS emotion for empathetic AI response
        if emotion:
            self.current_user_emotion = emotion
            
            # Map user emotion to appropriate AI response emotion
            ai_emotion = self._get_empathetic_emotion(emotion)
            self._log(f">>> SETTING AI TTS TO: {ai_emotion} (responding to user's {emotion}) <<<")
            
            # Update TTS emotion for next AI response
            self.update_tts_emotion(ai_emotion)
            
            # Notify UI about user's emotion (for eye animation)
            if self._on_emotion:
                self._on_emotion(emotion)
        else:
            self._log(f"No emotion detected in user speech")
        
        self._log(f"User said: {text}")
        if text and self._on_transcript:
            self._on_transcript(text, True)
    
    def _handle_conversation_cleared(self, data):
        """Handle conversation.cleared - context cleared"""
        self._log("Conversation context cleared")
    
    def _handle_conversation_chat_requires_action(self, data):
        """Handle conversation.chat.requires_action - plugin/tool call needed"""
        action_data = data.get("data", {})
        self._log(f"Action required: {action_data}")
        # For now, we don't handle client-side plugins
    
    # === Upstream Commands ===
    
    def _send_event(self, event_type: str, data: Optional[Dict] = None):
        """Send an event to Coze"""
        if not self.is_connected or not self.ws:
            self._log(f"Cannot send {event_type}: not connected")
            return
            
        event = {
            "id": self._generate_event_id(),
            "event_type": event_type
        }
        if data:
            event["data"] = data
            
        try:
            self.ws.send(json.dumps(event))
        except Exception as e:
            self._log(f"Failed to send {event_type}: {e}")
    
    def _send_chat_config(self):
        """Send initial chat configuration"""
        config = {
            "chat_config": {
                "auto_save_history": True,
                "user_id": "remy_companion_user"
            },
            "input_audio": {
                "format": "pcm",
                "codec": "pcm",
                "sample_rate": AUDIO_SAMPLE_RATE,
                "channel": AUDIO_CHANNELS,
                "bit_depth": AUDIO_BIT_DEPTH
            },
            "output_audio": {
                "codec": "pcm",
                "pcm_config": {
                    "sample_rate": OUTPUT_SAMPLE_RATE,
                    "frame_size_ms": 100  # 100ms frames
                },
                "speech_rate": 0,  # Normal speed
                "loudness_rate": 0  # Normal volume
                # voice_id: Uses whatever voice is configured in Coze bot settings
                # For multi-emotion support, select a 多情感 voice in the bot settings:
                # e.g., 柔美女友（多情感）- ID: 7524987545197821971
            },
            "turn_detection": {
                "type": VAD_MODE,
                "silence_duration_ms": VAD_SILENCE_DURATION_MS,
                "prefix_padding_ms": VAD_PREFIX_PADDING_MS
            },
            "asr_config": {
                "stream_mode": "output_no_stream",  # Required for emotion detection
                "enable_emotion": True,  # Detect user emotions from voice
                # Supported emotions: angry, happy, neutral, sad, surprise
                "enable_ddc": True,  # Smooth out filler words
                "enable_punc": True,  # Add punctuation
            }
        }
        
        self._log(f"Sending config: VAD={VAD_MODE}, emotion_detection=enabled")
        self._send_event("chat.update", config)
    
    def send_audio(self, audio_data: bytes):
        """
        Stream audio data to Coze.
        Audio should be PCM format matching the configured sample rate.
        """
        if not self.is_connected or not self.is_configured:
            return
            
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        self._send_event("input_audio_buffer.append", {"delta": audio_b64})
    
    def commit_audio(self):
        """
        Commit the audio buffer (for client_interrupt mode).
        In server_vad mode, this is handled automatically.
        """
        self._send_event("input_audio_buffer.complete")
    
    def clear_audio_buffer(self):
        """Clear the audio input buffer"""
        self._send_event("input_audio_buffer.clear")
    
    def cancel_response(self):
        """Interrupt/cancel the current AI response"""
        self._send_event("conversation.chat.cancel")
        self.is_ai_speaking = False
    
    def clear_context(self):
        """Clear conversation context/history"""
        self._send_event("conversation.clear")
    
    def send_text_message(self, text: str, role: str = "user"):
        """
        Send a text message instead of audio.
        Useful for testing or text-based input.
        """
        self._send_event("conversation.message.create", {
            "role": role,
            "content_type": "text",
            "content": text
        })
    
    def synthesize_speech(self, text: str):
        """
        Have the AI speak a specific text without triggering a response.
        Useful for proactive messages.
        """
        self._send_event("input_text.generate_audio", {
            "mode": "text",
            "text": text
        })
    
    def update_tts_emotion(self, emotion: str):
        """
        Update the TTS emotion for the next AI response.
        
        Supported emotions: happy, sad, angry, surprised, neutral
        
        Note: Requires a multi-emotion voice (多情感音色) to be selected
        in Coze bot settings for this to have an effect.
        """
        # Map emotions to what Coze TTS expects
        emotion_map = {
            "happy": "happy",
            "sad": "sad",
            "angry": "angry",
            "surprised": "surprise",  # Coze uses "surprise" not "surprised"
            "neutral": "neutral",
        }
        
        coze_emotion = emotion_map.get(emotion.lower(), "neutral")
        
        self._log(f">>> UPDATING TTS EMOTION TO: {coze_emotion} <<<")
        
        # Send chat.update to change the TTS emotion
        config = {
            "output_audio": {
                "codec": "pcm",
                "pcm_config": {
                    "sample_rate": OUTPUT_SAMPLE_RATE,
                    "frame_size_ms": 100
                },
                "emotion_config": {
                    "emotion": coze_emotion
                }
            }
        }
        
        self._send_event("chat.update", config)
    
    def _get_empathetic_emotion(self, user_emotion: str) -> str:
        """
        Map user's emotion to an appropriate empathetic AI response emotion.
        
        - User happy → AI happy (share the joy)
        - User sad → AI sad (show empathy)  
        - User angry → AI neutral (stay calm)
        - User surprised → AI happy (share excitement)
        """
        empathy_map = {
            "happy": "happy",      # Share their joy
            "sad": "sad",          # Show empathy
            "angry": "neutral",    # Stay calm, don't escalate
            "surprised": "happy",  # Share the excitement
            "neutral": "neutral",
        }
        return empathy_map.get(user_emotion.lower(), "neutral")