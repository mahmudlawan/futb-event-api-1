import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from rest_framework.test import APIClient

from core.models import User

def test_fcm_token_update():
    client = APIClient()
    
    # Create test user
    email = "fcm_test@futb.edu.ng"
    user, _ = User.objects.get_or_create(email=email, defaults={
        'username': email,
        'first_name': 'FCM',
        'last_name': 'Test'
    })
    
    # Authenticate
    client.force_authenticate(user=user)
    
    # Patch token
    response = client.patch('/api/auth/fcm-token/', {'fcm_token': 'test_firebase_token_123'}, format='json')
    
    if response.status_code == 200:
        print("SUCCESS: FCM token updated successfully via API.")
        
        # Verify in DB
        user.refresh_from_db()
        if user.fcm_token == 'test_firebase_token_123':
            print("VERIFIED: Token saved in DB correctly.")
        else:
            print("FAILED: Token not saved in DB correctly.")
    else:
        print(f"FAILED: Expected 200, got {response.status_code}")
        print(response.data)

if __name__ == '__main__':
    print("Running Sprint 4 Verification...")
    test_fcm_token_update()
