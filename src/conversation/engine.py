"""Conversation engine using OpenAI GPT-4o with function calling for visitor state management."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from openai import OpenAI, APIError

logger = logging.getLogger(__name__)


@dataclass
class VisitorState:
    """Tracks the state of a visitor interaction."""

    purpose: Optional[str] = None  # "meeting" | "delivery" | "inquiry" | None
    visitor_name: Optional[str] = None
    visitor_company: Optional[str] = None
    meeting_with: Optional[str] = None
    has_appointment: Optional[bool] = None
    package_needs_signature: Optional[bool] = None
    conversation_over: bool = False
    notes: Optional[str] = None


@dataclass
class ConversationResponse:
    """Response from processing a user message."""

    text: str
    state: VisitorState
    conversation_over: bool


class ConversationEngine:
    """
    Brain of the AI receptionist system. Uses OpenAI GPT-4o with function calling
    to maintain natural conversation while tracking visitor state.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize conversation engine.

        Args:
            config: Configuration dict with keys:
                - openai_api_key: str, OpenAI API key
                - gpt_model: str, GPT model (default: "gpt-4o")
                - employee_directory: list[dict], list of employees with name, role, email
                - office_name: str, name of the office/company
        """
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.model = config.get("gpt_model", "gpt-4o")
        self.employee_directory = config.get("employee_directory", [])
        self.office_name = config.get("office_name", "our office")

        self.state = VisitorState()
        self.messages = []

        logger.info(f"ConversationEngine initialized with model {self.model}")

    def start_conversation(self) -> str:
        """
        Begin a new conversation with a visitor.

        Returns:
            The warm greeting message for the visitor.
        """
        self.state = VisitorState()
        self.messages = []

        # Build system prompt with context
        employee_list = ", ".join([f"{e.get('name')} ({e.get('role')})" for e in self.employee_directory])
        system_prompt = f"""You are a friendly, warm, and professional AI receptionist. You have a natural conversational style —
you're not robotic or overly formal. Think of yourself as that really helpful person at the front desk
who genuinely enjoys meeting people.

Your personality:
- Warm and welcoming, but not over-the-top
- Professional without being stiff
- You use natural language (contractions, casual phrases when appropriate)
- You have a gentle sense of humor
- You're attentive and remember details from the conversation
- You keep responses concise (1-3 sentences usually) since you're speaking out loud

Your responsibilities:
- Greet visitors warmly
- Determine their purpose (meeting someone, delivering a package, general inquiry)
- For meetings: get visitor's name, company, who they're meeting, if they have an appointment
- For deliveries: determine if signature is needed
- For inquiries: help with general questions about the office
- Once you have the needed information, let them know you'll notify the right person
- Say goodbye naturally

Context:
- Office: {self.office_name}
- Current time: {datetime.now().strftime('%A, %I:%M %p')}
- Team members: {employee_list if employee_list else 'Standard office team'}

Important:
- Always call the update_visitor_state function with your response and any new information you gather
- Don't ask for ALL information at once — have a natural conversation
- If someone seems confused or is just passing by, handle it gracefully
- Keep track of what you've already asked — don't repeat questions
"""

        self.messages.append({"role": "system", "content": system_prompt})

        # Get initial greeting from GPT
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages + [
                {
                    "role": "user",
                    "content": "[A visitor has just walked in. Greet them warmly.]",
                }
            ],
            tools=self._get_tools(),
            tool_choice="required",
        )

        return self._process_response(response)

    def process_message(self, user_message: str) -> ConversationResponse:
        """
        Process a user message and generate response.

        Args:
            user_message: The transcribed text from the visitor

        Returns:
            ConversationResponse with text, updated state, and conversation_over flag
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        logger.info(f"Processing message: {user_message[:100]}...")

        # Call GPT-4o with function calling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self._get_tools(),
                    tool_choice="required",
                    temperature=0.7,
                )

                result_text = self._process_response(response)

                return ConversationResponse(
                    text=result_text,
                    state=self.state,
                    conversation_over=self.state.conversation_over,
                )

            except APIError as e:
                logger.warning(f"API error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    logger.error("Max retries exceeded, returning default response")
                    return ConversationResponse(
                        text="I'm having a moment of trouble. Could you say that again?",
                        state=self.state,
                        conversation_over=False,
                    )
                # Wait before retry
                import time
                time.sleep(1 * (attempt + 1))

    def is_conversation_over(self) -> bool:
        """Check if conversation has ended."""
        return self.state.conversation_over

    def get_state(self) -> VisitorState:
        """Get current visitor state."""
        return self.state

    def reset(self) -> None:
        """Reset for next visitor."""
        self.state = VisitorState()
        self.messages = []
        logger.info("Conversation state reset for next visitor")

    def _process_response(self, response) -> str:
        """
        Process OpenAI response, handle tool calls, and update state.

        Args:
            response: The response from OpenAI API

        Returns:
            The text response to speak to visitor
        """
        # Add assistant response to message history
        self.messages.append({"role": "assistant", "content": response.content})

        # Process tool calls
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "update_visitor_state":
                    tool_args = json.loads(tool_call.function.arguments)
                    self._update_state_from_function(tool_args)
                    logger.debug(f"State updated: {asdict(self.state)}")

                    # Add tool result to messages
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": "State updated successfully",
                        }
                    )

        # Extract the response text (usually in response.content or first tool call)
        if response.content:
            return response.content
        elif response.tool_calls:
            # Text is in the function call arguments
            for tool_call in response.tool_calls:
                if tool_call.function.name == "update_visitor_state":
                    args = json.loads(tool_call.function.arguments)
                    return args.get("response", "")
        return "I'm here to help! What brings you in today?"

    def _update_state_from_function(self, args: dict) -> None:
        """
        Update visitor state from function call arguments.

        Args:
            args: Arguments from update_visitor_state function call
        """
        if "purpose" in args and args["purpose"]:
            self.state.purpose = args["purpose"]
        if "visitor_name" in args and args["visitor_name"]:
            self.state.visitor_name = args["visitor_name"]
        if "visitor_company" in args and args["visitor_company"]:
            self.state.visitor_company = args["visitor_company"]
        if "meeting_with" in args and args["meeting_with"]:
            self.state.meeting_with = args["meeting_with"]
        if "has_appointment" in args:
            self.state.has_appointment = args["has_appointment"]
        if "package_needs_signature" in args:
            self.state.package_needs_signature = args["package_needs_signature"]
        if "conversation_over" in args:
            self.state.conversation_over = args["conversation_over"]
        if "notes" in args and args["notes"]:
            self.state.notes = args["notes"]

    def _get_tools(self) -> list[dict]:
        """
        Define the function calling tools for GPT.

        Returns:
            List of tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "update_visitor_state",
                    "description": "Update the visitor tracking state and provide your spoken response",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "response": {
                                "type": "string",
                                "description": "Your spoken response to the visitor",
                            },
                            "purpose": {
                                "type": "string",
                                "enum": ["meeting", "delivery", "inquiry"],
                                "description": "Purpose of visit",
                            },
                            "visitor_name": {
                                "type": "string",
                                "description": "Name of the visitor",
                            },
                            "visitor_company": {
                                "type": "string",
                                "description": "Company the visitor is from",
                            },
                            "meeting_with": {
                                "type": "string",
                                "description": "Name of person they're here to see",
                            },
                            "has_appointment": {
                                "type": "boolean",
                                "description": "Whether visitor has a scheduled appointment",
                            },
                            "package_needs_signature": {
                                "type": "boolean",
                                "description": "Whether the package requires a signature",
                            },
                            "conversation_over": {
                                "type": "boolean",
                                "description": "True if the conversation has naturally concluded",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Any additional notes about the visit",
                            },
                        },
                        "required": ["response", "conversation_over"],
                    },
                },
            }
        ]
