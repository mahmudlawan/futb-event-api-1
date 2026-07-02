import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_event_reminder_email(user_email, user_full_name, event_title, event_date_time, event_venue, minutes_before):
    """
    Sends a well-formatted plain-text reminder email to the user about an upcoming event.
    """
    subject = f"Reminder: {event_title} starts in {minutes_before} minutes"
    
    # If it's more than 60 minutes, display it in hours if appropriate (e.g., 2 hours).
    time_display = f"{minutes_before} minutes"
    if minutes_before >= 60 and minutes_before % 60 == 0:
        time_display = f"{minutes_before // 60} hours"
    
    subject = f"Reminder: {event_title} starts in {time_display}"
    
    body = f"""Hi {user_full_name},

This is a quick reminder that you have an upcoming event!

Event Details:
- Title: {event_title}
- Date & Time: {event_date_time.strftime('%B %d, %Y at %I:%M %p')}
- Venue: {event_venue}

The event starts in {time_display}. We look forward to seeing you there!

Best regards,
Smart Campus Event Team
"""

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info(f"Successfully sent reminder email for '{event_title}' to {user_email}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send reminder email to {user_email}: {e}")
        return False
