from django.core.management.base import BaseCommand
from core.tasks import send_event_reminders

class Command(BaseCommand):
    help = 'Sends scheduled event reminders (Push & Email) to attendees'

    def handle(self, *args, **kwargs):
        self.stdout.write("Running scheduled event reminders...")
        try:
            send_event_reminders()
            self.stdout.write(self.style.SUCCESS("Successfully sent event reminders."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error running send_event_reminders: {e}"))
