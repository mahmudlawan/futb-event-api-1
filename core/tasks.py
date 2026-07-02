import logging
from datetime import timedelta
from django.utils import timezone
from core.models import Event, Notification
from core.firebase import send_push_notification
from core.email_utils import send_event_reminder_email

logger = logging.getLogger(__name__)

def send_event_reminders():
    """
    Finds upcoming events in specific windows (24h, 2h, 30m before) and sends
    reminders to users with active tickets.
    """
    now = timezone.now()
    windows = [
        {"minutes": 24 * 60, "name": "24 hours"},
        {"minutes": 2 * 60, "name": "2 hours"},
        {"minutes": 30, "name": "30 minutes"}
    ]
    
    logger.info("Starting send_event_reminders task...")

    for window in windows:
        minutes = window["minutes"]
        target_time = now + timedelta(minutes=minutes)
        # 5 minute tolerance
        start_time = target_time - timedelta(minutes=5)
        end_time = target_time + timedelta(minutes=5)

        events = Event.objects.filter(
            date_time__gte=start_time,
            date_time__lt=end_time,
            status='upcoming'
        )

        for event in events:
            # Find all active tickets for this event
            active_tickets = event.tickets.filter(status='active').select_related('user')
            
            for ticket in active_tickets:
                user = ticket.user
                event_title = event.title
                
                # Check if we already sent a reminder for this specific window/event to avoid duplicates
                # We can check if a notification exists within the last 15 mins or so, but let's 
                # just send it and rely on cron scheduling (run every 5 mins).
                # Actually, to prevent spam if the cron runs twice in 5 mins:
                recent_notification = Notification.objects.filter(
                    user=user, 
                    event=event,
                    type='email',
                    sent_at__gte=now - timedelta(minutes=10)
                ).exists()
                
                if recent_notification:
                    continue

                full_name = user.get_full_name() or user.username
                
                # 1. Send Email Reminder
                email_success = send_event_reminder_email(
                    user_email=user.email,
                    user_full_name=full_name,
                    event_title=event_title,
                    event_date_time=event.date_time,
                    event_venue=event.venue,
                    minutes_before=minutes
                )
                
                Notification.objects.create(
                    user=user,
                    event=event,
                    type='email',
                    message=f"Reminder: {event_title} starts in {window['name']}",
                    sent_at=now if email_success else None,
                    status='sent' if email_success else 'failed'
                )

                # 2. Send Push Notification (if token exists)
                if user.fcm_token:
                    push_title = f"Upcoming Event: {event_title}"
                    push_body = f"Starts in {window['name']} at {event.venue}"
                    
                    push_success = send_push_notification(
                        fcm_token=user.fcm_token,
                        title=push_title,
                        body=push_body
                    )
                    
                    Notification.objects.create(
                        user=user,
                        event=event,
                        type='push',
                        message=push_body,
                        sent_at=now if push_success else None,
                        status='sent' if push_success else 'failed'
                    )
                
    logger.info("Completed send_event_reminders task.")
