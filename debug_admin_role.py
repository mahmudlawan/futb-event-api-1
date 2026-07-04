import os
import django

# Clear bad OS env if present
if os.environ.get('EMAIL_HOST_PASSWORD') and ' ' in os.environ.get('EMAIL_HOST_PASSWORD', ''):
    del os.environ['EMAIL_HOST_PASSWORD']

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from rest_framework.test import APIClient
from core.models import User

client = APIClient()

# Check the user in DB
user = User.objects.get(email='abutturab236900@gmail.com')
print(f"DB role: {user.role}")
print(f"DB is_staff: {user.is_staff}")
print()

# Simulate JWT login (same as Postman POST /api/auth/login/)
login_response = client.post('/api/auth/login/', {
    'email': 'abutturab236900@gmail.com',
    'password': 'Mah@236900'  # Replace with actual password if different
}, format='json')

print(f"Login status: {login_response.status_code}")
if login_response.status_code == 200:
    data = login_response.data
    print(f"Login response role: {data.get('role')}")
    print(f"Login response full_name: {data.get('full_name')}")
    
    # Now use the access token to hit test-reminder
    access_token = data.get('access')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    reminder_response = client.post('/api/notifications/test-reminder/', format='json')
    print(f"\nTest-reminder status: {reminder_response.status_code}")
    print(f"Test-reminder response: {reminder_response.data}")
else:
    print(f"Login failed: {login_response.data}")
    print("NOTE: If login fails, the password in this script may be wrong.")
    print("Trying with force_authenticate instead...")
    
    client.force_authenticate(user=user)
    reminder_response = client.post('/api/notifications/test-reminder/', format='json')
    print(f"\nTest-reminder status (force_auth): {reminder_response.status_code}")
    print(f"Test-reminder response: {reminder_response.data}")
