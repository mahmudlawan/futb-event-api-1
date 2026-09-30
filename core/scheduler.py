from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
import logging
import atexit

logger = logging.getLogger(__name__)

_scheduler = None

def start_scheduler():
  """
  Start the APScheduler background 
  scheduler. Safe to call multiple 
  times — only starts once.
  """
  global _scheduler
  
  if _scheduler is not None:
    return
  
  print("[SCHEDULER] Starting background scheduler...")
  
  _scheduler = BackgroundScheduler(
    timezone='Africa/Lagos'
    # Nigerian timezone
    # Change to 'UTC' if preferred
  )
  
  # Import here to avoid circular imports
  from .tasks import send_event_reminders
  
  # Add the reminder job — runs 
  # every 5 minutes
  _scheduler.add_job(
    func=send_event_reminders,
    trigger=IntervalTrigger(minutes=5),
    id='send_reminders',
    name='Send Event Reminders',
    replace_existing=True,
    max_instances=1,
    # Prevent overlap if a run 
    # takes longer than 5 minutes
    misfire_grace_time=60,
    # If a run was missed by less 
    # than 60 seconds, still run it
  )
  
  _scheduler.start()
  
  print("[SCHEDULER] Started. Reminders will check every 5 minutes.")
  logger.info(
    "[SCHEDULER] Background scheduler started successfully."
  )
  
  # Gracefully shut down when Django stops
  atexit.register(lambda: 
    _scheduler.shutdown(wait=False) if (_scheduler is not None and _scheduler.running) else None
  )

def stop_scheduler():
  global _scheduler
  if _scheduler is not None:
    if _scheduler.running:
      _scheduler.shutdown(wait=False)
    _scheduler = None
    print("[SCHEDULER] Stopped.")
