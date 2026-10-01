import logging
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from .models import (
  Event, Ticket, Notification, User
)

logger = logging.getLogger(__name__)

def send_event_reminders():
  """
  Check all three reminder windows and 
  send notifications to registered students.
  This function is designed to be called 
  every 5 minutes automatically.
  """
  
  now = timezone.now()
  logger.info(
    f"[REMINDERS] Running at {now}"
  )
  print(
    f"[REMINDERS] Running at {now}"
  )
  
  total_sent = 0
  
  # Define the three reminder windows
  # Each window has a centre point and 
  # a ±5 minute tolerance
  windows = [
    {
      'label': '24-hour',
      'centre': now + timedelta(hours=24),
      'tolerance': timedelta(minutes=5),
    },
    {
      'label': '2-hour',
      'centre': now + timedelta(hours=2),
      'tolerance': timedelta(minutes=5),
    },
    {
      'label': '30-minute',
      'centre': now + timedelta(minutes=30),
      'tolerance': timedelta(minutes=5),
    },
  ]
  
  for window in windows:
    window_start = (
      window['centre'] - window['tolerance']
    )
    window_end = (
      window['centre'] + window['tolerance']
    )
    
    # Find events in this window
    events_in_window = Event.objects.filter(
      date_time__gte=window_start,
      date_time__lte=window_end,
      status='published',
    )
    
    if not events_in_window.exists():
      print(
        f"[REMINDERS] {window['label']} "
        f"window: no events found"
      )
      continue
    
    print(
      f"[REMINDERS] {window['label']} "
      f"window: {events_in_window.count()} "
      f"event(s) found"
    )
    
    for event in events_in_window:
      
      # Get all students with active 
      # tickets for this event
      tickets = Ticket.objects.filter(
        event=event,
        status__in=['active', 'used']
      ).select_related('user')
      
      if not tickets.exists():
        print(
          f"[REMINDERS]   {event.title}: "
          f"no registered students"
        )
        continue
      
      print(
        f"[REMINDERS]   {event.title}: "
        f"sending to {tickets.count()} "
        f"student(s)"
      )
      
      for ticket in tickets:
        student = ticket.user
        
        # Map window label to reminder_type
        reminder_type_map = {
          '24-hour': '24h',
          '2-hour': '2h', 
          '30-minute': '30m',
        }
        reminder_type = reminder_type_map.get(
          window['label'], 'general'
        )
        
        # Try to create a notification record
        # If it already exists (unique_together constraint), get_or_create returns 
        # created=False and we skip sending
        notification, created = Notification.objects.get_or_create(
          user=student,
          event=event,
          reminder_type=reminder_type,
          defaults={
            'type': 'email',
            'message': (
              f"{window['label'].title()} "
              f"reminder: {event.title}"
            ),
            'scheduled_time': window['centre'],
            'sent_at': timezone.now(),
            'status': 'pending',
          }
        )
        
        if not created:
          print(
            f"[REMINDERS]     SKIPPING "
            f"{student.email} — "
            f"{reminder_type} reminder "
            f"already sent for "
            f"{event.title}"
          )
          continue
        
        # Record is new — proceed with sending
        push_sent = False
        email_sent = False
        
        # Send FCM push notification
        if student.fcm_token:
          try:
            from .firebase import send_push_notification
            push_sent = send_push_notification(
              fcm_token=student.fcm_token,
              title=(
                f"⏰ {window['label'].title()} Reminder"
              ),
              body=(
                f"{event.title} starts in "
                f"{window['label']}! "
                f"Check your QR ticket."
              ),
            )
          except Exception as e:
            print(
              f"[REMINDERS]     FCM FAILED for {student.email}: {e}"
            )
        
        # Send email reminder
        try:
          from .email_utils import send_event_reminder_email
          email_sent = send_event_reminder_email(
            user_email=student.email,
            user_full_name=(
              student.get_full_name() or student.email.split('@')[0]
            ),
            event_title=event.title,
            event_date_time=event.date_time,
            event_venue=event.venue,
            minutes_before=(
              24 * 60 if '24' in window['label']
              else 120 if '2-hour' in window['label']
              else 30
            ),
          )
          if email_sent:
            print(
              f"[REMINDERS]     Email sent to {student.email}"
            )
          else:
            print(
              f"[REMINDERS]     Email FAILED for {student.email}"
            )
        except Exception as e:
          print(
            f"[REMINDERS]     Email FAILED for {student.email}: {e}"
          )
        
        # Update notification record with actual result
        if email_sent or push_sent:
          notification.type = (
            'both' if (email_sent and push_sent)
            else 'push' if push_sent
            else 'email'
          )
          notification.status = 'sent'
          notification.sent_at = timezone.now()
          notification.save()
          total_sent += 1
          print(
            f"[REMINDERS]     Notification record saved (ID: {notification.id})"
          )
        else:
          # Both failed — delete the record so it can be retried next run
          notification.delete()
          print(
            f"[REMINDERS]     All delivery methods failed for {student.email} — will retry next run"
          )
  
  print(
    f"[REMINDERS] Complete. Total sent: {total_sent}"
  )
  logger.info(
    f"[REMINDERS] Complete. Total sent: {total_sent}"
  )
  return total_sent
