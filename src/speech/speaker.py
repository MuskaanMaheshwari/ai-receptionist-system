"""Text-to-speech module using OpenAI TTS API."""

from __future__ import annotations

import io
import logging
import tempfile
from typing import Callable, Optional

import pygame.mixer
from openai import OpenAI

logger = logging.getLogger(__name__)


class SpeechSpeaker:
    """
    Generates speech from text using OpenAI TTS API and plays it through speakers.
    Supports callbacks for animation state changes (e.g., mouth movement).
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize speech speaker.

        Args:
            config: Configuration dict with keys:
                - openai_api_key: str, OpenAI API key
                - voice: str, voice to use (default: "nova")
                  Options: "alloy", "echo", "fable", "onyx", "nova", "shimmer"
                - model: str, TTS model (default: "tts-1")
                  Options: "tts-1" (fast), "tts-1-hd" (high quality)
                - speed: float, speech speed 0.25-4.0 (default: 1.0)
        """
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.voice = config.get("voice", "nova")  # warm, friendly female voice
        self.model = config.get("model", "tts-1")
        self.speed = config.get("speed", 1.0)

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
            logger.info("Pygame mixer initialized")
        except Exception as e:
            logger.warning(f"Pygame mixer initialization warning: {e}")

        logger.info(
            f"SpeechSpeaker initialized (voice={self.voice}, model={self.model}, "
            f"speed={self.speed})"
        )

    def speak(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_end: Optional[Callable[[], None]] = None,
    ) -> bool:
        """
        Generate speech from text and play it.

        Calls on_start() before playing (for UI state like opening mouth)
        and on_end() after playing (for closing mouth, returning to idle).

        Args:
            text: Text to speak
            on_start: Optional callback invoked before playback
            on_end: Optional callback invoked after playback

        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to speak()")
            return False

        logger.info(f"Generating speech for: {text[:100]}...")

        try:
            # Generate audio
            audio_data = self._generate_audio(text)
            if audio_data is None:
                return False

            # Call on_start callback
            if on_start:
                try:
                    on_start()
                except Exception as e:
                    logger.warning(f"on_start callback error: {e}")

            # Play audio
            success = self._play_audio(audio_data)

            # Call on_end callback
            if on_end:
                try:
                    on_end()
                except Exception as e:
                    logger.warning(f"on_end callback error: {e}")

            return success

        except Exception as e:
            logger.error(f"Speech generation/playback failed: {e}")
            return False

    def _generate_audio(self, text: str) -> Optional[bytes]:
        """
        Generate audio using OpenAI TTS API.

        Args:
            text: Text to convert to speech

        Returns:
            Audio data as bytes (MP3 format), or None if generation fails
        """
        try:
            logger.debug(f"Calling TTS API (voice={self.voice}, model={self.model})")

            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="mp3",
                speed=self.speed,
            )

            audio_data = response.content
            logger.info(f"Generated {len(audio_data)} bytes of audio")
            return audio_data

        except Exception as e:
            logger.error(f"TTS API error: {e}")
            return None

    def _play_audio(self, audio_data: bytes) -> bool:
        """
        Play audio data through speakers.

        Args:
            audio_data: Audio data as bytes (MP3 format)

        Returns:
            True if playback successful, False otherwise
        """
        try:
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            logger.info(f"Playing audio from {temp_path}")

            # Load and play audio
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                import time
                time.sleep(0.1)

            logger.info("Audio playback completed")

            # Cleanup
            import os
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

            return True

        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            return False

    def set_voice(self, voice: str) -> None:
        """
        Change the voice for subsequent calls.

        Args:
            voice: Voice name ("alloy", "echo", "fable", "onyx", "nova", "shimmer")
        """
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice in valid_voices:
            self.voice = voice
            logger.info(f"Voice changed to {voice}")
        else:
            logger.warning(f"Invalid voice {voice}, keeping {self.voice}")

    def set_speed(self, speed: float) -> None:
        """
        Change the speech speed for subsequent calls.

        Args:
            speed: Speed multiplier 0.25-4.0
        """
        if 0.25 <= speed <= 4.0:
            self.speed = speed
            logger.info(f"Speech speed changed to {speed}")
        else:
            logger.warning(f"Invalid speed {speed}, must be 0.25-4.0")
