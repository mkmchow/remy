"""
Configuration for Remy AI Desk Companion
"""
import os

# Coze API Credentials
# Get these from your Coze dashboard: https://www.coze.cn
# You can set via environment variables or replace the defaults below
COZE_ACCESS_TOKEN = os.environ.get(
    "COZE_ACCESS_TOKEN",
    "YOUR_ACCESS_TOKEN_HERE"  # Replace with your token
)
COZE_BOT_ID = os.environ.get(
    "COZE_BOT_ID", 
    "YOUR_BOT_ID_HERE"  # Replace with your bot ID
)

# Coze WebSocket endpoint (Chinese server)
COZE_WS_URL = f"wss://ws.coze.cn/v1/chat?bot_id={COZE_BOT_ID}"

# Audio Settings
AUDIO_SAMPLE_RATE = 24000  # Coze default
AUDIO_CHANNELS = 1  # Mono
AUDIO_BIT_DEPTH = 16
AUDIO_CHUNK_DURATION_MS = 100  # 100ms chunks
AUDIO_CHUNK_SIZE = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_DURATION_MS / 1000)  # samples per chunk

# Output audio settings
OUTPUT_SAMPLE_RATE = 24000
OUTPUT_CHANNELS = 1

# VAD Settings
VAD_MODE = "server_vad"  # server_vad for free conversation, client_interrupt for push-to-talk
VAD_SILENCE_DURATION_MS = 500  # How long silence before considering speech ended
VAD_PREFIX_PADDING_MS = 600  # Audio to include before speech detected

# UI Settings (3.5" Raspberry Pi display: 480x320 pixels)
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320
DEBUG_MODE = True
FPS = 60

# Colors (dark theme to match robot aesthetic)
BG_COLOR = (40, 40, 45)  # Dark gray
EYE_COLOR = (255, 140, 160)  # Soft pink/coral like the robot image
EYE_GLOW_COLOR = (255, 180, 190)
DEBUG_BG_COLOR = (30, 30, 35)
DEBUG_TEXT_COLOR = (150, 150, 150)

# Eye animation states
class EyeState:
    # Conversation states
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    BLINKING = "blinking"
    
    # Emotion states (from Coze ASR emotion detection)
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"  # Same as idle