# =============================================================================
# app/services/email_service.py — SendGrid Email Delivery Service
# =============================================================================
"""
Email delivery via the SendGrid free tier.

Responsible for sending the OTP login email.  The HTML template is
defined inline so the service is self-contained and easy to test.
"""

import logging
from typing import Optional

from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, HtmlContent

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Raised when email delivery fails."""


def send_otp_email(to_email: str, otp_code: str, couple_names: str) -> bool:
    """
    Send the OTP login code to a guest via a beautifully branded HTML email.

    The OTP code is never logged — only its masked form (``XXXXXX``) is
    written to logs.

    Args:
        to_email: Recipient email address.
        otp_code: The 6-digit plaintext OTP to include in the email.
                  **Never log this value.**
        couple_names: Couple's names string used in the email subject/body.

    Returns:
        True if the email was accepted by SendGrid (2xx status).

    Raises:
        EmailServiceError: If SendGrid returns an error or is misconfigured.
    """
    api_key = current_app.config.get("SENDGRID_API_KEY")
    from_email = current_app.config.get("SENDGRID_FROM_EMAIL")
    from_name = current_app.config.get("SENDGRID_FROM_NAME", couple_names)

    if not api_key:
        raise EmailServiceError("SENDGRID_API_KEY is not configured.")

    subject = f"Your login code for {couple_names}'s Wedding"

    html_content = _build_otp_html(otp_code=otp_code, couple_names=couple_names)

    message = Mail(
        from_email=(from_email, from_name),
        to_emails=to_email,
        subject=subject,
        html_content=HtmlContent(html_content),
    )

    try:
        sg = SendGridAPIClient(api_key=api_key)
        response = sg.send(message)
        status = response.status_code
        # Log without the OTP code
        logger.info(
            "OTP email sent to %s — SendGrid status %s (code masked)",
            to_email,
            status,
        )
        return 200 <= status < 300

    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        raise EmailServiceError(f"Failed to send email: {exc}") from exc


def _build_otp_html(otp_code: str, couple_names: str) -> str:
    """
    Build the branded HTML body for the OTP email.

    Args:
        otp_code: The 6-digit OTP to embed in the email.
        couple_names: Couple's names for personalisation.

    Returns:
        HTML string ready for use as the email body.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Your Login Code</title>
</head>
<body style="margin:0;padding:0;background:#0d0d0d;font-family:'Lato',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d0d;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#141414;border:1px solid #2a2a2a;border-radius:4px;overflow:hidden;">

          <!-- Header banner -->
          <tr>
            <td style="background:#c9a96e;padding:28px 40px;text-align:center;">
              <p style="margin:0;font-family:'Montserrat',Arial,sans-serif;
                        font-size:11px;letter-spacing:4px;text-transform:uppercase;
                        color:#0d0d0d;">You're Invited</p>
              <h1 style="margin:8px 0 0;font-family:'Georgia',serif;
                         font-size:28px;font-weight:400;color:#0d0d0d;">
                {couple_names}
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <p style="margin:0 0 16px;color:#b0b0b0;font-size:15px;line-height:1.7;">
                Someone (hopefully you!) requested a login code for the
                wedding website. Use the code below — it expires in
                <strong style="color:#ffffff;">10 minutes</strong>.
              </p>

              <!-- OTP Code Box -->
              <div style="background:#0d0d0d;border:1px solid #c9a96e;border-radius:4px;
                          text-align:center;padding:28px 20px;margin:28px 0;">
                <p style="margin:0 0 8px;font-family:'Montserrat',Arial,sans-serif;
                           font-size:10px;letter-spacing:3px;text-transform:uppercase;
                           color:#c9a96e;">Your Verification Code</p>
                <p style="margin:0;font-size:42px;font-weight:700;letter-spacing:12px;
                           color:#ffffff;font-family:'Montserrat',Arial,sans-serif;">
                  {otp_code}
                </p>
              </div>

              <p style="margin:0 0 16px;color:#666666;font-size:13px;line-height:1.7;">
                If you did not request this code, please ignore this email.
                For security, this code can only be used once.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="border-top:1px solid #2a2a2a;padding:20px 40px;text-align:center;">
              <p style="margin:0;color:#444444;font-size:12px;">
                Sent with love from {couple_names}'s wedding website.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
