"""Speech-to-text module using OpenAI Whisper API."""

from __future__ import annotations

import io
import logging
import wave
from typing import Optional

import sounddevice as sd
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class SpeechListener:
    """
    Captures audio from microphone and transcribes it using OpenAI Whisper API.
    Handles silence detection to know when the speaker is done.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize speech listener.

        Args:
            config: Configuration dict with keys:
                - openai_api_key: str, OpenAI API key
                - mic_device_index: int, microphone device index (default: None = default device)
                - sample_rate: int, audio sample rate (default: 16000)
                - silence_threshold: float, volume threshold for silence (default: 0.02)
                - language: str, language code (default: "en")
        """
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.mic_device_index = config.get("mic_device_index", None)
        self.sample_rate = config.get("sample_rate", 16000)
        self.silence_threshold = config.get("silence_threshold", 0.02)
        self.language = config.get("language", "en")

        logger.info(
            f"SpeechListener initialized (sample_rate={self.sample_rate}, "
            f"device={self.mic_device_index})"
        )

    def listen(self, timeout: float = 10.0, phrase_timeout: float = 3.0) -> Optional[str]:
        """
        Listen for audio from microphone and transcribe using Whisper.

        Records audio until silence is detected or timeout is reached.
        Uses phrase_timeout to detect when speaker is done (3 seconds of silence).

        Args:
            timeout: Maximum time to listen in seconds (default: 10.0)
            phrase_timeout: Time of silence to consider phrase complete (default: 3.0)

        Returns:
            Transcribed text, or None if no speech detected
        """
        logger.info(f"Listening for audio (timeout={timeout}s, phrase_timeout={phrase_timeout}s)")

        audio_data = self._record_audio(timeout, phrase_timeout)

        if audio_data is None:
            logger.info("No audio recorded")
            return None

        # Transcribe using Whisper API
        try:
            logger.info("Sending audio to Whisper API for transcription")
            transcript = self._transcribe_audio(audio_data)

            if transcript:
                logger.info(f"Transcription: {transcript}")
            else:
                logger.info("Whisper returned empty transcription")

            return transcript

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def _record_audio(
        self, timeout: float = 10.0, phrase_timeout: float = 3.0
    ) -> Optional[bytes]:
        """
        Record audio from microphone with silence detection.

        Args:
            timeout: Maximum recording time in seconds
            phrase_timeout: Time of silence to stop recording

        Returns:
            Audio data as WAV bytes, or None if no audio detected
        """
        import time

        frames = []
        silent_chunks = 0
        silent_chunks_threshold = int(phrase_timeout * self.sample_rate / 1024)
        start_time = time.time()

        logger.info("Starting audio recording")

        try:
            with sd.InputStream(
                device=self.mic_device_index,
                samplerate=self.sample_rate,
                channels=1,
                blocksize=1024,
            ) as stream:
                while True:
                    # Check timeout
                    if time.time() - start_time > timeout:
                        logger.info("Recording timeout reached")
                        break

                    # Read audio chunk
                    data, overflowed = stream.read(1024)
                    if overflowed:
                        logger.warning("Audio buffer overflow")

                    frames.append(data)

                    # Detect silence
                    volume = np.abs(data).mean()
                    if volume < self.silence_threshold:
                        silent_chunks += 1
                        if silent_chunks >= silent_chunks_threshold:
                            logger.info("Silence detected, stopping recording")
                            break
                    else:
                        silent_chunks = 0

        except Exception as e:
            logger.error(f"Error during audio recording: {e}")
            return None

        if not frames:
            logger.info("No audio frames recorded")
            return None

        # Convert frames to audio bytes
        audio_data = np.concatenate(frames)

        # Convert to WAV format in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())

        wav_data = wav_buffer.getvalue()
        logger.info(f"Recorded {len(wav_data)} bytes of audio")

        return wav_data

    def _transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            audio_data: Audio data as WAV bytes

        Returns:
            Transcribed text, or None if transcription fails
        """
        try:
            # Create BytesIO object for API
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"

            # Call Whisper API
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=self.language,
            )

            transcript = response.text.strip()
            return transcript if transcript else None

        except Exception as e:
            logger.error(f"Whisper API error: {e}")
            return None
