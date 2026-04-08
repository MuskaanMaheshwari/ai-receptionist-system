"""Email notification system for visitor alerts."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from ..conversation.engine import VisitorState

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Sends email notifications to employees when visitors arrive,
    packages are delivered, or inquiries need attention.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize email notifier.

        Args:
            config: Configuration dict with keys:
                - smtp_host: str, SMTP server hostname
                - smtp_port: int, SMTP server port (default: 587)
                - smtp_user: str, SMTP username/email
                - smtp_password: str, SMTP password
                - from_address: str, sender email address
                - office_name: str, name of office/company
        """
        self.smtp_host = config.get("smtp_host")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_user = config.get("smtp_user")
        self.smtp_password = config.get("smtp_password")
        self.from_address = config.get("from_address", self.smtp_user)
        self.office_name = config.get("office_name", "Our Office")

        # Validate configuration
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning("Email configuration incomplete - notifications disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"EmailNotifier initialized (smtp_host={self.smtp_host})")

    def notify_employee(
        self, employee_email: str, employee_name: str, visitor: VisitorState
    ) -> bool:
        """
        Send meeting notification to an employee.

        Args:
            employee_email: Email address of the employee
            employee_name: Name of the employee
            visitor: Visitor state with details

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email notifications disabled")
            return False

        subject = f"Visitor Alert: {visitor.visitor_name or 'Guest'} at {self.office_name}"

        # Build email body
        company_info = f" from {visitor.visitor_company}" if visitor.visitor_company else ""
        appointment_status = (
            "has an appointment"
            if visitor.has_appointment
            else "doesn't have an appointment"
        )

        body = f"""
Hi {employee_name},

A visitor has arrived to meet with you!

VISITOR DETAILS:
• Name: {visitor.visitor_name or 'Not provided'}
• Company: {visitor.visitor_company or 'Not provided'}
• Appointment: {appointment_status}
• Time: {datetime.now().strftime('%I:%M %p')}

Additional Notes: {visitor.notes or 'None'}

Please proceed to the reception area to meet your visitor.

Best regards,
{self.office_name} AI Receptionist
"""

        return self._send_email(employee_email, subject, body)

    def notify_delivery(self, recipient_email: str, visitor: VisitorState) -> bool:
        """
        Send delivery notification.

        Args:
            recipient_email: Email address to notify
            visitor: Visitor/package state with details

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email notifications disabled")
            return False

        subject = f"Delivery Received at {self.office_name}"

        signature_req = (
            "Signature required"
            if visitor.package_needs_signature
            else "No signature required"
        )

        body = f"""
A package has been delivered!

DELIVERY DETAILS:
• From: {visitor.visitor_name or 'Unknown sender'}
• Company: {visitor.visitor_company or 'Unknown'}
• Time: {datetime.now().strftime('%I:%M %p')}
• Signature Required: {signature_req}

Additional Notes: {visitor.notes or 'None'}

Please retrieve your package from the reception area.

Best regards,
{self.office_name} AI Receptionist
"""

        return self._send_email(recipient_email, subject, body)

    def notify_inquiry(self, recipient_email: str, visitor: VisitorState) -> bool:
        """
        Send general inquiry notification.

        Args:
            recipient_email: Email address to notify
            visitor: Visitor state with details

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email notifications disabled")
            return False

        subject = f"General Inquiry at {self.office_name}"

        body = f"""
An office inquiry has been received.

VISITOR DETAILS:
• Name: {visitor.visitor_name or 'Not provided'}
• Company: {visitor.visitor_company or 'Not provided'}
• Time: {datetime.now().strftime('%I:%M %p')}

Inquiry Notes: {visitor.notes or 'No specific details recorded'}

Please follow up if needed.

Best regards,
{self.office_name} AI Receptionist
"""

        return self._send_email(recipient_email, subject, body)

    def _send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send an email via SMTP with TLS.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            logger.info(f"Sending email to {to} - {subject}")

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = to

            # Add plain text part
            msg.attach(MIMEText(body, "plain"))

            # Add HTML part for better formatting
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        {body.replace(chr(10), '<br>')}
                    </div>
                </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check credentials")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
