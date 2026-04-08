# AI Receptionist System

A vision-guided conversational AI receptionist that detects visitors, engages in natural voice conversation, and manages visitor workflows — built with OpenAI GPT-4o, Whisper, and TTS.

## Features

**Vision-Based Detection:** YOLOv8 monitors your front entrance in real-time, automatically detecting when visitors arrive. No visitor list or buzzer needed.

**Natural Conversation:** GPT-4o powers context-aware dialogue that sounds human. The system asks for names, meeting purposes, and routes visitors intelligently while maintaining a professional tone.

**Full Voice I/O:** Visitors speak naturally; Whisper transcribes their speech. The AI responds via realistic OpenAI TTS voices, creating a seamless conversational experience without keyboards or touchscreens.

**Smart Notifications:** When a visitor arrives, the system sends instant email notifications to the target employee with visitor name, purpose, and arrival time.

**Professional Dashboard:** CustomTkinter-based kiosk interface with animated status indicators (breathing pulse for idle, ring pulse for listening, waveform for speaking) and live conversation logs.

**Zero-Setup Deployment:** Runs on laptop or dedicated hardware. Plug in a webcam, configure API keys, and launch. No external services or databases required.

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│                   AI RECEPTIONIST                     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Camera ──→ YOLOv8 Person Detection                  │
│                 ↓                                     │
│             Visitor Detected?                        │
│                 ↓                                     │
│  Microphone ──→ Whisper STT ──────┐                 │
│                                   ↓                 │
│                            GPT-4o Chat Engine        │
│                            (Context Aware)           │
│                                   ↓                 │
│  Speakers ←─── OpenAI TTS ←──────┘                 │
│                                                       │
│  Email ←─ Visitor Notifications                      │
│                                                       │
│  CustomTkinter GUI ─ Real-time Dashboard & Logs      │
│                                                       │
└──────────────────────────────────────────────────────┘
```

## Visitor Interaction Flow

1. **Detection:** Visitor walks into frame → YOLOv8 triggers
2. **Greeting:** AI speaks: "Hello! Welcome to [Company]. How can I help you?"
3. **Listen:** Microphone captures visitor's response (e.g., "Hi, I'm here for Jane Smith")
4. **Process:** Whisper transcribes, GPT-4o extracts name and purpose
5. **Respond:** AI speaks confirmation: "Great! Let me notify Jane that you're here."
6. **Notify:** Email sent to Jane: "Visitor John Doe is here for a meeting"
7. **Offer Help:** "Please have a seat. Jane will be right with you."
8. **End:** Conversation ends after confirmation or after N silent attempts

<!-- Insert flowchart image here -->
![AI Receptionist Flowchart](assets/media/flowchart.png)
## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/ai-receptionist-system.git
cd ai-receptionist-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your credentials:

```bash
cp .env.example .env
# Edit .env with your keys:
#   OPENAI_API_KEY=sk-...
#   SMTP_USER=your-email@gmail.com
#   SMTP_PASSWORD=app-password-here
```

Get your OpenAI API key: https://platform.openai.com/account/api-keys

### 3. Customize Settings

Edit `config/config.yaml`:

```yaml
office:
  name: "Your Company"
  welcome_message: "Welcome to {office_name}!"

employees:
  - name: "Jane Smith"
    email: "jane@company.com"
```

### 4. Run

```bash
python main.py
```

The dashboard opens. Point your webcam at the entrance and interact with arriving visitors.

## Configuration

### config/config.yaml

**Vision** — Camera and detection tuning:
- `camera_index`: Which camera to use (0 = default)
- `confidence_threshold`: Detection confidence (0.0-1.0, default 0.70)
- `min_bbox_ratio` / `max_bbox_ratio`: Person size thresholds
- `detection_cooldown`: Seconds between triggers (default 30)

**Conversation** — Chat behavior:
- `model`: GPT model to use (default gpt-4o)
- `max_tokens`: Response length for TTS (default 150)
- `temperature`: Creativity (0.0=exact, 1.0=creative; default 0.7)

**Speech Recognition** — Whisper settings:
- `silence_threshold`: Audio level to detect silence (default 500 RMS)
- `listen_timeout`: Max listening time per phrase (default 10s)
- `phrase_timeout`: Silence duration to end phrase (default 3s)

**Text-to-Speech** — OpenAI TTS:
- `voice`: Choose from alloy, echo, fable, onyx, nova, shimmer (default nova)
- `speed`: Playback speed 0.25x to 4.0x (default 1.0)

**Email** — Visitor notifications:
- `enabled`: true/false to send emails
- `smtp_host` / `smtp_port`: SMTP server
- `fallback_recipient`: Default email if employee not found

**GUI** — Dashboard appearance:
- `fullscreen`: true for kiosk mode, false for windowed
- `width` / `height`: Window dimensions
- `theme`: "dark" (recommended) or "light"

## GUI Dashboard

The dashboard provides real-time visual feedback:

### Animation States

| State | Animation | Meaning |
|-------|-----------|---------|
| **Idle** | Breathing blue circle | System ready, no visitor |
| **Listening** | Expanding green rings | Microphone active, capturing speech |
| **Talking** | Oscillating purple bars | Speaking TTS response |

### Display Elements

- **Status Line:** Current system state
- **Conversation Log:** All visitor ↔ AI exchanges in real-time
- **Visitor Info Panel:** Name, purpose, meeting target, detection confidence
- **Control Buttons:** Settings, Quit

## Project Structure

```
ai-receptionist-system/
├── src/
│   ├── gui/
│   │   ├── __init__.py
│   │   └── dashboard.py          # CustomTkinter GUI with animations
│   ├── vision/
│   │   └── detector.py           # YOLOv8 person detection
│   ├── conversation/
│   │   └── manager.py            # GPT-4o chat with context
│   ├── audio/
│   │   ├── speech_recognition.py # Whisper STT
│   │   └── tts.py                # OpenAI TTS playback
│   └── notifications/
│       └── email_notifier.py     # SMTP email sending
│
├── config/
│   └── config.yaml               # All system settings
│
├── docs/
│   └── architecture.md           # Detailed technical docs
│
├── main.py                       # Entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # API key template
├── .gitignore                    # Git exclusions
├── LICENSE                       # MIT License
└── README.md                     # This file
```

## How It Works

### Visitor Detection
YOLOv8 nano model runs inference on each camera frame (~30fps). When a person is detected with high confidence and proper size (not too close, not too far), a cooldown timer prevents immediate re-triggering.

### Conversation State Machine
1. **Detect** → Visitor in frame → Start conversation
2. **Listen** → Capture speech until silence detected
3. **Process** → Whisper transcribes; GPT-4o generates response
4. **Speak** → TTS plays response to visitor
5. **Loop** → Back to Listen (up to N turns or until hand-off complete)
6. **End** → Send notifications, log interaction, return to idle

### Multi-Turn Context
The conversation manager maintains history so the AI understands references like "yes, that's correct" without asking again. This creates natural dialogue flow.

### Email Routing
The system matches the visitor's stated purpose/target employee against your employee directory. Emails include visitor name, purpose, and a timestamp for efficient hand-offs.

## Hardware Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Webcam | 720p+ | USB or built-in; auto-focused preferred |
| Microphone | Standard audio device | USB headset or system mic fine |
| Speakers | Any | For TTS playback |
| Network | Stable internet | For OpenAI API calls (mostly upload-limited) |
| Compute | CPU-capable | YOLOv8n runs on CPU; GPU optional for speed |

**Tested Platforms:** macOS, Linux, Windows

## Key Design Decisions

### Why OpenAI Unified API?
Consolidating chat, STT, and TTS under one API key simplifies deployment and billing. No managing separate Stripe accounts or juggling credentials. One API, three capabilities.

### Why CustomTkinter?
Native tkinter is dated; CustomTkinter provides modern dark-mode UI that looks professional on a reception desk kiosk. Easy to customize, lightweight, cross-platform.

### Why YOLOv8 Nano?
Nano model is 6MB, runs on CPU at 30fps, and has strong accuracy for person detection. Larger models aren't necessary—you just need to know "person in frame?" Ultralytics auto-downloads and caches it on first run.

### Why Threaded GUI?
Separating GUI from the main detection/conversation loop prevents UI freezing. The dashboard updates smoothly while heavy operations (listening, API calls) happen in the background.

### Why Conversation History?
Maintaining context prevents awkward repeat questions. Multi-turn dialogue feels natural and reduces cognitive load on visitors.

## Performance

| Operation | Latency | Overhead |
|-----------|---------|----------|
| YOLOv8 inference (per frame) | 20–40ms | Minimal CPU (~10%) |
| Whisper transcription | 5–10s | Dependent on audio length |
| GPT-4o response generation | 1–3s | Depends on payload |
| TTS audio synthesis | 0.5–2s | Non-blocking |
| Email send | 1–2s | Async, doesn't block UI |

**Typical interaction time:** 8–15 seconds from "Hi!" to email sent.

**Throughput:** Roughly one visitor per minute in continuous operation.

## Troubleshooting

**No camera detected:**
- Check `camera_index` in config (try 0, 1, 2, ...)
- Verify camera permissions (esp. macOS/Linux)
- Try `python -m cv2` to test OpenCV

**Whisper times out:**
- Increase `listen_timeout` in config
- Check microphone levels
- Verify microphone is not muted

**API errors:**
- Confirm `OPENAI_API_KEY` is set and valid
- Check internet connection
- Monitor API quota at https://platform.openai.com/account/usage

**Emails not sending:**
- For Gmail: use app-specific password, not regular password
- Enable "Less secure apps" if not using 2FA
- Check `SMTP_USER` and `SMTP_PASSWORD` in .env

**Dashboard animations jerky:**
- Lower `animation_fps` in config if CPU is maxed
- Close other heavy applications

## License

MIT License. See LICENSE file for details.

---

**Author:** Muskaan Maheshwari  
**Status:** Production-ready portfolio project  
**Last Updated:** 2025-04-09
