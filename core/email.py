"""Email notifications via Resend."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.config import settings

if TYPE_CHECKING:
    from db.models import Booking, Trip

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, html: str) -> None:
    """Send an email via Resend. Silently skips if not configured."""
    if not settings.resend_api_key:
        logger.debug("Resend not configured — skipping email to %s", to)
        return

    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s: %s", to, subject)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)


def _base_html(content: str) -> str:
    """Wrap content in a branded email template."""
    return f"""
    <div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 24px; background: #FBF7F0;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="font-family: 'Cormorant Garamond', Georgia, serif; color: #1B2A4A; font-size: 28px; margin: 0;">
          Concierge
        </h1>
      </div>
      <div style="background: white; border-radius: 12px; padding: 32px; border: 1px solid rgba(201, 150, 59, 0.2);">
        {content}
      </div>
      <div style="text-align: center; margin-top: 24px;">
        <p style="color: #64748b; font-size: 12px; margin: 0;">
          Concierge &mdash; AI travel assistant, built with care.
        </p>
      </div>
    </div>
    """


def send_booking_confirmation(to: str, booking: "Booking", trip: "Trip") -> None:
    """Send a booking confirmation email."""
    details = booking.details or {}
    name = details.get("name", details.get("hotel_name", f"{booking.domain.capitalize()} booking"))
    ref = booking.booking_reference or "Pending"

    content = f"""
    <h2 style="color: #1B2A4A; font-size: 20px; margin: 0 0 16px;">Booking Confirmed</h2>
    <p style="color: #334155; font-size: 14px; line-height: 1.6; margin: 0 0 16px;">
      Your {booking.domain} booking has been confirmed.
    </p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr>
        <td style="padding: 8px 0; color: #64748b; font-size: 13px;">Item</td>
        <td style="padding: 8px 0; color: #1B2A4A; font-size: 13px; text-align: right;">{name}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #64748b; font-size: 13px;">Provider</td>
        <td style="padding: 8px 0; color: #1B2A4A; font-size: 13px; text-align: right;">{booking.provider}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #64748b; font-size: 13px;">Reference</td>
        <td style="padding: 8px 0; color: #1B2A4A; font-size: 13px; text-align: right;">{ref}</td>
      </tr>
      <tr style="border-top: 1px solid #e2e8f0;">
        <td style="padding: 12px 0 0; color: #64748b; font-size: 13px; font-weight: 600;">Amount</td>
        <td style="padding: 12px 0 0; color: #1B2A4A; font-size: 16px; text-align: right; font-weight: 600;">${booking.amount:.2f}</td>
      </tr>
    </table>
    <div style="text-align: center; margin-top: 24px;">
      <a href="{settings.frontend_url}/trips/{trip.id}"
         style="display: inline-block; padding: 12px 24px; background: #1B2A4A; color: #FBF7F0; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 500;">
        View Trip
      </a>
    </div>
    """
    _send(to, f"Booking Confirmed: {name}", _base_html(content))


def send_trip_summary(to: str, trip: "Trip", bookings: list["Booking"]) -> None:
    """Send a trip summary email after all bookings complete."""
    total = sum(b.amount for b in bookings)
    booking_rows = ""
    for b in bookings:
        details = b.details or {}
        name = details.get("name", details.get("hotel_name", b.domain.capitalize()))
        booking_rows += f"""
        <tr>
          <td style="padding: 8px 0; color: #1B2A4A; font-size: 13px;">{name}</td>
          <td style="padding: 8px 0; color: #64748b; font-size: 13px; text-align: center;">{b.provider}</td>
          <td style="padding: 8px 0; color: #1B2A4A; font-size: 13px; text-align: right;">${b.amount:.2f}</td>
        </tr>
        """

    content = f"""
    <h2 style="color: #1B2A4A; font-size: 20px; margin: 0 0 8px;">Trip Booked Successfully</h2>
    <p style="color: #C9963B; font-size: 13px; margin: 0 0 16px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">
      {trip.goal}
    </p>
    <p style="color: #334155; font-size: 14px; line-height: 1.6; margin: 0 0 16px;">
      All your reservations have been confirmed. Here&rsquo;s a summary:
    </p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #e2e8f0;">
        <th style="padding: 8px 0; color: #64748b; font-size: 12px; text-align: left; text-transform: uppercase;">Item</th>
        <th style="padding: 8px 0; color: #64748b; font-size: 12px; text-align: center; text-transform: uppercase;">Provider</th>
        <th style="padding: 8px 0; color: #64748b; font-size: 12px; text-align: right; text-transform: uppercase;">Cost</th>
      </tr>
      {booking_rows}
      <tr style="border-top: 2px solid #e2e8f0;">
        <td colspan="2" style="padding: 12px 0 0; color: #1B2A4A; font-size: 14px; font-weight: 600;">Total</td>
        <td style="padding: 12px 0 0; color: #1B2A4A; font-size: 16px; text-align: right; font-weight: 600;">${total:.2f}</td>
      </tr>
    </table>
    <div style="text-align: center; margin-top: 24px;">
      <a href="{settings.frontend_url}/trips/{trip.id}"
         style="display: inline-block; padding: 12px 24px; background: #1B2A4A; color: #FBF7F0; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 500;">
        View Full Itinerary
      </a>
    </div>
    """
    _send(to, f"Trip Confirmed: {trip.goal}", _base_html(content))


def send_cancellation_confirmation(to: str, booking: "Booking", refund_amount: float) -> None:
    """Send a cancellation confirmation email."""
    details = booking.details or {}
    name = details.get("name", details.get("hotel_name", f"{booking.domain.capitalize()} booking"))
    ref = booking.booking_reference or ""

    content = f"""
    <h2 style="color: #1B2A4A; font-size: 20px; margin: 0 0 16px;">Booking Cancelled</h2>
    <p style="color: #334155; font-size: 14px; line-height: 1.6; margin: 0 0 16px;">
      Your {booking.domain} booking has been cancelled.
    </p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr>
        <td style="padding: 8px 0; color: #64748b; font-size: 13px;">Item</td>
        <td style="padding: 8px 0; color: #1B2A4A; font-size: 13px; text-align: right;">{name}</td>
      </tr>
      {"<tr><td style='padding: 8px 0; color: #64748b; font-size: 13px;'>Reference</td><td style='padding: 8px 0; color: #1B2A4A; font-size: 13px; text-align: right;'>" + ref + "</td></tr>" if ref else ""}
      <tr style="border-top: 1px solid #e2e8f0;">
        <td style="padding: 12px 0 0; color: #64748b; font-size: 13px; font-weight: 600;">Refund Amount</td>
        <td style="padding: 12px 0 0; color: #1a7a4c; font-size: 16px; text-align: right; font-weight: 600;">${refund_amount:.2f}</td>
      </tr>
    </table>
    <p style="color: #64748b; font-size: 12px; margin-top: 16px;">
      Refunds typically take 5-10 business days to appear on your statement.
    </p>
    """
    _send(to, f"Booking Cancelled: {name}", _base_html(content))
