import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from rest_framework.test import APIClient

from core.models import User

def test_reminder_trigger():
    client = APIClient()
    
    # Create test admin user
    email = "admin_test@futb.edu.ng"
    user, _ = User.objects.get_or_create(email=email, defaults={
        'username': email,
        'first_name': 'Admin',
        'last_name': 'Test',
        'role': 'admin', # must be admin
        'is_staff': True
    })
    
    # Authenticate
    client.force_authenticate(user=user)
    
    # Trigger reminder POST
    response = client.post('/api/notifications/test-reminder/', format='json')
    
    if response.status_code == 200:
        print("SUCCESS: Test reminder triggered via API successfully.")
        print("Response detail:", response.data.get('detail'))
    else:
        print(f"FAILED: Expected 200, got {response.status_code}")
        print(response.data)

if __name__ == '__main__':
    print("Running Sprint 4 Part C Verification...")
    test_reminder_trigger()
