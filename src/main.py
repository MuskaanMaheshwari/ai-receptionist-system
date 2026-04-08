"""Main application entry point for the AI Receptionist system."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
import os

from vision.detector import PersonDetector
from conversation.engine import ConversationEngine
from conversation.history import ConversationLogger
from speech.listener import SpeechListener
from speech.speaker import SpeechSpeaker
from notifications.email_sender import EmailNotifier
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)


class ReceptionistApp:
    """
    Main application class that orchestrates all subsystems of the AI receptionist.

    Manages the complete visitor lifecycle:
    1. Vision: Detect person entering reception zone
    2. Greeting: Start warm conversation
    3. Listening: Transcribe visitor speech
    4. Conversation: Process with GPT-4o
    5. Speaking: Generate and play response
    6. Notification: Alert relevant employees
    7. Logging: Record interaction for analytics
    """

    def __init__(self) -> None:
        """Initialize all subsystems from configuration."""
        # Load configuration
        self.config = self._load_config()

        # Initialize logging
        setup_logging(
            log_dir=self.config.get("log_dir", "logs"),
            level=self.config.get("log_level", "INFO"),
        )

        logger.info("=" * 60)
        logger.info("AI Receptionist System Initializing")
        logger.info("=" * 60)

        # Initialize subsystems
        try:
            logger.info("Initializing vision detector...")
            self.detector = PersonDetector(self.config.get("vision", {}))

            logger.info("Initializing conversation engine...")
            self.engine = ConversationEngine(self.config.get("conversation", {}))

            logger.info("Initializing conversation logger...")
            self.history = ConversationLogger(log_dir=self.config.get("log_dir", "logs"))

            logger.info("Initializing speech listener...")
            self.listener = SpeechListener(self.config.get("speech", {}))

            logger.info("Initializing speech speaker...")
            self.speaker = SpeechSpeaker(self.config.get("speech", {}))

            logger.info("Initializing email notifier...")
            self.notifier = EmailNotifier(self.config.get("email", {}))

            logger.info("All subsystems initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize subsystems: {e}")
            raise

    def run(self) -> None:
        """
        Run the main application loop.

        Continuously monitors for visitors and handles complete interactions
        from detection through notification.
        """
        logger.info("AI Receptionist started. Waiting for visitors...")

        def on_person_detected() -> None:
            """Callback when person detected in reception zone."""
            logger.info("Person detected - starting visitor interaction")
            self._handle_visitor()

        try:
            self.detector.run_detection_loop(
                on_person_detected=on_person_detected,
                cooldown_seconds=self.config.get("detection_cooldown", 30.0),
            )
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        finally:
            self.shutdown()

    def _handle_visitor(self) -> None:
        """
        Handle a complete visitor interaction lifecycle.

        Flow:
        1. Start conversation and greet visitor
        2. Listen and process messages in a loop
        3. Generate responses using GPT-4o
        4. Speak responses to visitor
        5. Send notifications when conversation ends
        6. Log interaction and reset for next visitor
        """
        logger.info("Starting visitor interaction")

        try:
            # Start conversation and greet
            greeting = self.engine.start_conversation()
            logger.info(f"Greeting: {greeting}")
            self.speaker.speak(greeting)

            consecutive_failures = 0
            max_failures = 3

            # Main conversation loop
            while not self.engine.is_conversation_over():
                # Listen for visitor input
                logger.info("Listening for visitor input...")
                transcript = self.listener.listen(timeout=10.0, phrase_timeout=3.0)

                if transcript is None:
                    consecutive_failures += 1
                    logger.warning(
                        f"No audio detected ({consecutive_failures}/{max_failures})"
                    )

                    if consecutive_failures >= max_failures:
                        farewell = "I didn't catch that. No worries — feel free to come back if you need anything!"
                        logger.info(f"Max failures reached, farewell: {farewell}")
                        self.speaker.speak(farewell)
                        # Force conversation end
                        self.engine.state.conversation_over = True
                        break

                    sorry = "Sorry, I didn't quite catch that. Could you say that again?"
                    logger.info(f"Retry: {sorry}")
                    self.speaker.speak(sorry)
                    continue

                consecutive_failures = 0

                # Process message and get response
                logger.info(f"Processing: {transcript}")
                response = self.engine.process_message(transcript)

                # Speak response
                logger.info(f"Response: {response.text}")
                self.speaker.speak(response.text)

            # Send notifications
            logger.info("Conversation ended, sending notifications...")
            self._send_notifications()

            # Log the interaction
            state = self.engine.get_state()
            self.history.log_conversation(state, self.engine.messages)

        except Exception as e:
            logger.error(f"Error during visitor interaction: {e}")
        finally:
            # Reset for next visitor
            self.engine.reset()
            logger.info("Visitor interaction complete, system ready for next visitor")

    def _send_notifications(self) -> None:
        """
        Send appropriate notifications based on visitor interaction.

        - Meeting: Notify the employee the visitor is meeting
        - Delivery: Notify package recipient or office manager
        - Inquiry: Notify office manager or general inbox
        """
        state = self.engine.get_state()

        if state.purpose == "meeting" and state.meeting_with:
            logger.info(f"Sending meeting notification for {state.meeting_with}")

            # Find employee in directory
            for employee in self.config.get("conversation", {}).get("employee_directory", []):
                if employee.get("name", "").lower() == state.meeting_with.lower():
                    success = self.notifier.notify_employee(
                        employee_email=employee.get("email"),
                        employee_name=employee.get("name"),
                        visitor=state,
                    )
                    if success:
                        logger.info(f"Meeting notification sent to {employee.get('email')}")
                    break
            else:
                logger.warning(f"Employee '{state.meeting_with}' not found in directory")

        elif state.purpose == "delivery":
            logger.info("Sending delivery notification")

            # Notify office manager or default recipient
            default_email = self.config.get("email", {}).get("default_recipient")
            if default_email:
                success = self.notifier.notify_delivery(
                    recipient_email=default_email, visitor=state
                )
                if success:
                    logger.info(f"Delivery notification sent to {default_email}")

        elif state.purpose == "inquiry":
            logger.info("Sending inquiry notification")

            # Notify office manager
            manager_email = self.config.get("email", {}).get("office_manager_email")
            if manager_email:
                success = self.notifier.notify_inquiry(
                    recipient_email=manager_email, visitor=state
                )
                if success:
                    logger.info(f"Inquiry notification sent to {manager_email}")

    def _load_config(self) -> dict:
        """
        Load configuration from environment variables and config.yaml.

        Priority:
        1. .env file (for sensitive credentials)
        2. config.yaml (for structured configuration)
        3. Environment variables (override both)

        Returns:
            Merged configuration dictionary
        """
        # Load .env file
        load_dotenv()

        # Start with base config
        config = {
            "log_dir": "logs",
            "log_level": "INFO",
            "detection_cooldown": 30.0,
            "vision": {
                "camera_index": 0,
                "model_path": "yolov8n",
                "confidence_threshold": 0.70,
                "min_bbox_ratio": 0.05,
                "max_bbox_ratio": 0.15,
            },
            "conversation": {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "gpt_model": "gpt-4o",
                "office_name": "Tech Office",
                "employee_directory": [],
            },
            "speech": {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "mic_device_index": None,
                "sample_rate": 16000,
                "silence_threshold": 0.02,
                "language": "en",
                "voice": "nova",
                "model": "tts-1",
                "speed": 1.0,
            },
            "email": {
                "smtp_host": os.getenv("SMTP_HOST"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": os.getenv("SMTP_USER"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "from_address": os.getenv("EMAIL_FROM"),
                "office_name": "Tech Office",
            },
        }

        # Load YAML config if exists
        config_file = Path("config.yaml")
        if config_file.exists():
            logger.info(f"Loading configuration from {config_file}")
            try:
                with open(config_file) as f:
                    yaml_config = yaml.safe_load(f) or {}
                    # Deep merge
                    for key, value in yaml_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
            except Exception as e:
                logger.warning(f"Failed to load config.yaml: {e}")

        # Override with environment variables
        if os.getenv("OPENAI_API_KEY"):
            config["conversation"]["openai_api_key"] = os.getenv("OPENAI_API_KEY")
            config["speech"]["openai_api_key"] = os.getenv("OPENAI_API_KEY")

        logger.info("Configuration loaded successfully")
        logger.debug(f"Config: {config}")

        return config

    def shutdown(self) -> None:
        """Clean up resources and shutdown gracefully."""
        logger.info("Shutting down AI Receptionist...")

        try:
            if hasattr(self, "detector"):
                self.detector.release()
        except Exception as e:
            logger.warning(f"Error releasing detector: {e}")

        logger.info("AI Receptionist shutdown complete")


def main() -> int:
    """
    Application entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        app = ReceptionistApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\nShutdown requested")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
