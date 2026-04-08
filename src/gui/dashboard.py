"""
CustomTkinter-based GUI dashboard for AI Receptionist System.
Provides a professional kiosk-style interface with real-time animations and status updates.
"""

import customtkinter as ctk
from tkinter import Canvas
import threading
from queue import Queue
import math


class ReceptionistDashboard:
    """Professional kiosk-style dashboard with animated status indicators."""

    def __init__(self, config: dict):
        """
        Initialize the dashboard.

        Args:
            config: Dictionary with GUI configuration (fullscreen, width, height, theme, animation_fps)
        """
        self.config = config
        self.root = ctk.CTk()
        self.root.title("AI Receptionist")

        # Set window mode
        if config.get("fullscreen", False):
            self.root.attributes("-fullscreen", True)
        else:
            width = config.get("width", 1024)
            height = config.get("height", 768)
            self.root.geometry(f"{width}x{height}")

        # Theme setup
        ctk.set_appearance_mode(config.get("theme", "dark"))
        ctk.set_default_color_theme("blue")

        # Animation state
        self.state = "idle"  # idle, listening, talking
        self.animation_frame = 0
        self.animation_fps = config.get("animation_fps", 30)
        self.animation_running = False

        # Thread-safe queue for updates
        self.update_queue = Queue()

        # Build UI
        self._build_ui()

        # Start animation loop
        self._start_animation()

    def _build_ui(self):
        """Construct the main dashboard layout."""
        # Main container
        main_frame = ctk.CTkFrame(self.root, fg_color="#1a1a2e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="AI RECEPTIONIST",
            font=("Helvetica", 32, "bold"),
            text_color="white",
        )
        title.pack(pady=(0, 20))

        # Animation canvas
        canvas_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e")
        canvas_frame.pack(fill="x", pady=(0, 20))

        self.canvas = Canvas(
            canvas_frame,
            width=300,
            height=200,
            bg="#1a1a2e",
            highlightthickness=0,
            cursor="arrow",
        )
        self.canvas.pack(anchor="center")

        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Status: Initializing...",
            font=("Helvetica", 14),
            text_color="#4A9BD9",
        )
        self.status_label.pack(pady=(0, 15))

        # Conversation log with scrolling
        log_label = ctk.CTkLabel(
            main_frame, text="Conversation Log", font=("Helvetica", 12, "bold"),
            text_color="white"
        )
        log_label.pack(anchor="w", pady=(10, 5))

        log_frame = ctk.CTkFrame(main_frame, fg_color="#262641")
        log_frame.pack(fill="both", expand=True, pady=(0, 15))

        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=("Courier", 10),
            fg_color="#262641",
            text_color="white",
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Visitor info panel
        info_label = ctk.CTkLabel(
            main_frame,
            text="Visitor Information",
            font=("Helvetica", 12, "bold"),
            text_color="white",
        )
        info_label.pack(anchor="w", pady=(10, 5))

        info_frame = ctk.CTkFrame(main_frame, fg_color="#262641")
        info_frame.pack(fill="x")

        self.info_text = ctk.CTkLabel(
            info_frame,
            text="Waiting for visitor...",
            font=("Courier", 10),
            text_color="#A0A0A0",
            justify="left",
        )
        self.info_text.pack(fill="x", padx=10, pady=10, anchor="w")

        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e")
        button_frame.pack(fill="x", pady=(20, 0))

        settings_btn = ctk.CTkButton(
            button_frame,
            text="Settings",
            font=("Helvetica", 12),
            fg_color="#4A9BD9",
            hover_color="#357ABD",
        )
        settings_btn.pack(side="left", padx=10)

        quit_btn = ctk.CTkButton(
            button_frame,
            text="Quit",
            font=("Helvetica", 12),
            fg_color="#4A4A6A",
            hover_color="#5A5A7A",
            command=self.shutdown,
        )
        quit_btn.pack(side="right", padx=10)

    def _start_animation(self):
        """Start the animation loop."""
        self.animation_running = True
        self._animate()

    def _animate(self):
        """Animation loop called at configured FPS."""
        if not self.animation_running:
            return

        self.animation_frame += 1
        self._draw_animation()

        # Schedule next frame
        interval = int(1000 / self.animation_fps)
        self.root.after(interval, self._animate)

    def _draw_animation(self):
        """Draw animation based on current state."""
        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        # Default canvas size if not yet rendered
        if width <= 1:
            width = 300
        if height <= 1:
            height = 200

        center_x = width / 2
        center_y = height / 2

        if self.state == "idle":
            self._draw_idle(center_x, center_y)
        elif self.state == "listening":
            self._draw_listening(center_x, center_y)
        elif self.state == "talking":
            self._draw_talking(center_x, center_y)

    def _draw_idle(self, cx: float, cy: float):
        """Draw gentle breathing circle animation."""
        # Breathing pulse: scales from 0.8 to 1.2
        pulse = math.sin(self.animation_frame * 0.03) * 0.2 + 1.0
        radius = 50 * pulse

        # Draw circle with soft gradient (approximated with color)
        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill="#4A9BD9",
            outline="#3A7BA9",
            width=2,
        )

        # Add center dot
        self.canvas.create_oval(
            cx - 8, cy - 8, cx + 8, cy + 8, fill="#E0E0E0", outline="#4A9BD9"
        )

    def _draw_listening(self, cx: float, cy: float):
        """Draw pulsing concentric rings expanding outward."""
        max_rings = 4
        max_radius = 80

        for ring in range(max_rings):
            # Calculate ring properties with wave animation
            phase = (self.animation_frame - ring * 15) * 0.05
            progress = (phase % (2 * math.pi)) / (2 * math.pi)

            # Rings expand and fade
            radius = max_radius * progress
            if radius < 10:
                radius = 10

            # Fade out as they expand
            alpha = int(255 * (1.0 - progress))
            color = f"#{alpha:02x}{76 + int(50 * progress):02x}{240:02x}"  # Green tint

            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=color,
                width=2,
            )

        # Central circle (steady)
        self.canvas.create_oval(
            cx - 20, cy - 20, cx + 20, cy + 20, fill="#4CAF50", outline="#2D8A3A"
        )

    def _draw_talking(self, cx: float, cy: float):
        """Draw animated waveform bars."""
        bar_count = 8
        bar_width = 20
        bar_spacing = 30
        start_x = cx - (bar_count * bar_spacing) / 2

        for i in range(bar_count):
            # Each bar oscillates at slightly different phase
            phase = self.animation_frame * 0.1 + i * 0.4
            height = abs(math.sin(phase)) * 60 + 20

            x1 = start_x + i * bar_spacing
            y1 = cy - height / 2
            y2 = cy + height / 2

            self.canvas.create_rectangle(
                x1,
                y1,
                x1 + bar_width - 5,
                y2,
                fill="#9C27B0",
                outline="#7A1FA0",
                width=1,
            )

    def set_idle(self):
        """Set dashboard to idle state."""
        self.state = "idle"
        self.update_status("Status: Idle")

    def set_listening(self):
        """Set dashboard to listening state."""
        self.state = "listening"
        self.update_status("Status: Listening...")

    def set_talking(self):
        """Set dashboard to talking state."""
        self.state = "talking"
        self.update_status("Status: Responding...")

    def update_status(self, text: str):
        """Update the status label."""
        self.status_label.configure(text=text)

    def update_visitor_info(self, state: dict):
        """
        Update visitor information panel.

        Args:
            state: Dictionary with keys like name, purpose, meeting_with, confidence
        """
        lines = []

        if "name" in state and state["name"]:
            lines.append(f"Name: {state['name']}")

        if "purpose" in state and state["purpose"]:
            lines.append(f"Purpose: {state['purpose']}")

        if "meeting_with" in state and state["meeting_with"]:
            lines.append(f"Meeting: {state['meeting_with']}")

        if "confidence" in state:
            lines.append(f"Detection: {state['confidence']:.1%}")

        info_text = "\n".join(lines) if lines else "Waiting for visitor..."
        self.info_text.configure(text=info_text)

    def log_message(self, role: str, text: str):
        """
        Add a message to the conversation log.

        Args:
            role: "Visitor" or "AI"
            text: Message content
        """
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{role}: {text}\n\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def run(self):
        """Start the GUI mainloop (runs in separate thread)."""
        self.root.mainloop()

    def shutdown(self):
        """Cleanup and close the dashboard."""
        self.animation_running = False
        self.root.quit()
        self.root.destroy()

    def process_queue(self):
        """Process any pending updates from the main thread."""
        try:
            while True:
                action, args = self.update_queue.get_nowait()
                if action == "status":
                    self.update_status(args)
                elif action == "visitor_info":
                    self.update_visitor_info(args)
                elif action == "log_message":
                    self.log_message(*args)
                elif action == "state":
                    self.state = args
        except:
            pass
