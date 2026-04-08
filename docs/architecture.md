# AI Receptionist System - Architecture Document

## System Overview

The AI Receptionist is a vision-guided conversational AI system designed to detect visitors, engage them in natural voice conversation, and manage visitor workflows. It combines computer vision (YOLOv8), large language models (GPT-4o), and speech technologies (Whisper + TTS) into a unified, kiosk-deployable system.

The system operates as a state machine that cycles through visitor detection, conversation engagement, and notification delivery. All components communicate through the OpenAI API, eliminating the need for multiple service credentials.

## Module Breakdown

### 1. Vision Module (`src/vision/detector.py`)
**Responsibility:** Detect and track visitor presence in frame

- **Input:** Live video stream from webcam
- **Component:** YOLOv8 nano model for person detection
- **Output:** Bounding boxes, confidence scores, frame annotations
- **Key Features:**
  - Automatic model download on first run
  - Configurable confidence thresholds
  - Size filtering (min/max bbox ratio) to ignore distant/occluded people
  - Cooldown mechanism to prevent repeated triggers
  - Thread-safe frame processing

**Key Methods:**
- `detect(frame)` → list of detections with bboxes and confidence
- `annotate_frame(frame, detections)` → frame with drawn bboxes
- `should_trigger()` → boolean based on cooldown and detection quality

### 2. Conversation Engine (`src/conversation/manager.py`)
**Responsibility:** Manage multi-turn visitor conversations with context preservation

- **Input:** Transcribed visitor utterances
- **Component:** GPT-4o via OpenAI API
- **Output:** Natural language responses
- **Key Features:**
  - System prompt engineering for receptionist behavior
  - Conversation history tracking
  - Visitor information extraction (name, purpose, meeting)
  - Graceful handling of inaudible responses
  - Token budgeting to keep responses concise for TTS

**Key Methods:**
- `start_conversation()` → initialize state
- `process_utterance(text)` → generate response
- `extract_visitor_info()` → return gathered state dict
- `end_conversation()` → cleanup and return summary

**State Tracking:**
- `visitor_name` - extracted from conversation
- `visit_purpose` - why they're visiting
- `meeting_person` - who they want to meet
- `failure_count` - consecutive inaudible attempts

### 3. Speech Recognition (`src/audio/speech_recognition.py`)
**Responsibility:** Convert spoken audio to text

- **Input:** Audio from microphone (real-time stream)
- **Component:** OpenAI Whisper API
- **Output:** Transcribed text strings
- **Key Features:**
  - Adaptive silence detection (RMS threshold)
  - Phrase segmentation (auto-detect utterance boundaries)
  - Language specification support
  - Timeout protection
  - Error recovery

**Key Methods:**
- `listen()` → text transcription of one utterance
- `listen_with_timeout(duration)` → time-limited listening
- `detect_silence(audio_chunk)` → boolean

**Workflow:**
1. Record audio chunks from mic
2. Detect silence to identify phrase boundaries
3. Once silence threshold is crossed, send accumulated audio to Whisper
4. Return transcription

### 4. Text-to-Speech (`src/audio/tts.py`)
**Responsibility:** Convert text responses to spoken audio

- **Input:** Response text from conversation engine
- **Component:** OpenAI TTS API
- **Output:** Audio playback (speakers)
- **Key Features:**
  - Multiple voice options (nova, alloy, etc.)
  - Configurable speed (0.25x to 4.0x)
  - Real-time streaming playback
  - Error handling for audio devices

**Key Methods:**
- `speak(text)` → async audio playback
- `set_voice(voice_name)` → switch voices

### 5. Email Notification (`src/notifications/email_notifier.py`)
**Responsibility:** Send visitor notifications to target employees

- **Input:** Visitor info dict (name, purpose, meeting_person)
- **Component:** SMTP (Gmail or custom)
- **Output:** Email messages
- **Key Features:**
  - Fallback recipient if target email unavailable
  - Graceful failure (logs error, doesn't crash)
  - Optional enable/disable flag
  - HTML email templates

**Key Methods:**
- `notify_visitor_arrival(visitor_info)` → send email
- `is_enabled()` → check if email is configured

### 6. GUI Dashboard (`src/gui/dashboard.py`)
**Responsibility:** Display real-time status and conversation to staff/visitors

- **Framework:** CustomTkinter (modern, dark-mode capable)
- **Output:** Visual kiosk interface
- **Key Features:**
  - Three animation states: idle (breathing pulse), listening (ring pulse), talking (waveform)
  - Conversation log panel with scrolling
  - Real-time visitor info display
  - Professional dark theme
  - Fullscreen (kiosk) mode support
  - Runs in separate thread from main logic

**Animation States:**
- **IDLE:** Gentle breathing circle, soft blue, indicates standby
- **LISTENING:** Expanding concentric rings, green, microphone active
- **TALKING:** Oscillating waveform bars, purple, speaking response

**Thread Safety:** Uses a Queue for safe inter-thread communication

## Data Flow: Detection → Conversation → Notification

```
┌──────────────┐
│  Camera/Webcam
└───────┬──────┘
        │
        ▼
┌──────────────────────────┐
│  YOLOv8 Person Detection │
│  (config.vision)         │
└───────┬──────────────────┘
        │ confidence > threshold
        │ AND size filters match
        │ AND cooldown elapsed
        ▼
   ┌─────────────┐
   │  VISITOR    │ ◄─── Detected human in frame
   │  TRIGGERED  │      Starts conversation timer
   └──────┬──────┘
          │
          ▼
   ┌─────────────────┐
   │ START LISTENING │ ◄─── "Hello! How can I help?"
   └────────┬────────┘
            │
            ▼
   ┌──────────────────────────┐
   │  Whisper STT (Listen)    │
   │  (config.speech_recognition)
   └────────┬─────────────────┘
            │ "I'm here for Jane Smith"
            ▼
   ┌──────────────────────────┐
   │  GPT-4o Conversation     │
   │  Extract: name, purpose  │
   │  Generate: next response │
   └────────┬─────────────────┘
            │ "Great! Let me notify Jane"
            ▼
   ┌──────────────────────────┐
   │  OpenAI TTS (Speak)      │
   │  (config.tts)            │
   └────────┬─────────────────┘
            │
            ▼
   ┌──────────────────────────┐
   │  SMTP Email Notification │
   │  To: jane@example.com    │
   └────────┬─────────────────┘
            │
            ▼
   ┌──────────────────────────┐
   │  END CONVERSATION        │
   │  Update Dashboard Stats  │
   └──────────────────────────┘
```

## State Machine for Visitor Interactions

```
[IDLE]
  ↓ (person detected + cooldown elapsed)
[DETECTION TRIGGERED]
  ↓ (initialize conversation)
[LISTENING FOR GREETING]
  ↓ (user speaks)
[PROCESSING UTTERANCE]
  ├─ (speech successful)
  │   ↓ (generate response)
  │   [TALKING (TTS playing)]
  │   ↓ (response finished)
  │   [LISTENING FOR RESPONSE]
  │   ↓ (loop back to PROCESSING)
  │
  └─ (speech failed / silent)
      ↓ (failure_count++)
      ├─ (< max_failures)
      │   ↓ (prompt again)
      │   [LISTENING FOR RESPONSE]
      │
      └─ (>= max_failures)
          ↓ (extract available info, send notification)
          [END CONVERSATION]
```

## Configuration System

The system uses a hierarchical configuration approach:

1. **Default Values** (hardcoded in code)
2. **config/config.yaml** (user settings for deployment)
3. **Environment Variables** (runtime overrides, secrets)

Priority: Environment > YAML > Defaults

This allows sensitive data (API keys) to be injected at runtime without committing to repo, while maintaining user-friendly YAML for tuning.

## Threading Model

The application uses two main threads:

### Main Thread
- Runs the detection → conversation → notification loop
- Blocks on vision and audio operations
- Safe to have long operations (listening waits up to 10 seconds)

### GUI Thread
- CustomTkinter mainloop
- Started at app launch
- Communicates with main thread via Queue
- Receives state updates and logs messages

**Thread Safety:**
- Use `queue.Queue` for inter-thread communication
- GUI updates only via `after()` or queue polling
- No direct manipulation of tkinter widgets from main thread

## OpenAI API Usage

All three speech/language components use the same OpenAI API key:

| Component | Model | Endpoint | Cost Model |
|-----------|-------|----------|-----------|
| Chat | gpt-4o | /chat/completions | $0.005 input / $0.015 output per 1K tokens |
| STT | whisper-1 | /audio/transcriptions | $0.02 per minute audio |
| TTS | tts-1 or tts-1-hd | /audio/speech | $0.015 per 1K chars (tts-1) |

**Example costs per visitor interaction (3 conversational turns):**
- Whisper: ~3 minutes × 3 = 9 min = $0.18
- GPT-4o: ~300 tokens = $0.004
- TTS: ~150 chars × 3 = 450 chars = $0.007
- **Total per visitor: ~$0.19**

## Error Handling Strategy

The system is designed to be resilient to common failures:

### Vision Failures
- Camera disconnected → log warning, keep retrying
- Detection model failure → fall back to dummy detector

### Audio Failures
- Microphone unavailable → warn user, can't proceed
- Whisper API timeout → retry with shorter audio window
- Inaudible speech → increment failure counter, end after N failures

### Conversation Failures
- GPT-4o API error → retry with exponential backoff
- Malformed response → graceful degradation

### Notification Failures
- SMTP error → log but don't crash, conversation continues
- Email disabled → silently skip

### GUI Failures
- Dashboard crash → main loop continues
- Canvas rendering error → fallback to text status

## Deployment Considerations

### Kiosk Mode
Set `gui.fullscreen: true` in config.yaml to run in dedicated display mode. Useful for physical reception desk installations.

### Hardware Requirements
- **Webcam:** 720p minimum, USB or built-in
- **Microphone:** Any USB or system audio device
- **Speakers:** For TTS playback
- **Network:** Stable internet for OpenAI API calls
- **Compute:** Minimal (YOLOv8n is lightweight, runs on CPU fine)

### Performance Profile

| Operation | Latency | Notes |
|-----------|---------|-------|
| YOLOv8 detection | 20-40ms | Per frame at 30fps |
| Listen (Whisper) | 5-10s | Depends on audio length |
| GPT-4o response | 1-3s | Cold start higher |
| TTS synthesis | 0.5-2s | Depends on text length |
| Email send | 1-2s | Async, optional |

**Total user wait time:** ~8-15 seconds per interaction (mostly listening + TTS).

## Security Considerations

1. **API Key Protection:** Never commit .env; use environment variables
2. **Audio Privacy:** Audio is streamed to Whisper, not stored locally
3. **Visitor Data:** Conversation history stored locally; configure retention policy
4. **Network:** Requires HTTPS to OpenAI (built-in)
5. **Physical Access:** Running on public kiosk — don't store sensitive employee data in memory

## Future Enhancements

- Multi-language support (via config switch)
- Visitor photo capture (with consent) for team notifications
- Real-time translation (multilingual meetings)
- Integration with calendar APIs for smart routing
- Custom LLM fine-tuning for domain-specific language
- Facial recognition (opt-in) for returning visitors
