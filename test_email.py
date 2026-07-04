import os
import django

# Clear the bad OS env variable if still present in this process
if os.environ.get('EMAIL_HOST_PASSWORD') and ' ' in os.environ.get('EMAIL_HOST_PASSWORD', ''):
    del os.environ['EMAIL_HOST_PASSWORD']

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail

pwd = settings.EMAIL_HOST_PASSWORD
print(f"Password length: {len(pwd)}")
print(f"Has spaces: {' ' in pwd}")
print(f"Password value: {repr(pwd)}")
print(f"Sending from: {settings.EMAIL_HOST_USER}")
print()

# Try sending a test email
print("Sending test email...")
try:
    send_mail(
        subject="FUTB Smart Campus – Email Test",
        message="This is a test email from the FUTB Smart Campus notification engine. If you received this, SMTP is working correctly.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.EMAIL_HOST_USER],
        fail_silently=False,
    )
    print("SUCCESS: Test email sent! Check your inbox.")
except Exception as e:
    print(f"FAILED: {e}")
