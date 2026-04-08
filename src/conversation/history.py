"""Conversation history logging and management."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .engine import VisitorState

logger = logging.getLogger(__name__)


class ConversationLogger:
    """
    Logs visitor conversations to structured JSON files with daily rotation.
    Provides ability to retrieve recent conversation summaries for context.
    """

    def __init__(self, log_dir: str = "logs") -> None:
        """
        Initialize conversation logger.

        Args:
            log_dir: Directory to store conversation logs (default: "logs")
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        logger.info(f"ConversationLogger initialized with log dir: {self.log_dir}")

    def log_conversation(
        self, visitor_state: VisitorState, messages: list[dict]
    ) -> None:
        """
        Log a completed conversation to file.

        Args:
            visitor_state: Final state of the visitor interaction
            messages: Complete message history of conversation
        """
        # Get daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"conversations_{today}.jsonl"

        # Create conversation record
        record = {
            "timestamp": datetime.now().isoformat(),
            "visitor": {
                "name": visitor_state.visitor_name,
                "company": visitor_state.visitor_company,
                "purpose": visitor_state.purpose,
            },
            "interaction": {
                "meeting_with": visitor_state.meeting_with,
                "has_appointment": visitor_state.has_appointment,
                "package_needs_signature": visitor_state.package_needs_signature,
                "notes": visitor_state.notes,
            },
            "message_count": len(messages),
            "messages": self._sanitize_messages(messages),
        }

        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
            logger.info(f"Conversation logged to {log_file}")
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

    def get_recent_summary(self, n: int = 5) -> str:
        """
        Get summary of recent conversations for context.

        Args:
            n: Number of recent conversations to include

        Returns:
            Summary string of recent visitor interactions
        """
        conversations = []

        # Look for recent log files (today and yesterday)
        log_files = sorted(self.log_dir.glob("conversations_*.jsonl"), reverse=True)[:2]

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if conversations and len(conversations) >= n:
                            break
                        try:
                            record = json.loads(line)
                            conversations.append(record)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"Failed to read log file {log_file}: {e}")

        if not conversations:
            return "No recent conversations on record."

        # Build summary
        summary_lines = ["Recent visitor interactions:"]
        for i, conv in enumerate(conversations[:n], 1):
            visitor = conv.get("visitor", {})
            interaction = conv.get("interaction", {})
            name = visitor.get("name", "Unknown")
            purpose = visitor.get("purpose", "Unknown")
            meeting = interaction.get("meeting_with")

            line = f"{i}. {name or 'Unnamed'} - {purpose}"
            if meeting:
                line += f" (meeting with {meeting})"
            summary_lines.append(line)

        return "\n".join(summary_lines)

    def _sanitize_messages(self, messages: list[dict]) -> list[dict]:
        """
        Sanitize messages for logging (remove API keys, etc).

        Args:
            messages: Raw message history from conversation

        Returns:
            Sanitized message history
        """
        sanitized = []
        for msg in messages:
            msg_copy = msg.copy()
            # Remove system prompt details (too verbose)
            if msg.get("role") == "system":
                msg_copy["content"] = "[System prompt - context initialization]"
            sanitized.append(msg_copy)
        return sanitized
