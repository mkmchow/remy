# Remy - AI Desk Companion

A real-time voice AI desk companion using Coze's WebSocket API with animated eyes display.

![Remy](https://img.shields.io/badge/Platform-Raspberry%20Pi-red) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## Features

- 🎤 **Real-time voice conversation** with Coze AI
- 👀 **Animated eyes** that react to emotions (happy, sad, angry, surprised)
- 🔊 **Server-side VAD** - efficient voice activity detection
- ⚡ **Interruption support** - interrupt the AI mid-sentence
- 🎭 **Emotion detection** - from both user speech and AI responses
- 📱 **Compact UI** - designed for 3.5" Raspberry Pi display (480x320)

## Demo

The UI displays animated pink eyes that:
- Blink naturally
- Change shape based on detected emotions
- Pulse when speaking
- Show conversation state (idle, listening, thinking, speaking)

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Edit `config.py` and add your Coze credentials:
```python
COZE_ACCESS_TOKEN = "your_token_here"
COZE_BOT_ID = "your_bot_id_here"
```

### 3. Run

```bash
python main.py
```

## Files

| File | Description |
|------|-------------|
| `main.py` | Main application entry point |
| `config.py` | Configuration and credentials |
| `coze_client.py` | WebSocket client for Coze real-time API |
| `audio_handler.py` | Microphone capture and speaker playback |
| `ui_eyes.py` | Pygame-based animated eyes UI |

## Controls

- **Space** - Toggle UI visibility (show only eyes)
- **ESC** - Exit
- **Click emotion buttons** - Test different eye expressions
- **Click arrow** - Expand/collapse debug log

## Configuration

### Audio Settings (in `config.py`)
- `AUDIO_SAMPLE_RATE`: Input sample rate (default: 24000Hz)
- `OUTPUT_SAMPLE_RATE`: Output sample rate (default: 24000Hz)

### UI Settings
- `WINDOW_WIDTH`: 480 (for 3.5" Pi display)
- `WINDOW_HEIGHT`: 320
- `DEBUG_MODE`: Show debug log

### Voice Settings
Configure in Coze bot settings:
- Select a multi-emotion voice (多情感) for expressive TTS
- Set up system prompt for personality

## Raspberry Pi Setup

1. Install Raspberry Pi OS
2. Enable audio (USB microphone + speaker recommended)
3. Install Python dependencies
4. Run with `python main.py`

The UI is designed for 480x320 resolution (3.5" display).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      main.py                            │
│                   (Orchestrator)                        │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────────┐ ┌───────────┐ ┌───────────────┐
│ coze_client   │ │  audio    │ │   ui_eyes     │
│ (WebSocket)   │ │ (PyAudio) │ │  (Pygame)     │
└───────────────┘ └───────────┘ └───────────────┘
        │             │             │
        ▼             ▼             ▼
   Coze API      Microphone     Display
                 Speaker
```

## Emotion System

The eyes react to emotions detected from:
1. **AI response content** - Keywords trigger emotions
2. **Conversation state** - Listening, thinking, speaking

Emotions auto-reset to neutral after 5 seconds of idle.

## Related Projects

- [Remy RTC](../Remy%20RTC) - RTC version for browser-based testing

## License

MIT
