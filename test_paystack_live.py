import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from django.conf import settings

def test_paystack():
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key or secret_key == 'your_paystack_secret_key':
        print("ERROR: Paystack secret key not properly set in settings.")
        return

    print("Testing Paystack integration with provided Secret Key...")
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json"
    }
    data = {
        "email": "testuser@futb.edu.ng",
        "amount": 100000, # 1000 NGN
        "reference": "TEST-LIVE-12345"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get('status'):
                print("SUCCESS: Connected to Paystack!")
                print("Authorization URL:", res_data['data']['authorization_url'])
                print("Access Code:", res_data['data']['access_code'])
                print("Reference:", res_data['data']['reference'])
            else:
                print("Failed to initialize transaction:", res_data)
        else:
            print(f"FAILED: HTTP {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == '__main__':
    test_paystack()
