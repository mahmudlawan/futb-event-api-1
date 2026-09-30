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
        
        # Skip if we already sent this 
        # reminder to this student 
        # for this event
        # Check by looking for existing 
        # notification in the same window
        already_sent = Notification.objects\
          .filter(
            user=student,
            event=event,
            scheduled_time__gte=window_start,
            scheduled_time__lte=window_end,
            status='sent',
          ).exists()
        
        if already_sent:
          print(
            f"[REMINDERS]     Skipping "
            f"{student.email} — already sent"
          )
          continue
        
        # Build reminder message
        time_label = window['label']
        event_time_str = event.date_time\
          .strftime('%A, %d %B %Y at %I:%M %p')
        
        subject = (
          f"Reminder: {event.title} "
          f"starts in {time_label}!"
        )
        
        message = f"""
Hello {student.first_name or student.email.split('@')[0]},

This is your {time_label} reminder for 
the following event:

EVENT:  {event.title}
DATE:   {event_time_str}
VENUE:  {event.venue}

Your QR ticket is ready in the 
FUTB Smart Campus app under 
"My Tickets". Please have it ready 
to scan at the entrance.

See you there!

FUTB Smart Campus Team
Federal University of Technology, Babura
        """.strip()
        
        # Track success/failure
        push_sent = False
        email_sent = False
        
        # Send push notification via FCM
        if student.fcm_token:
          try:
            from .firebase import \
              send_push_notification
            push_sent = send_push_notification(
              fcm_token=student.fcm_token,
              title=f"⏰ {time_label.title()} "
                f"Reminder",
              body=f"{event.title} starts "
                f"in {time_label}! "
                f"Check your QR ticket.",
            )
          except Exception as e:
            logger.error(
              f"FCM failed for "
              f"{student.email}: {e}"
            )
            print(
              f"[REMINDERS]     FCM FAILED "
              f"for {student.email}: {e}"
            )
        
        # Send email reminder
        try:
          send_mail(
            subject=subject,
            message=message,
            from_email=settings\
              .DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
          )
          email_sent = True
          print(
            f"[REMINDERS]     Email sent "
            f"to {student.email}"
          )
        except Exception as e:
          logger.error(
            f"Email failed for "
            f"{student.email}: {e}"
          )
          print(
            f"[REMINDERS]     Email FAILED "
            f"for {student.email}: {e}"
          )
        
        # Save notification record 
        # regardless of outcome
        if email_sent or push_sent:
          Notification.objects.create(
            user=student,
            event=event,
            type='push' if push_sent 
              else 'email',
            message=f"{time_label.title()} "
              f"reminder: {event.title} "
              f"starts in {time_label}.",
            scheduled_time=window['centre'],
            sent_at=timezone.now(),
            status='sent',
          )
          total_sent += 1
        else:
          # Record the failure
          Notification.objects.create(
            user=student,
            event=event,
            type='email',
            message=f"FAILED: {time_label} "
              f"reminder for {event.title}",
            scheduled_time=window['centre'],
            sent_at=timezone.now(),
            status='failed',
          )
  
  print(
    f"[REMINDERS] Complete. "
    f"Total sent: {total_sent}"
  )
  logger.info(
    f"[REMINDERS] Complete. "
    f"Total sent: {total_sent}"
  )
  return total_sent
